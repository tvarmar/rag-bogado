"""Run a small local experiment; semantic judgments require a separate review."""

import argparse
import copy
import hashlib
import json
import subprocess
import threading
from pathlib import Path

from rag_bogado.generation.generator import (
    SCHEMA,
    SYSTEM_PROMPT,
    OllamaGenerator,
    prepare_context,
)
from rag_bogado.indexing.catalog import DocumentCatalog
from rag_bogado.indexing.service import query_active
from rag_bogado.ingestion.loader import load_pdf
from rag_bogado.ingestion.normalizer import normalize_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/evaluation/generation-2026-09-11")
    )
    parser.add_argument("--retrieval", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generator = OllamaGenerator()
    metadata = {
        "system_prompt": SYSTEM_PROMPT,
        "response_schema": SCHEMA,
        "runtime": generator.request("/api/version"),
        "tags": generator.request("/api/tags"),
        "model": generator.request("/api/show", {"model": generator.model}),
    }
    (args.output_dir / "model.json").write_text(json.dumps(metadata, indent=2))
    with DocumentCatalog(Path("data/catalog/catalog.sqlite3")) as catalog:
        active = catalog.active_index("eu_ai_act")
    original = Path(active["source_path"])
    assert hashlib.sha256(original.read_bytes()).hexdigest() == active["content_hash"]
    pages = {p.page_number: normalize_text(p.text) for p in load_pdf(original)}
    article4 = pages[51].split("CAPÍTULO II")[0].strip()
    query = {
        "document_id": "eu_ai_act",
        "version_id": active["version_id"],
        "content_hash": active["content_hash"],
        "source_path": str(original),
        "index_id": active["index_id"],
        "question": "¿Quién debe garantizar la alfabetización en IA del personal?",
        "results": [
            {
                "score": 1.0,
                "chunk": {
                    "text": article4,
                    "source": original.name,
                    "page_number": 51,
                    "chunk_id": "known-article-4",
                },
            }
        ],
    }
    # Known evidence is an exact normalized excerpt, not a retrieved chunk.
    (args.output_dir / "known-evidence.json").write_text(
        json.dumps(query, ensure_ascii=False, indent=2)
    )
    jobs = []
    if not args.retrieval:
        generator.request("/api/generate", {"model": generator.model, "keep_alive": 0})
        jobs.extend([("known-cold", query, 3, 4096), ("known-warm", query, 3, 4096)])
        negative = copy.deepcopy(query)
        negative["question"] = "¿Cuál es la receta de una tortilla de patatas?"
        jobs.append(("unrelated-evidence", negative, 3, 4096))
        empty = copy.deepcopy(query)
        empty["results"] = []
        jobs.append(("empty-evidence", empty, 3, 4096))
    else:
        dataset = json.loads(
            Path("src/rag_bogado/evaluation/datasets/generation.json").read_text()
        )
        for case in dataset["development"]:
            with DocumentCatalog(Path("data/catalog/catalog.sqlite3")) as catalog:
                retrieved = query_active(
                    catalog, "eu_ai_act", case["question"], top_k=10
                )
            (args.output_dir / f"{case['id']}-retrieved.json").write_text(
                json.dumps(retrieved, ensure_ascii=False, indent=2)
            )
            for count in (3, 5):
                jobs.append((f"{case['id']}-top{count}", retrieved, count, 8192))
    summary = []
    for name, evidence, count, context in jobs:
        stop = threading.Event()
        samples = []
        rss_samples = []

        def monitor():
            while not stop.is_set():
                sample = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                )
                if sample.returncode == 0:
                    samples.append(int(sample.stdout.strip().splitlines()[0]))
                rss = subprocess.run(
                    ["ps", "-C", "ollama,llama-server", "-o", "rss="],
                    capture_output=True,
                    text=True,
                )
                if rss.returncode == 0:
                    rss_samples.append(sum(int(v) for v in rss.stdout.split()))
                stop.wait(0.5)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        try:
            result = generator.generate(
                evidence, max_passages=count, context_tokens=context
            )
        except (RuntimeError, ValueError) as error:
            result = {"error": str(error)}
            if hasattr(error, "response"):
                result["rejected_response"] = error.response
        finally:
            stop.set()
            thread.join()
        result["experiment"] = {
            "name": name,
            "max_passages": count,
            "context_tokens": context,
            "gpu_peak_sampled_mib": max(samples, default=None),
            "gpu_sample_count": len(samples),
            "ollama_and_runner_sum_rss_peak_kib": max(rss_samples, default=None),
        }
        (args.output_dir / f"{name}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        row = {
            "name": name,
            "status": result.get("status"),
            "claims": result.get("claims"),
            "error": result.get("error"),
            "selected": len(result.get("sources", [])),
            "metrics": result.get("metrics"),
            "experiment": result["experiment"],
        }
        summary.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (
        args.output_dir
        / ("retrieval-summary.json" if args.retrieval else "summary.json")
    ).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if args.retrieval:
        rows = []
        for threshold in (None, 0.84, 0.87, 0.9):
            for name, evidence, count, context in jobs:
                if count != 5:
                    continue
                selected, _ = prepare_context(
                    evidence,
                    max_passages=count,
                    context_tokens=context,
                    min_score=threshold,
                )
                rows.append(
                    {
                        "case": name,
                        "min_score": threshold,
                        "selected_pages": [s["page"] for s in selected],
                    }
                )
        (args.output_dir / "threshold-selection.json").write_text(
            json.dumps(
                {
                    "kind": "selection_only_exploratory_threshold_sweep",
                    "calibrated": False,
                    "rows": rows,
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
