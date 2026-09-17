# RAG-Bogado

A learning project for retrieval-augmented generation over regulatory documents.
The current implementation parses regulatory XML documents (such as BOE / EUR-Lex),
preserves structured legal units (recitals, articles, annexes), creates chunks, and
retrieves passages using embeddings. Experimental local LLM synthesis with source
citations is available in the terminal. A user interface and BOE synchronization
remain planned.

## Setup and checks

```bash
uv sync --locked --python 3.12
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Tests use a fake embedding model and synthetic XML fixtures. They do not need a local
corpus, model downloads, or Internet access. Installing dependencies initially
requires a connection. GitHub Actions runs these checks on pushes and pull
requests using the lockfile; semantic evaluation runs separately.
The workflow follows the [official uv integration guide](https://docs.astral.sh/uv/guides/integration/github/).

## Documentation map

- [PROJECT_PLAN.md](PROJECT_PLAN.md): scope, architecture, tools, milestones, and acceptance criteria.
- [TODO.md](TODO.md): next session, known failures, reproduction commands, relevant files, and delivery status.
- `ESTUDIAR.md` (local, Git-ignored): personal learning checklist in Spanish; not included in a fresh clone.
- [AGENTS.md](AGENTS.md): session startup and closing instructions for coding assistants.
- [Session history](docs/session-history.md): archived deliveries; consult only when historical context is needed.

## Project structure

```text
rag-bogado/
├── README.md                  # Entry point, file map, setup and usage
├── PROJECT_PLAN.md            # Project goals and roadmap
├── TODO.md                    # Actionable handoff for the next session
├── ESTUDIAR.md                # Theory and learning progress
├── AGENTS.md                  # Session maintenance instructions
├── pyproject.toml / uv.lock   # Dependencies and reproducible environment
├── .github/workflows/ci.yml   # Automated tests and Ruff checks
├── src/rag_bogado/
│   ├── ingestion/            # xml_loader.py, normalizer.py, chunker.py
│   ├── retrieval/            # embeddings.py, retriever.py,
│   │                        # persistent_retriever.py, vector_store.py
│   ├── indexing/             # indexer.py, catalog.py, configuration.py,
│   │                        # service.py, __main__.py (catalog CLI)
│   ├── generation/           # generator.py, questions.py, service.py,
│   │                        # multi_query.py, support.py, structured.py,
│   │                        # __main__.py (synthesis CLI)
│   └── evaluation/           # metrics.py, runner.py, __main__.py,
│                            # README.md, datasets/, reports/
├── tests/                    # Deterministic unit and integration tests
├── scripts/                  # serve_ollama.sh, evaluate_generation.py,
│                            # evaluate_question_workflow.py,
│                            # compare_saved_contexts.py, evaluate_multi_query.py,
│                            # review_saved_answer.py
├── docs/                     # Experiments, multi-query.md, session-history.md
└── data/                     # Ignored local XML documents, catalog, vectors,
                             # model weights, runtime and evaluation runs
```

API, UI, and official-source synchronization are planned in the roadmap.
Update this map when adding, moving, or removing modules.

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

## Document catalog and standalone queries

Index the local AI Act and activate it only after verifying every expected point:

```bash
uv run python -m rag_bogado.indexing index data/documents/eu_ai_act.xml --document-id eu_ai_act_xml --title "EU AI Act (XML)"
uv run python -m rag_bogado.indexing query --document-id eu_ai_act_xml "¿Qué obligaciones de transparencia se establecen?" --top-k 5
uv run python -m rag_bogado.indexing history --document-id eu_ai_act_xml
uv run python -m rag_bogado.indexing failures
```

The stable `--document-id` identifies the logical document; use the same ID when
indexing an updated copy. SHA-256 distinguishes original versions. Indexing retains
each XML under `data/catalog/originals/` and records model revision, processing
configuration, collection location, timestamps, and indexing outcomes in SQLite.
Repeating the same index reuses its vectors and document version, while recording
a new attempt. Use `--catalog PATH` before the subcommand to choose another catalog.

The query command loads the active collection and pinned local model from SQLite.
It does not read, normalize, chunk, or embed the XML. Output contains retrieved
passages and scores plus document/version/index identity and the retained original
path. This command returns evidence; use the separate generation command below
for experimental synthesis and insufficient-evidence handling.

`documents` identifies each document; `document_versions` records distinct original
hashes; `indexing_runs` records attempts and which complete index is active. Foreign
keys prevent mismatched document/version records, and a unique partial index permits
only one active run per document. The catalog provides parameterized JOIN queries
for history and failures, using Python's built-in
[`sqlite3`](https://docs.python.org/3.12/library/sqlite3.html).

Qdrant and SQLite do not share a transaction. The coordinator builds a separate
collection, verifies completeness, and then switches the active run in a SQLite
transaction. A caught indexing/activation failure is recorded and preserves the
previous active version. A hard process termination may leave a `preparing` run;
rerun indexing to resume missing vectors in a new attempt. Originals, prior runs,
and old collections are retained. This local workflow uses Qdrant's path lock and
does not support concurrent writers across independently configured store paths.

Queries select only the active collection and reject a missing/incomplete one.
Failures before a run starts (such as invalid XML documents or an unavailable model) are
reported by the command but are not indexing-run records. Catalog paths are local
absolute paths; moving data requires updating/rebuilding the catalog. Automatic
schema migrations and official-source/version metadata remain future work.

## Local evidence answers and experimental synthesis

With the local Ollama runtime and `qwen3:4b-instruct` installed:

```bash
bash scripts/serve_ollama.sh
```

In another terminal:

```bash
uv run python -m rag_bogado.generation --question "¿Quién debe garantizar la alfabetización en IA del personal?"
```

The live command detects individual questions, searches the original plus one
rewrite for each, combines rankings with RRF, and
returns an `answers` list with per-question statuses and citations such as
`Q1-S2`. Output includes exact passages, page numbers, local version identity,
and timing/token metrics. A missing answer does not hide the other parts. Invalid citation IDs and
inconsistent or truncated responses are rejected. These checks do not establish
semantic support; review the original evidence. Question separation and
abstention are experimental: some subject enumerations are over-split and
unsupported claims remain in the measured compound-query case. No
similarity threshold has been calibrated.

By default, the LLM selects source IDs and the application copies their full
retrieved text into the answer. No generated prose is used in this mode. This
preserves exact text, but does not certify relevance or complete legal context.
Use `--answer-mode synthesis` explicitly for experimental paraphrasing with
mandatory automated claim review. Real evaluation found false approvals by that
reviewer, so synthesis is not accepted as reliably grounded.

See [two-search retrieval and evaluation](docs/multi-query.md) for the workflow,
manual evaluation rubric, comparison command and limitations.

See [the local generation experiment](docs/local-generation.md) for installation,
saved-evidence replay, model provenance, measurements, and remaining limitations.
