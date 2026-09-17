# Saved-source synthesis replay — 2026-09-16

The development experiment isolates synthesis from retrieval and question splitting.
It reuses the saved sources of d03 (two grouped questions) and d02 (a paraphrase),
with local `qwen3:4b-instruct`, temperature 0, seed 42, an 8192-token context and
512 output tokens. The automated reviewer is unchanged. No held-out cases ran.

## Findings

| Run | Application outcome | Assistant inspection of saved evidence |
| --- | --- | --- |
| d03 Q1, original prompt | Rejected | Wrong citation in one claim; another omits qualifications but receives a positive claim review. |
| d03 Q2, original prompt | Rejected | Preparation timing cites S1, which only supports updating. |
| d03 Q1, final prompt | Answered | S5 claim preserves qualifications; peripheral recitals and a truncated list remain. Not accepted as a full fix. |
| d03 Q2, final prompt | Answered | Preparation and updating are covered together, supported by S1 and S7. |
| d02, final prompt | Answered | One S4 claim preserves the source's qualifications. |

These are assistant observations, not user acceptance or verification of current law.
For example, the final d03 Q2 answer was:

> La documentación técnica de una IA de alto riesgo debe prepararse antes de su introducción en el mercado o puesta en servicio y mantenerse adecuadamente actualizada durante toda la vida útil del sistema. [S1, S7]

S7 contains the preparation timing and updating requirement; S1 contains updating
throughout the system's lifetime. IDs are local to each replay; the report maps
them to the original question-specific IDs and includes full source text.

The compact prompt asks for direct evidence per requested aspect, preservation of
qualifications, and no completion of cut sentences. This improved the observed
answers but did not eliminate irrelevant claims or reviewer false positives.
There was one final run per case; reliability across repetitions and generalization
remain unmeasured. d02 shares the literacy topic and is not independent validation.

## Context-budget confound

A longer initial prompt dropped source 7 from Q1. That run is retained as diagnostic
output but excluded from controlled comparison. Another variant retained Q1 sources
but completed a cut sentence; Q2 with that variant was blocked before inference
because a source would be dropped. The final compact prompt preserves all seven
d03 sources and all six d02 sources. The replay tool now rejects source loss before
calling the model. This guard belongs to diagnostic replay; production context
selection still operates within its configured budget.

All seven completed runs, prompts, model calls, source mappings and outcomes are
in [the report](../src/rag_bogado/evaluation/reports/synthesis-replay-2026-09-16.json).
Queueing and cold loading affect recorded timings; these are not latency benchmarks.

## Reproduce the final prompt

Start the existing local runtime with `bash scripts/serve_ollama.sh`, then run:

```bash
uv run python scripts/review_saved_answer.py --source-report src/rag_bogado/evaluation/reports/grouped-compound-review.json --case d03 --search-count 2 --question-id Q2 --source-mode all --output-dir data/evaluation/d03-replay-new
```

Choose a new output directory for each run. `--source-mode all` replays all saved
sources, including those of rejected synthesis. The default `literal` mode retains
the original exact-copy validation. Drafts are diagnostic and stay separate from
the gated application answer. Original prompts are preserved in the report.

Next: evaluate context selection and reviewer relevance on the remaining Q1 failure,
using positive and negative development examples. Do not promote synthesis based
on an automated approval or tune against held-out questions.
