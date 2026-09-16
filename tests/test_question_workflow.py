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
        if "query" in payload["format"].get("properties", {}):
            question = json.loads(payload["messages"][1]["content"])["question"]
            return {
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps({"query": question})},
            }
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
        "results": [
            {
                "score": 0.9,
                "chunk": {
                    "source": "doc.pdf",
                    "page_number": 1,
                    "chunk_id": 0,
                    "text": question,
                },
            }
        ],
    }


def test_each_question_has_independent_retrieval_and_citations():
    generator = FakeGenerator(["First?", "Second?", "Third?"])
    seen = []

    def tracked(question):
        seen.append(question)
        return retrieve(question)

    result = answer_questions("Original compound question", generator, tracked)
    assert seen == ["First?", "Second?", "Third?"]
    assert [q["results"][0]["chunk"]["text"] for q in generator.contexts] == seen
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


def test_pipeline_searches_twice_but_generates_once_per_original_question():
    generator = FakeGenerator(["First?", "Second?"])
    original_request = generator.request

    def respond(path, payload):
        if "query" in payload["format"]["properties"]:
            question = json.loads(payload["messages"][1]["content"])["question"]
            return {
                "done": True,
                "done_reason": "stop",
                "message": {"content": json.dumps({"query": question + " rewritten"})},
            }
        return original_request(path, payload)

    generator.request = respond
    seen = []

    def search(question):
        seen.append(question)
        original = question.removesuffix(" rewritten")
        return dict(retrieve(original), question=question)

    result = answer_questions("Compound", generator, search)
    assert result["status"] == "answered"
    assert seen == ["First?", "First? rewritten", "Second?", "Second? rewritten"]
    assert [q["question"] for q in generator.contexts] == ["First?", "Second?"]
    assert all(len(q["results"][0]["retrieval_hits"]) == 2 for q in generator.contexts)


def test_invalid_search_count_rejected_before_model_call():
    with pytest.raises(ValueError, match="Search count"):
        answer_questions("Original", None, None, search_count=3)


def test_rejected_first_question_remains_visible_when_second_answers():
    generator = FakeGenerator(["Who?", "When install and remove?"])
    generate = generator.generate

    def respond(query, **options):
        if query["question"] == "Who?":
            return dict(
                query,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                support_review={"status": "rejected"},
            )
        return generate(query, **options)

    generator.generate = respond
    result = answer_questions("Who and when?", generator, retrieve, search_count=1)
    assert result["status"] == "partial"
    assert [a["question"] for a in result["answers"]] == [
        "Who?",
        "When install and remove?",
    ]
    assert result["answers"][0]["answer_state"] == "review_rejected"
    assert result["answers"][0]["display_message"]
    assert result["answers"][0]["claims"] == []
    assert result["answers"][1]["claims"][0]["citations"] == ["Q2-S1"]
    assert result["unanswered_questions"] == [
        {"question_id": "Q1", "question": "Who?", "reason": "review_rejected"}
    ]


def test_abstention_error_and_rejection_are_distinct_outcomes():
    result = answer_questions(
        "Several",
        FakeGenerator(["First?", "Missing?", "Failed?"]),
        retrieve,
        search_count=1,
    )
    assert [a["answer_state"] for a in result["answers"]] == [
        "answered",
        "abstained",
        "error",
    ]
    assert [q["reason"] for q in result["unanswered_questions"]] == [
        "abstained",
        "error",
    ]


def test_single_question_cannot_drop_an_enumerated_subject():
    original = "What requirements apply to students and teachers?"
    generator = FakeGenerator(["What requirements apply to students?"])
    result = answer_questions(original, generator, retrieve, search_count=1)
    assert result["decomposition"]["questions"] == [original]
    assert result["decomposition"]["single_question_restored"] is True
    assert result["decomposition"]["proposed_questions"] == generator.questions
    assert generator.contexts[0]["question"] == original
    assert result["answers"][0]["question"] == original
