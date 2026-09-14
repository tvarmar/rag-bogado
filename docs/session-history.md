# Historial de sesiones

Archivo histórico migrado desde PROJECT_PLAN.md el 2026-09-14. Los estados de
PR, checks y próximos pasos describen su fecha; no son instrucciones vigentes.
El punto de entrada actual es [TODO.md](../TODO.md). Las referencias antiguas
a «section 11» corresponden al plan anterior a esta reorganización.


## Session — 2026-09-08

### Completed

- Revised the roadmap around a local MVP, learning goals, free local execution, and later BOE synchronization.
- Fixed empty chunks, PDF resource handling, and retrieval edge cases; added regression tests.
- Preserved the existing module organization and the retriever's reference to `EmbeddingModel`.
- Organized evaluation code, questions, documentation, and reference reports under `src/rag_bogado/evaluation/`; kept automated tests in `tests/`.
- Wrote the project and evaluation README files in English; retained Spanish questions and evidence to match the corpus.
- Created a reproducible evaluation with 12 answerable questions and two negative questions.
- Updated relevance judgments to accept reviewed alternative evidence that helps answer the question, including appropriate recitals.
- Recorded results under the updated criterion: Hit@1 = 50%, Hit@5 = 91.67%, Hit@10 = 91.67%, MRR@10 = 0.6597. These reflect a changed evaluation criterion, not an improved retrieval algorithm.
- Added future multi-passage LLM synthesis and independent research on top-k, thresholds, context selection, and token budgets to the plan.
- Verified 34 passing tests, Ruff lint, and formatting locally.
- Prepared GitHub Actions and provided the branch, commit, and pull request workflow; the user published the PR and reported two successful checks in GitHub.

### State at the end of the session

- The PR remains open; merging it is pending.
- Remote CI success was reported by the user, not independently checked by the assistant.
- Qdrant persistence and LLM generation have not been implemented.
- This session-log update was added after the reported successful checks and still needs to be committed and pushed to the PR branch.

## Next session

1. Review the working tree and commit/push this session-log update if it is still pending.
2. Review the PR's final diff and confirm that checks pass for its latest commit.
3. Merge the PR, then update the local `main` branch.
4. Start the Qdrant persistence milestone on a new branch: first review what a collection, vector, point ID, and payload represent and how they fit the current code.
5. Define the first small implementation: persist a few chunks with their metadata, reopen the store, and retrieve them without recalculating their embeddings.
6. Preserve the current retriever and evaluation as references; compare results when the persistent retrieval path is ready.

Continue in small, explained steps, following the existing folder structure and
writing new code documentation in English. Update this log at the end of the next
session with completed work, remaining work, and the next starting point.

## Session — 2026-09-09

### Completed and verified

- Closed the September 8 delivery: session notes committed as `b4a7039`, PR #1
  merged, and local `main` updated after independently checking remote CI.
- Implemented Qdrant disk persistence, reproducible point/index identities, batch
  insertion, compatibility/input validation, and `SearchResult` reconstruction.
- Added resumable `DocumentIndexer`, `PersistentRetriever`, and evaluation
  build/reuse modes. Preserved the in-memory retriever as the reference.
- Compared memory, Qdrant build, and Qdrant reuse in separate processes on the
  AI Act: 1,041 chunks, 14 questions, all 140 top-ten positions identical.
  Hit@1 = 50%, Hit@5 = Hit@10 = 91.67%, MRR@10 = 0.6597. Maximum score difference
  was approximately 1.2e-7; reuse calculated zero passage embeddings.
- Committed persistence as `efc68fb` and merged PR #2 after both remote checks passed.
- Implemented SQLite documents, original versions, and indexing attempts with
  foreign keys, uniqueness constraints, parameterized JOINs, and transactions.
- Built and verified separate vector collections before activating a run. Tested
  failure isolation, rollback during activation, and retry of missing passages.
- Added index/query/history/failures commands, retained hash-addressed originals,
  and active-only query without rereading, chunking, or embedding the PDF.
- Registered `eu_ai_act`, local version 1, reusing all existing vectors. A separate
  query returned five passages with version identity and the retained original.
- Committed the catalog implementation as `5795376` and published PR #3; both
  remote implementation checks passed. This closing plan update travels in the
  same PR, whose final commit must pass CI before the closing merge.
- Verified 56 tests plus Ruff lint/format. No model download or paid service was
  required for the real local validation; embeddings ran on `cuda:0`.

### Evidence and reproduction

- `src/rag_bogado/evaluation/reports/persistence-comparison.json`: comparison,
  provenance, and measurements. Full local runs live in `data/evaluation/`.
- `data/evaluation/catalog-query-2026-09-09.json`: real catalog query output.
- `README.md`: indexing, standalone querying, history, and failures commands.
- Delivery links: [PR #2](https://github.com/tvarmar/rag-bogado/pull/2),
  [PR #3](https://github.com/tvarmar/rag-bogado/pull/3).

### Remaining scope and next starting point

- The local retrieval/persistence/catalog increment is implemented. Generation,
  abstention, API, and UI have not been implemented.
- The development evaluation is small and contains no held-out split yet.
- Official identifiers/source dates, schema migrations, and multiwriter
  coordination remain future work. Hard termination can leave a preparing attempt;
  a new attempt resumes vectors while retaining the previous active version.
- End-of-day procedure: commit/push this handoff, check CI on the latest PR #3
  commit, merge PR #3, and update local `main`. Keep branch history and local data.
- The next work session follows section 11: inspect hardware, compare local LLM
  options with the user, and build a first measured terminal synthesis with citations.

The September 8 next-session instructions above are historical. Section 11 and
this September 9 handoff define the current starting point.


## Session — 2026-09-11

### Implemented and measured

- Selected Qwen3 4B Instruct Q4_K_M with the user after checking WSL RAM and the
  RTX 4050 6 GB GPU. Installed Ollama 0.34.0 locally under ignored `data/runtime/`
  and model weights under `data/models/`; loopback server with cloud disabled.
- Created `feat/local-generation`. Added an Ollama adapter, bounded context
  selection, exact-source output, per-claim citation-ID validation, terminal
  query/replay commands, and deterministic generation tests.
- Measured known Article 4 synthesis: 7.44 s after model reload, 1.98 s warm,
  445 prompt tokens / 96 output tokens, sampled device VRAM 3,133 MiB.
- Compared top three/five on four development questions at 8,192 context tokens;
  device VRAM reached 4,388 MiB including retained embedding allocations.
- Added a development/held-out split, an exploratory selection-only threshold
  sweep, and a reference report with 12 runs and assistant evidence review.
- Preserved failed initial outputs. Corrected an ambiguous status instruction;
  validation continues to reject inconsistent or truncated answers.
- Initial synthesis increment passed 68 tests; the final question-workflow
  increment passed 86 tests plus Ruff lint/format locally. Closing delivery is
  tracked on `feat/local-generation`; remote CI is checked after pushing.

### Findings and remaining work

- Top five recovers the useful fourth-ranked passage for the paraphrase; top
  three appropriately abstains on its selected context.
- Both compound-question answers fail coverage and do not acknowledge missing
  parts. Top five additionally uses a cut, out-of-scope passage. This is an
  explicitly recorded quality failure, not an accepted completed feature.
- The known response identifies actors and the duty to adopt measures but omits
  qualifications; it must not be presented as an exhaustive legal explanation.
- The tested negative questions abstain, but broader and held-out validation,
  threshold calibration, and coverage-aware selection remain pending.
- `src/rag_bogado/evaluation/reports/local-generation.json` preserves results,
  model digest, prompt, metrics, exact passages, and review. Full local attempts
  are in `data/evaluation/generation-2026-09-11*`.
- `docs/local-generation.md` documents reproduction and measurement limits.
  The local server can be started with `bash scripts/serve_ollama.sh`.
- First measured-synthesis target complete; milestones 5/6 and MVP acceptance
  remain open. Section 11 defines the next starting point.


### Question-workflow increment and session handoff

- Agreed with the user to separate explicit questions, retrieve independently,
  and answer each with its own evidence and abstention status.
- Added a bounded local question separator and orchestration that preserves each
  question, namespaces citations, isolates failures, and rejects mixing document
  versions. Live CLI uses this flow; saved evidence replay stays unchanged.
- Real compound query produced three self-contained questions and three separate
  retrievals/answers. Mixed query produced one answer and one explicit abstention.
- Measured 22.54 s total for the compound pipeline and 12.13 s for the mixed case;
  these include retrieval and separation, unlike the earlier generation-only times.
- Preserved comparison and simple-question cases, but recorded over-splitting of
  a subject enumeration. The compound preparation answer is still unsupported:
  separation improves organization but does not guarantee retrieval or generation
  correctness. No semantic acceptance is claimed.
- Reference: `src/rag_bogado/evaluation/reports/question-workflow.json`; full local
  runs: `data/evaluation/question-workflow-2026-09-11/`. A prompt-only follow-up
  did not resolve the remaining failures and is retained separately as v2.
- Final local checks: 86 tests passed, Ruff lint/format passed. Runtime and weights
  remain ignored by Git. The user requested plan updates and GitHub publication;
  publish the code, tests, docs, and reference reports together.
- The next session starts with section 11. Do not repeat installation or treat
  the old single-query coverage work as still unimplemented.


### GitHub delivery

- Implementation published as `ae475c6` on `feat/local-generation`.
- [PR #4](https://github.com/tvarmar/rag-bogado/pull/4) is open as a draft against
  `main`; it has not been merged. The draft records the remaining semantic failures.
- This handoff update travels in the same PR. Check CI against its latest head
  before marking it ready or merging; local validation is 86 tests plus Ruff.

## Session — 2026-09-14

- Separated the file map, roadmap, actionable TODO and learning checklist; added
  session instructions and preserved earlier handoffs in this archive.
- Confirmed PR #4 is an open draft with successful checks on `dcd7601`.
- Diagnosed the preparation failure: complete evidence at rank seven is excluded
  by the five-passage cap. Added `scripts/compare_saved_contexts.py` and replayed
  five saved development questions across three configurations (15 model calls).
- Ten allowed passages / 8,192 tokens selects seven and restores supported timing.
  More context still permits citation-support failures; defaults remain unchanged.
- Reference: `src/rag_bogado/evaluation/reports/context-selection.json` and
  `docs/context-selection.md`. Held-out questions remain untouched.
- Local checks: 86 tests passed; Ruff lint/format passed. No commit/push this session.
  Current next steps are in TODO.md.

### Two-search workflow and evidence output — 2026-09-14

- Implemented original plus one rewrite, stable RRF union, provenance checks,
  ten-source maximum by default and a one-search comparison mode.
- Added automated per-claim synthesis review and a manual multidimensional rubric.
  Real evaluation found false approvals, including omitted qualifications and an
  invented duty; synthesis remains explicitly experimental.
- Default output now copies selected source chunks exactly. This prevents generated
  prose from entering that answer, without certifying relevance or complete context.
- Completed six synthesis and six exact-passage development runs; all literal output
  matches its source. Exact-mode rewrites repeated the original, so no multi-query
  quality improvement is claimed. Reports and limits are in `docs/multi-query.md`.
- Final local validation: 125 tests passed, Ruff lint/format and diff checks passed.
  No commit/push; earlier user changes, including ignored study notes, were preserved.
