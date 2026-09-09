import pytest

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.retriever import Retriever, similarity


class FakeEmbeddingModel:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],
        ]


def create_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id=0,
            text="Primer chunk",
            source="test.pdf",
            page_number=1,
        ),
        Chunk(
            chunk_id=1,
            text="Segundo chunk",
            source="test.pdf",
            page_number=2,
        ),
        Chunk(
            chunk_id=2,
            text="Tercer chunk",
            source="test.pdf",
            page_number=3,
        ),
    ]


def test_similarity_calculates_dot_product():
    result = similarity(
        [1.0, 2.0],
        [3.0, 4.0],
    )

    assert result == 11.0


def test_retriever_orders_results_by_similarity():
    retriever = Retriever(
        chunks=create_chunks(),
        embedding_model=FakeEmbeddingModel(),
    )

    results = retriever.search(
        "pregunta",
        top_k=3,
    )

    assert results[0].chunk.text == "Primer chunk"
    assert results[1].chunk.text == "Segundo chunk"
    assert results[2].chunk.text == "Tercer chunk"


def test_retriever_respects_top_k():
    retriever = Retriever(
        chunks=create_chunks(),
        embedding_model=FakeEmbeddingModel(),
    )

    results = retriever.search(
        "pregunta",
        top_k=2,
    )

    assert len(results) == 2


@pytest.mark.parametrize("top_k, expected", [(0, 0), (10, 3)])
def test_retriever_top_k_boundaries(top_k, expected):
    retriever = Retriever(create_chunks(), FakeEmbeddingModel())
    assert len(retriever.search("pregunta", top_k=top_k)) == expected


def test_retriever_rejects_negative_top_k():
    retriever = Retriever(create_chunks(), FakeEmbeddingModel())
    with pytest.raises(ValueError, match="top_k"):
        retriever.search("pregunta", top_k=-1)


def test_retriever_rejects_blank_query():
    retriever = Retriever(create_chunks(), FakeEmbeddingModel())
    with pytest.raises(ValueError, match="query"):
        retriever.search(" \n ")


def test_empty_corpus_does_not_call_model():
    class UnavailableModel:
        def embed_query(self, text):
            raise AssertionError("Model should not be called")

        def embed_passages(self, texts):
            raise AssertionError("Model should not be called")

    assert Retriever([], UnavailableModel()).search("pregunta") == []


@pytest.mark.parametrize("embedding_count", [2, 4])
def test_retriever_rejects_mismatched_embedding_count(embedding_count):
    class MismatchedEmbeddingModel(FakeEmbeddingModel):
        def embed_passages(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in range(embedding_count)]

    with pytest.raises(ValueError, match="one embedding per chunk"):
        Retriever(create_chunks(), MismatchedEmbeddingModel())


def test_similarity_rejects_different_dimensions():
    with pytest.raises(ValueError):
        similarity([1.0], [1.0, 2.0])
