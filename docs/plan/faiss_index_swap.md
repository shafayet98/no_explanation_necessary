# Plan: FAISS Index Swap

## Goal
Replace the numpy brute-force search in `index/engine.py` with `faiss.IndexFlatIP`
behind the same `build/load/search` interface, so zero code above the index layer
changes, eval recall holds, and query latency improves.

---

## Which layers are touched

**Index layer only** (`index/engine.py`).

Supporting edits that are not layer logic:
- `requirements.txt` — adds faiss-cpu (dependency, not a layer)
- `scripts/build_index.py` — updates the cache-hit filename check (script, not a layer)
- `tests/test_phase1.py` — updates index unit tests to match the new internals

No seam violations: every change is either inside the index layer or in the tooling
around it.

---

## Current phase check

Phase 6 is complete and merged. Phase 7 is next in the prescribed order. ✓

---

## Steps

### 1. Install faiss-cpu
Uncomment `faiss-cpu~=1.9` in `requirements.txt`. Run `pip install faiss-cpu` and
confirm `import faiss` works in the venv.

Done when: `python -c "import faiss; print(faiss.__version__)"` exits 0.

**Risk note:** On Apple Silicon, `faiss-cpu` may require the `--pre` flag or a
version pin. Verify the install works before writing any code — if `faiss-cpu` can't
be installed, the rest of the plan is blocked. See Risks section.

---

### 2. Record the pre-change eval baseline
Run `python eval/eval.py` and note the current numbers.
Expected: recall@10 = **0.5907**, MRR = **0.4236** (Phase 6).

Done when: eval.py output matches the Phase 6 row in `eval/baselines.json`.

---

### 3. Rewrite `index/engine.py` internals

Replace the numpy state and I/O with FAISS. Signatures of `build()`, `load()`,
`search()`, and `SearchResult` are **unchanged**.

Changes:

- **Add** `_FAISS_PATH = _CACHE_DIR / "index.faiss"` path constant.
- **Replace** module-level `_vectors: np.ndarray | None` with
  `_index: faiss.Index | None`. `_records` is unchanged.
- **`build()`**: create `faiss.IndexFlatIP(EMBEDDING_DIM)`, call
  `index.add(vectors.astype(np.float32))`, then `faiss.write_index(index, str(_FAISS_PATH))`.
  `records.pkl` and `meta.json` writes are unchanged.
- **`load()`**: load via `faiss.read_index(str(_FAISS_PATH))` instead of
  `np.load(_VECTORS_PATH)`. Validation logic (MODEL_ID + EMBEDDING_DIM check from
  meta.json) is unchanged. Guard check switches to `if not _FAISS_PATH.exists()`.
- **`search()`**: replace `_vectors @ query_vector` with
  `_index.search(query_vector.reshape(1, -1).astype(np.float32), raw_k)` which
  returns `(distances_2d, indices_2d)`. Extract `distances_2d[0]` and `indices_2d[0]`,
  skip any index == -1 (FAISS sentinel for not-found). Dedup-by-word loop is
  unchanged. Guard check switches to `if _index is None`.

`IndexFlatIP` is **exact** inner-product search. Because vectors are L2-normalised,
IP == cosine sim, so scores are numerically identical to the numpy dot product.

Done when: `pytest tests/test_phase1.py` passes (after Step 4 updates the tests).

---

### 4. Update `scripts/build_index.py`

The cache-hit check currently looks for `_VECTORS_PATH = _CACHE_DIR / "vectors.npy"`.
Change it to look for `_FAISS_PATH = _CACHE_DIR / "index.faiss"`.

Done when: `python scripts/build_index.py --force` rebuilds cleanly and a second
run prints "Cache hit".

---

### 5. Update `tests/test_phase1.py`

The four index tests currently reference `vectors.npy` and the `_vectors` module
attribute directly. They need to work with the FAISS internals.

- **`_make_synthetic_index`** helper: currently writes `vectors.npy` by hand.
  Rewrite to call `eng.build(vecs, records)` via monkeypatching, so it exercises
  the real `build()` path rather than bypassing it.
- **`test_index_build_and_load`**: assert `(cache_dir / "index.faiss").exists()`
  instead of `vectors.npy`; monkeypatch `_FAISS_PATH` instead of `_VECTORS_PATH`;
  check `eng._index is not None` instead of `eng._vectors`.
- **`test_index_search_returns_sorted`**: update monkeypatch to `_FAISS_PATH`
  and `_index`; use updated `_make_synthetic_index`.
- **`test_index_model_mismatch_raises`**: currently writes a wrong `vectors.npy`.
  Replace with a call to `eng.build()` (after patching a wrong MODEL_ID into meta)
  so the test creates a valid `index.faiss`, then a fresh `load()` call detects the
  mismatch from `meta.json`.

Done when: `pytest tests/` → all 80 tests pass (same count as Phase 6).

---

### 6. Rebuild the index with FAISS
Run `python scripts/build_index.py --force` to clear the old numpy cache and write
`index/cache/index.faiss`.

Done when: `index/cache/index.faiss` exists, `index/cache/vectors.npy` is gone.

---

### 7. Run eval and verify recall holds
Run `python eval/eval.py`.

Done when: recall@10 and MRR are within floating-point noise of the Phase 6 numbers
(0.5907 / 0.4236). Because `IndexFlatIP` is exact search, any deviation means a bug
in the implementation, not an approximation trade-off.

---

### 8. Latency spot-check
Time 5 queries with `scripts/query.py` before and after (using `time`).

Done when: FAISS p50 latency is ≤ the numpy p50 (even a tie is fine at this corpus
size; the architectural change is the point).

---

### 9. Record Phase 7 baseline
Run `python eval/eval.py --save-baseline --phase 7`.

Done when: `eval/baselines.json` has a Phase 7 entry with matching numbers.

---

## Eval impact

This is a quality-affecting change (the index is the retrieve step). Eval gate is
**active**.

- Run before (Step 2): Phase 6 baseline — recall@10 = 0.5907, MRR = 0.4236.
- Run after (Step 7): must match or exceed.
- Since `IndexFlatIP` is exact search, numbers should be bit-for-bit identical.
  Any regression is a bug.

---

## Files to create or modify

| File | Change |
|------|--------|
| `requirements.txt` | Uncomment `faiss-cpu~=1.9` |
| `index/engine.py` | Rewrite `build/load/search` internals; `_vectors` → `_index`; add `_FAISS_PATH` |
| `scripts/build_index.py` | `_VECTORS_PATH` → `_FAISS_PATH` in cache-hit check |
| `tests/test_phase1.py` | Update 4 index tests + `_make_synthetic_index` helper |
| `docs/plan/faiss_index_swap.md` | This plan file (new) |

No new files cross a layer boundary.

---

## Risks / open questions

**1. faiss-cpu on Apple Silicon (macOS ARM)**
`faiss-cpu` on arm64 macOS may not install via a plain `pip install faiss-cpu`. The
workaround is usually `pip install faiss-cpu --pre` or using a conda environment.
**This must be verified before writing any code.** If faiss-cpu cannot be installed,
Phase 7 is blocked until a working install path is found.

**2. numpy 2.x compatibility**
The project pins `numpy~=2.1`. Older `faiss-cpu` builds link against numpy 1.x C ABI
and may crash on numpy 2.x with an ABI mismatch. If this happens, either pin
`faiss-cpu` to a newer build that supports numpy 2 or downgrade numpy to 1.26.

**3. Old cache file**
`index/cache/vectors.npy` exists from previous phases. Step 6's `--force` flag
clears it. If the user tries to run queries without rebuilding (after engine.py
changes but before `--force`), `load()` will raise `FileNotFoundError` because
`index.faiss` won't exist yet. This is the correct behaviour — not a bug.

**4. Exact vs approximate**
`IndexFlatIP` is exact (same results as numpy). If the corpus grows beyond ~500k
vectors and latency becomes a problem, upgrade to `IndexIVFFlat` (approximate,
requires training + nprobe tuning). That is a future decision; do not implement it
now.

---

## Estimated scope

**Small** (< 2 hours). The work is entirely inside one layer; the interface contract
is frozen; no new design decisions are needed beyond confirming faiss-cpu installs.
