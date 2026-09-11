"""Check question separation and per-question retrieval on local development cases."""

import argparse
import json
from pathlib import Path

from rag_bogado.generation.generator import SCHEMA, SYSTEM_PROMPT, OllamaGenerator
from rag_bogado.generation.questions import (
    QUESTION_PROMPT,
    QUESTION_SCHEMA,
    split_questions,
)
from rag_bogado.generation.service import answer_questions
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/evaluation/question-workflow-2026-09-11"),
    )
    destination = parser.parse_args().output_dir
    destination.mkdir(parents=True, exist_ok=True)
    generator = OllamaGenerator()
    metadata = {
        "runtime": generator.request("/api/version"),
        "models": generator.request("/api/tags"),
        "question_prompt": QUESTION_PROMPT,
        "question_schema": QUESTION_SCHEMA,
        "generation_prompt": SYSTEM_PROMPT,
        "generation_schema": SCHEMA,
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2))
    cases = [
        ("simple", "¿Quién debe procurar la alfabetización en IA?", 1),
        (
            "comparison",
            "¿Qué diferencias hay entre las obligaciones de proveedores "
            "y responsables del despliegue?",
            1,
        ),
        (
            "enumerated_subjects",
            "¿Qué obligaciones de transparencia tienen proveedores "
            "y responsables del despliegue?",
            1,
        ),
        (
            "compound",
            "¿Quién debe procurar la alfabetización en IA y cuándo debe prepararse "
            "y actualizarse la documentación técnica de una IA de alto riesgo?",
            3,
        ),
        (
            "mixed",
            "¿Cuándo se elabora la documentación técnica de un sistema de IA de alto "
            "riesgo? ¿Cuál es el número de teléfono del delegado de protección "
            "de datos de mi empresa?",
            2,
        ),
    ]
    for name, question, count in cases:
        if name not in {"compound", "mixed"}:
            result = split_questions(question, generator)
        else:
            retrievals = []
            with DocumentCatalog(Path("data/catalog/catalog.sqlite3")) as catalog:

                def retrieve(individual):
                    query = query_active(catalog, "eu_ai_act", individual, top_k=10)
                    retrievals.append(query)
                    return query

                result = answer_questions(
                    question, generator, retrieve, max_passages=5, context_tokens=8192
                )
            (destination / f"{name}-retrievals.json").write_text(
                json.dumps(retrievals, ensure_ascii=False, indent=2) + "\n"
            )
        result["expected_question_count"] = count
        (destination / f"{name}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "case": name,
                    "decomposition": result.get("decomposition", result),
                    "answers": [
                        {
                            "question": a["question"],
                            "status": a["status"],
                            "claims": a["claims"],
                        }
                        for a in result.get("answers", [])
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
