# Two-search retrieval and evidence review

The live workflow separates explicit questions, then searches with each original
question and one local LLM rewrite. It selects evidence per original question
from the combined results. It never answers the rewrite itself.
There is no recursive loop or answer-driven retry. A request has at most six
detected questions, two searches per question and, in experimental synthesis mode, six draft claims per answer.

## Combining evidence

Each search retrieves ten candidates by default. Reciprocal Rank Fusion (RRF)
adds `1 / (60 + rank)` for each list containing a point. Points appearing in only
one list remain candidates. Duplicate point IDs in the same list get one vote;
conflicting text for the same point is rejected. Document, version, content hash
and index identity must match across searches and answered questions.

RRF scores are separate from embedding similarities and are not probabilities.
Ties preserve original-query order. No rules target a particular article, page,
question, or expected answer. Selection permits up to ten final sources within
the existing conservative token budget; it may send fewer. The context is not
expanded simply because two searches ran. An identical rewrite runs only once.
Malformed rewrites or failed searches yield a visible per-question error.

The response preserves both search rankings, the rewrite, per-point ranks and
scores under `retrieval`. `retrieval_seconds` includes rewriting and both searches;
rewrite timing is also available separately. Rewriting fidelity is not certified:
the prompt forbids altered intent, but structural validation cannot prove that.

RRF reference: [Microsoft documentation](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking).
Query rewriting reference: [Ma et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.322/).

## Default: exact source passages

The default `--answer-mode evidence` asks the LLM only for source IDs. The application
validates the IDs, rejects duplicates and contradictory statuses, and copies each
selected passage verbatim into `claims`, with its citation. No LLM-authored prose
is admitted to this output. Conditions inside that retrieved passage remain intact.
Unknown IDs, extra generated text and invalid output are errors.

`answer_mode = evidence` and `support_review.status = exact_source_copy` distinguish
this output from synthesis. `answered` means evidence was selected, not that a legal
explanation was certified. These are entire **retrieved chunks**, not necessarily
complete articles: extraction/chunking can still omit surrounding context, and the
LLM may select irrelevant passages. Exact copying proves text provenance only.
Users must still inspect the original document for applicability and completeness.

## Experimental synthesis and mandatory review

With explicit `--answer-mode synthesis`, generation is instructed to use only selected evidence, answer only the requested
question, and preserve qualifications. Citation validation first checks structure
and membership. A separate local LLM call then reviews each claim against **only
its own cited passages**, checking support, relevance and preserved qualifications.
Review calls have an 8,192-token budget and a 1,024-token output limit.

Every claim needs a complete, positive verdict. Any negative verdict discards the
whole draft, returns empty `claims` and `insufficient_evidence`, and records
`support_review.status = rejected`. This means the draft failed review; it does
not establish that the corpus has no answer. Removing only rejected claims could
silently drop a necessary qualification, so no partial draft is published.
Unavailable, malformed, incomplete, over-budget or truncated review yields an
error, never an accepted answer. Empty evidence and model abstention need no review.
Rejected draft text is not returned in the answer. Original sources remain visible.

This gate applies to synthesis in both live queries and saved-evidence replay and
cannot be disabled while retaining synthesis. Existing historical reports retain the earlier prompts
and unreviewed behavior; current replay defaults to exact passages. Request
`--answer-mode synthesis` to run the new synthesis prompt and gate.

**Automated review is fallible.** The same local model can share errors with its
draft. A passing verdict is not proof of entailment or legal correctness.
`human_verified` and `semantic_support_reviewed` are not set to true by the model.
No guarantee of zero hallucinations or readiness for legal reliance is claimed.
Unsupported claims are unacceptable; measured false approvals must remain failures
in the evaluation rather than being relabeled as successful answers.

## Evaluation

Start the local Ollama server as documented in [local-generation.md](local-generation.md).

```bash
uv run python scripts/evaluate_multi_query.py --output-dir data/evaluation/multi-query-new
```

The destination must not exist. This runs known development queries with one and
two searches and identical final passage/token budgets. Its default evaluates exact
passages; add `--answer-mode synthesis` to evaluate synthesis with mandatory review.
It saves each completed case, model provenance, prompts, raw rankings, answers,
review verdicts and total pipeline latency. Both arms use the same answer mode and prompt; synthesis arms both include
review, so the comparison isolates search count rather than old/new guardrails.
Question separation is repeated with deterministic settings; inspect the outputs
before comparing if the detected questions differ. Cases are development-only;
held-out questions remain reserved. Model caching and order affect latency.

Each answer includes a blank manual evaluation form. Fill these dimensions
separately, against the original request and its actual citations:

| Field | Values / criterion |
| --- | --- |
| `answers_request` | yes / partial / no |
| `requested_parts`, `answered_parts` | Counts of explicit requested parts and those covered |
| `supported_claims`, `total_claims` | Count all assertions; one unsupported clause makes its claim unsupported |
| `qualifications_preserved` | yes / partial / no; conditions, exceptions, actors and obligation strength |
| `no_unnecessary_information` | yes / partial / no |
| `appropriate_abstention` | yes / no / not_applicable; distinguish missing evidence from rejecting a useful draft |
| `rewrite_faithful` | yes / partial / no / not_applicable |

An empty answer has zero claims, not a perfect support score. An execution error
is not a successful abstention. Accept varied wording and alternative valid
sources: there is no exact reference answer check and no weighted aggregate that
can hide an unsupported assertion. Numeric acceptance thresholds require reviewed
examples; none are assumed calibrated. An automated judge's verdict is recorded
separately from the manual labels.

The CLI defaults to exact source passages and two searches. Use `--search-count 1` for the baseline; both
modes default to `--max-passages 10 --context-tokens 8192`. Saved replay performs
no new search regardless of `--search-count`.

## September 14 measurements

Reference reports retain exact inputs, outputs and assistant inspection alongside
the still-blank human evaluation forms:

- [Synthesis comparison](../src/rag_bogado/evaluation/reports/multi-query-synthesis.json):
  six runs / twelve subquestion answers. The automated judge falsely approved
  omitted literacy qualifications and an invented duty from a cut preparation
  passage. The latter even varied between repeated identical retrievals. A passing
  judge verdict is therefore explicitly insufficient for acceptance.
- [Exact-passage comparison](../src/rag_bogado/evaluation/reports/multi-query-evidence.json):
  six runs / twelve subquestion answers. Every returned text exactly matches its
  cited chunk. The negative phone-number question abstains in both arms. Literacy
  still includes peripheral passages; copying cannot establish relevance.

All rewrites in the exact-passage run repeated the original, so its nominal
two-search arm executed one effective search per question. It does **not**
demonstrate a multi-query quality gain. The synthesis run did exercise a distinct
literacy rewrite; deterministic tests also exercise distinct lists and fusion.
Further development examples are needed to measure faithful, useful rewrites.
No claim of optimality for RRF or ten passages is made.

Observed exact-passage pipeline times were approximately 4–5 seconds (simple),
13–14 seconds (compound) and 9–10 seconds (mixed). Synthesis runs took approximately
14–36 seconds. These are individual cache/order-dependent measurements, not a
controlled latency benchmark. No held-out cases or new models were used.

## Joint development review

The [nine-case review sheet](development-review.md) starts with a saved real answer
and keeps user judgments pending until supplied. Run cases incrementally with
`--dataset src/rag_bogado/evaluation/datasets/development-review.json --case d02
--search-count 1`. The original three default cases remain unchanged. The dataset
loader selects only `development`, never `held_out`.

## Group related actions without dropping questions

Updated question separation keeps coordinated actions with the same interrogative,
object and context together. It uses generic examples outside the legal corpus;
there are no rules for specific articles or expected legal answers. If the model
returns only one question, the original user text is retained deterministically:
separation must not become a lossy rewrite. The proposed text and whether it was
restored remain visible in `decomposition`.

For the development compound request, the final decomposition is now:

1. ¿Quién debe procurar la alfabetización en IA?
2. ¿Cuándo debe prepararse y actualizarse la documentación técnica de una IA de alto riesgo?

The second question still contains two requested aspects; a two-question split
does not prove the generated answer covers both. Earlier reference reports retain
the historical three-question split.

Every processed question has `answer_state`: `answered`, `review_rejected`,
`abstained` or `error`. Unanswered parts have a user-facing `display_message` and
also appear in `unanswered_questions`. A reviewer rejection is distinct from not
obtaining an answer from selected evidence. Existing `status` values are preserved
for compatibility. `answered` remains an execution/model outcome, not legal approval.

The old d03 A run did extract all questions: the reviewer subsequently rejected
literacy and preparation. Grouping alone does not fix those synthesis failures.
The new state/message fields prevent downstream presentation from silently skipping
such parts. UI consumers should render every answer block, not only nonempty claims.

[Question-grouping evaluation](../src/rag_bogado/evaluation/reports/question-grouping.json)
records nine development cases before and after the single-question protection.
The initial prompt-only attempt lost a subject in d04; that failure is retained.
After protection, the reviewed nine outputs preserve the intended requests.

```bash
uv run python scripts/evaluate_multi_query.py \
  --dataset src/rag_bogado/evaluation/datasets/development-review.json \
  --split-only --output-dir data/evaluation/question-grouping-new
```

This command performs no retrieval or generation of answers and never selects the
held-out split. Its `separated` status is execution success, not a semantic score.
