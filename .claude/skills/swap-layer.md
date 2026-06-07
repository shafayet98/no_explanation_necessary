# Skill: Safely Swap a Layer Implementation

Use when replacing the internals of a layer — e.g. numpy → FAISS, MiniLM → a larger embedding model, cross-encoder → LLM reranker.

The goal: change the implementation without touching any code above the layer. If you need to change code in two layers, the abstraction is wrong — fix it first.

## Pre-Swap Checklist

1. **Record the baseline.** Run `python eval.py` and write down the current recall@10 and MRR. This is your revert target if things go wrong.
2. **Confirm the interface contract.** Read `.claude/rules/layer-contracts.md` for the layer you're swapping. Write down the exact function signatures that must stay identical.
3. **Check what calls this layer.** Grep for the layer's module name across the codebase. Every call site is a contract you must not break.
4. **Identify what changes.** List the internals that change (data structures, libraries, file formats) vs. the surface that must stay the same (function signatures, return types).

## Swap Process

**1. Create a new implementation file alongside the old one.**
   - `index/engine_faiss.py` alongside `index/engine.py`
   - Do not modify the working implementation yet.

**2. Implement the new version to the same interface.**
   - Same function signatures. Same return types. Same field names on dataclasses.
   - Add a `# SWAP: replacing numpy brute force` comment at the top for easy identification.

**3. Write a side-by-side test.**
   Run both implementations on the same query and compare:
   ```python
   old_results = old_engine.search(vec, k=50)
   new_results = new_engine.search(vec, k=50)
   # Top results should be similar (not identical for approximate methods like FAISS)
   ```

**4. Swap the import in the layer's `__init__.py`.**
   One line change. Nothing else.

**5. Run the full eval harness.**
   ```
   python eval.py
   ```
   Compare recall@10 and MRR against the baseline from step 1.
   - Both hold or improve → proceed.
   - Either regresses → investigate before shipping. Do not revert blindly — understand why first.

**6. Run the canary test.**
   `/canary` — confirm behaviour is unchanged relative to the current phase expectation.

**7. Delete the old implementation file** once confident in the new one.

## Embedding Model Swap Specifics

Swapping the embedding model requires re-indexing — the cached vectors are model-specific.

1. Change `MODEL_ID` and `EMBEDDING_DIM` in `embedding/embedder.py`.
2. Change the `embed()` implementation.
3. Run `/reindex` — this re-embeds everything with the new model.
4. The index will refuse to load if `meta.json`'s MODEL_ID doesn't match the current embedder. This is intentional.
5. Run `python eval.py` against the new index. The baseline comparison is against the old model's numbers.

## Index Backend Swap (numpy → FAISS) Specifics

FAISS uses approximate nearest neighbour — recall may slightly decrease vs. exact brute force.

- Use `faiss.IndexFlatIP` for exact search first (same results as numpy, just faster at scale).
- Only switch to an approximate index (`IndexIVFFlat`, `IndexHNSW`) if latency demands it, and verify eval recall hasn't dropped more than 1–2% absolute.
- Store the FAISS index to `index/cache/index.faiss` alongside `records.pkl` and `meta.json`.

## Revert Procedure

1. Change the import in `__init__.py` back to the old implementation.
2. If it was an embedding model swap: run `/reindex` with the old model restored.
3. Run `python eval.py` and confirm numbers match the pre-swap baseline.
