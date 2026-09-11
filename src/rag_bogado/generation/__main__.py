"""Synthesize active evidence or a saved query through a local Ollama server."""

import argparse
import json
from pathlib import Path

from rag_bogado.generation.generator import OllamaGenerator
from rag_bogado.generation.service import answer_questions
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--question")
    inputs.add_argument("--evidence-json", type=Path)
    parser.add_argument("--document-id", default="eu_ai_act")
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/catalog.sqlite3")
    )
    parser.add_argument("--model", default="qwen3:4b-instruct")
    parser.add_argument("--retrieve-k", type=int, default=10)
    parser.add_argument("--max-passages", type=int, default=5)
    parser.add_argument("--context-tokens", type=int, default=8192)
    parser.add_argument("--output-tokens", type=int, default=512)
    parser.add_argument(
        "--min-score", type=float, help="Experimental, uncalibrated relevance threshold"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        generator = OllamaGenerator(args.model)
        options = dict(
            max_passages=args.max_passages,
            context_tokens=args.context_tokens,
            output_tokens=args.output_tokens,
            min_score=args.min_score,
        )
        if args.evidence_json:
            query = json.loads(args.evidence_json.read_text())
            result = generator.generate(query, **options)
        else:
            with DocumentCatalog(args.catalog) as catalog:
                result = answer_questions(
                    args.question,
                    generator,
                    lambda question: query_active(
                        catalog, args.document_id, question, top_k=args.retrieve_k
                    ),
                    **options,
                )
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n")
        print(serialized)
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
