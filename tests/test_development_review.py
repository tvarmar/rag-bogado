"""Joint review must never select reserved questions for development runs."""

import json
import runpy
from pathlib import Path

import pytest


@pytest.fixture
def load_cases():
    script = Path(__file__).resolve().parents[1] / "scripts/evaluate_multi_query.py"
    return runpy.run_path(str(script))["load_cases"]


def test_reserved_cases_cannot_be_selected(load_cases, tmp_path):
    dataset = tmp_path / "questions.json"
    dataset.write_text(
        json.dumps(
            {
                "development": [{"id": "d01", "question": "Development?"}],
                "held_out": [{"id": "h01", "question": "Reserved?"}],
            }
        )
    )
    assert [case["id"] for case in load_cases(dataset)] == ["d01"]
    with pytest.raises(ValueError, match="Unknown development"):
        load_cases(dataset, ["h01"])


def test_case_selection_preserves_review_metadata(load_cases, tmp_path):
    dataset = tmp_path / "questions.json"
    cases = [
        {"id": "d01", "question": "First?"},
        {"id": "d02", "question": "Second?", "requested_parts": ["A", "B"]},
    ]
    dataset.write_text(json.dumps({"development": cases}))
    assert load_cases(dataset, ["d02"]) == [cases[1]]


def test_duplicate_ids_rejected_before_evaluation(load_cases, tmp_path):
    dataset = tmp_path / "questions.json"
    case = {"id": "d01", "question": "Question?"}
    dataset.write_text(json.dumps({"development": [case, case]}))
    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(dataset)


def test_replay_can_keep_all_sources_of_a_rejected_synthesis():
    script = Path(__file__).resolve().parents[1] / "scripts/review_saved_answer.py"
    select = runpy.run_path(str(script))["select_sources"]
    sources = [{"id": "Q2-S1", "text": "Complete evidence."}]
    answer = {"answer_mode": "synthesis", "claims": [], "sources": sources}
    assert select(answer, "all") == sources
    with pytest.raises(ValueError, match="literal"):
        select(answer, "literal")


def test_literal_replay_rejects_modified_source_text():
    script = Path(__file__).resolve().parents[1] / "scripts/review_saved_answer.py"
    select = runpy.run_path(str(script))["select_sources"]
    answer = {
        "answer_mode": "evidence",
        "claims": [{"text": "Altered.", "citations": ["S1"]}],
        "sources": [{"id": "S1", "text": "Original."}],
    }
    with pytest.raises(ValueError, match="differs"):
        select(answer, "literal")


def test_replay_fails_before_model_call_if_context_would_drop_a_source(
    tmp_path, monkeypatch
):
    script = Path(__file__).resolve().parents[1] / "scripts/review_saved_answer.py"
    saved = tmp_path / "saved.json"
    answer = dict.fromkeys(
        ("document_id", "version_id", "content_hash", "index_id", "source_path"),
        "test",
    )
    answer.update(
        question_id="Q1",
        question="Question?",
        sources=[
            {
                "id": "S1",
                "document": "doc",
                "page": 1,
                "chunk_id": 0,
                "text": "x" * 9000,
            }
        ],
    )
    saved.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "case": "simple",
                        "search_count": 1,
                        "result": {"answers": [answer]},
                    }
                ]
            }
        )
    )
    output = tmp_path / "output"
    monkeypatch.setattr(
        "sys.argv",
        [
            str(script),
            "--source-report",
            str(saved),
            "--source-mode",
            "all",
            "--output-dir",
            str(output),
        ],
    )
    with pytest.raises(ValueError, match="drop saved sources"):
        runpy.run_path(str(script), run_name="__main__")
    assert not output.exists()
