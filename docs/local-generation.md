# Local generation experiment

Session: 2026-09-11. Status: first measured synthesis completed; generation quality acceptance pending.

## Measured environment

- WSL on an Intel Core i7-13620H; four logical CPUs exposed.
- Approximately 13 GiB RAM total and 12 GiB available at inspection.
- NVIDIA GeForce RTX 4050 Laptop GPU: 6,141 MiB VRAM, idle at inspection.
- Approximately 947 GiB filesystem space available inside WSL. This does not
  establish the free capacity of the Windows disk backing the virtual disk.
- Neither `ollama` nor `llama-server` was found on PATH.
- Baseline: 56 tests passed; Ruff lint and formatting checks passed.

## Candidates and runtime

Start with a four-billion-parameter model quantized to four bits. Download size
is not runtime memory: weights, context cache, runtime buffers, and the embedding
model must share available resources. Measure actual GPU allocation and latency.

| Candidate | Published artifact / license | Role in this experiment |
| --- | --- | --- |
| Qwen3 4B Instruct | Ollama Q4_K_M, 2.5 GB; Apache 2.0 | Selected first baseline |
| Qwen3.5 4B | Apache 2.0; multilingual results published by Qwen | Alternative to measure |
| Gemma 3 4B | Ollama Q4_K_M, 3.3 GB; Gemma terms | Alternative to measure |

These are candidates, not a measured ranking for Spanish regulatory synthesis.
The selected runtime is Ollama, with a local HTTP API and response token/timing
metrics. llama.cpp is an alternative with direct GGUF and CUDA configuration.
The selected artifact, runtime version, and measurements are recorded below. Do not interpret upstream family benchmarks as results for our corpus.

Primary sources checked on 2026-09-11:

- https://ollama.com/library/qwen3:4b-instruct
- https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://ollama.com/library/gemma3:4b
- https://docs.ollama.com/api/chat
- https://github.com/ggml-org/llama.cpp

## First measurement

1. Use complete, known evidence from the retained local PDF. Record document
   hash, version, page, chunk identifiers, and exact text.
2. Start with a 4,096-token context window and a short output budget; account for
   instructions, question, evidence, and generated tokens together.
3. Record cold and warm latency separately, prompt/output token counts, model
   digest, quantization, runtime version, and GPU/RAM use.
4. Review every generated claim against the supplied passages and check that
   each citation resolves to evidence actually supplied to the model.
5. Include empty evidence and an unrelated question. Valid citation identifiers
   alone do not establish that claims are supported.
6. Connect active-index retrieval after the known-evidence experiment. Compare
   three and five selected passages, preserving complementary content. Evaluate
   incomplete exceptions and conditions explicitly.

No similarity threshold is calibrated yet. A high score or nonempty result list
must not be treated as proof that sufficient evidence was retrieved. Reserve new
questions before tuning any context selection or abstention policy.

## Running the experiment

The selected model is `qwen3:4b-instruct` (Q4_K_M, Apache 2.0). The manually
installed runtime is Ollama 0.34.0. Its executable and libraries live under
`data/runtime/ollama/`; weights live under `data/models/ollama/`. Ollama also
creates its local identity under `~/.ollama/` on first start.

Start the server in a separate terminal from this checkout:

```bash
bash scripts/serve_ollama.sh
```

The script binds to loopback, disables Ollama cloud, and permits one concurrent
inference. Stop it with Ctrl+C when finished. No system startup service is added.
The initial downloads require Internet; subsequent inference uses local weights.

To reproduce on another machine, download the official Linux AMD64 archive for
Ollama 0.34.0 from its GitHub release and extract it into `data/runtime/ollama/`
with a zstd-capable tar. Keep its `bin/` and `lib/` directories together. The
first setup here used Python `zstandard` in `data/runtime/python-tools` because
no zstd executable was installed; this is not an application dependency.

```bash
data/runtime/ollama/bin/ollama pull qwen3:4b-instruct
uv run python scripts/evaluate_generation.py
uv run python scripts/evaluate_generation.py --retrieval
```

The model tag is mutable. The experiment saves `/api/version`, `/api/tags`, and
`/api/show` in `model.json`; check the digest before comparing another run. The
observed manifest digest is
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
Preserve the local manifest and blobs to retain that exact artifact.

Ask through the active catalog, or replay saved evidence without embeddings:

```bash
uv run python -m rag_bogado.generation --question '¿Quién debe garantizar la alfabetización en IA del personal?'
uv run python -m rag_bogado.generation --evidence-json data/evaluation/generation-2026-09-11-v3/known-evidence.json
```

The JSON response separates claims from exact original sources and retains the
original PDF path, hash, version, and index identity. Each claim has citation IDs.
`semantic_support_reviewed: false` is deliberate: structural citation validation
cannot verify entailment. `insufficient_evidence` can mean that no passage fitted
the selection policy, or that the model judged the supplied context insufficient;
it is not proof that the complete corpus contains no answer.

The current selector uses UTF-8 byte length as a conservative upper bound for
Qwen's byte-level BPE, with a template reserve and output budget. It does not cut
passages to make them fit. Exact/contained duplicates on the same page are
removed; partially overlapping passages remain intact to preserve complementary
conditions. The retrieval comparison uses 8,192 context tokens and records the
actual selected count. This conservative policy can leave usable space empty;
an exact tokenizer and overlap-aware grouping are possible later improvements.

The small development/held-out split lives in
`src/rag_bogado/evaluation/datasets/generation.json`. The experiment only executes
development cases. Its reports need manual claim-support, coverage, and
abstention review; no semantic pass rate is inferred from HTTP success or valid
JSON. Threshold calibration and held-out validation remain pending.

## Measured results and review

The reference report is
[`local-generation.json`](../src/rag_bogado/evaluation/reports/local-generation.json).
Full local runs are under `data/evaluation/generation-2026-09-11-v3/`; earlier
attempts remain in the adjacent initial, diagnostic, and v2 directories.

| Configuration | Wall time | Prompt / output tokens | Sampled device VRAM |
| --- | --- | --- | --- |
| Known Article 4, reload | 7.44 s | 445 / 96 | 3,133 MiB |
| Same evidence, warm | 1.98 s | 445 / 96 | 3,133 MiB |
| Paraphrase, top 3 | 5.07 s, including context resize/reload | 987 / 19 | 4,388 MiB |
| Paraphrase, top 5 | 2.06 s | 1,485 / 101 | 4,388 MiB |
| Compound question, top 3 | 1.87 s | 932 / 68 | 4,388 MiB |
| Compound question, top 5 | 2.71 s | 1,437 / 127 | 4,388 MiB |

These are individual observations, not stable latency estimates. Warm runs benefit
from prompt caching. Generation timings exclude retrieval and Python startup;
GPU figures during retrieval experiments include retained embedding allocations.
Summed Ollama/runner RSS peaked near 2.70 GiB during model loading; it can count
shared mappings twice and excludes the Python embedding process. Sampling at
0.5-second intervals can miss peaks. The first installation run had a slower
startup; the table describes a later model reload with system caches warm.

Assistant review of the actual supplied passages found:

- The known-evidence response identifies the correct actors and duty to adopt
  measures, with S1 pointing to the complete original Article 4 excerpt. It omits
  qualifications, including the extent-possible wording and contextual factors;
  it is not an exhaustive legal explanation of that article.
- The paraphrase's useful evidence ranks fourth. Top three abstains appropriately
  on its selected context; top five answers using S4 on page 51.
- Both compound-question responses fail coverage. Top three only answers updating;
  top five adds a statement about a non-high-risk assessment from a cut passage.
  Neither explicitly acknowledges the unanswered parts. Structurally valid
  citations did not establish a complete, relevant answer.
- Both development negatives abstain with either three or five retrieved passages.
  Empty evidence also abstains without calling the LLM. This small set does not
  establish reliable abstention in general.

The exploratory threshold sweep only evaluates selection, not new LLM responses.
A threshold of 0.84 removes the two negatives but preserves the positive queries'
irrelevant/incomplete candidates. At 0.87, the paraphrase loses its useful fourth
passage while retaining an irrelevant first passage. No threshold is enabled by
default or accepted as calibrated. The held-out questions remain unexecuted.

The first session target is achieved: measured local synthesis with verifiable
sources. Milestones 5/6 remain incomplete because compound-question coverage,
qualification preservation, and explicit reporting of insufficient context need
improvement before an API/UI delivery.

## Why separate retrieval and context selection?

The Sentence Transformers [retrieve-and-rerank guide](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
uses a fast first-stage retriever followed by query/passage scoring. This supports
keeping the candidate pool separate from LLM context. A reranker is a candidate
experiment here, not an implemented quality improvement.

[Lost in the Middle](https://arxiv.org/abs/2307.03172) measures sensitivity to where
relevant information occurs in context. Its findings motivate testing context
selection and ordering, but are not evidence about this exact Qwen run. Our own
observations show that raising top-k helped one question and did not resolve the
compound question. An adaptive policy should consider coverage as well as scores.

## Separate questions within one query

The live `--question` command now runs a local question-separation step, retrieves
up to ten candidates independently for each detected question, and generates a
separate answer from each selected context. Its default context is 8,192 tokens.
The original query and the detected questions remain visible in the JSON output.

```bash
uv run python -m rag_bogado.generation --question '¿Quién debe procurar la alfabetización en IA y cuándo debe prepararse y actualizarse la documentación técnica de una IA de alto riesgo?'
```

The response contains `decomposition` and `answers`. Each answer has a question
ID, its own status, exact sources, provenance, and metrics. Citation IDs such as
`Q1-S2` cannot accidentally resolve to another question's source. The final list
is assembled without another LLM rewrite, so an answer, abstention, or error is
not dropped during presentation. All retrievals must refer to the same document
version/index. A detected version change is reported as an error for that part.

Top-level status is `answered` if every part reports an answer, `partial` if
some parts answer and others abstain or fail, `insufficient_evidence` if all
abstain, and `error` if there are errors and no successful answers. These are
execution/model statuses, not certification of semantic correctness. Failure to
obtain a valid decomposition stops the request; individual retrieval/generation
failures remain visible and do not prevent later questions from being processed.
The separator accepts one to six questions and rejects malformed, duplicate, or
truncated output; fidelity and coverage are not automatically verified.

Saved `--evidence-json` replay retains the original single-context behavior: it
neither separates questions nor performs new retrieval. This keeps the first
synthesis benchmark reproducible.

Run the focused development experiment with:

```bash
uv run python scripts/evaluate_question_workflow.py --output-dir data/evaluation/question-workflow-new
```

The reference is
[`question-workflow.json`](../src/rag_bogado/evaluation/reports/question-workflow.json).
The compound query is separated into three self-contained questions, with
independent source sets. A mixed query correctly answers document preparation
and abstains on a company-specific phone number. Recorded total pipeline times
were 22.54 s for the three-part query and 12.13 s for the mixed query, including
separation, retrieval and generation, excluding interpreter startup.

This increment does not resolve answer reliability. The preparation subquestion
still selects passages missing the relevant timing sentence and the model infers
unsupported timing from a cut recital. Literacy responses can include peripheral
claims and incomplete citation support. The comparison and simple-question cases
are preserved, but a subject enumeration is over-split. The report records these
failures explicitly. Held-out questions remain unexecuted.
