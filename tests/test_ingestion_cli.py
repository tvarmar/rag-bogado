"""Deterministic tests for the ingestion and BOE synchronization CLI."""

import json
import sys
from types import SimpleNamespace

import httpx

from rag_bogado.ingestion import __main__ as cli
from rag_bogado.ingestion.boe import BoeClient
from rag_bogado.ingestion.sync import BoeSyncResult

SAMPLE_METADATA_JSON = """{
    "status": {"code": "200", "text": "ok"},
    "data": [{
        "identificador": "BOE-A-2018-16673",
        "titulo": "Ley de Protección de Datos",
        "fecha_actualizacion": "20260101T000000Z",
        "url_eli": "https://www.boe.es/eli/es/lo/2018/12/05/3",
        "url_html_consolidada": "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
        "fecha_publicacion": "20181206",
        "fecha_vigencia": "20181207",
        "vigencia_agotada": "N",
        "estado_consolidacion": {"codigo": "3", "texto": "Finalizado"}
    }]
}"""


def test_metadata_command(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_METADATA_JSON)

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        cli, "BoeClient", lambda *a, **kw: BoeClient(client=mock_client)
    )

    monkeypatch.setattr(sys, "argv", ["ingestion", "metadata", "BOE-A-2018-16673"])
    cli.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["official_id"] == "BOE-A-2018-16673"
    assert data["estado_consolidacion"] == "Finalizado"


def test_sync_command(tmp_path, monkeypatch, capsys):
    class FakeModel:
        def __init__(self, *args, **kwargs):
            self.model = SimpleNamespace(get_embedding_dimension=lambda: 2)

    monkeypatch.setattr(cli, "EmbeddingModel", FakeModel)

    class FakeSyncService:
        def __init__(self, **kwargs):
            pass

        def sync_documents(self, identifiers):
            return [
                BoeSyncResult(
                    action="reindexed",
                    document_id=doc_id,
                    content_hash="abc123hash",
                    run_id=1,
                )
                for doc_id in identifiers
            ]

    monkeypatch.setattr(cli, "BoeSyncService", FakeSyncService)
    monkeypatch.setattr(
        cli,
        "BoeClient",
        lambda *a, **kw: httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200))
        ),
    )

    catalog_path = tmp_path / "catalog.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingestion",
            "sync",
            "BOE-A-2018-16673",
            "--catalog",
            str(catalog_path),
        ],
    )
    cli.main()
    out = capsys.readouterr().out
    results = json.loads(out)
    assert len(results) == 1
    assert results[0]["action"] == "reindexed"
    assert results[0]["document_id"] == "BOE-A-2018-16673"
    assert results[0]["content_hash"] == "abc123hash"
