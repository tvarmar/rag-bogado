"""First persistence experiment, using synthetic vectors without a model."""

from dataclasses import asdict

import pytest
from qdrant_client import QdrantClient, models

from rag_bogado.ingestion.chunker import Chunk


def test_chunks_survive_reopening_and_keep_their_ranking(tmp_path):
    path = str(tmp_path / "qdrant")
    collection = "persistence_example"
    chunks = [
        Chunk(0, "First example passage", "example.pdf", 1),
        Chunk(0, "Second example passage", "example.pdf", 2),
    ]
    # These unit vectors are test fixtures, not semantic embeddings.
    # Point IDs are collection-wide; chunk_id alone repeats across pages.
    client = QdrantClient(path=path)
    try:
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=3, distance=models.Distance.DOT),
        )
        client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=1, vector=[1.0, 0.0, 0.0], payload=asdict(chunks[0])
                ),
                models.PointStruct(
                    id=2, vector=[0.0, 1.0, 0.0], payload=asdict(chunks[1])
                ),
            ],
        )
    finally:
        client.close()

    # A new client only queries saved data: no insertion or embedding calls.
    reopened = QdrantClient(path=path)
    try:
        results = reopened.query_points(
            collection_name=collection,
            query=[1.0, 0.0, 0.0],
            limit=2,
            with_payload=True,
        ).points
        assert reopened.count(collection_name=collection, exact=True).count == 2
        assert [result.id for result in results] == [1, 2]
        assert [result.score for result in results] == pytest.approx([1.0, 0.0])
        assert [Chunk(**result.payload) for result in results] == chunks
    finally:
        reopened.close()
