# Retrieval evaluation

This development dataset contains 12 questions with evidence references and two
questions outside the corpus. References were checked against the local
144-page `eu_ai_act.pdf`. Page numbers are one-based PDF positions.
The SHA-256 hash in `datasets/questions.json` identifies the exact document;
a different copy requires reviewing the references. This does not verify whether
the legislation is currently in force.

## Organization

- `runner.py`: loads the corpus, runs retrieval, and writes an evaluation report.
- `metrics.py`: computes evidence ranks, Hit@k, and MRR@10.
- `__main__.py`: provides the `python -m rag_bogado.evaluation` entry point.
- `datasets/questions.json`: versioned questions and evidence references.
- `reports/baseline.json`: the reference run recorded before this reorganization.
- `reports/useful-evidence.json`: the run using reviewed evidence alternatives.
- `README.md`: reproduction instructions and interpretation.

Evaluation belongs to the application package because it runs a real model against
a corpus to measure retrieval quality. Its automated checks remain in
`tests/test_evaluation.py`, alongside the other component tests.

## Running the evaluation

From the project root, with the PDF in `data/documents/` and the model cached:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 uv run python -m rag_bogado.evaluation
```

The default question file is resolved relative to this package. New reports go to
`data/evaluation/latest.json`, which is ignored by Git, keeping the reference run
unchanged. Use `--questions` or `--output` to override these paths.

Evaluation uses local files only and pins the model revision. If the model is
missing from the cache, download it explicitly once with Internet access:

```bash
uv run python -c 'from rag_bogado.retrieval.embeddings import EmbeddingModel; EmbeddingModel(revision="614241f622f53c4eeff9890bdc4f31cfecc418b3")'
```

The runner checks the PDF hash and evidence anchors before instantiating the
model. Reports include metrics, configuration, dependency versions, hashes,
timings, and the top ten passages per question. Indexing time includes model
initialization and embeddings, but excludes PDF extraction. Query timing starts
after indexing.

To evaluate a different chunking configuration:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 uv run python -m rag_bogado.evaluation --chunk-size 1500 --overlap 200 --output data/evaluation/chunks-1500.json
```

## Original reference results (single-location criterion)

Recorded on 2026-09-08 using multilingual E5 small, 800-character chunks,
120-character overlap, and 1,041 chunks:

| Metric | Result |
| --- | --- |
| Hit@1 | 3/12 = 25% |
| Hit@5 | 9/12 = 75% |
| Hit@10 | 10/12 = 83.33% |
| MRR@10 | 0.4702 |

The CPU run with `OMP_NUM_THREADS=2` took approximately 72.2 seconds to load/index
and 37.7 ms per query on average. These measurements describe that machine and run,
not general performance guarantees.

The reference report retains its original code hashes and paths as historical
provenance. Moving files does not make it a new evaluation run.

Initial review:

- `q01`: the selected definition in Article 3, page 46, is absent from the top ten.
  The first passage is a relevant recital on inference on page 4, but does not
  contain the complete selected definition.
- `q04`: the selected Article 9 passage on page 56 is absent from the top ten.
  The first result, recital 65 on page 19, does explain continuous risk management.
  This is useful alternative evidence despite the metric recording a miss.
- `q13` and `q14`: retrieval returns passages even though the corpus has no answer.
  Nearest-neighbor retrieval does not implement abstention.

Review which alternative evidence should count before comparing configurations,
then keep that criterion fixed. Retrieval parameters were not tuned to these results.

## Useful-evidence criterion (dataset schema 2)

The new run, with the same model and chunking configuration, produced:

| Metric | Result |
| --- | --- |
| Hit@1 | 6/12 = 50% |
| Hit@5 | 11/12 = 91.67% |
| Hit@10 | 11/12 = 91.67% |
| MRR@10 | 0.6597 |

Each question now has an `evidence` list. Its entries contain a PDF page, a human
reference such as `Article 9` or `Recital 65`, and an identifying anchor. A passage
matching any accepted entry counts; the earliest matching result determines the
rank, regardless of the order of alternatives. An empty list marks a negative
question and remains excluded from Hit@k and MRR.

Seven recital alternatives were reviewed in the source PDF: risk management,
dataset quality, automatic logging, transparency, human oversight, performance
requirements, and AI literacy. The review included passages outside the original
top-ranked results, such as the transparency explanation in recital 72.
Each added entry records why it supports the question. This list is not exhaustive.

Topical similarity alone is insufficient. For example, recital 20 explains literacy
but is not used to identify who must ensure staff literacy (`q02`); recital 71
discusses maintaining documentation but is not accepted as the answer to when it
must initially be prepared (`q06`). The partial discussion of inference on page 4
is not accepted as the full definition requested by `q01`.

If a question explicitly requests a particular article, list only evidence that
satisfies that request. The matcher does not infer question intent: these reviewed
references encode it. Recitals are explanatory evidence, not interchangeable legal
provisions; keep their labels when interpreting or eventually citing a passage.

The original report is preserved with its original references. Any increase under
schema 2 reflects a changed relevance criterion, not an improvement to the retriever.
Use a fixed schema-2 dataset for future retrieval comparisons. Because this review
was informed partly by observed failures, these remain development results; assess
generalization with separately reviewed held-out questions.

## Metric definitions and limitations

- Hit@k is the fraction of the 12 answerable questions with matching evidence in
  the first k results.
- MRR@10 averages the reciprocal of the first matching rank, using zero for a miss.
- A match requires the document plus the page and anchor of any accepted evidence
  alternative, ignoring case and whitespace differences.
- Negative questions are reported for inspection and excluded from these metrics.

Anchors are an approximation: they may reject valid alternative evidence and do
not guarantee that a passage contains the full answer. Inspect retrieved text
before attributing misses to embeddings or chunking. Article numbers are human
review references, not metadata currently extracted by the pipeline.

This small, single-document development set does not measure generalization or
LLM answer quality. Create a held-out question set before repeated tuning.
Questions requiring multiple sources remain a future extension.

## Tests and current boundaries

`tests/test_evaluation.py` checks metric calculations and evidence matching with
artificial results, including alternatives, earliest rank, explicit-reference
restrictions, and negative questions. Retriever tests cover ranking, limits, empty corpora, and
embedding count/dimension errors. The loader test creates a temporary PDF with
a header, body, and footer.

The retriever references `EmbeddingModel` from `retrieval/embeddings.py`.
Tests supply a fake model without creating or downloading a real model.

Words longer than `chunk_size` may be split to guarantee progress. Chunk IDs are
local to a page: use document, page, and chunk ID together when reading reports.
Persistent IDs belong to the next milestone.
