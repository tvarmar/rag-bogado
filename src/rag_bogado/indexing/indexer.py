"""Identify an index and embed only passages missing from its collection."""

import hashlib
import json
from dataclasses import asdict

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.embeddings import EmbeddingModel
from rag_bogado.retrieval.vector_store import QdrantVectorStore, point_id


def index_identity(chunks: list[Chunk], configuration: dict) -> str:
    """Hash corpus/processing/model configuration and the actual ordered chunks."""
    content = json.dumps(
        {"configuration": configuration, "chunks": [asdict(c) for c in chunks]},
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(content.encode()).hexdigest()


class DocumentIndexer:
    def __init__(self, store: QdrantVectorStore, model: EmbeddingModel) -> None:
        self.store = store
        self.model = model

    def ensure_index(
        self,
        chunks: list[Chunk],
        index_id: str,
        *,
        reuse_only: bool = False,
        batch_size: int = 64,
    ) -> int:
        """Return the number of embedded passages; resume missing batches safely.

        The caller must use a collection dedicated to index_id. Query only after
        this method succeeds. This is a single-index completeness check, not a
        transactional document-version catalog.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not index_id.strip():
            raise ValueError("index_id cannot be blank")
        ids = [point_id(chunk, index_id) for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate passage identities")
        missing = []
        for start in range(0, len(ids), batch_size):
            present = self.store.client.retrieve(
                collection_name=self.store.collection,
                ids=ids[start : start + batch_size],
                with_payload=False,
                with_vectors=False,
            )
            present_ids = {str(point.id) for point in present}
            missing.extend(
                chunk
                for chunk, identifier in zip(
                    chunks[start : start + batch_size],
                    ids[start : start + batch_size],
                    strict=True,
                )
                if identifier not in present_ids
            )
        count = self.store.client.count(self.store.collection, exact=True).count
        if count != len(chunks) - len(missing):
            raise ValueError("Collection contains passages outside this index")
        if reuse_only and missing:
            raise ValueError(
                "Index is incomplete; build it before using --index-mode reuse"
            )
        for start in range(0, len(missing), batch_size):
            batch = missing[start : start + batch_size]
            vectors = self.model.embed_passages([chunk.text for chunk in batch])
            self.store.upsert(batch, vectors, index_id=index_id, batch_size=batch_size)
        return len(missing)
