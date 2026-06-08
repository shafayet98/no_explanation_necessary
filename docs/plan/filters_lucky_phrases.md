# Plan: Filters, Lucky Mode, and Phrase Normalization

## Goal

`query()` applies `QueryFilters` (pos, starts_with, max_length), returns a single top
result in "feeling lucky" mode, normalizes multi-word phrase inputs, and the `/query`
API endpoint is wired to accept and forward all of these — with eval showing no
regression against the Phase 5 baseline.

---

## Which layers are touched

| Layer | Change |
|---|---|
| Understanding | Primary: filter application, lucky mode, phrase normalization — all in `understanding/query.py` |
| Interface | Secondary: wire filter params + lucky flag from HTTP request body into `QueryFilters` and call `query()`. **No logic here** — thin pass-through only. |

Two-layer touch is expected and correct per the Phase 6 row in `docs/architecture.md`.
The seam is intact: the interface layer holds zero business logic.

---

## Current phase check

Phase 5 is complete (merged, baselines recorded). Phase 6 is next in sequence. In order.

---

## Steps

### Step 1 — Input normalization helper (`understanding/query.py`)

Add `_normalize_input(text: str) -> str` at the top of `query()`:
- Strip leading/trailing whitespace
- Collapse internal runs of whitespace to a single space
- Strip leading/trailing sentence-ending punctuation (`.`, `,`, `!`, `?`) that could
  bleed into the embedding

Apply at the very top of `query()` before classification. This covers multi-word
phrase inputs like `"  silver lining. "` → `"silver lining"`.

**Done when:** unit test confirms `"  the smell  of rain. "` normalizes to
`"the smell of rain"` and that the result from `query()` matches the un-padded form.

---

### Step 2 — Filter predicate + oversampling (`understanding/query.py`)

Add `_passes_filter(record: WordRecord, filters: QueryFilters) -> bool`:

```python
def _passes_filter(record, filters):
    if filters.pos is not None and record.pos != filters.pos:
        return False
    if filters.starts_with is not None and not record.word.lower().startswith(filters.starts_with.lower()):
        return False
    if filters.max_length is not None and len(record.word) > filters.max_length:
        return False
    return True
```

Update `_run_single_concept()` to accept `filters: QueryFilters | None = None`:
- When any filter is active, retrieve `k=100` from the index instead of `k=50`
  to compensate for filter attrition.
- After reranking, apply `_passes_filter` to the full reranked list, then take `[:10]`.
- If fewer than 10 results survive the filter, return what's left (no fallback — the
  user asked for it).

**Done when:** mocked unit test verifies:
- `pos="n"` filter excludes non-noun results
- `starts_with="p"` filter is case-insensitive and excludes non-matching words
- `max_length=5` excludes words longer than 5 characters
- Combined filters apply all conditions
- `filters=None` passes everything through unchanged

---

### Step 3 — Thread `filters` through `query()` (`understanding/query.py`)

Update `query()` to accept `filters` and pass it into `_run_single_concept()` on
both the single-concept and multi-concept paths.

Multi-concept path: apply the same `filters` to each sub-concept group. This is
intentional — if the user asked for nouns starting with "p", that constraint applies
to all groups.

**Done when:** calling `query("...", filters=QueryFilters(pos="n", starts_with=None,
max_length=None))` returns only noun results across all groups.

---

### Step 4 — "Feeling lucky" mode (`understanding/query.py`)

Add `lucky: bool = False` as a keyword argument to `query()`. When `True`, truncate
each `ConceptGroup.results` to `[:1]` before returning. This is a presentation
concern — one line added after groups are assembled.

This extends the layer contract. The change is backwards-compatible (existing callers
pass no `lucky` arg, default is `False`). Update `docs/architecture.md` to record
the new signature.

**Done when:** `query("...", lucky=True)` returns exactly 1 result per group;
`query("...", lucky=False)` returns up to 10 per group as before.

---

### Step 5 — Tests (`tests/test_filters.py`)

New test file. All external calls (index/engine, embedder, reranker) mocked so tests
pass without a loaded index or API key.

Test cases:
- `_normalize_input`: whitespace collapsing, punctuation stripping, empty string
- `_passes_filter`: each filter field independently, combined filters, `None` filters
- `_run_single_concept` with filters: verify filtered results only (mock the
  reranker to return a fixed list with mixed pos/word properties)
- `query()` with filters threaded through single-concept path
- `query()` with `lucky=True` returns exactly 1 result per group
- `query()` with `lucky=False` (default) returns up to 10

**Done when:** `pytest tests/test_filters.py` passes without any live model or
index loaded.

---

### Step 6 — Eval gate

Run `python eval/eval.py` **before** making any code changes (confirm Phase 5
baseline: recall@10 = 0.5855, MRR = 0.4227).

Run again **after** all changes. The eval harness calls `understanding_query(case["description"])` with no filters and no lucky flag, so filter logic is inert during eval. Phrase normalization may marginally affect a handful of cases if any descriptions had trailing punctuation — the effect is expected to be negligible.

Gate: numbers must be ≥ Phase 5 baseline. If any metric drops, investigate before proceeding.

After a passing eval: `python eval/eval.py --save-baseline --phase 6`.

---

## Eval impact

Filter and lucky-mode logic are not invoked by the eval harness (no filters passed,
no lucky flag). Phrase normalization may cause trivially small changes. **Eval must
still be run** — the gate rule applies to every quality change regardless.

Baseline to compare against: **recall@10 = 0.5855, MRR = 0.4227** (Phase 5).

---

## Files to create or modify

| File | Change |
|---|---|
| `understanding/query.py` | Add `_normalize_input`, `_passes_filter`, update `_run_single_concept` + `query` for filters + lucky |
| `docs/architecture.md` | Update `query()` signature to document `lucky` param |
| `tests/test_filters.py` | New test file for filters, lucky mode, normalization (all mocked) |
| `docs/plan/filters_lucky_phrases.md` | This file |

No new files cross a layer boundary. `tests/` is orthogonal infrastructure.

---

## Risks / open questions

1. **Filter attrition returning 0 results** — with very restrictive combined filters
   (e.g., pos="v" + starts_with="z" + max_length=3), 0 results may survive. Decision:
   return an empty `results` list — the user asked for it. No silent relaxation.
   The interface layer can surface this as an empty response; the frontend (Phase 8)
   decides how to render it.

2. **k=100 oversampling overhead** — doubling the vector search window when filters are
   active is a safe heuristic. If a filter is highly restrictive (e.g., max_length=3),
   even k=100 may not yield 10 survivors. Accepted limitation — flag in docstring.

3. **Multi-word phrase handling scope** — scoped to input normalization (whitespace
   collapsing, punctuation stripping). Short multi-word phrases like "silver lining"
   already classify correctly as "single" via the existing heuristics; no special
   routing needed. Filters (starts_with, max_length) apply to multi-word result words
   using the full phrase string, which is the natural behaviour.

4. **lucky signature change** — adds `lucky: bool = False` to `query()`. This is
   backwards-compatible but changes the layer contract. Document in
   `docs/architecture.md`.

5. **Interface layer** — deferred to Phase 8. Filters and lucky mode are exercised
   through `scripts/query.py` and the eval harness directly.

---

## Estimated scope

**Small–Medium** (~2–3 hours). Filter logic is straightforward; the main time is
in writing mocked tests that cover the filter combinations without loading the index.
