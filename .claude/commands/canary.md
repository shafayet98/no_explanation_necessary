---
description: Run the permanent canary test case and interpret it against the current phase.
---

Run the permanent canary test case through the current system and interpret the result relative to the current phase.

The canary input is:
"The rain finds me before I'm ready for it, soaking through my collar as I stand frozen on the pavement, watching the gutters swell into little rivers. And somehow I don't move—I just let it come, breathing in that strange grey peace, like the sky finally said the thing I'd been too afraid to."

Steps:
1. Determine the current phase by checking which phase files/features exist (e.g. does `understanding/classifier.py` exist and have a real implementation?).
2. Run the query through the system using whatever entry point is available (terminal query script, API, or direct Python call).
3. Show the raw output.
4. Interpret the result against phase expectations:
   - Phase 0–4: A single averaged-vector result is expected and correct. Note which words appeared. This is not a bug.
   - Phase 5+: Should return grouped concepts. Check for at minimum: a rain/smell concept (expect petrichor or similar), a calm/acceptance concept (expect resignation, equanimity, or similar), a release concept (expect catharsis or similar). Check that results are labelled as interpretations, not definitive answers.
5. If Phase 5+ and the result is still a single averaged guess, flag it as a regression in the understanding layer.
6. Summarise: "Current phase: X. Expected behaviour: Y. Observed: Z. Status: PASS / NEEDS ATTENTION."
