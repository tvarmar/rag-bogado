"""Query an already indexed collection without embedding its passages."""

from rag_bogado.retrieval.embeddings import EmbeddingModel
from rag_bogado.retrieval.retriever import SearchResult
from rag_bogado.retrieval.vector_store import QdrantVectorStore


class PersistentRetriever:
    def __init__(self, store: QdrantVectorStore, model: EmbeddingModel) -> None:
        self.store = store
        self.model = model

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        if top_k < 0:
            raise ValueError("top_k cannot be negative")
        if not query.strip():
            raise ValueError("query cannot be blank")
        if (
            top_k == 0
            or self.store.client.count(self.store.collection, exact=True).count == 0
        ):
            return []
        return self.store.search(self.model.embed_query(query), top_k=top_k)
