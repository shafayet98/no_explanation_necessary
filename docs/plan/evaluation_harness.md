# Plan: Evaluation Harness (Phase 2)

## Goal

`python eval/eval.py` runs ~200 hand-written test cases through the live index,
prints recall@10 and MRR, compares against the Phase 1 baseline recorded in
`eval/baselines.json`, and exits non-zero if the harness itself errors — making
the eval gate operational for all future phases.

---

## Which layers are touched

**Eval harness only.** `eval/` is orthogonal to the five layers (see
`docs/architecture.md`). The harness is a consumer of two existing public APIs:

- `embedding.embed()` — Embedding layer
- `index.load()` and `index.search()` — Index layer

No layer implementation changes. No seam concerns.

> The Understanding layer is bypassed in Phase 2 because it is still a stub.
> The harness calls `embed` + `search` directly. When Phase 5 lands, update eval
> to route through `understanding.query()`.

---

## Steps

### Step 1 — Write test cases (no code)

Populate `eval/test_cases.jsonl` with 200 `{"description": "...", "expected_word": "..."}` pairs.

Distribution:
- **60 easy** — synonym or near-paraphrase of the definition.
  Example: `"a feeling of great happiness"` → `"joy"`.
  These should be reliably recalled.
- **90 medium** — own-words definition without using the target word.
  Example: `"the deep contentment that comes after a hard day's work"` → `"satisfaction"`.
  Expected word should appear in top 10 most of the time.
- **50 hard** — evocative, poetic, or indirect.
  Example: `"the smell of rain on dry earth"` → `"petrichor"`.
  These test the limits of the Phase 1 system; some will fail, which is the point.

Constraints:
- All expected words must be confirmed present in `data/raw/corpus.jsonl`.
- Include the curated eval targets already in the corpus (petrichor, saudade).
- Normalise expected words to lowercase to match `WordRecord.word`.

Done when: `eval/test_cases.jsonl` has ≥ 150 lines, each with `description` and
`expected_word`, every expected word present in the corpus.

### Step 2 — Implement `eval/eval.py`

Replace the `NotImplementedError` stub with a working harness:

```
load index
for each test case:
    embed description → search(k=10) → find rank of expected_word
compute:
    recall@10  = fraction of cases where word appears in top 10
    MRR        = mean of 1/rank (0 if not found)
print:
    per-case table (description | expected | rank or MISS | score)
    aggregate: recall@10, MRR
    delta vs. latest baseline in baselines.json
exit 0 on success, exit 1 if harness itself errors
```

CLI interface:
- `python eval/eval.py` — run and compare against baseline.
- `python eval/eval.py --save-baseline --phase N` — run, then append result to
  `baselines.json` as `{"phase": N, "recall_at_10": ..., "mrr": ..., "date": "YYYY-MM-DD"}`.
  `--phase` defaults to (highest existing phase + 1) if omitted.

Done when: `python eval/eval.py` prints recall@10 and MRR without errors.

### Step 3 — Record Phase 1 baseline

Run `python eval/eval.py --save-baseline --phase 1`.

Done when: `eval/baselines.json` has exactly one entry with `"phase": 1` and real
metric values.

### Step 4 — Add harness unit tests

Add `tests/test_eval.py` with:
- Test that `eval/test_cases.jsonl` parses without error and every line has both
  required keys.
- Test that `eval/baselines.json` is valid JSON with at least one entry.
- Smoke test: run harness logic on a 3-case in-memory fixture and assert
  hand-computed recall and MRR values are correct.

Done when: `pytest tests/` passes (16/16: 13 existing + 3 new).

---

## Eval impact

Phase 2 is the eval gate — it cannot run before itself. After Step 3 records the
baseline, the gate is active for all subsequent phases.

---

## Files to create or modify

| File | Change |
|---|---|
| `eval/test_cases.jsonl` | Populate with ~200 hand-written test pairs (currently empty) |
| `eval/eval.py` | Replace stub with full implementation |
| `eval/baselines.json` | Record Phase 1 baseline (currently `[]`) |
| `tests/test_eval.py` | New — harness unit tests |

No file crosses a layer boundary.

---

## Risks / decisions

1. **Expected word not in corpus.** Cross-check each expected word against
   `data/raw/corpus.jsonl` before finalising. Words like `sonder` may be absent.

2. **Exact-match normalisation.** Match expected word against `WordRecord.word`
   case-insensitively. A lemma mismatch ("nostalgic" vs "nostalgia") scores as MISS.

3. **Phase 1 baseline will be low.** ~0.50–0.65 recall@10 is expected with
   single-sense, no-reranker. That is fine — the baseline exists to be beaten.

---

## Estimated scope

Medium — roughly half a day. Test case writing is the bulk of the work.

Order: Step 1 → Step 2 → Step 3 → Step 4.
