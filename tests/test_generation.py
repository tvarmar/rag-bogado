"""Generation must preserve evidence and reject unverifiable output structure."""

import copy

import pytest

from rag_bogado.generation.generator import (
    OllamaGenerator,
    prepare_context,
    validate_answer,
)


@pytest.fixture
def query():
    return {
        "document_id": "test",
        "version_id": 1,
        "content_hash": "hash",
        "source_path": "/original.pdf",
        "index_id": "index",
        "question": "¿Qué dice?",
        "results": [
            {
                "score": 0.9,
                "chunk": {
                    "text": "Evidencia original.",
                    "source": "original.pdf",
                    "page_number": 2,
                    "chunk_id": 0,
                },
            }
        ],
    }


def test_sources_keep_exact_text_and_provenance(query):
    sources, messages = prepare_context(query)
    assert sources[0]["text"] == query["results"][0]["chunk"]["text"]
    assert (sources[0]["page"], sources[0]["version_id"]) == (2, 1)
    assert sources[0]["id"] in messages[1]["content"]


def test_duplicates_removed_but_complementary_passages_preserved(query):
    query["results"].append(copy.deepcopy(query["results"][0]))
    other = copy.deepcopy(query["results"][0])
    other["chunk"]["text"] = "original. Una excepción complementaria."
    other["chunk"]["chunk_id"] = 1
    query["results"].append(other)
    sources, _ = prepare_context(query)
    assert len(sources) == 2
    assert sources[1]["text"] == other["chunk"]["text"]


def test_oversized_passage_is_not_truncated(query):
    query["results"][0]["chunk"]["text"] = "x" * 10000
    assert prepare_context(query)[0] == []
    query["question"] = "x" * 10000
    with pytest.raises(ValueError, match="exceed"):
        prepare_context(query)


def test_no_evidence_never_calls_model(query, monkeypatch):
    generator = OllamaGenerator()

    def unexpected(*args):
        pytest.fail("Empty evidence must not call model")

    monkeypatch.setattr(generator, "request", unexpected)
    result = generator.generate(query, min_score=0.95)
    assert result["status"] == "insufficient_evidence"
    assert result["claims"] == []


@pytest.mark.parametrize(
    "answer",
    [
        {"status": "answered", "claims": []},
        {
            "status": "insufficient_evidence",
            "claims": [{"text": "X", "citations": ["S1"]}],
        },
        {"status": "answered", "claims": [{"text": "X", "citations": ["S99"]}]},
        {"status": "answered", "claims": [{"text": "X", "citations": []}]},
        {"status": "answered", "claims": [{"text": "", "citations": ["S1"]}]},
    ],
)
def test_invalid_claims_rejected(query, answer):
    with pytest.raises(ValueError):
        validate_answer(answer, prepare_context(query)[0])


def test_truncated_generation_is_rejected(query, monkeypatch):
    generator = OllamaGenerator()
    monkeypatch.setattr(
        generator,
        "request",
        lambda *args: {
            "done": True,
            "done_reason": "length",
            "message": {"content": "{}"},
        },
    )
    with pytest.raises(ValueError, match="did not finish"):
        generator.generate(query)


def test_successful_generation_preserves_sources_and_metrics(query, monkeypatch):
    import json

    generator = OllamaGenerator()
    answer = {
        "status": "answered",
        "claims": [{"text": "Una afirmación respaldada.", "citations": ["S1"]}],
    }
    calls = []

    def respond(path, payload):
        calls.append((path, payload))
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(answer)},
            "prompt_eval_count": 150,
            "eval_count": 30,
        }

    monkeypatch.setattr(generator, "request", respond)
    result = generator.generate(query)
    assert result["claims"] == answer["claims"]
    assert result["sources"][0]["text"] == "Evidencia original."
    assert result["content_hash"] == query["content_hash"]
    assert result["metrics"]["eval_count"] == 30
    assert result["semantic_support_reviewed"] is False
    assert calls[0][1]["options"]["num_ctx"] == 4096
    assert calls[0][1]["stream"] is False


def test_context_selection_respects_count_and_byte_budget(query):
    for page in range(3, 10):
        result = copy.deepcopy(query["results"][0])
        result["chunk"]["page_number"] = page
        result["chunk"]["text"] = "ñ" * 200
        query["results"].append(result)
    sources, messages = prepare_context(query, max_passages=3)
    assert len(sources) == 3
    used = sum(len(m["content"].encode("utf-8")) for m in messages)
    assert used + 256 + 512 <= 4096
