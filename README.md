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

## Local vector storage

`QdrantVectorStore` stores precomputed vectors on disk and returns `SearchResult`
objects. It defaults to 384 dimensions and dot-product similarity, matching the
current normalized E5 embeddings. It does not generate embeddings itself.

```python
from pathlib import Path
from rag_bogado.retrieval.vector_store import QdrantVectorStore

# chunks and vectors are produced once by the ingestion and embedding layers.
with QdrantVectorStore(Path("data/qdrant"), "corpus_v1") as store:
    store.upsert(
        chunks, vectors, index_id="document-hash:processing-config:model-revision"
    )

# Later, including after restarting the application:
with QdrantVectorStore(Path("data/qdrant"), "corpus_v1") as store:
    results = store.search(query_vector, top_k=5)
```

The example assumes existing `chunks`, `vectors`, and `query_vector` variables.
The application still needs to embed each new question. Point IDs are reproducible
from the index identity and chunk metadata/text; repeating the same insertion
replaces matching points instead of duplicating them. Use a real document/version
and processing identity in place of the illustrative `index_id` above.

Close the store before opening another client at the same path. Existing
collections must have the requested dimension and DOT distance. Keep each
collection tied to one corpus/model/processing configuration: dimensional
compatibility does not establish model compatibility. Upserts do not remove old
document versions, and multiple batches are not atomic. Version activation and
failure recovery await the indexing/catalog layer.

Run `uv run pytest tests/test_vector_store.py` to check persistence, repeat
insertion, metadata, similarity scores, and invalid input using synthetic vectors.
`DocumentIndexer` embeds only missing passages, and `PersistentRetriever` embeds
only questions. The evaluation runner connects both to this adapter; the in-memory
`Retriever` remains the reference. See the evaluation guide for build/reuse commands.

API reference: [official Qdrant client documentation](https://github.com/qdrant/qdrant-client).
