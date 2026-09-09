"""Reproducible identity inputs shared by evaluation and catalog indexing."""

import hashlib
from importlib.metadata import version
from pathlib import Path


def index_configuration(
    corpus_sha256: str,
    model_name: str,
    revision: str,
    dimension: int,
    chunk_size: int = 800,
    overlap: int = 120,
) -> dict:
    return {
        "corpus_sha256": corpus_sha256,
        "model": model_name,
        "revision": revision,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "processing_code_sha256": {
            str(path.relative_to(Path(__file__).parents[1])): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in [
                *sorted((Path(__file__).parents[1] / "ingestion").glob("*.py")),
                Path(__file__).parents[1] / "retrieval" / "embeddings.py",
            ]
        },
        "embedding_dependencies": {
            name: version(name) for name in ("sentence-transformers", "torch")
        },
        "dimension": dimension,
        "distance": "Dot",
    }
