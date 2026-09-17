"""Replay saved evidence for manual synthesis review.

Diagnostic output retains drafts separately from the application's gated answer.
No retrieval, prompt tuning, source expansion or held-out evaluation is performed.
"""

import argparse
import json
from pathlib import Path

from rag_bogado.generation.generator import (
    SCHEMA,
    SYSTEM_PROMPT,
    OllamaGenerator,
    prepare_context,
)
from rag_bogado.generation.support import SUPPORT_PROMPT, SUPPORT_SCHEMA


def select_sources(answer, source_mode):
    """Keep saved source order; literal mode verifies exact-copy provenance."""
    if source_mode == "all":
        if not answer["sources"]:
            raise ValueError("Expected nonempty saved sources")
        return answer["sources"]
    if answer.get("answer_mode") != "evidence" or not answer["claims"]:
        raise ValueError("Expected a nonempty literal answer")
    by_id = {s["id"]: s for s in answer["sources"]}
    selected = []
    for claim in answer["claims"]:
        if len(claim["citations"]) != 1:
            raise ValueError("Expected one citation per literal passage")
        source = by_id[claim["citations"][0]]
        if claim["text"] != source["text"]:
            raise ValueError("Literal answer differs from its source")
        selected.append(source)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--case", default="simple")
    parser.add_argument("--search-count", type=int, default=1)
    parser.add_argument("--question-id", default="Q1")
    parser.add_argument("--source-mode", choices=("literal", "all"), default="literal")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    saved = json.loads(args.source_report.read_text())
    run = next(
        r
        for r in saved["runs"]
        if r["case"] == args.case and r["search_count"] == args.search_count
    )
    answer = next(
        a for a in run["result"]["answers"] if a["question_id"] == args.question_id
    )
    selected = select_sources(answer, args.source_mode)
    query = {
        key: answer[key]
        for key in (
            "question",
            "document_id",
            "version_id",
            "content_hash",
            "index_id",
            "source_path",
        )
    }
    query["results"] = [
        {
            "score": 0.0,  # Replay only: order is fixed, no score threshold is used.
            "chunk": {
                "source": s["document"],
                "page_number": s["page"],
                "chunk_id": s["chunk_id"],
                "text": s["text"],
            },
        }
        for s in selected
    ]
    replay_sources, _ = prepare_context(
        query, max_passages=len(selected), context_tokens=8192
    )
    if [s["text"] for s in replay_sources] != [s["text"] for s in selected]:
        raise ValueError(
            "Replay would drop saved sources; comparison is not controlled"
        )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "scope": "diagnostic replay; draft is not an accepted answer",
        "source_report": str(args.source_report),
        "source_case": args.case,
        "source_search_count": args.search_count,
        "source_question_id": args.question_id,
        "source_mode": args.source_mode,
        "source_id_mapping": {f"S{i}": s["id"] for i, s in enumerate(selected, 1)},
        "query": query,
        "generation_prompt": SYSTEM_PROMPT,
        "generation_schema": SCHEMA,
        "support_prompt": SUPPORT_PROMPT,
        "support_schema": SUPPORT_SCHEMA,
        "model_calls": [],
        "human_review": None,
    }
    destination = args.output_dir / "review.json"

    def save():
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    class RecordingGenerator(OllamaGenerator):
        def request(self, path, payload=None):
            response = super().request(path, payload)
            if path == "/api/chat":
                report["model_calls"].append({"request": payload, "response": response})
                save()
            return response

    generator = RecordingGenerator()
    save()
    try:
        report["runtime"] = generator.request("/api/version")
        report["models"] = generator.request("/api/tags")
        save()
        report["application_answer"] = generator.generate(
            query,
            max_passages=len(selected),
            context_tokens=8192,
            answer_mode="synthesis",
        )
    except (ValueError, RuntimeError, OSError) as error:
        report["error"] = str(error)
    save()
    print(
        json.dumps(
            report.get("application_answer", {"error": report.get("error")}),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
