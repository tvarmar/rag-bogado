"""Question isolation, abstention, and visible failures across a compound query."""

import json

import pytest

from rag_bogado.generation.generator import GenerationError
from rag_bogado.generation.questions import split_questions
from rag_bogado.generation.service import answer_questions


class FakeGenerator:
    model = "fake"

    def __init__(self, questions):
        self.questions = questions
        self.contexts = []

    def request(self, path, payload):
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps({"questions": self.questions})},
        }

    def generate(self, query, **options):
        self.contexts.append(query)
        if query["question"] == "Missing?":
            return dict(query, status="insufficient_evidence", claims=[], sources=[])
        if query["question"] == "Failed?":
            raise ValueError("Invalid generated citation")
        return dict(
            query,
            status="answered",
            sources=[{"id": "S1", "text": query["results"][0], "page": 1}],
            claims=[{"text": "Supported", "citations": ["S1"]}],
        )


def retrieve(question):
    return {
        "question": question,
        "document_id": "doc",
        "version_id": 1,
        "content_hash": "hash",
        "index_id": "index",
        "results": [question],
    }


def test_each_question_has_independent_retrieval_and_citations():
    generator = FakeGenerator(["First?", "Second?", "Third?"])
    seen = []

    def tracked(question):
        seen.append(question)
        return retrieve(question)

    result = answer_questions("Original compound question", generator, tracked)
    assert seen == ["First?", "Second?", "Third?"]
    assert [q["results"] for q in generator.contexts] == [[q] for q in seen]
    assert result["status"] == "answered"
    assert [a["question_id"] for a in result["answers"]] == ["Q1", "Q2", "Q3"]
    for index, answer in enumerate(result["answers"], 1):
        assert answer["claims"][0]["citations"] == [f"Q{index}-S1"]
        assert answer["sources"][0]["id"] == f"Q{index}-S1"
    assert result["decomposition"]["semantic_coverage_verified"] is False


def test_missing_evidence_does_not_hide_or_block_other_answers():
    result = answer_questions(
        "Compound", FakeGenerator(["First?", "Missing?", "Last?"]), retrieve
    )
    assert result["status"] == "partial"
    assert [a["status"] for a in result["answers"]] == [
        "answered",
        "insufficient_evidence",
        "answered",
    ]
    assert result["answers"][1]["question"] == "Missing?"


def test_failure_does_not_become_abstention_or_drop_an_answer():
    result = answer_questions("Compound", FakeGenerator(["Failed?", "Last?"]), retrieve)
    assert result["status"] == "partial"
    assert result["answers"][0]["status"] == "error"
    assert result["answers"][1]["status"] == "answered"


def test_changed_version_is_not_silently_mixed():
    def changed(question):
        return dict(retrieve(question), version_id=2 if question == "Second?" else 1)

    generator = FakeGenerator(["First?", "Second?"])
    result = answer_questions("Compound", generator, changed)
    assert len(generator.contexts) == 1
    assert "version changed" in result["answers"][1]["error"]


@pytest.mark.parametrize("questions", [[], [""], ["same", "SAME"], [1], ["x"] * 7])
def test_invalid_decomposition_rejected_before_retrieval(questions):
    with pytest.raises(GenerationError):
        answer_questions(
            "Compound",
            FakeGenerator(questions),
            lambda _: pytest.fail("Must not retrieve"),
        )


def test_single_question_keeps_a_single_answer():
    result = answer_questions("Single?", FakeGenerator(["Single?"]), retrieve)
    assert len(result["answers"]) == 1
    assert result["answers"][0]["question"] == "Single?"


def test_truncated_split_rejected():
    generator = FakeGenerator(["First?"])
    generator.request = lambda *args: {"done": True, "done_reason": "length"}
    with pytest.raises(GenerationError, match="did not finish"):
        split_questions("Compound?", generator)


def test_question_budget_checked_before_model_call():
    with pytest.raises(ValueError, match="budget"):
        split_questions("ñ" * 10000, FakeGenerator(["Ignored?"]))


def test_no_answer_with_mixed_errors_is_not_reported_as_partial_success():
    result = answer_questions(
        "Compound", FakeGenerator(["Missing?", "Failed?"]), retrieve
    )
    assert result["status"] == "error"
    assert len(result["answers"]) == 2


def test_all_questions_can_abstain():
    generator = FakeGenerator(["First?", "Second?"])
    generator.generate = lambda query, **kw: dict(
        query, status="insufficient_evidence", sources=[], claims=[]
    )
    result = answer_questions("Compound", generator, retrieve)
    assert result["status"] == "insufficient_evidence"


def test_failed_retrieval_keeps_following_questions():
    def failed(question):
        if question == "First?":
            raise OSError("Store unavailable")
        return retrieve(question)

    result = answer_questions("Compound", FakeGenerator(["First?", "Second?"]), failed)
    assert result["answers"][0]["status"] == "error"
    assert result["answers"][1]["status"] == "answered"


def test_mismatched_question_cannot_receive_an_answer():
    generator = FakeGenerator(["First?"])
    result = answer_questions("Original", generator, lambda _: retrieve("Other?"))
    assert result["status"] == "error"
    assert generator.contexts == []


def test_cli_routes_live_questions_through_separation(monkeypatch, capsys):
    import sys
    from contextlib import nullcontext

    from rag_bogado.generation import __main__ as cli

    generator = FakeGenerator(["First?", "Missing?"])
    monkeypatch.setattr(cli, "OllamaGenerator", lambda *args: generator)
    monkeypatch.setattr(cli, "DocumentCatalog", lambda _: nullcontext(object()))
    monkeypatch.setattr(cli, "query_active", lambda cat, doc, q, **kw: retrieve(q))
    monkeypatch.setattr(sys, "argv", ["generation", "--question", "Compound?"])
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "partial"
    assert [a["question"] for a in result["answers"]] == ["First?", "Missing?"]


def test_cli_evidence_replay_does_not_split_or_retrieve(tmp_path, monkeypatch, capsys):
    import sys

    from rag_bogado.generation import __main__ as cli

    evidence = tmp_path / "query.json"
    evidence.write_text(json.dumps(retrieve("First?")))
    generator = FakeGenerator([])
    generator.request = lambda *args: pytest.fail("Replay must not split")
    monkeypatch.setattr(cli, "OllamaGenerator", lambda *args: generator)
    monkeypatch.setattr(
        cli, "DocumentCatalog", lambda _: pytest.fail("Must not retrieve")
    )
    monkeypatch.setattr(sys, "argv", ["generation", "--evidence-json", str(evidence)])
    cli.main()
    assert json.loads(capsys.readouterr().out)["status"] == "answered"
