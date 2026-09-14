"""Unsupported drafts and failed reviewers must never become accepted answers."""

import json

import pytest

from rag_bogado.generation.generator import GenerationError, OllamaGenerator
from rag_bogado.generation.support import review_answer


def verdict(**changes):
    return dict(
        id=0, supported=True, relevant=True, qualifications_preserved=True, **changes
    )


def answer():
    return {
        "question": "When?",
        "status": "answered",
        "claims": [{"text": "Before use.", "citations": ["S1"]}],
        "sources": [
            {"id": "S1", "text": "Before use."},
            {"id": "S2", "text": "Uncited evidence."},
        ],
    }


class Reviewer:
    model = "fake"

    def __init__(self, reviews):
        self.reviews = reviews
        self.inputs = []

    def request(self, path, payload):
        self.inputs.append(json.loads(payload["messages"][1]["content"]))
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps({"reviews": self.reviews})},
        }


def test_review_sees_only_the_claims_own_citations():
    reviewer = Reviewer([verdict()])
    result = review_answer(answer(), reviewer)
    assert result["status"] == "passed"
    assert result["human_verified"] is False
    assert reviewer.inputs[0]["claims"][0]["sources"] == answer()["sources"][:1]


@pytest.mark.parametrize("flag", ["supported", "relevant", "qualifications_preserved"])
def test_any_negative_verdict_rejects_the_whole_draft(flag):
    review = verdict()
    review[flag] = False
    assert review_answer(answer(), Reviewer([review]))["status"] == "rejected"


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [verdict(), verdict()],
        [{}],
        [{**verdict(), "id": 1}],
        [{**verdict(), "supported": "true"}],
        [{**verdict(), "id": False}],
    ],
)
def test_missing_or_invalid_verdicts_cannot_approve(reviews):
    with pytest.raises(ValueError):
        review_answer(answer(), Reviewer(reviews))


def test_reviewer_failure_propagates():
    reviewer = Reviewer([])
    reviewer.request = lambda *args: {"done": True, "done_reason": "length"}
    with pytest.raises(GenerationError):
        review_answer(answer(), reviewer)


def test_abstention_needs_no_reviewer_call():
    result = review_answer(
        dict(answer(), status="insufficient_evidence", claims=[]), None
    )
    assert result["status"] == "not_applicable"


def test_rejected_generation_does_not_expose_draft_claims(monkeypatch):
    generator = OllamaGenerator()
    draft = {"status": "answered", "claims": answer()["claims"]}

    def respond(path, payload):
        if "reviews" in payload["format"]["properties"]:
            content = {"reviews": [{**verdict(), "supported": False}]}
        else:
            content = draft
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(content)},
        }

    monkeypatch.setattr(generator, "request", respond)
    query = {
        "document_id": "doc",
        "version_id": 1,
        "content_hash": "hash",
        "index_id": "index",
        "source_path": "original.pdf",
        "question": "When?",
        "results": [
            {
                "score": 0.9,
                "chunk": {
                    "source": "doc.pdf",
                    "page_number": 1,
                    "chunk_id": 0,
                    "text": "No timing here.",
                },
            }
        ],
    }
    result = generator.generate(query, answer_mode="synthesis")
    assert result["claims"] == []
    assert result["status"] == "insufficient_evidence"
    assert result["support_review"]["status"] == "rejected"
    assert "Before use." not in json.dumps(result)
