"""Catalog constraints, failure isolation, restart, and active-only retrieval."""

import sqlite3

import pytest

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import publish_index, query_active
from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.vector_store import QdrantVectorStore


class Model:
    def __init__(self, *args, **kwargs):
        self.passages = []

    def embed_passages(self, texts):
        self.passages.extend(texts)
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def publish(catalog, tmp_path, revision="v1", model=None, **overrides):
    args = dict(
        document_id="act",
        title="Act",
        source_path=tmp_path / "original.pdf",
        chunks=[Chunk(0, revision, "act.pdf", 1)],
        configuration={
            "corpus_sha256": revision,
            "model": "test",
            "revision": "pinned",
            "dimension": 2,
        },
        store_path=tmp_path / "vectors",
        model=model or Model(),
    )
    args.update(overrides)
    return publish_index(catalog, **args)


def test_reindex_is_idempotent_and_queries_work_without_source_after_restart(tmp_path):
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        model = Model()
        first = publish(catalog, tmp_path, model=model)
        second = publish(catalog, tmp_path, model=model)
        assert first["index_id"] == second["index_id"]
        assert first["embedded_passages"] == 1
        assert second["embedded_passages"] == 0
        assert model.passages == ["v1"]
        history = catalog.history("act")
        assert len({row["version_id"] for row in history}) == 1
        assert [row["active"] for row in history] == [0, 1]

    class QueryOnly(Model):
        def __init__(self, model, **kwargs):
            assert model == "test"
            assert kwargs == {"revision": "pinned", "local_files_only": True}

        def embed_passages(self, texts):
            raise AssertionError("No passage embeddings allowed")

    assert not (tmp_path / "original.pdf").exists()
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        result = query_active(catalog, "act", "Question?", model_factory=QueryOnly)
        assert result["results"][0]["chunk"]["text"] == "v1"
        assert result["content_hash"] == "v1"


def test_partial_failure_preserves_old_version_and_retry_activates_new(tmp_path):
    class Failing(Model):
        def embed_passages(self, texts):
            if texts == ["second"]:
                raise RuntimeError("Model failure")
            return super().embed_passages(texts)

    new_chunks = [Chunk(0, "new", "act.pdf", 1), Chunk(1, "second", "act.pdf", 1)]
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        publish(catalog, tmp_path)
        with pytest.raises(RuntimeError, match="Model failure"):
            publish(catalog, tmp_path, "v2", Failing(), chunks=new_chunks, batch_size=1)
        assert catalog.active_index("act")["content_hash"] == "v1"
        assert catalog.failed_runs()[0]["error"] == "Model failure"
        result = query_active(catalog, "act", "Question?", model_factory=Model)
        assert [r["chunk"]["text"] for r in result["results"]] == ["v1"]
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        model = Model()
        assert (
            publish(catalog, tmp_path, "v2", model, chunks=new_chunks)[
                "embedded_passages"
            ]
            == 1
        )
        assert model.passages == ["second"]
        assert catalog.active_index("act")["content_hash"] == "v2"
        result = query_active(catalog, "act", "Question?", model_factory=Model)
        assert {r["chunk"]["text"] for r in result["results"]} == {"new", "second"}
        assert len(catalog.history("act")) == 3


def test_activation_transaction_rolls_back_if_second_update_fails(tmp_path):
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        publish(catalog, tmp_path)
        catalog.connection.executescript("""
            CREATE TRIGGER reject_new_activation BEFORE UPDATE ON indexing_runs
            WHEN NEW.active = 1 AND NEW.id > 1
            BEGIN SELECT RAISE(ABORT, 'simulated activation failure'); END;
        """)
        with pytest.raises(sqlite3.IntegrityError, match="simulated"):
            publish(catalog, tmp_path, "v2")
        assert catalog.active_index("act")["content_hash"] == "v1"
        assert catalog.history("act")[-1]["status"] == "failed"


def test_sql_constraints_and_parameterized_document_names(tmp_path):
    identifier = "act'; DROP TABLE documents; --"
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        publish(catalog, tmp_path, document_id=identifier)
        assert catalog.active_index(identifier)["title"] == "Act"
        publish(catalog, tmp_path, "v2", document_id=identifier)
        with pytest.raises(sqlite3.IntegrityError):
            with catalog.connection:
                catalog.connection.execute(
                    "UPDATE indexing_runs SET active = 1 WHERE id = 1"
                )
        with pytest.raises(sqlite3.IntegrityError):
            with catalog.connection:
                catalog.connection.execute(
                    "UPDATE indexing_runs SET version_id = 999 WHERE id = 1"
                )
        with pytest.raises(ValueError, match="No active"):
            catalog.active_index("unknown")


def test_failed_initial_index_never_becomes_queryable(tmp_path):
    class Failing(Model):
        def embed_passages(self, texts):
            raise RuntimeError("Failure")

    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        with pytest.raises(RuntimeError):
            publish(catalog, tmp_path, model=Failing())
        with pytest.raises(ValueError, match="No active"):
            query_active(catalog, "act", "Question?", model_factory=Model)
        failed = catalog.failed_runs()[0]
        with pytest.raises(ValueError, match="preparing"):
            catalog.activate(failed["id"])


def test_missing_active_collection_fails_without_loading_model(tmp_path):
    with DocumentCatalog(tmp_path / "catalog.sqlite3") as catalog:
        publish(catalog, tmp_path)
        active = catalog.active_index("act")
        with QdrantVectorStore(
            tmp_path / "vectors", active["collection_name"], dimension=2
        ) as store:
            store.client.delete_collection(store.collection)

        def unavailable(*args, **kwargs):
            raise AssertionError("Model should not load for a missing index")

        with pytest.raises(ValueError, match="missing"):
            query_active(catalog, "act", "Question?", model_factory=unavailable)
