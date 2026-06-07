# Eval Gate Rules

The evaluation harness is the single source of truth for quality. These rules are non-negotiable from Phase 2 onward.

## The Gate

**Before any quality change:** run `python eval.py` and note the current recall@10 and MRR.
**After any quality change:** run `python eval.py` again.
- Numbers go up → keep the change.
- Numbers go down → revert the change. Do not ship it.
- Numbers stay the same → the change is neutral on quality; use other criteria (speed, simplicity) to decide.

"Quality change" means anything that could affect which words appear in results or in what order: embedding model, reranker, index type, understanding layer routing, deduplication logic, filter logic.

## The Test Set is Sacred

- Never delete test cases.
- Whenever a query fails (expected word not in top 10), add it to `eval/test_cases.jsonl` as a new permanent case.
- The test set grows monotonically. It is the accumulated record of where the system has failed.
- When adding test cases, cover all difficulty levels: easy (synonym/paraphrase), medium (own-words definition), hard (evocative/poetic).

## Baselines

- `eval/baselines.json` stores the metric snapshot at the end of each phase.
- Format: `[{"phase": 1, "recall_at_10": 0.62, "mrr": 0.41, "date": "2024-01-15"}, ...]`
- Record a baseline entry after completing each phase. This is the permanent record of progress.

## Metrics

**Recall@10:** fraction of test cases where the expected word appears in the top 10 results.
- Measures: does the system find the right word at all?
- Target: should improve at every phase with a quality focus.

**MRR (Mean Reciprocal Rank):** average of 1/rank for each test case where the word was found (0 if not found).
- Measures: does the system rank the right word near the top?
- The more sensitive metric — use MRR as the tiebreaker when recall is tied.

## What Eval Does NOT Cover

- Latency (measure separately with a timing script if needed).
- Subjective quality of mood/passage interpretations — these require human review.
- The canary test case — run that manually when touching the understanding layer.
