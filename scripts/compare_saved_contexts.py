"""Replay saved development retrievals to isolate passage and context budgets.

Does not retrieve, change the active index, or evaluate held-out questions.
Reports preserve exact inputs and outputs; semantic review remains manual.
"""

import argparse
import json
from pathlib import Path

from rag_bogado.generation.generator import (
    SCHEMA,
    SYSTEM_PROMPT,
    GenerationError,
    OllamaGenerator,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrievals", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Refuse to overwrite an earlier experiment, including partial failures.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    generator = OllamaGenerator()
    report = {
        "runtime": generator.request("/api/version"),
        "models": generator.request("/api/tags"),
        "system_prompt": SYSTEM_PROMPT,
        "schema": SCHEMA,
        "scope": "saved development retrieval replay; excludes retrieval latency",
        "semantic_support_reviewed": False,
        "runs": [],
    }
    destination = args.output_dir / "comparison.json"
    for path in args.retrievals:
        queries = json.loads(path.read_text())
        for query in queries:
            for passages, tokens in ((5, 8192), (10, 8192), (10, 16384)):
                run = {
                    "input_path": str(path),
                    "query": query,
                    "max_passages": passages,
                    "context_tokens": tokens,
                }
                try:
                    run["response"] = generator.generate(
                        query,
                        max_passages=passages,
                        context_tokens=tokens,
                        answer_mode="synthesis",
                    )
                except GenerationError as error:
                    run.update(error=str(error), rejected_response=error.response)
                except (ValueError, RuntimeError) as error:
                    run["error"] = str(error)
                report["runs"].append(run)
                destination.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\n"
                )
                response = run.get("response", {})
                print(
                    json.dumps(
                        {
                            "question": query["question"],
                            "max_passages": passages,
                            "context_tokens": tokens,
                            "selected": len(response.get("sources", [])),
                            "claims": response.get("claims"),
                            "error": run.get("error"),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    main()
