"""Exercise the public evaluation entry point with a deterministic local model."""

import hashlib
import json
import sys
from types import SimpleNamespace

from rag_bogado.evaluation import runner
from rag_bogado.ingestion.loader import Page


def test_evaluation_build_and_reuse_match_memory(tmp_path, monkeypatch):
    corpus = tmp_path / "fixture.pdf"
    corpus.write_bytes(b"fixture")
    questions = tmp_path / "questions.json"
    questions.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "corpus": corpus.name,
                "sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
                "relevance_policy": "test",
                "questions": [
                    {
                        "id": "q1",
                        "question": "Question?",
                        "evidence": [
                            {"page": 1, "reference": "fixture", "anchor": "Evidence"}
                        ],
                    }
                ],
            }
        )
    )
    passage_calls = []

    class Model:
        def __init__(self, *args, **kwargs):
            self.model = SimpleNamespace(
                device="cpu", get_embedding_dimension=lambda: 2
            )

        def embed_passages(self, texts):
            passage_calls.extend(texts)
            return [[1.0, 0.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 0.0]

    monkeypatch.setattr(runner, "EmbeddingModel", Model)
    monkeypatch.setattr(
        runner, "load_pdf", lambda path: [Page(1, "Evidence", corpus.name)]
    )
    reports = []
    for backend, mode in [
        ("memory", "build"),
        ("qdrant", "build"),
        ("qdrant", "reuse"),
    ]:
        output = tmp_path / f"{backend}-{mode}.json"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "evaluation",
                "--documents",
                str(tmp_path),
                "--questions",
                str(questions),
                "--output",
                str(output),
                "--backend",
                backend,
                "--index-mode",
                mode,
                "--store-path",
                str(tmp_path / "qdrant"),
            ],
        )
        runner.main()
        reports.append(json.loads(output.read_text()))
    assert passage_calls == ["Evidence", "Evidence"]
    assert [report["embedded_passages"] for report in reports] == [1, 1, 0]
    assert len({report["index_id"] for report in reports}) == 1
    assert all(report["metrics"] == reports[0]["metrics"] for report in reports)
    assert all(
        report["questions"][0]["results"] == reports[0]["questions"][0]["results"]
        for report in reports
    )
