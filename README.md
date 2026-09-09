# RAG-Bogado

A learning project for retrieval-augmented generation over regulatory documents.
The current implementation extracts PDFs, normalizes text, creates chunks, and
retrieves passages using embeddings. LLM answers, a user interface, and BOE
synchronization are planned but not implemented yet.

## Setup and checks

```bash
uv sync --locked --python 3.12
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Tests use a fake embedding model and temporary PDFs. They do not need a local
corpus, model downloads, or Internet access. Installing dependencies initially
requires a connection. GitHub Actions runs these checks on pushes and pull
requests using the lockfile; semantic evaluation runs separately.
The workflow follows the [official uv integration guide](https://docs.astral.sh/uv/guides/integration/github/).

## Project structure

- `src/rag_bogado/ingestion/`: PDF extraction, normalization, and chunking.
- `src/rag_bogado/retrieval/`: the embedding model and semantic retriever.
- `src/rag_bogado/evaluation/`: evaluation runner, metrics, questions, and reference reports.
- `tests/`: automated checks for these components.
- `data/`: local documents and generated evaluation runs, excluded from Git.

## Local evaluation

See the [evaluation guide](src/rag_bogado/evaluation/README.md) for reproduction
steps, metric definitions, and known limitations. Evaluation questions and evidence
remain in Spanish to match the source corpus.

The [project plan](PROJECT_PLAN.md) describes the scope and next milestones.
