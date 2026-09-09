"""Coordinate complete vector indexes with the catalog's active version."""

from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.indexer import DocumentIndexer, index_identity
from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.embeddings import EmbeddingModel
from rag_bogado.retrieval.persistent_retriever import PersistentRetriever
from rag_bogado.retrieval.vector_store import QdrantVectorStore


def publish_index(
    catalog: DocumentCatalog,
    *,
    document_id: str,
    title: str,
    source_path: Path,
    chunks: list[Chunk],
    configuration: dict,
    store_path: Path,
    model: EmbeddingModel,
    batch_size: int = 64,
) -> dict:
    """Build/verify vectors before atomically switching the catalog pointer.

    One immutable collection per index keeps the previously active version intact
    during failure. The local Qdrant lock serializes builders using the same path.
    A hard process termination may leave a preparing run; retry creates a new
    attempt and resumes existing vectors. Old attempts remain as history.
    """
    identity = index_identity(chunks, configuration)
    collection = "index_" + identity
    with QdrantVectorStore(
        store_path, collection, dimension=configuration["dimension"]
    ) as store:
        run_id = catalog.start_run(
            document_id=document_id,
            title=title,
            content_hash=configuration["corpus_sha256"],
            source_path=source_path,
            index_id=identity,
            collection=collection,
            store_path=store_path,
            configuration=configuration,
            expected_chunks=len(chunks),
        )
        try:
            indexer = DocumentIndexer(store, model)
            embedded = indexer.ensure_index(chunks, identity, batch_size=batch_size)
            indexer.ensure_index(chunks, identity, reuse_only=True)
            catalog.activate(run_id)
        except Exception as error:
            catalog.fail(run_id, str(error))
            raise
    return {"run_id": run_id, "index_id": identity, "embedded_passages": embedded}


def query_active(
    catalog: DocumentCatalog,
    document_id: str,
    question: str,
    *,
    top_k: int = 5,
    model_factory=EmbeddingModel,
) -> dict:
    """Query only the active version, loading its pinned model without the PDF."""
    if not question.strip() or top_k < 0:
        raise ValueError("A nonblank question and nonnegative top_k are required")
    active = catalog.active_index(document_id)
    config = active["configuration"]
    for dependency, expected_version in config.get(
        "embedding_dependencies", {}
    ).items():
        if version(dependency) != expected_version:
            raise ValueError("Embedding dependencies changed; reindex before querying")
    with QdrantVectorStore(
        Path(active["store_path"]),
        active["collection_name"],
        dimension=config["dimension"],
        create_if_missing=False,
    ) as store:
        if (
            store.client.count(store.collection, exact=True).count
            != active["expected_chunks"]
        ):
            raise ValueError("Active index is incomplete; reindex before querying")
        model = model_factory(
            config["model"], revision=config["revision"], local_files_only=True
        )
        results = PersistentRetriever(store, model).search(question, top_k=top_k)
    return {
        "document_id": document_id,
        "version_id": active["version_id"],
        "content_hash": active["content_hash"],
        "source_path": active["source_path"],
        "index_id": active["index_id"],
        "question": question,
        "results": [asdict(result) for result in results],
    }
