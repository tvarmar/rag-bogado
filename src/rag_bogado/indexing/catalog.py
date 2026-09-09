"""SQLite document history and atomic activation of complete vector indexes."""

import json
import sqlite3
from pathlib import Path


class DocumentCatalog:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY CHECK(length(trim(id)) > 0),
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id),
                content_hash TEXT NOT NULL,
                source_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, content_hash),
                UNIQUE(id, document_id)
            );
            CREATE TABLE IF NOT EXISTS indexing_runs (
                id INTEGER PRIMARY KEY,
                document_id TEXT NOT NULL,
                version_id INTEGER NOT NULL,
                index_id TEXT NOT NULL,
                collection_name TEXT NOT NULL,
                store_path TEXT NOT NULL,
                configuration TEXT NOT NULL,
                expected_chunks INTEGER NOT NULL CHECK(expected_chunks > 0),
                status TEXT NOT NULL DEFAULT 'preparing'
                    CHECK(status IN ('preparing', 'ready', 'failed')),
                active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0, 1)),
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                FOREIGN KEY(version_id, document_id)
                    REFERENCES document_versions(id, document_id),
                CHECK(active = 0 OR status = 'ready')
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_index_per_document
                ON indexing_runs(document_id) WHERE active = 1;
            CREATE INDEX IF NOT EXISTS runs_by_status ON indexing_runs(status);
            CREATE INDEX IF NOT EXISTS runs_by_version ON indexing_runs(version_id);
        """)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "DocumentCatalog":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def start_run(
        self,
        *,
        document_id: str,
        title: str,
        content_hash: str,
        source_path: Path,
        index_id: str,
        collection: str,
        store_path: Path,
        configuration: dict,
        expected_chunks: int,
    ) -> int:
        """Register one version idempotently and a distinct attempt for each run."""
        if expected_chunks <= 0:
            raise ValueError("Cannot activate an empty document")
        if not document_id.strip() or not content_hash.strip() or not index_id.strip():
            raise ValueError("Document, content and index identities cannot be blank")
        encoded = json.dumps(configuration, sort_keys=True, allow_nan=False)
        with self.connection:
            self.connection.execute(
                "INSERT INTO documents(id, title) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET title = excluded.title",
                (document_id, title),
            )
            self.connection.execute(
                "INSERT INTO document_versions(document_id, content_hash, source_path) "
                "VALUES (?, ?, ?) ON CONFLICT(document_id, content_hash) DO NOTHING",
                (document_id, content_hash, str(source_path.resolve())),
            )
            version = self.connection.execute(
                "SELECT id FROM document_versions "
                "WHERE document_id = ? AND content_hash = ?",
                (document_id, content_hash),
            ).fetchone()["id"]
            cursor = self.connection.execute(
                "INSERT INTO indexing_runs(document_id, version_id, index_id, "
                "collection_name, store_path, configuration, expected_chunks) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    version,
                    index_id,
                    collection,
                    str(store_path.resolve()),
                    encoded,
                    expected_chunks,
                ),
            )
            return cursor.lastrowid

    def activate(self, run_id: int) -> None:
        """Switch the active run atomically, after the coordinator verified Qdrant."""
        with self.connection:
            # Acquire the write lock before reading state for the transition.
            self.connection.execute("BEGIN IMMEDIATE")
            run = self.connection.execute(
                "SELECT document_id, status FROM indexing_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None or run["status"] != "preparing":
                raise ValueError("Only a preparing run can be activated")
            self.connection.execute(
                "UPDATE indexing_runs SET active = 0 "
                "WHERE document_id = ? AND active = 1",
                (run["document_id"],),
            )
            self.connection.execute(
                "UPDATE indexing_runs SET status = 'ready', active = 1, "
                "finished_at = CURRENT_TIMESTAMP WHERE id = ?",
                (run_id,),
            )

    def fail(self, run_id: int, error: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE indexing_runs SET status = 'failed', error = ?, "
                "finished_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'preparing'",
                (error, run_id),
            )

    def active_index(self, document_id: str) -> dict:
        row = self.connection.execute(
            "SELECT r.*, v.content_hash, v.source_path, d.title "
            "FROM indexing_runs r JOIN document_versions v ON v.id = r.version_id "
            "JOIN documents d ON d.id = r.document_id "
            "WHERE r.document_id = ? AND r.active = 1 AND r.status = 'ready'",
            (document_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"No active index for document {document_id!r}")
        result = dict(row)
        result["configuration"] = json.loads(result["configuration"])
        return result

    def history(self, document_id: str) -> list[dict]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT r.id, r.version_id, v.content_hash, r.index_id, r.status, "
                "r.active, r.error, r.created_at, r.finished_at "
                "FROM indexing_runs r JOIN document_versions v ON v.id = r.version_id "
                "WHERE r.document_id = ? ORDER BY r.id",
                (document_id,),
            )
        ]

    def failed_runs(self) -> list[dict]:
        return [
            dict(row)
            for row in self.connection.execute(
                "SELECT r.id, d.id AS document_id, d.title, v.content_hash, r.error "
                "FROM indexing_runs r JOIN document_versions v ON v.id = r.version_id "
                "JOIN documents d ON d.id = r.document_id "
                "WHERE r.status = 'failed' ORDER BY r.id"
            )
        ]
