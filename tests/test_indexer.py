"""Persistent indexing, restart, and query integration without model downloads."""

import pytest

from rag_bogado.indexing.indexer import DocumentIndexer, index_identity
from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.persistent_retriever import PersistentRetriever
from rag_bogado.retrieval.retriever import Retriever
from rag_bogado.retrieval.vector_store import QdrantVectorStore


class Model:
    def __init__(self):
        self.passages = []

    def embed_passages(self, texts):
        self.passages.extend(texts)
        return [[1.0, 0.0] if text == "First" else [0.0, 1.0] for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def chunks():
    return [Chunk(0, "First", "a.pdf", 1), Chunk(0, "Second", "a.pdf", 2)]


def test_restart_queries_match_reference_without_reembedding(tmp_path):
    model = Model()
    identity = index_identity(chunks(), {"revision": "fixed"})
    with QdrantVectorStore(tmp_path, identity, dimension=2) as store:
        assert DocumentIndexer(store, model).ensure_index(chunks(), identity) == 2
    assert model.passages == ["First", "Second"]

    class QueryOnlyModel(Model):
        def embed_passages(self, texts):
            raise AssertionError("Reopening must not embed passages")

    with QdrantVectorStore(tmp_path, identity, dimension=2) as store:
        model = QueryOnlyModel()
        indexer = DocumentIndexer(store, model)
        assert indexer.ensure_index(chunks(), identity, reuse_only=True) == 0
        assert indexer.ensure_index(chunks(), identity) == 0
        results = PersistentRetriever(store, model).search("question")
        assert results == Retriever(chunks(), Model()).search("question")


def test_interrupted_index_rejects_reuse_and_resumes_missing_passages(tmp_path):
    class FailingModel(Model):
        def embed_passages(self, texts):
            if texts == ["Second"]:
                raise RuntimeError("Interrupted")
            return super().embed_passages(texts)

    with QdrantVectorStore(tmp_path, "test", dimension=2) as store:
        with pytest.raises(RuntimeError, match="Interrupted"):
            DocumentIndexer(store, FailingModel()).ensure_index(
                chunks(), "v1", batch_size=1
            )
    with QdrantVectorStore(tmp_path, "test", dimension=2) as store:
        model = Model()
        indexer = DocumentIndexer(store, model)
        with pytest.raises(ValueError, match="incomplete"):
            indexer.ensure_index(chunks(), "v1", reuse_only=True)
        assert model.passages == []
        assert indexer.ensure_index(chunks(), "v1") == 1
        assert model.passages == ["Second"]
        assert indexer.ensure_index(chunks(), "v1", reuse_only=True) == 0


def test_foreign_index_and_duplicate_passages_are_rejected(tmp_path):
    with QdrantVectorStore(tmp_path, "test", dimension=2) as store:
        indexer = DocumentIndexer(store, Model())
        indexer.ensure_index(chunks(), "v1")
        with pytest.raises(ValueError, match="outside"):
            indexer.ensure_index(chunks(), "v2")
        with pytest.raises(ValueError, match="Duplicate"):
            indexer.ensure_index([chunks()[0], chunks()[0]], "v1")


def test_identity_changes_with_corpus_processing_or_model():
    original = index_identity(chunks(), {"model": "a", "size": 800})
    assert original == index_identity(chunks(), {"size": 800, "model": "a"})
    assert original != index_identity(chunks(), {"model": "b", "size": 800})
    assert original != index_identity(chunks(), {"model": "a", "size": 900})
    assert original != index_identity(chunks()[:1], {"model": "a", "size": 800})


def test_query_validation_and_empty_index_do_not_call_model(tmp_path):
    class UnavailableModel:
        def embed_query(self, text):
            raise AssertionError("No embedding expected")

    with QdrantVectorStore(tmp_path, "test", dimension=2) as store:
        retriever = PersistentRetriever(store, UnavailableModel())
        assert retriever.search("question") == []
        assert retriever.search("question", top_k=0) == []
        with pytest.raises(ValueError, match="query"):
            retriever.search(" ")
        with pytest.raises(ValueError, match="top_k"):
            retriever.search("question", top_k=-1)
