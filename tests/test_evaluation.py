import pytest

from rag_bogado.evaluation.metrics import evidence_rank, summarize
from rag_bogado.ingestion.chunker import Chunk
from rag_bogado.retrieval.retriever import SearchResult


def test_metrics_include_misses_in_denominator():
    assert summarize([1, 5, 10, None]) == {
        "hit@1": 0.25,
        "hit@5": 0.5,
        "hit@10": 0.75,
        "mrr@10": 0.325,
    }


def test_metrics_reject_empty_dataset():
    with pytest.raises(ValueError):
        summarize([])


def test_rank_requires_source_page_and_evidence():
    results = [
        SearchResult(0.9, Chunk(0, "evidencia", "other.pdf", 2)),
        SearchResult(0.8, Chunk(1, "evidencia", "test.pdf", 1)),
        SearchResult(0.7, Chunk(2, "irrelevante", "test.pdf", 2)),
        SearchResult(0.6, Chunk(3, "La EVIDENCIA\n correcta", "test.pdf", 2)),
    ]
    evidence = [{"page": 2, "reference": "Article 1", "anchor": "evidencia correcta"}]
    assert evidence_rank(results, "test.pdf", evidence) == 4
    evidence[0]["anchor"] = "ausente"
    assert evidence_rank(results, "test.pdf", evidence) is None


def test_rank_accepts_alternative_evidence_before_primary_reference():
    results = [
        SearchResult(0.9, Chunk(0, "Useful explanation", "test.pdf", 1)),
        SearchResult(0.8, Chunk(1, "Formal provision", "test.pdf", 2)),
    ]
    evidence = [
        {"page": 2, "reference": "Article 1", "anchor": "Formal provision"},
        {"page": 1, "reference": "Recital 1", "anchor": "Useful explanation"},
    ]
    assert evidence_rank(results, "test.pdf", evidence) == 1
    assert evidence_rank(results, "test.pdf", list(reversed(evidence))) == 1


def test_rank_does_not_accept_unlisted_evidence_for_specific_article_request():
    results = [SearchResult(0.9, Chunk(0, "Useful explanation", "test.pdf", 1))]
    evidence = [{"page": 2, "reference": "Article 1", "anchor": "Formal provision"}]
    assert evidence_rank(results, "test.pdf", evidence) is None


def test_rank_returns_none_for_negative_question_or_empty_results():
    results = [SearchResult(0.9, Chunk(0, "Some text", "test.pdf", 1))]
    evidence = [{"page": 1, "reference": "Article 1", "anchor": "Some text"}]
    assert evidence_rank(results, "test.pdf", []) is None
    assert evidence_rank([], "test.pdf", evidence) is None
