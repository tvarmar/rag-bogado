# Saved-context selection experiment

Date: 2026-09-14. Development-only diagnostic; no retrieval, reindexing, question
separation, or held-out evaluation is performed in this replay.

## Diagnosis

For the saved preparation question, the complete Article 11 timing sentence is
already ranked seventh (page 58, chunk 3). The fourth-ranked passage is also from
page 58 but starts after that sentence. The live default sends at most five
passages: the useful evidence is lost at selection, not absent from the retrieved
top ten. Raising a similarity threshold would not promote rank seven over the
higher-scoring passages.

## Reproduction

Start the existing local server with `bash scripts/serve_ollama.sh`, then:

```bash
uv run python scripts/compare_saved_contexts.py \
  --retrievals data/evaluation/question-workflow-2026-09-11/compound-retrievals.json \
    data/evaluation/question-workflow-2026-09-11/mixed-retrievals.json \
  --output-dir data/evaluation/context-comparison-new
```

The output directory must not exist. Each completed attempt is saved immediately
in `comparison.json`, including rejected model output when available. Inputs,
model digest, runtime, prompt, exact sources, generation configuration and metrics
are preserved. Saved retrievals require the previous local experiment files;
the reference report linked below also retains the input queries.

The three configurations keep the prompt, model, output budget, and candidate
order fixed: five passages / 8,192 tokens; ten / 8,192; ten / 16,384. Passage
counts are upper limits: the conservative UTF-8 budget can select fewer.

## Review and limits

The reference report is
[context-selection.json](../src/rag_bogado/evaluation/reports/context-selection.json).
Full local output is `data/evaluation/context-comparison-2026-09-14/comparison.json`.
Assistant review checks claims against supplied passages; it is not expert legal
approval or an automated semantic guarantee.

For preparation, five passages reproduce the unsupported timing claim. Allowing
ten with the same 8,192-token budget selects seven and includes the missing
sentence; the generated timing claim is supported by S7. Increasing context to
16,384 selects all ten, but its answer adds a lifetime qualification not contained
in its sole cited source S7. More context does not guarantee better citation support.

All 15 calls completed with structurally valid output. The saved negative question
abstains in all three configurations. Updating and the alternative preparation
wording retain supporting evidence, although larger contexts add peripheral claims.
The literacy responses still omit qualifications and include peripheral claims.
This experiment establishes a concrete selection failure and a usable configuration
for the measured preparation case; it does not establish a generally accepted
selection policy. Production defaults remain unchanged pending broader evidence
and support review. The CLI already accepts `--max-passages 10` with its default
8,192-token context for further development comparisons.

Times measure individual generation calls, including model loads/context resizing
when they occur, and exclude retrieval and question separation. Cache reuse and
configuration order affect timings. No general latency or quality rate is inferred.
