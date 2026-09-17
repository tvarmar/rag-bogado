"""Compare one/two searches with equal final budgets and mandatory support review."""

import argparse
import json
from pathlib import Path

from rag_bogado.generation.generator import (
    EVIDENCE_PROMPT,
    EVIDENCE_SCHEMA,
    SCHEMA,
    SYSTEM_PROMPT,
    OllamaGenerator,
)
from rag_bogado.generation.multi_query import REWRITE_PROMPT, REWRITE_SCHEMA
from rag_bogado.generation.questions import (
    QUESTION_PROMPT,
    QUESTION_SCHEMA,
    split_questions,
)
from rag_bogado.generation.service import answer_questions
from rag_bogado.generation.support import SUPPORT_PROMPT, SUPPORT_SCHEMA
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active

CASES = [
    ("simple", "¿Quién debe procurar la alfabetización en IA?"),
    (
        "compound",
        "¿Quién debe procurar la alfabetización en IA y cuándo debe prepararse "
        "y actualizarse la documentación técnica de una IA de alto riesgo?",
    ),
    (
        "mixed",
        "¿Cuándo se elabora la documentación técnica de un sistema de IA de alto "
        "riesgo? ¿Cuál es el número de teléfono del delegado de protección de datos "
        "de mi empresa?",
    ),
]


def load_cases(dataset=None, selected=None):
    """Select development cases only; never execute a dataset's held-out split."""
    cases = (
        [{"id": name, "question": question} for name, question in CASES]
        if dataset is None
        else json.loads(dataset.read_text())["development"]
    )
    if not isinstance(cases, list) or not cases:
        raise ValueError("Expected nonempty development cases")
    ids = []
    for case in cases:
        if not isinstance(case, dict) or any(
            not isinstance(case.get(key), str) or not case[key].strip()
            for key in ("id", "question")
        ):
            raise ValueError("Each development case needs an id and question")
        ids.append(case["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate development case ids")
    if selected and not set(selected) <= set(ids):
        raise ValueError("Unknown development case id")
    return [case for case in cases if not selected or case["id"] in selected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, help="Read only its development split")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--search-count", type=int, choices=(1, 2), action="append")
    parser.add_argument(
        "--split-only",
        action="store_true",
        help="Evaluate question separation without retrieval or answers",
    )
    parser.add_argument(
        "--record-drafts",
        action="store_true",
        help="Diagnostic: retain drafts separately from accepted answers",
    )
    parser.add_argument("--max-passages", type=int, default=5)
    parser.add_argument(
        "--relative-margin",
        type=float,
        default=0.025,
        help="Discard passages whose score drops below max_score - relative_margin",
    )
    parser.add_argument("--output-tokens", type=int, default=768)
    parser.add_argument(
        "--answer-mode", choices=("evidence", "synthesis"), default="evidence"
    )
    args = parser.parse_args()
    cases = load_cases(args.dataset, args.case_ids)
    args.output_dir.mkdir(parents=True, exist_ok=False)

    class DiagnosticGenerator(OllamaGenerator):
        def request(self, path, payload=None):
            response = super().request(path, payload)
            if (
                args.record_drafts
                and path == "/api/chat"
                and payload["format"] == SCHEMA
            ):
                drafts.append(
                    {
                        "input": json.loads(payload["messages"][1]["content"]),
                        "response": response,
                        "accepted_answer": False,
                    }
                )
            return response

    drafts = []
    generator = DiagnosticGenerator()
    report = {
        "scope": "known development cases; no held-out questions",
        "split_only": args.split_only,
        "development_cases": cases,
        "runtime": generator.request("/api/version"),
        "models": generator.request("/api/tags"),
        "prompts": {
            "evidence": EVIDENCE_PROMPT,
            "generation": SYSTEM_PROMPT,
            "rewrite": REWRITE_PROMPT,
            "separation": QUESTION_PROMPT,
            "support": SUPPORT_PROMPT,
        },
        "schemas": {
            "evidence": EVIDENCE_SCHEMA,
            "generation": SCHEMA,
            "rewrite": REWRITE_SCHEMA,
            "separation": QUESTION_SCHEMA,
            "support": SUPPORT_SCHEMA,
        },
        "configuration": {
            "answer_mode": args.answer_mode,
            "retrieve_k": 10,
            "max_passages": args.max_passages,
            "relative_margin": args.relative_margin,
            "context_tokens": 8192,
            "output_tokens": args.output_tokens,
        },
        "runs": [],
    }
    for case in cases:
        name, question = case["id"], case["question"]
        search_counts = (0,) if args.split_only else (args.search_count or (1, 2))
        for searches in dict.fromkeys(search_counts):
            drafts.clear()
            run = {"case": name, "search_count": searches}
            try:
                if args.split_only:
                    result = {
                        "question": question,
                        "status": "separated",
                        "decomposition": split_questions(question, generator),
                        "answers": [],
                    }
                else:
                    with DocumentCatalog(
                        Path("data/catalog/catalog.sqlite3")
                    ) as catalog:
                        result = answer_questions(
                            question,
                            generator,
                            lambda text: query_active(
                                catalog, "eu_ai_act", text, top_k=10
                            ),
                            search_count=searches,
                            max_passages=args.max_passages,
                            relative_margin=args.relative_margin,
                            context_tokens=8192,
                            output_tokens=args.output_tokens,
                            answer_mode=args.answer_mode,
                        )
                run["result"] = result
                # Manual labels, not self-certified LLM quality scores.
                run["manual_review"] = [
                    {
                        "question_id": answer["question_id"],
                        "answers_request": None,
                        "requested_parts": None,
                        "answered_parts": None,
                        "supported_claims": None,
                        "total_claims": len(answer["claims"]),
                        "qualifications_preserved": None,
                        "no_unnecessary_information": None,
                        "appropriate_abstention": None,
                        "rewrite_faithful": None,
                        "notes": "Pending review; check abstention correctness too.",
                    }
                    for answer in result["answers"]
                ]
            except (ValueError, OSError, RuntimeError, KeyError) as error:
                run["error"] = str(error)
            if args.record_drafts:
                run["diagnostic_drafts"] = list(drafts)
            report["runs"].append(run)
            (args.output_dir / "comparison.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )
            print(
                json.dumps(
                    {
                        "case": name,
                        "search_count": searches,
                        "status": run.get("result", {}).get("status"),
                        "error": run.get("error"),
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
