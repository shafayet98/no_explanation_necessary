---
description: Run the evaluation harness and compare results against the baseline.
---

Run the evaluation harness and compare results against the recorded baseline.

Steps:
1. Check that `eval/test_cases.jsonl` exists and report how many test cases it contains.
2. Check that `eval/baselines.json` exists and show the most recent baseline entry (phase, recall@10, MRR, date).
3. Run `python eval.py` from the project root and capture the output.
4. Parse the recall@10 and MRR from the output.
5. Compare against the most recent baseline:
   - Show the delta for each metric (+ is improvement, - is regression).
   - If either metric regressed, warn clearly: "REGRESSION: MRR dropped from X to Y — do not ship this change."
   - If both improved, confirm: "Both metrics improved. Safe to keep."
6. Ask if the user wants to record this as a new baseline entry in `eval/baselines.json`.

If `eval/eval.py` does not exist yet, report that the eval harness has not been built (Phase 2 is incomplete) and stop.
