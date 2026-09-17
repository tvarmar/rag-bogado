"""Fusion must preserve unique evidence, provenance and the original intent."""

import copy
import json

import pytest

from rag_bogado.generation.multi_query import fuse_queries, retrieve_questions


def query(question, ids, version=1):
    return {
        "question": question,
        "document_id": "doc",
        "version_id": version,
        "content_hash": "hash",
        "index_id": "index",
        "results": [
            {
                "score": 0.9 - rank / 100,
                "chunk": {
                    "source": "doc.pdf",
                    "page_number": 1,
                    "chunk_id": chunk,
                    "text": f"Original evidence {chunk}",
                },
            }
            for rank, chunk in enumerate(ids)
        ],
    }


class Rewriter:
    model = "fake"

    def __init__(self, rewrite):
        self.rewrite = rewrite

    def request(self, path, payload):
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps({"query": self.rewrite})},
        }


def test_fusion_promotes_agreement_without_discarding_unique_evidence():
    first, second = query("Original", [1, 2, 3]), query("Rewrite", [4, 2, 5])
    original = copy.deepcopy(first)
    fused = fuse_queries([first, second])
    assert [r["chunk"]["chunk_id"] for r in fused["results"]] == [2, 1, 4, 3, 5]
    assert fused["question"] == "Original"
    assert first == original
    assert fused["results"][0]["score"] == 0.89
    assert fused["results"][0]["fusion_score"] == pytest.approx(2 / 62)
    assert len(fused["results"][0]["retrieval_hits"]) == 2


def test_duplicate_within_ranking_cannot_vote_twice():
    result = fuse_queries([query("Original", [1, 1]), query("Other", [])])
    assert len(result["results"]) == 1
    assert result["results"][0]["fusion_score"] == pytest.approx(1 / 61)


@pytest.mark.parametrize(
    "field", ["document_id", "version_id", "content_hash", "index_id"]
)
def test_fusion_rejects_mixed_document_identity(field):
    second = query("Rewrite", [2])
    second[field] = "changed"
    with pytest.raises(ValueError, match="version changed"):
        fuse_queries([query("Original", [1]), second])


def test_conflicting_text_under_same_point_is_rejected():
    first, second = query("Original", [1]), query("Rewrite", [1])
    second["results"][0]["chunk"]["text"] = "Altered evidence"
    with pytest.raises(ValueError, match="Conflicting"):
        fuse_queries([first, second])


def test_two_searches_preserve_original_question_and_both_rankings():
    seen = []

    def retrieve(text):
        seen.append(text)
        return query(text, [len(seen)])

    result = retrieve_questions("Original", Rewriter("Rewrite"), retrieve)
    assert seen == ["Original", "Rewrite"]
    assert result["question"] == "Original"
    assert result["retrieval"]["queries"] == seen
    assert len(result["results"]) == 2


def test_identical_rewrite_is_not_a_second_vote():
    result = retrieve_questions(
        "Original", Rewriter("original"), lambda text: query(text, [1])
    )
    assert len(result["retrieval"]["rankings"]) == 1
    assert result["results"][0]["fusion_score"] == pytest.approx(1 / 61)


def test_baseline_does_not_call_rewriter():
    result = retrieve_questions(
        "Original", None, lambda q: query(q, [1]), search_count=1
    )
    assert result["retrieval"]["queries"] == ["Original"]


@pytest.mark.parametrize("rewrite", ["", " ", 3, [], "x" * 5000])
def test_invalid_rewrite_stops_before_search(rewrite):
    with pytest.raises(ValueError, match="rewrite"):
        retrieve_questions(
            "Original", Rewriter(rewrite), lambda _: pytest.fail("Must not search")
        )


def test_mismatched_returned_question_is_rejected():
    with pytest.raises(ValueError, match="different question"):
        retrieve_questions(
            "Original", Rewriter("Rewrite"), lambda _: query("Other", [1])
        )
