"""FastAPI application factory and route definitions for RAG-Bogado."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from rag_bogado.api.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
)
from rag_bogado.generation.generator import OllamaGenerator
from rag_bogado.generation.service import answer_questions
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active

logger = logging.getLogger("rag_bogado.api")
DEFAULT_STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    *,
    catalog_path: Path | None = None,
    generator_factory: Callable[[], Any] | None = None,
    query_fn: Callable[[Any, str, str, int], dict] | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Create a configured FastAPI application with injectable service dependencies."""
    default_catalog_path = catalog_path or Path("data/catalog/catalog.sqlite3")
    default_generator_factory = generator_factory or (lambda: OllamaGenerator())
    default_query_fn = query_fn or (
        lambda catalog, doc_id, text, top_k: query_active(
            catalog, doc_id, text, top_k=top_k
        )
    )
    resolved_static_dir = static_dir or DEFAULT_STATIC_DIR

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
            "Verify document catalog accessibility and list active queryable documents."
        ),
    )
    def health_check() -> HealthResponse:
        try:
            if not default_catalog_path.exists():
                logger.warning("Catalog path does not exist: %s", default_catalog_path)
                return HealthResponse(
                    status="degraded",
                    version="0.1.0",
                    catalog_ready=False,
                    active_documents=[],
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
                )
        except Exception as err:
            logger.error("Health check catalog query failed: %s", err)
            return HealthResponse(
                status="degraded",
                version="0.1.0",
                catalog_ready=False,
                active_documents=[],
            )

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
                # Check document existence and active index
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
