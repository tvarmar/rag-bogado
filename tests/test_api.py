"""Deterministic tests for the RAG-Bogado FastAPI application."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag_bogado.api.app import create_app
from rag_bogado.indexing.catalog import DocumentCatalog


@pytest.fixture
def catalog_with_document(tmp_path: Path) -> Path:
    catalog_path = tmp_path / "catalog.sqlite3"
    with DocumentCatalog(catalog_path) as catalog:
        run_id = catalog.start_run(
            document_id="test_doc",
            title="Test Regulatory Law",
            content_hash="abc123hash",
            source_path=tmp_path / "test_doc.xml",
            index_id="idx_123",
            collection="index_idx_123",
            store_path=tmp_path / "qdrant",
            configuration={
                "corpus_sha256": "abc123hash",
                "dimension": 384,
                "model": "fake",
            },
            expected_chunks=5,
        )
        catalog.activate(run_id)
    return catalog_path


class FakeGenerator:
    """Deterministic fake generator for testing API without LLM inference."""

    def __init__(self, answer_status: str = "answered"):
        self.answer_status = answer_status
        self.model = "fake-model"

    def generate(self, query: dict, **kwargs) -> dict:
        sources = [
            {
                "id": "S1",
                "document": "test_doc.xml",
                "page": 0,
                "chunk_id": 1,
                "version_id": query.get("version_id", 1),
                "text": "Artículo 1. Texto de prueba.",
                "article": "Artículo 1",
                "unit_type": "article",
            }
        ]
        claims = (
            [{"text": "Afirmación probada.", "citations": ["S1"]}]
            if self.answer_status == "answered"
            else []
        )
        return {
            "document_id": query["document_id"],
            "version_id": query["version_id"],
            "content_hash": query["content_hash"],
            "source_path": query["source_path"],
            "index_id": query["index_id"],
            "question": query["question"],
            "status": self.answer_status,
            "answer_mode": kwargs.get("answer_mode", "synthesis"),
            "sources": sources,
            "claims": claims,
            "model": self.model,
            "display_message": None
            if self.answer_status == "answered"
            else "Falta evidencia",
        }

    def request(self, path: str, payload: dict | None = None) -> dict:
        import json

        if path == "/api/chat":
            format_schema = (payload or {}).get("format", {})
            props = format_schema.get("properties", {})
            if "questions" in props:
                content = json.dumps({"questions": [json_question(payload)]})
            elif "query" in props:
                content = json.dumps({"query": json_question(payload)})
            elif "reviews" in props:
                content = json.dumps(
                    {
                        "status": "passed",
                        "reviews": [
                            {
                                "id": 0,
                                "supported": True,
                                "relevant": True,
                                "qualifications_preserved": True,
                            }
                        ],
                    }
                )
            else:
                content = "{}"
            return {
                "done": True,
                "done_reason": "stop",
                "message": {"content": content},
            }
        return {}


def json_question(payload: dict) -> str:
    import json

    user_msg = payload["messages"][1]["content"]
    data = json.loads(user_msg)
    return data.get("query") or data.get("question") or "Pregunta de prueba"


def fake_query_active(catalog, doc_id, text, top_k):
    active = catalog.active_index(doc_id)
    return {
        "document_id": doc_id,
        "version_id": active["version_id"],
        "content_hash": active["content_hash"],
        "source_path": active["source_path"],
        "index_id": active["index_id"],
        "question": text,
        "results": [
            {
                "score": 0.92,
                "chunk": {
                    "text": "Artículo 1. Texto de prueba.",
                    "source": "test_doc.xml",
                    "page_number": 0,
                    "chunk_id": 1,
                    "article": "Artículo 1",
                    "unit_type": "article",
                },
            }
        ],
    }


def test_health_check_ok(catalog_with_document: Path):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["catalog_ready"] is True
    assert "test_doc" in data["active_documents"]


def test_health_check_degraded_when_missing_catalog(tmp_path: Path):
    app = create_app(catalog_path=tmp_path / "nonexistent.sqlite3")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["catalog_ready"] is False
    assert data["active_documents"] == []


def test_openapi_schema_available(catalog_with_document: Path):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/health" in schema["paths"]
    assert "/ask" in schema["paths"]


def test_ask_endpoint_success(catalog_with_document: Path):
    app = create_app(
        catalog_path=catalog_with_document,
        generator_factory=lambda: FakeGenerator("answered"),
        query_fn=fake_query_active,
    )
    client = TestClient(app)
    payload = {
        "question": "¿Quién tiene la obligación?",
        "document_id": "test_doc",
        "answer_mode": "synthesis",
        "search_count": 1,
        "max_passages": 5,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "¿Quién tiene la obligación?"
    assert data["status"] == "answered"
    assert len(data["answers"]) == 1
    answer = data["answers"][0]
    assert answer["status"] == "answered"
    assert len(answer["claims"]) == 1
    assert answer["claims"][0]["text"] == "Afirmación probada."
    assert answer["claims"][0]["citations"] == ["Q1-S1"]
    assert len(answer["sources"]) == 1
    assert answer["sources"][0]["id"] == "Q1-S1"
    assert answer["sources"][0]["article"] == "Artículo 1"


def test_ask_endpoint_unknown_document_returns_404(catalog_with_document: Path):
    app = create_app(
        catalog_path=catalog_with_document,
        generator_factory=lambda: FakeGenerator("answered"),
        query_fn=fake_query_active,
    )
    client = TestClient(app)
    payload = {
        "question": "¿Quién tiene la obligación?",
        "document_id": "unknown_doc",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ask_endpoint_empty_question_validation_error(catalog_with_document: Path):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    payload = {"question": "   ", "document_id": "test_doc"}
    response = client.post("/ask", json=payload)
    assert response.status_code == 422


def test_ask_endpoint_invalid_search_count_validation_error(
    catalog_with_document: Path,
):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    payload = {
        "question": "Pregunta válida",
        "document_id": "test_doc",
        "search_count": 5,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 422


def test_ask_endpoint_invalid_answer_mode_validation_error(
    catalog_with_document: Path,
):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    payload = {
        "question": "Pregunta válida",
        "document_id": "test_doc",
        "answer_mode": "creative",
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 422


def test_root_index_serves_html(catalog_with_document: Path):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "RAG-Bogado" in response.text


def test_static_assets_served(catalog_with_document: Path):
    app = create_app(catalog_path=catalog_with_document)
    client = TestClient(app)

    css_res = client.get("/static/styles.css")
    assert css_res.status_code == 200
    assert "text/css" in css_res.headers.get("content-type", "")

    js_res = client.get("/static/app.js")
    assert js_res.status_code == 200
    assert "javascript" in js_res.headers.get("content-type", "")


def test_root_index_fallback_without_html(tmp_path: Path):
    empty_static = tmp_path / "empty_static"
    empty_static.mkdir()
    app = create_app(catalog_path=tmp_path / "catalog.sqlite3", static_dir=empty_static)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "RAG-Bogado API is running"}
