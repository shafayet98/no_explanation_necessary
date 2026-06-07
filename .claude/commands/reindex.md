---
description: Rebuild the embedding index from scratch (re-embeds all records).
---

Rebuild the embedding index from scratch.

Steps:
1. Before doing anything, warn the user: "This will delete the existing cached index and re-embed all records. This takes several minutes. Confirm? (yes/no)"
2. Wait for confirmation. If not confirmed, stop.
3. Check that the embedding model is available (try importing sentence-transformers and loading the model).
4. Delete `index/cache/vectors.npy`, `index/cache/records.pkl`, and `index/cache/meta.json` if they exist.
5. Run `python scripts/build_index.py` and stream the output so the user can see progress.
6. After completion, verify the cache files were written:
   - `index/cache/vectors.npy` — report shape (N records × embedding dim)
   - `index/cache/records.pkl` — report number of records
   - `index/cache/meta.json` — report MODEL_ID stored
7. Run a quick smoke test: query for "the smell of rain on dry earth" and confirm petrichor appears in the top 10. Report the result.
8. If Phase 2 is complete, offer to run `/eval` to check that the new index hasn't regressed on metrics.
