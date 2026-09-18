"""FastAPI application factory and route definitions for RAG-Bogado."""

from __future__ import annotations

import logging
import os
import sys
import urllib.request
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from rag_bogado.api.schemas import (
    AskRequest,
    AskResponse,
    DocumentInfoModel,
    DocumentsListResponse,
    HealthResponse,
    SyncResponse,
    SyncResultModel,
)
from rag_bogado.generation.generator import OllamaGenerator
from rag_bogado.generation.service import answer_questions
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active
from rag_bogado.ingestion.boe import BoeClient
from rag_bogado.ingestion.corpus import OFFICIAL_CORPUS_DOCUMENTS
from rag_bogado.ingestion.sync import BoeSyncResult, BoeSyncService

logger = logging.getLogger("rag_bogado.api")
DEFAULT_STATIC_DIR = Path(__file__).parent / "static"


def check_ollama_alive(ollama_url: str = "http://127.0.0.1:11434") -> bool:
    """Quick non-blocking probe to verify if Ollama daemon is responsive."""
    try:
        req = urllib.request.Request(f"{ollama_url.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as response:
            return response.status == 200
    except Exception:
        return False


def sync_official_corpus(
    catalog_path: Path,
    *,
    boe_client: BoeClient | None = None,
    model: Any = None,
    store_path: Path | str | None = None,
    identifiers: list[str] | None = None,
) -> list[BoeSyncResult]:
    """Check and synchronize official regulatory documents against BOE."""
    target_defs = (
        [doc for doc in OFFICIAL_CORPUS_DOCUMENTS if doc.document_id in identifiers]
        if identifiers
        else OFFICIAL_CORPUS_DOCUMENTS
    )
    if not catalog_path.exists():
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        DocumentCatalog(catalog_path).close()

    results: list[BoeSyncResult] = []
    client = boe_client or BoeClient()
    should_close_client = boe_client is None
    try:
        with DocumentCatalog(catalog_path) as catalog:
            service = BoeSyncService(
                catalog=catalog,
                boe_client=client,
                model=model,
                store_path=store_path
                or Path(os.environ.get("QDRANT_URL", "data/qdrant")),
            )
            for doc_def in target_defs:
                try:
                    if service.model is None and not catalog.has_active_index(
                        doc_def.document_id
                    ):
                        from rag_bogado.retrieval.embeddings import EmbeddingModel

                        service.model = EmbeddingModel(
                            "intfloat/multilingual-e5-small",
                            revision="614241f622f53c4eeff9890bdc4f31cfecc418b3",
                            local_files_only=True,
                        )
                    res = service.sync_document(
                        doc_def.document_id, doc_def.official_id
                    )
                    results.append(res)
                except Exception as err:
                    logger.error(
                        "Sync failed for %s (%s): %s",
                        doc_def.document_id,
                        doc_def.official_id,
                        err,
                    )
                    results.append(
                        BoeSyncResult(
                            action="failed",
                            document_id=doc_def.document_id,
                            error=str(err),
                        )
                    )
    finally:
        if should_close_client:
            client.close()
    return results


def create_app(
    *,
    catalog_path: Path | None = None,
    generator_factory: Callable[[], Any] | None = None,
    query_fn: Callable[[Any, str, str, int], dict] | None = None,
    static_dir: Path | None = None,
    sync_on_startup: bool | None = None,
    boe_client_factory: Callable[[], BoeClient] | None = None,
) -> FastAPI:
    """Create a configured FastAPI application with injectable service dependencies."""
    default_catalog_path = catalog_path or Path(
        os.environ.get("CATALOG_PATH", "data/catalog/catalog.sqlite3")
    )
    default_generator_factory = generator_factory or (lambda: OllamaGenerator())
    default_query_fn = query_fn or (
        lambda catalog, doc_id, text, top_k: query_active(
            catalog, doc_id, text, top_k=top_k
        )
    )
    resolved_static_dir = static_dir or Path(
        os.environ.get("STATIC_DIR", str(DEFAULT_STATIC_DIR))
    )

    is_testing = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules
    should_sync = (
        sync_on_startup
        if sync_on_startup is not None
        else (os.environ.get("SYNC_CORPUS_ON_STARTUP", "1") == "1" and not is_testing)
    )

    @asynccontextmanager
    async def app_lifespan(app_instance: FastAPI):
        if should_sync:
            logger.info("Comprobando sincronización del corpus BOE en el arranque...")
            try:
                b_client = boe_client_factory() if boe_client_factory else None
                sync_official_corpus(default_catalog_path, boe_client=b_client)
            except Exception as exc:
                logger.warning(
                    "Sincronización inicial del corpus omitida o con fallo de red: %s",
                    exc,
                )
        yield

    app = FastAPI(
        title="RAG-Bogado API",
        description=(
            "Local Retrieval-Augmented Generation service over regulatory documents "
            "with strict citation verification, multi-query RRF, and fail-closed "
            "abstention."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=app_lifespan,
    )

    if resolved_static_dir.exists():
        app.mount("/static", StaticFiles(directory=resolved_static_dir), name="static")

    @app.get(
        "/",
        summary="Web User Interface",
        description="Serve the interactive web client for RAG-Bogado.",
        include_in_schema=False,
    )
    def index():
        index_file = resolved_static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "RAG-Bogado API is running"}

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Service health check",
        description=(
            "Verify catalog accessibility, Ollama availability, and active documents."
        ),
    )
    def health_check() -> HealthResponse:
        ollama_ok = check_ollama_alive()
        try:
            if not default_catalog_path.exists():
                logger.warning("Catalog path does not exist: %s", default_catalog_path)
                return HealthResponse(
                    status="degraded",
                    version="0.1.0",
                    catalog_ready=False,
                    active_documents=[],
                    ollama_ready=ollama_ok,
                )
            with DocumentCatalog(default_catalog_path) as catalog:
                rows = catalog.connection.execute(
                    "SELECT DISTINCT document_id FROM indexing_runs "
                    "WHERE active = 1 AND status = 'ready'"
                ).fetchall()
                active_docs = [row["document_id"] for row in rows]
                return HealthResponse(
                    status="ok",
                    version="0.1.0",
                    catalog_ready=True,
                    active_documents=active_docs,
                    ollama_ready=ollama_ok,
                )
        except Exception as err:
            logger.error("Health check catalog query failed: %s", err)
            return HealthResponse(
                status="degraded",
                version="0.1.0",
                catalog_ready=False,
                active_documents=[],
                ollama_ready=ollama_ok,
            )

    @app.get(
        "/api/documents",
        response_model=DocumentsListResponse,
        summary="List corpus documents",
        description="Metadata and readiness for all 4 corpus documents.",
    )
    def list_documents() -> DocumentsListResponse:
        docs_info: list[DocumentInfoModel] = []
        active_count = 0
        if not default_catalog_path.exists():
            for doc in OFFICIAL_CORPUS_DOCUMENTS:
                docs_info.append(
                    DocumentInfoModel(
                        id=doc.document_id,
                        official_id=doc.official_id,
                        title=doc.title,
                        short_name=doc.short_name,
                        scope_description=doc.scope_description,
                        active=False,
                    )
                )
            return DocumentsListResponse(
                documents=docs_info,
                total=len(docs_info),
                active_count=0,
            )

        with DocumentCatalog(default_catalog_path) as catalog:
            for doc in OFFICIAL_CORPUS_DOCUMENTS:
                is_active = catalog.has_active_index(doc.document_id)
                if is_active:
                    active_count += 1
                meta = catalog.get_sync_metadata(doc.document_id) or {}
                docs_info.append(
                    DocumentInfoModel(
                        id=doc.document_id,
                        official_id=doc.official_id,
                        title=meta.get("title") or doc.title,
                        short_name=doc.short_name,
                        scope_description=doc.scope_description,
                        active=is_active,
                        sync_status=meta.get("sync_status"),
                        last_checked_at=meta.get("last_checked_at"),
                        last_updated=meta.get("last_updated"),
                        source_url=(
                            meta.get("source_url")
                            or f"https://www.boe.es/buscar/act.php?id={doc.official_id}"
                        ),
                    )
                )

        return DocumentsListResponse(
            documents=docs_info,
            total=len(docs_info),
            active_count=active_count,
        )

    @app.post(
        "/api/documents/sync",
        response_model=SyncResponse,
        summary="Trigger corpus sync",
        description="Check and synchronize the 4 regulatory documents against BOE.",
    )
    def sync_documents() -> SyncResponse:
        try:
            b_client = boe_client_factory() if boe_client_factory else None
            results = sync_official_corpus(default_catalog_path, boe_client=b_client)
            model_results = [
                SyncResultModel(
                    document_id=r.document_id,
                    action=r.action,
                    status="ok" if r.action != "failed" else "error",
                    error=r.error,
                )
                for r in results
            ]
            all_ok = all(r.action != "failed" for r in results)
            return SyncResponse(
                status="completed" if all_ok else "partial",
                results=model_results,
            )
        except Exception as exc:
            logger.error("Corpus sync failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sincronización del corpus fallida: {exc}",
            ) from exc

    @app.post(
        "/ask",
        response_model=AskResponse,
        summary="Ask a question",
        description=(
            "Answer a question using retrieved legal passages, optional synthesis, "
            "and verifiable citation identifiers."
        ),
    )
    def ask_question(request: AskRequest) -> AskResponse:
        logger.info(
            "Received /ask request for document=%r (mode=%s, search_count=%d)",
            request.document_id,
            request.answer_mode,
            request.search_count,
        )
        if not default_catalog_path.exists():
            logger.error("Catalog path not found: %s", default_catalog_path)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Document catalog database is not available",
            )
        try:
            with DocumentCatalog(default_catalog_path) as catalog:
                try:
                    catalog.active_index(request.document_id)
                except ValueError as err:
                    logger.warning(
                        "Document %r not found or not active: %s",
                        request.document_id,
                        err,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=(
                            f"Document {request.document_id!r} not found or "
                            f"has no active index: {err}"
                        ),
                    ) from err

                generator = default_generator_factory()
                result = answer_questions(
                    request.question,
                    generator,
                    lambda text: default_query_fn(
                        catalog,
                        request.document_id,
                        text,
                        top_k=request.max_passages * 2,
                    ),
                    search_count=request.search_count,
                    max_passages=request.max_passages,
                    relative_margin=request.relative_margin,
                    context_tokens=request.context_tokens,
                    output_tokens=request.output_tokens,
                    answer_mode=request.answer_mode,
                )
                logger.info(
                    "Query completed for document=%r: status=%s, answers=%d",
                    request.document_id,
                    result.get("status"),
                    len(result.get("answers", [])),
                )
                return AskResponse.model_validate(result)
        except HTTPException:
            raise
        except (ValueError, RuntimeError, OSError, KeyError) as err:
            err_msg = str(err)
            if any(
                k in err_msg
                for k in (
                    "Connection refused",
                    "Local Ollama request failed",
                    "111",
                    "URLError",
                )
            ):
                logger.warning("Ollama service unavailable: %s", err)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "El servicio local de LLM (Ollama) no está disponible en "
                        "127.0.0.1:11434. Asegúrate de iniciarlo en el servidor "
                        "ejecutando: 'bash scripts/serve_ollama.sh'"
                    ),
                ) from err
            logger.error(
                "Query execution failed for document=%r: %s",
                request.document_id,
                err,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query execution failed: {err}",
            ) from err

    return app


app = create_app()
