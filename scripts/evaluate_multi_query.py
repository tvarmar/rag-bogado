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
from rag_bogado.generation.questions import QUESTION_PROMPT, QUESTION_SCHEMA
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--answer-mode", choices=("evidence", "synthesis"), default="evidence"
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    generator = OllamaGenerator()
    report = {
        "scope": "known development cases; no held-out questions",
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
            "max_passages": 10,
            "context_tokens": 8192,
            "output_tokens": 512,
        },
        "runs": [],
    }
    for name, question in CASES:
        for searches in (1, 2):
            run = {"case": name, "search_count": searches}
            try:
                with DocumentCatalog(Path("data/catalog/catalog.sqlite3")) as catalog:
                    result = answer_questions(
                        question,
                        generator,
                        lambda text: query_active(catalog, "eu_ai_act", text, top_k=10),
                        search_count=searches,
                        max_passages=10,
                        context_tokens=8192,
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
