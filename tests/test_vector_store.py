"""Exercise the persistent adapter against a real local Qdrant collection."""

import pytest
from qdrant_client import QdrantClient, models

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.retriever import similarity
from rag_bogado.retrieval.vector_store import QdrantVectorStore, point_id


def test_reopen_preserves_metadata_ranking_and_idempotency(tmp_path):
    chunks = [
        Chunk(0, "First", "a.pdf", 1),
        Chunk(0, "Second", "a.pdf", 2),
        Chunk(0, "Third", "b.pdf", 1),
    ]
    vectors = [[1.0, 0.0, 0.0], [0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    query = [0.0, 1.0, 0.0]
    with QdrantVectorStore(tmp_path, "test", dimension=3) as store:
        store.upsert(chunks, vectors, index_id="fixture-v1", batch_size=2)
        store.upsert(chunks, vectors, index_id="fixture-v1", batch_size=1)
    with QdrantVectorStore(tmp_path, "test", dimension=3) as store:
        results = store.search(query)
        assert len(results) == 3
        assert results[0].chunk == chunks[1]
        assert {r.chunk.source for r in results} == {"a.pdf", "b.pdf"}
        for result in results:
            position = chunks.index(result.chunk)
            assert result.score == pytest.approx(similarity(query, vectors[position]))
        assert len(store.search(query, top_k=1)) == 1
        assert store.search(query, top_k=0) == []


def test_point_ids_distinguish_document_page_and_processing_version():
    chunk = Chunk(0, "Text", "a.pdf", 1)
    assert point_id(chunk, "v1") == point_id(Chunk(0, "Text", "a.pdf", 1), "v1")
    ids = {
        point_id(chunk, "v1"),
        point_id(chunk, "v2"),
        point_id(Chunk(0, "Text", "b.pdf", 1), "v1"),
        point_id(Chunk(0, "Text", "a.pdf", 2), "v1"),
        point_id(Chunk(1, "Text", "a.pdf", 1), "v1"),
        point_id(Chunk(0, "Changed", "a.pdf", 1), "v1"),
    }
    assert len(ids) == 6


@pytest.mark.parametrize(
    "distance,size", [(models.Distance.COSINE, 3), (models.Distance.DOT, 4)]
)
def test_incompatible_collection_is_preserved_and_client_closed(
    tmp_path, distance, size
):
    client = QdrantClient(path=str(tmp_path))
    try:
        client.create_collection(
            "test", vectors_config=models.VectorParams(size=size, distance=distance)
        )
    finally:
        client.close()
    with pytest.raises(ValueError, match="Collection must match"):
        QdrantVectorStore(tmp_path, "test", dimension=3)
    client = QdrantClient(path=str(tmp_path))
    try:
        config = client.get_collection("test").config.params.vectors
        assert config.size == size
        assert config.distance == distance
    finally:
        client.close()


@pytest.mark.parametrize(
    "bad_vector", [[1.0], [float("nan"), 0.0, 0.0], [float("inf"), 0.0, 0.0]]
)
def test_invalid_batch_does_not_write_partial_data(tmp_path, bad_vector):
    chunks = [Chunk(0, "First", "a.pdf", 1), Chunk(1, "Second", "a.pdf", 1)]
    with QdrantVectorStore(tmp_path, "test", dimension=3) as store:
        with pytest.raises(ValueError):
            store.upsert(
                chunks, [[1.0, 0.0, 0.0], bad_vector], index_id="v1", batch_size=1
            )
        assert store.search([1.0, 0.0, 0.0]) == []
        with pytest.raises(ValueError):
            store.search(bad_vector)


def test_empty_input_and_invalid_arguments(tmp_path):
    with QdrantVectorStore(tmp_path, "test", dimension=3) as store:
        store.upsert([], [], index_id="v1")
        assert store.search([1.0, 0.0, 0.0]) == []
        with pytest.raises(ValueError, match="one vector"):
            store.upsert([Chunk(0, "Text", "a.pdf", 1)], [], index_id="v1")
        with pytest.raises(ValueError, match="index_id"):
            store.upsert([], [], index_id=" ")
        with pytest.raises(ValueError, match="batch_size"):
            store.upsert([], [], index_id="v1", batch_size=0)
        with pytest.raises(ValueError, match="top_k"):
            store.search([1.0, 0.0, 0.0], top_k=-1)
