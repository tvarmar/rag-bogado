"""Deterministic tests for the BOE API client and metadata parsing."""

import httpx
import pytest

from rag_bogado.ingestion.boe import (
    BoeApiError,
    BoeClient,
    BoeDocumentNotFoundError,
    BoeNetworkError,
    compute_content_hash,
)

SAMPLE_METADATA_JSON = """{
    "status": {
        "code": "200",
        "text": "ok"
    },
    "data": [
        {
            "fecha_actualizacion": "20260720T102442Z",
            "identificador": "BOE-A-2018-16673",
            "titulo": "Ley Orgánica 3/2018, de Protección de Datos Personales",
            "url_eli": "https://www.boe.es/eli/es/lo/2018/12/05/3",
            "url_html_consolidada": "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
            "fecha_publicacion": "20181206",
            "fecha_vigencia": "20181207",
            "vigencia_agotada": "N",
            "estatus_derogacion": "N",
            "estado_consolidacion": {
                "codigo": "3",
                "texto": "Finalizado"
            }
        }
    ]
}"""

SAMPLE_BOE_XML = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status>
    <code>200</code>
    <text>ok</text>
  </status>
  <data>
    <metadatos>
      <identificador>BOE-A-2018-16673</identificador>
      <titulo>Ley Orgánica 3/2018</titulo>
    </metadatos>
    <texto>
      <p class="articulo">Artículo 1. Objeto de la ley.</p>
      <p class="parrafo">1. La presente ley tiene por objeto...</p>
    </texto>
  </data>
</response>"""


def test_compute_content_hash():
    h1 = compute_content_hash("hello world")
    h2 = compute_content_hash(b"hello world")
    assert h1 == h2
    assert len(h1) == 64
    assert compute_content_hash("hello world") == compute_content_hash("hello world")
    assert compute_content_hash("different") != h1


def test_get_metadata_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/id/BOE-A-2018-16673/metadatos")
        assert request.headers.get("Accept") == "application/json"
        return httpx.Response(200, text=SAMPLE_METADATA_JSON)

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    meta = boe_client.get_metadata("BOE-A-2018-16673")
    assert meta.official_id == "BOE-A-2018-16673"
    assert "Protección de Datos" in meta.title
    assert meta.source == "BOE"
    assert meta.fecha_actualizacion == "20260720T102442Z"
    assert meta.estado_consolidacion == "Finalizado"
    assert meta.estado_consolidacion_codigo == "3"
    assert meta.vigencia_agotada is False
    assert meta.last_checked_at != ""
    assert meta.to_dict()["official_id"] == "BOE-A-2018-16673"


def test_get_metadata_404_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    with pytest.raises(BoeDocumentNotFoundError, match="was not found"):
        boe_client.get_metadata("BOE-A-0000-00000")


def test_get_metadata_payload_error():
    error_json = '{"status": {"code": "500", "text": "Internal error"}, "data": []}'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=error_json)

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    with pytest.raises(BoeApiError, match="non-200 code '500'"):
        boe_client.get_metadata("BOE-A-2018-16673")


def test_get_metadata_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    with pytest.raises(BoeNetworkError, match="Network error"):
        boe_client.get_metadata("BOE-A-2018-16673")


def test_get_metadata_blank_identifier():
    boe_client = BoeClient()
    with pytest.raises(ValueError, match="cannot be blank"):
        boe_client.get_metadata("   ")


def test_download_xml_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/id/BOE-A-2018-16673")
        assert request.headers.get("Accept") == "application/xml"
        return httpx.Response(200, text=SAMPLE_BOE_XML)

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    xml_content = boe_client.download_xml("BOE-A-2018-16673")
    assert "<response>" in xml_content
    assert '<p class="articulo">Artículo 1' in xml_content


def test_download_xml_404_in_body():
    xml_404 = (
        "<response><status><code>404</code><text>No existe</text></status></response>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=xml_404)

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    with pytest.raises(BoeDocumentNotFoundError, match="404 status body"):
        boe_client.download_xml("BOE-A-0000-00000")


def test_download_xml_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    boe_client = BoeClient(client=mock_client)

    with pytest.raises(BoeNetworkError, match="Network error downloading BOE XML"):
        boe_client.download_xml("BOE-A-2018-16673")
