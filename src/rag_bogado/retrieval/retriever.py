from dataclasses import dataclass

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.embeddings import EmbeddingModel


@dataclass
class SearchResult:
    score: float
    chunk: Chunk


def similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        embedding_model: EmbeddingModel,
    ) -> None:
        self.chunks = chunks
        self.embedding_model = embedding_model

        self.embeddings = embedding_model.embed_passages(
            [chunk.text for chunk in chunks]
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        query_embedding = self.embedding_model.embed_query(query)

        results = []

        for chunk, embedding in zip(
            self.chunks,
            self.embeddings,
            strict=True,
        ):
            score = similarity(query_embedding, embedding)

            results.append(
                SearchResult(
                    score=score,
                    chunk=chunk,
                )
            )

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return results[:top_k]
