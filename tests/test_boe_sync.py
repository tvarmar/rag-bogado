"""Deterministic integration tests for BoeSyncService and catalog synchronization."""

import httpx
import pytest

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.ingestion.boe import BoeClient
from rag_bogado.ingestion.sync import BoeSyncService


class FakeEmbeddingModel:
    def __init__(self, dimension: int = 2):
        self.dimension = dimension
        self.passages_embedded = []

    def embed_passages(self, texts):
        self.passages_embedded.extend(texts)
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


SAMPLE_METADATA_JSON_V1 = """{
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

SAMPLE_METADATA_JSON_V2 = """{
    "status": {"code": "200", "text": "ok"},
    "data": [{
        "identificador": "BOE-A-2018-16673",
        "titulo": "Ley de Protección de Datos (Actualizada)",
        "fecha_actualizacion": "20260601T000000Z",
        "url_eli": "https://www.boe.es/eli/es/lo/2018/12/05/3",
        "url_html_consolidada": "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673",
        "fecha_publicacion": "20181206",
        "fecha_vigencia": "20181207",
        "vigencia_agotada": "N",
        "estado_consolidacion": {"codigo": "3", "texto": "Finalizado"}
    }]
}"""

SAMPLE_XML_V1 = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status><code>200</code><text>ok</text></status>
  <data>
    <texto>
      <p class="articulo">Artículo 1. Objeto de la ley.</p>
      <p class="parrafo">1. La presente ley tiene por objeto regular datos.</p>
      <p class="articulo">Artículo 2. Ámbito de aplicación.</p>
      <p class="parrafo">Esta norma aplica a todos los tratamientos en España.</p>
    </texto>
  </data>
</response>"""

SAMPLE_XML_V2 = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status><code>200</code><text>ok</text></status>
  <data>
    <texto>
      <p class="articulo">Artículo 1. Objeto de la ley.</p>
      <p class="parrafo">1. La presente ley tiene por objeto datos modificados.</p>
      <p class="articulo">Artículo 2. Ámbito de aplicación.</p>
      <p class="parrafo">Esta norma aplica a todos los tratamientos en la UE.</p>
    </texto>
  </data>
</response>"""


@pytest.fixture
def catalog_fixture(tmp_path):
    catalog_path = tmp_path / "catalog.sqlite3"
    with DocumentCatalog(catalog_path) as catalog:
        yield catalog


def test_initial_sync_creates_version_and_active_index(tmp_path, catalog_fixture):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadatos"):
            return httpx.Response(200, text=SAMPLE_METADATA_JSON_V1)
        return httpx.Response(200, text=SAMPLE_XML_V1)

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    result = service.sync_document("BOE-A-2018-16673")
    assert result.action == "reindexed"
    assert result.document_id == "BOE-A-2018-16673"
    assert result.run_id is not None
    assert len(model.passages_embedded) > 0

    assert catalog_fixture.has_active_index("BOE-A-2018-16673")
    active = catalog_fixture.active_index("BOE-A-2018-16673")
    assert active["content_hash"] == result.content_hash

    meta = catalog_fixture.get_sync_metadata("BOE-A-2018-16673")
    assert meta is not None
    assert meta["sync_status"] == "synced"
    assert meta["estado_consolidacion"] == "Finalizado"
    assert meta["last_updated"] == "20260101T000000Z"


def test_subsequent_sync_skips_when_metadata_date_unchanged(tmp_path, catalog_fixture):
    download_called = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadatos"):
            return httpx.Response(200, text=SAMPLE_METADATA_JSON_V1)
        download_called.append(True)
        return httpx.Response(200, text=SAMPLE_XML_V1)

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    res1 = service.sync_document("BOE-A-2018-16673")
    assert res1.action == "reindexed"
    assert len(download_called) == 1

    embedded_count_before = len(model.passages_embedded)
    download_called.clear()

    # Second sync: metadata fecha_actualizacion has not changed
    res2 = service.sync_document("BOE-A-2018-16673")
    assert res2.action == "skipped_up_to_date"
    assert len(download_called) == 0
    assert len(model.passages_embedded) == embedded_count_before


def test_metadata_updated_without_reindexing_when_content_hash_identical(
    tmp_path, catalog_fixture
):
    metadata_response = [SAMPLE_METADATA_JSON_V1]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadatos"):
            return httpx.Response(200, text=metadata_response[0])
        return httpx.Response(200, text=SAMPLE_XML_V1)

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    res1 = service.sync_document("BOE-A-2018-16673")
    assert res1.action == "reindexed"

    embedded_count = len(model.passages_embedded)

    # Official BOE registry touched the record (fecha_actualizacion changed),
    # but the text content is completely identical:
    metadata_response[0] = SAMPLE_METADATA_JSON_V2

    res2 = service.sync_document("BOE-A-2018-16673")
    assert res2.action == "metadata_updated"
    # Zero new embeddings generated!
    assert len(model.passages_embedded) == embedded_count

    meta = catalog_fixture.get_sync_metadata("BOE-A-2018-16673")
    assert meta["last_updated"] == "20260601T000000Z"
    assert "Actualizada" in meta["title"]


def test_modified_content_reindexes_and_activates_new_version(
    tmp_path, catalog_fixture
):
    metadata_response = [SAMPLE_METADATA_JSON_V1]
    xml_response = [SAMPLE_XML_V1]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadatos"):
            return httpx.Response(200, text=metadata_response[0])
        return httpx.Response(200, text=xml_response[0])

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    res1 = service.sync_document("BOE-A-2018-16673")
    assert res1.action == "reindexed"
    v1_hash = res1.content_hash

    # Now both metadata and content change
    metadata_response[0] = SAMPLE_METADATA_JSON_V2
    xml_response[0] = SAMPLE_XML_V2

    res2 = service.sync_document("BOE-A-2018-16673")
    assert res2.action == "reindexed"
    assert res2.content_hash != v1_hash

    # Active index points to new hash
    active = catalog_fixture.active_index("BOE-A-2018-16673")
    assert active["content_hash"] == res2.content_hash

    # History records both versions
    hist = catalog_fixture.history("BOE-A-2018-16673")
    assert len(hist) == 2
    assert [h["active"] for h in hist] == [0, 1]


def test_download_failure_preserves_active_version_and_records_error(
    tmp_path, catalog_fixture
):
    metadata_response = [SAMPLE_METADATA_JSON_V1]
    should_fail_download = [False]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadatos"):
            return httpx.Response(200, text=metadata_response[0])
        if should_fail_download[0]:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, text=SAMPLE_XML_V1)

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    res1 = service.sync_document("BOE-A-2018-16673")
    assert res1.action == "reindexed"
    v1_hash = res1.content_hash

    # Now server fails during download:
    metadata_response[0] = SAMPLE_METADATA_JSON_V2
    should_fail_download[0] = True

    res2 = service.sync_document("BOE-A-2018-16673")
    assert res2.action == "failed"
    assert "Download failed" in res2.error

    # Previous active index is still completely safe and active!
    active = catalog_fixture.active_index("BOE-A-2018-16673")
    assert active["content_hash"] == v1_hash

    meta = catalog_fixture.get_sync_metadata("BOE-A-2018-16673")
    assert meta["sync_status"] == "error"
    assert "500" in meta["last_error"]


def test_sync_documents_list(tmp_path, catalog_fixture):
    def handler(request: httpx.Request) -> httpx.Response:
        if "BOE-1" in request.url.path:
            if request.url.path.endswith("/metadatos"):
                return httpx.Response(200, text=SAMPLE_METADATA_JSON_V1)
            return httpx.Response(200, text=SAMPLE_XML_V1)
        return httpx.Response(404, text="Not Found")

    boe_client = BoeClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    model = FakeEmbeddingModel(dimension=2)

    service = BoeSyncService(
        catalog=catalog_fixture,
        boe_client=boe_client,
        model=model,
        raw_dir=tmp_path / "raw",
        store_path=tmp_path / "vectors",
        dimension=2,
    )

    results = service.sync_documents(["BOE-1", "BOE-NONEXISTENT"])
    assert len(results) == 2
    assert results[0].action == "reindexed"
    assert results[1].action == "failed"
