"""Service for synchronizing regulatory documents from the official BOE API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.configuration import index_configuration
from rag_bogado.indexing.service import publish_index
from rag_bogado.ingestion.boe import (
    BoeClient,
    BoeDocumentMetadata,
    BoeError,
    compute_content_hash,
)
from rag_bogado.ingestion.xml_loader import load_xml_chunks
from rag_bogado.retrieval.embeddings import EmbeddingModel


@dataclass(frozen=True)
class BoeSyncResult:
    """Result of an automated or manual sync operation for a single document."""

    action: str  # 'skipped_up_to_date', 'metadata_updated', 'reindexed', 'failed'
    document_id: str
    metadata: BoeDocumentMetadata | None = None
    content_hash: str | None = None
    run_id: int | None = None
    error: str | None = None


class BoeSyncService:
    """Orchestrates metadata checks, hash verification and atomic reindexing."""

    def __init__(
        self,
        catalog: DocumentCatalog,
        boe_client: BoeClient,
        model: EmbeddingModel | object,
        *,
        raw_dir: Path | str = Path("data/raw"),
        store_path: Path | str | None = None,
        chunk_size: int = 800,
        overlap: int = 120,
        dimension: int = 384,
        model_name: str = "intfloat/multilingual-e5-small",
        revision: str = "e4ce9877abf4ed59fe848b943265004db73919e1",
    ) -> None:
        self.catalog = catalog
        self.boe_client = boe_client
        self.model = model
        self.raw_dir = Path(raw_dir)
        self.store_path = store_path
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.dimension = dimension
        self.model_name = model_name
        self.revision = revision

    def sync_document(self, document_id: str) -> BoeSyncResult:
        """Check official metadata and atomically reindex only if content changed."""
        doc_id = document_id.strip()
        if not doc_id:
            raise ValueError("Document identifier cannot be blank")

        now_utc = datetime.now(timezone.utc).isoformat()

        # Step 1: Consult official metadata
        try:
            meta = self.boe_client.get_metadata(doc_id)
        except (BoeError, Exception) as exc:
            self.catalog.record_sync_error(doc_id, str(exc), now_utc)
            return BoeSyncResult(
                action="failed",
                document_id=doc_id,
                error=f"Metadata fetch failed: {exc}",
            )

        has_active = self.catalog.has_active_index(doc_id)

        # Step 2: If registry update date unchanged and index active, skip download
        if has_active:
            active_info = self.catalog.active_index(doc_id)
            sync_meta = self.catalog.get_sync_metadata(doc_id)
            if (
                sync_meta
                and sync_meta.get("last_updated") == meta.fecha_actualizacion
                and sync_meta.get("content_hash") == active_info.get("content_hash")
            ):
                self.catalog.record_sync_metadata(
                    document_id=doc_id,
                    source=meta.source,
                    official_id=meta.official_id,
                    title=meta.title,
                    source_url=meta.source_url,
                    url_eli=meta.url_eli,
                    last_updated=meta.fecha_actualizacion,
                    estado_consolidacion=meta.estado_consolidacion,
                    estado_consolidacion_codigo=meta.estado_consolidacion_codigo,
                    fecha_publicacion=meta.fecha_publicacion,
                    fecha_vigencia=meta.fecha_vigencia,
                    vigencia_agotada=meta.vigencia_agotada,
                    content_hash=active_info["content_hash"],
                    last_checked_at=now_utc,
                    downloaded_at=sync_meta.get("downloaded_at"),
                    sync_status="synced",
                )
                return BoeSyncResult(
                    action="skipped_up_to_date",
                    document_id=doc_id,
                    metadata=meta,
                    content_hash=active_info["content_hash"],
                )

        # Step 3: Download official XML text
        try:
            xml_content = self.boe_client.download_xml(doc_id)
        except (BoeError, Exception) as exc:
            self.catalog.record_sync_error(doc_id, str(exc), now_utc)
            return BoeSyncResult(
                action="failed",
                document_id=doc_id,
                metadata=meta,
                error=f"Download failed: {exc}",
            )

        # Step 4: Compute content hash
        hash_val = compute_content_hash(xml_content)

        # Step 5: If content text has identical hash, update metadata without reindexing
        if has_active:
            active_info = self.catalog.active_index(doc_id)
            if active_info.get("content_hash") == hash_val:
                self.catalog.record_sync_metadata(
                    document_id=doc_id,
                    source=meta.source,
                    official_id=meta.official_id,
                    title=meta.title,
                    source_url=meta.source_url,
                    url_eli=meta.url_eli,
                    last_updated=meta.fecha_actualizacion,
                    estado_consolidacion=meta.estado_consolidacion,
                    estado_consolidacion_codigo=meta.estado_consolidacion_codigo,
                    fecha_publicacion=meta.fecha_publicacion,
                    fecha_vigencia=meta.fecha_vigencia,
                    vigencia_agotada=meta.vigencia_agotada,
                    content_hash=hash_val,
                    last_checked_at=now_utc,
                    downloaded_at=now_utc,
                    sync_status="synced",
                )
                return BoeSyncResult(
                    action="metadata_updated",
                    document_id=doc_id,
                    metadata=meta,
                    content_hash=hash_val,
                )

        # Step 6: Content changed or new document; write raw XML and reindex
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        xml_path = self.raw_dir / f"{doc_id}_{hash_val[:12]}.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        chunks = load_xml_chunks(xml_path, max_chunk_size=self.chunk_size)
        if not chunks:
            err_msg = "Downloaded XML contains no indexable legal chunks"
            self.catalog.record_sync_error(doc_id, err_msg, now_utc)
            return BoeSyncResult(
                action="failed",
                document_id=doc_id,
                metadata=meta,
                content_hash=hash_val,
                error=err_msg,
            )

        configuration = index_configuration(
            corpus_sha256=hash_val,
            model_name=self.model_name,
            revision=self.revision,
            dimension=self.dimension,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
        )

        try:
            publish_res = publish_index(
                self.catalog,
                document_id=doc_id,
                title=meta.title or doc_id,
                source_path=xml_path,
                chunks=chunks,
                configuration=configuration,
                store_path=self.store_path,
                model=self.model,
            )
            run_id = publish_res["run_id"]
        except Exception as exc:
            self.catalog.record_sync_error(doc_id, str(exc), now_utc)
            return BoeSyncResult(
                action="failed",
                document_id=doc_id,
                metadata=meta,
                content_hash=hash_val,
                error=f"Reindex failed: {exc}",
            )

        self.catalog.record_sync_metadata(
            document_id=doc_id,
            source=meta.source,
            official_id=meta.official_id,
            title=meta.title,
            source_url=meta.source_url,
            url_eli=meta.url_eli,
            last_updated=meta.fecha_actualizacion,
            estado_consolidacion=meta.estado_consolidacion,
            estado_consolidacion_codigo=meta.estado_consolidacion_codigo,
            fecha_publicacion=meta.fecha_publicacion,
            fecha_vigencia=meta.fecha_vigencia,
            vigencia_agotada=meta.vigencia_agotada,
            content_hash=hash_val,
            last_checked_at=now_utc,
            downloaded_at=now_utc,
            sync_status="synced",
        )

        return BoeSyncResult(
            action="reindexed",
            document_id=doc_id,
            metadata=meta,
            content_hash=hash_val,
            run_id=run_id,
        )

    def sync_documents(self, identifiers: list[str]) -> list[BoeSyncResult]:
        """Process a list of BOE identifiers sequentially."""
        return [self.sync_document(doc_id) for doc_id in identifiers]
