"""Offline retrieval baseline: python -m rag_bogado.evaluation --help."""

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from rag_bogado.evaluation.metrics import evidence_rank, summarize
from rag_bogado.ingestion.chunker import chunk_page
from rag_bogado.ingestion.loader import Page, load_pdf
from rag_bogado.ingestion.normalizer import normalize_text
from rag_bogado.retrieval.embeddings import EmbeddingModel
from rag_bogado.retrieval.retriever import Retriever


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, default=Path("data/documents"))
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path(__file__).parent / "datasets" / "questions.json",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/evaluation/latest.json")
    )
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--model", default="intfloat/multilingual-e5-small")
    parser.add_argument(
        "--revision", default="614241f622f53c4eeff9890bdc4f31cfecc418b3"
    )
    args = parser.parse_args()
    dataset_bytes = args.questions.read_bytes()
    dataset = json.loads(dataset_bytes)
    if dataset.get("schema_version") != 2:
        parser.error("Expected question dataset schema_version 2")
    pdf = args.documents / dataset["corpus"]
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != dataset["sha256"]:
        parser.error("Corpus hash differs: review evidence before evaluating")
    pages = [
        Page(page.page_number, normalize_text(page.text), page.source)
        for page in load_pdf(pdf)
    ]
    for question in dataset["questions"]:
        for alternative in question["evidence"]:
            if not 1 <= alternative["page"] <= len(pages):
                parser.error(f"Invalid evidence page: {question['id']}")
            page = pages[alternative["page"] - 1]
            if (
                not alternative["anchor"].strip()
                or " ".join(alternative["anchor"].split()).casefold()
                not in " ".join(page.text.split()).casefold()
            ):
                parser.error(f"Evidence anchor not found: {question['id']}")
    chunks = [
        chunk
        for page in pages
        for chunk in chunk_page(page, args.chunk_size, args.overlap)
    ]

    started = perf_counter()
    model = EmbeddingModel(args.model, revision=args.revision, local_files_only=True)
    retriever = Retriever(chunks, model)
    indexing_seconds = perf_counter() - started
    rows = []
    ranks = []
    for question in dataset["questions"]:
        started = perf_counter()
        results = retriever.search(question["question"], top_k=10)
        elapsed = perf_counter() - started
        rank = None
        if question["evidence"]:
            rank = evidence_rank(results, dataset["corpus"], question["evidence"])
            ranks.append(rank)
        rows.append(
            {
                **question,
                "rank@10": rank,
                "seconds": elapsed,
                "results": [
                    {
                        "page": r.chunk.page_number,
                        "chunk_id": r.chunk.chunk_id,
                        "score": r.score,
                        "text": r.chunk.text,
                    }
                    for r in results
                ],
            }
        )
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_schema_version": dataset["schema_version"],
        "relevance_policy": dataset["relevance_policy"],
        "corpus_sha256": digest,
        "questions_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "uv_lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "code_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path("src/rag_bogado").rglob("*.py"))
        },
        "model": args.model,
        "revision": args.revision,
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "chunks": len(chunks),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": str(model.model.device),
        "dependencies": {
            name: version(name)
            for name in ("sentence-transformers", "torch", "pymupdf")
        },
        "indexing_seconds": indexing_seconds,
        "answerable_questions": len(ranks),
        "negative_questions": len(rows) - len(ranks),
        "metrics": summarize(ranks),
        "questions": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {args.output}")
