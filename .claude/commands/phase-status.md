---
description: Report the current build phase and what remains to complete it.
---

Report the current build phase and what remains to complete it.

Steps:
1. Inspect the codebase to determine which phases are complete. For each phase, check its "Done when" condition:

   Phase 0 — done when: all five layer folders exist with stub files containing the correct function signatures.
   Phase 1 — done when: a query script exists and "the smell of rain on dry earth" returns petrichor in the top 10 (run it live if possible).
   Phase 2 — done when: `eval/eval.py` exists, `eval/test_cases.jsonl` has at least 150 cases, and running `python eval.py` prints recall@10 and MRR.
   Phase 3 — done when: `data/loader.py` emits one record per sense (check WordRecord.sense > 0 in the output), and eval numbers exceed the Phase 1 baseline.
   Phase 4 — done when: `understanding/reranker.py` exists with a real implementation, and eval MRR exceeds the Phase 3 baseline.
   Phase 5 — done when: `understanding/classifier.py` classifies input type and multi-concept queries return grouped results.
   Phase 6 — done when: QueryFilters are wired end-to-end and eval with filter-constrained cases passes.
   Phase 7 — done when: `index/engine.py` uses FAISS and eval recall is unchanged vs Phase 6.
   Phase 8 — done when: `interface/api.py` is running and `interface/frontend/` has a working React app.

2. Report:
   - Current phase (the highest phase whose "Done when" condition is fully met).
   - Status of the current in-progress phase: which conditions are met, which are not.
   - The specific next action needed to advance to the next phase.

3. Show the latest eval metrics from `eval/baselines.json` if it exists.

Keep the report concise. One sentence per phase condition. Flag any "Done when" condition that is partially met.
