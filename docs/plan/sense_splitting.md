# Plan: Sense Splitting (Phase 3)

## Goal

The system embeds every (word, sense, definition) triple separately, deduplicates at the result stage so no word appears twice in the top 10, and eval improves over the Phase 2 baseline (`recall@10 = 0.6167`, `MRR = 0.4461`).

---

## Which layers are touched

**Data layer** (`scripts/fetch_corpus.py`, `data/loader.py`) — the corpus format changes and `load_records()` changes its expansion logic.

**Index layer** (`index/engine.py`) — deduplication is added as a post-retrieval step inside `search()`.

Two layers is expected and correct here: the data contract changes (more records), which the index layer must handle cleanly (dedupe before returning). No seam issues — each change stays within its own layer's boundary.

---

## Current phase check

Phase 1 and Phase 2 are both complete and merged into `main`. This is the correct next phase. Eval gate is active.

---

## Steps

### Step 1 — Update `scripts/fetch_corpus.py` to collect all senses *(data layer)*

Change `_fetch_entry` from "return the first definition found" to "collect all (pos,
definition) pairs across all entries and meanings." New corpus line format:

```json
{"word": "bank", "senses": [{"sense": 0, "pos": "n", "definition": "..."}, {"sense": 1, "pos": "v", "definition": "..."}]}
```

The resume logic keyed on `entry["word"]` still works since the top-level `"word"` key is unchanged.

Re-run `python scripts/fetch_corpus.py --force` to re-fetch with all senses.

Done when: every line in `corpus.jsonl` has a `"senses"` key with a non-empty list.

---

### Step 2 — Update `data/loader.py` to expand senses into one WordRecord each *(data layer)*

Iterate over `entry["senses"]` and emit one `WordRecord` per sense. The `sense` field
becomes the real sense index (0, 1, 2…). The `id` is a global counter across all
records. `embed_text` stays `"{word}: {definition}"`.

Done when: `load_records()` returns significantly more records than 3,787 (expect
~8k–15k), and each `(word, sense)` pair is unique.

---

### Step 3 — Add deduplication to `index/engine.py` *(index layer)*

After retrieving the raw top candidates, group by word and keep only the
highest-scoring sense per word before returning. Retrieve a larger internal shortlist
(`k * 5`) to ensure enough unique words survive deduplication.

Signature stays identical — deduplication is an internal implementation detail.

Done when: `search(k=10)` never returns two results with the same word.

---

### Step 4 — Rebuild the index *(operational — no layer change)*

Run `python scripts/build_index.py --force`. Must use `--force` because the corpus
changed but the model ID is unchanged — the cache-validity check only compares model
ID, so without `--force` it would incorrectly report a cache hit.

Done when: build completes and `index/cache/meta.json` shows the new (larger) record
count.

---

### Step 5 — Run eval and record Phase 3 baseline *(eval — no layer change)*

Run `python eval/eval.py` before rebuilding (should reproduce Phase 2 baseline) and
again after. If numbers improve, record with:

```
python eval/eval.py --save-baseline --phase 3
```

Done when: Phase 3 entry written to `eval/baselines.json`.

---

## Eval impact

Yes — quality change. Run `python eval/eval.py` before (baseline: `recall@10 = 0.6167`,
`MRR = 0.4461`) and after rebuilding. Numbers must go up to keep the change.

---

## Files to create or modify

| File | Change |
|---|---|
| `scripts/fetch_corpus.py` | `_fetch_entry` collects all senses; new `"senses"` list corpus format |
| `data/loader.py` | Expands each entry's `senses` into one `WordRecord` each |
| `index/engine.py` | Deduplication by word inside `search()` |
| `eval/baselines.json` | New Phase 3 entry added by eval script |
| `docs/plan/sense_splitting.md` | This plan document |

No new files cross a layer boundary.

---

## Risks / open questions

1. **Re-fetch time**: ~3,787 words with 20 concurrent workers takes several minutes.
   Unavoidable since the current corpus has only one sense per word.
2. **Dedup requires oversampling**: `search(k=10)` must retrieve `k * 5` raw results
   internally before deduping, otherwise fewer than 10 unique words may survive.
3. **`--force` is mandatory after re-fetch**: `build_index.py`'s cache check only
   compares model ID, not corpus content. Must always pass `--force` when the corpus
   has changed.
4. **Sense count variance**: Some words have 10+ senses in the Free Dictionary API;
   others have 1. Final record count could be 8k–20k. Embedding time scales accordingly.

---

## Estimated scope

**Medium (half day)** — code changes are straightforward; time is dominated by
re-fetching the corpus (~5–10 min) and re-embedding the larger record set (~5–10 min
on first run).
