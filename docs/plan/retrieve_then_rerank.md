# Plan: Retrieve-then-Rerank

> Phase 4. Builds directly on Phase 3 (sense-splitting). Must restore and beat the
> Phase 1/2 baseline before Phase 3 is considered complete.

---

## Goal

Implement cross-encoder reranking in the understanding layer so that Phase 4 beats
the Phase 1/2 baseline (recall@10 ≥ 0.6167, MRR ≥ 0.4461), completing Phase 3.

---

## Which layers are touched

| Layer | Changed? | Why |
|---|---|---|
| Understanding (`understanding/reranker.py`, `understanding/query.py`) | **Yes** | Reranker lives here; `query()` wires the full pipeline |
| Eval harness (`eval/eval.py`) | **Yes** | Must route through `query()` to actually measure the reranker |
| Index (`index/engine.py`) | No | `search()` already oversamples and deduplicates — no change needed |
| Embedding | No | Model is unchanged |
| Data | No | Corpus and loader are unchanged |
| Interface | No | API stub is unchanged |

**Seam check:** Only the understanding layer changes. The eval harness is orthogonal
infrastructure (not one of the five layers), so updating it is not a layer-boundary
violation. The "update eval to call `understanding.query()` when Phase 5 lands" note
in the codebase was written before Phase 4 was concrete — Phase 4 is when the
reranker activates, so this is the right moment to make that update.

---

## Current phase check

Phase 3 is shipped (branch merged into `main`) but per the progress log is not
considered complete until Phase 4 restores the baseline. Phase 4 builds directly on
Phase 3. This task is in-order.

---

## Steps

### 1. Implement `understanding/reranker.py` — cross-encoder scoring

**Layer:** Understanding

Replace the stub with a real implementation:

- Add a lazy-loaded `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` singleton
  (same lazy pattern as the embedder singleton). Model downloads once to the
  HuggingFace cache (~68 MB); no `requirements.txt` change needed — `sentence-transformers`
  is already installed and includes `CrossEncoder`.
- Update the type signature: `rerank(candidates: list[SearchResult], query_text: str) -> list[SearchResult]`
- Build input pairs as `(query_text, record.embed_text)` for each candidate.
  `embed_text` is already formatted as `"word: definition"`, which is the right
  document format for the cross-encoder.
- Score all pairs in one batch (`model.predict(pairs)`). `ms-marco-MiniLM-L-6-v2`
  returns raw logits — higher = more relevant. Sort descending by cross-encoder score.
- Return the full reordered list (no truncation here — caller decides how many to keep).

**Done when:** `rerank([sr1, sr2, sr3], "test query")` returns the same three items
in a (potentially different) order without error. Lazy model load confirmed.

---

### 2. Implement `understanding/query.py` `query()` — single-concept path

**Layer:** Understanding

Implement the single-concept retrieval path in `query()`:

1. Call `index.engine.load()` — idempotent, safe to call on every request.
2. Call `embedding.embed([user_input])` → shape `(1, 384)` vector.
3. Call `index.engine.search(query_vec, k=50)` → 50 `SearchResult` objects, already
   deduplicated by word (one best-scoring sense per word).
4. Call `reranker.rerank(candidates, user_input)` → same 50 results reordered by
   cross-encoder relevance.
5. Slice `[:10]` for the final top 10.
6. Convert each `SearchResult` to a `RankedResult` (fill `word`, `pos`, `definition`,
   `score` from `record`; set `is_interpretation=False`).
7. Return `QueryResponse(mode="single", groups=[ConceptGroup(label=user_input, results=[...])])`.

**Dedup decision:** dedup by word already happens inside `search()` (Phase 3). The
reranker receives 50 unique-word candidates and reorders them. This is the decided
design: the cross-encoder's primary quality lever is ranking *different words* against
each other — it is very good at saying "petrichor fits better than pleasant." Sense
selection within a single word is a much smaller win. Moving dedup out of `search()`
would require the caller to request far more raw records (~5–10x) to guarantee 10
unique words in the final result (with ~11 senses/word average, 50 raw records yields
only ~5–7 unique words). That added complexity is not justified by the marginal gain.
If a model-choice or input-format problem is found after eval, those are investigated
first; dedup placement is not on the table.

**Done when:** `query("the smell of rain on dry earth")` returns a `QueryResponse`
with `petrichor` in the top 10 `RankedResult` items.

---

### 3. Update `eval/eval.py` to route through `understanding.query.query()`

**Layer:** Eval harness (orthogonal infrastructure)

This step is **required** — without it, `eval.py` never calls the reranker and Phase
4's quality improvement cannot be measured.

- Replace the current `embed() + search()` loop in `run_eval()` with per-case calls
  to `understanding.query.query(user_input)`.
- Extract word + score from the returned `QueryResponse.groups[0].results` list.
- Rank computation and recall/MRR metrics are unchanged.
- `index.engine.load()` is now called implicitly inside `query()` — remove the
  explicit `load()` call at the top of `run_eval()`.

**Speed note:** this loses batch embedding (180 individual embeds instead of one
batch). Acceptable for an offline eval harness. If eval becomes slow, a batch
optimization can be added later without changing the interface.

**Done when:** `python eval/eval.py` runs to completion and prints recall@10 + MRR
using the reranked results path.

---

### 4. Add unit tests in `tests/test_reranker.py`

**Layer:** Test suite (orthogonal)

Three tests:

1. **Order changes:** build two `SearchResult` objects with identical bi-encoder
   scores but craft the query so the cross-encoder should prefer one over the other.
   Assert that `rerank()` returns them in the new order. (Integration test — runs the
   real model.)
2. **No candidates dropped:** assert `len(rerank(candidates, q)) == len(candidates)`.
3. **Empty input:** assert `rerank([], "any query")` returns `[]` without error.

**Done when:** `pytest tests/test_reranker.py` passes (all 3 tests green).

---

### 5. Update `scripts/query.py` to call `understanding.query.query()`

**Layer:** Scripts (orthogonal)

Replace the direct `embed() + search()` calls in `scripts/query.py` with a call to
`understanding.query.query(user_input)` and render from the returned `QueryResponse`.
This makes the terminal script exercise the full production path including the
reranker, rather than a separate shortcut.

**Done when:** `python scripts/query.py "the smell of rain on dry earth"` prints
reranked results with petrichor in the top 3.

---

### 6. Eval gate — run before and after, save baseline

**Run before** (confirm Phase 3 state):
```
python eval/eval.py
```
Expected: recall@10 ≈ 0.5222, MRR ≈ 0.3845.

**Run after** (Phase 4 with reranker active):
```
python eval/eval.py
```
Target: recall@10 ≥ 0.6167, MRR ≥ 0.4461 (Phase 1/2 floor).

**If numbers improve — save baseline:**
```
python eval/eval.py --save-baseline --phase 4
```

**If numbers regress or fail to beat baseline:**
1. Check cross-encoder input format — try `(query, definition_only)` instead of
   `(query, "word: definition")`.
2. Check whether `ms-marco` logit direction is correct (higher = more relevant).
3. As fallback, try `cross-encoder/stsb-roberta-base` (symmetric similarity). This
   model is better suited to pairs that are semantically parallel rather than
   query-document asymmetric.
4. Last resort: don't revert Phase 3 — note the delta and record Phase 4 anyway,
   since the reranker architecture is correct even if this specific model is not
   optimal.

---

## Eval impact

**Yes — directly affects ranking order.** The reranker changes which of the 50
retrieved candidates appear in top 10 and in what order.

Baseline to beat:
- Phase 1/2: recall@10 = **0.6167**, MRR = **0.4461** (the real floor)
- Phase 3 (current, pre-reranker): recall@10 = **0.5222**, MRR = **0.3845**

`python eval/eval.py` must be run before (confirm Phase 3 state) and after (measure
Phase 4 improvement).

---

## Files to create or modify

| File | Action | Notes |
|---|---|---|
| `understanding/reranker.py` | Modify | Replace stub with cross-encoder implementation |
| `understanding/query.py` | Modify | Implement `query()` single-concept path |
| `eval/eval.py` | Modify | Route through `understanding.query.query()` |
| `scripts/query.py` | Modify | Route through `understanding.query.query()` |
| `tests/test_reranker.py` | Create | 3 unit tests for reranker |
| `docs/plan/retrieve_then_rerank.md` | Create | This file |
| `eval/baselines.json` | Modify | Append Phase 4 entry after eval passes |

No new files cross a layer boundary. `tests/test_reranker.py` is in the test folder,
orthogonal to the layer stack.

---

## Risks / open questions

1. **Cross-encoder model format.** `ms-marco-MiniLM-L-6-v2` returns logits (not
   0–1). Higher is more relevant — sort descending. If the model is somehow inverted,
   results will be catastrophically worse; easy to detect on first eval run.

2. **Input pair format.** Plan uses `(query_text, record.embed_text)` where
   `embed_text = "word: definition"`. If this hurts quality (the word itself biases
   the cross-encoder), try `(query_text, record.definition)` only. Document the
   result either way.

3. **Eval speed.** Switching from batch embed to per-query `query()` calls will slow
   eval (~2–4x). Not a blocker — eval is offline. If it becomes painful, add a
   `--fast` flag that skips the reranker.

4. **`ms-marco` vs. `stsb-roberta`.** `ms-marco` is trained for asymmetric
   query-passage relevance, which maps well to "does this definition describe what
   the user wants?" `stsb-roberta-base` is symmetric. Try `ms-marco` first; if MRR
   doesn't improve, `stsb-roberta-base` is the documented fallback.

---

## Estimated scope

**Medium (half day).** Two core implementations (reranker.py, query.py), one harness
update (eval.py), one script update (query.py), three tests. No new dependencies. No
infrastructure changes.
