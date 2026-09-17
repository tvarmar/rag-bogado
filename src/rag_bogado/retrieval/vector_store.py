"""Persistent local storage for precomputed passage vectors."""

import json
import math
from dataclasses import asdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.retriever import SearchResult


def point_id(chunk: Chunk, index_id: str) -> str:
    """Identify a passage within a versioned processing run reproducibly."""
    identity = json.dumps([index_id, asdict(chunk)], sort_keys=True, ensure_ascii=False)
    return str(uuid5(NAMESPACE_URL, "rag-bogado:" + identity))


class QdrantVectorStore:
    """Own a local client; close it before another client opens the same path.

    Use one collection per corpus/model/processing configuration for now.
    Version activation and removal of obsolete passages belong to the future
    indexing/catalog layer; upsert alone does not replace a document.
    """

    def __init__(
        self,
        path: Path | str | None = None,
        collection: str = "",
        *,
        url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        client: QdrantClient | None = None,
        dimension: int = 384,
        create_if_missing: bool = True,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        if not collection.strip():
            raise ValueError("collection cannot be blank")
        self.collection = collection
        self.dimension = dimension
        if client is not None:
            self.client = client
        elif url is not None:
            self.client = QdrantClient(url=url)
        elif host is not None:
            self.client = QdrantClient(host=host, port=port or 6333)
        elif path is not None:
            str_path = str(path)
            if str_path.startswith(("http://", "https://")):
                self.client = QdrantClient(url=str_path)
            else:
                self.client = QdrantClient(path=str_path)
        else:
            raise ValueError("Either path, url, host, or client must be provided")
        try:
            if self.client.collection_exists(collection):
                config = self.client.get_collection(collection).config.params.vectors
                if (
                    not isinstance(config, models.VectorParams)
                    or config.size != dimension
                    or config.distance != models.Distance.DOT
                ):
                    raise ValueError("Collection must match dimension and DOT distance")
            else:
                if not create_if_missing:
                    raise ValueError("The catalog's vector collection is missing")
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=models.VectorParams(
                        size=dimension, distance=models.Distance.DOT
                    ),
                )
        except Exception:
            self.client.close()
            raise

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "QdrantVectorStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _validate_vector(self, vector: list[float]) -> None:
        if len(vector) != self.dimension:
            raise ValueError(f"Expected vector dimension {self.dimension}")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("Vector values must be finite")

    def upsert(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
        *,
        index_id: str,
        batch_size: int = 64,
    ) -> None:
        """Insert or replace matching IDs; validate all vectors before writing.

        index_id must identify document version and processing configuration,
        including the embedding model revision. Reusing it with unchanged chunks
        is idempotent. Multiple batches are not a single transaction.
        """
        if not index_id.strip():
            raise ValueError("index_id cannot be blank")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if len(chunks) != len(vectors):
            raise ValueError("Expected one vector per chunk")
        for vector in vectors:
            self._validate_vector(vector)
        for start in range(0, len(chunks), batch_size):
            self.client.upsert(
                collection_name=self.collection,
                wait=True,
                points=[
                    models.PointStruct(
                        id=point_id(chunk, index_id),
                        vector=vector,
                        payload={**asdict(chunk), "index_id": index_id},
                    )
                    for chunk, vector in zip(
                        chunks[start : start + batch_size],
                        vectors[start : start + batch_size],
                        strict=True,
                    )
                ],
            )

    def search(self, query_vector: list[float], top_k: int = 10) -> list[SearchResult]:
        """Search saved vectors without embedding or inserting passages."""
        if top_k < 0:
            raise ValueError("top_k cannot be negative")
        self._validate_vector(query_vector)
        if top_k == 0:
            return []
        points = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points
        results = []
        for point in points:
            payload = point.payload or {}
            results.append(
                SearchResult(
                    score=point.score,
                    chunk=Chunk(
                        chunk_id=payload["chunk_id"],
                        text=payload["text"],
                        source=payload["source"],
                        page_number=payload.get("page_number", 0),
                        article=payload.get("article"),
                        unit_type=payload.get("unit_type"),
                    ),
                )
            )
        return results
