# Plan: Understanding Layer — Input Classification and LLM Decomposition

## Goal

When this task is done, the understanding layer classifies every query as single-concept
or multi-concept, routes multi-concept passages through an LLM that extracts 2–3 clean
sub-queries, runs each through the existing retrieve+rerank pipeline, and returns a
`QueryResponse(mode="grouped")` with all results marked `is_interpretation=True`; the
canary passage returns 3–4 labelled concept groups; existing 180 single-concept eval
cases are unaffected.

---

## Which Layers Are Touched

**Understanding layer only** — `understanding/classifier.py`, `understanding/query.py`,
and a new `understanding/decomposer.py`.

The eval harness (`eval/eval.py`, `eval/test_cases.jsonl`) is orthogonal to the five
architecture layers and changes alongside every phase. That is expected, not a seam
violation.

No changes to data, embedding, index, or interface layers. If any step requires touching
index or embedding, stop — the seam is wrong.

---

## Current Phase Check

Phase 4 is complete and merged to `main` (PR #6, commit `17d5bb3`). Eval baseline:
recall@10 = 0.5611, MRR = 0.4039. Phase 5 is the correct next step.

---

## Steps

### Step 1 — Implement `classify()` in `understanding/classifier.py`

Heuristics-based; no LLM call. Returns `"single"` or `"multi"`.

Signal set (all must be measured cheaply on the raw text):

| Signal | Threshold |
|---|---|
| character count | > 150 chars → candidate |
| sentence count | ≥ 2 sentences (split on `.!?`) → candidate |
| independent clause markers | ≥ 2 coordinating conjunctions or semicolons → candidate |
| multi-signal agreement | classify as "multi" only if ≥ 2 signals fire |

The threshold is intentionally conservative. Every existing eval case is a short
single-clause description (median ~60 chars). The canary passage is 265 chars, 2
sentences, and heavily conjunction-loaded — it must classify as "multi".

**Done when:**
- `classify("the smell of rain on dry earth") == "single"`
- `classify(CANARY_TEXT) == "multi"`
- Unit test: a 30-case fixture covering short easy cases (all "single") and 5 long
  passage samples (all "multi") passes.

---

### Step 2 — Create `understanding/decomposer.py`

New file. Single public function:

```python
def decompose(text: str) -> list[tuple[str, str]]:
    # Returns [(label, clean_query), ...], 2–4 items.
    # label   — short human-readable phrase, e.g. "the rain smell"
    # clean_query — concise rephrasing suitable for vector search
```

LLM call using the Anthropic Python SDK (model: `claude-haiku-4-5-20251001`). The
prompt instructs the model to:
1. Read the passage.
2. Identify 2–4 distinct emotional/sensory/conceptual moments.
3. For each: write a short label and a clean 5–10 word search query.
4. Return JSON: `[{"label": "...", "query": "..."}, ...]`.

Structured output via `tool_use` or a strict JSON prompt — exact approach confirmed
below in Risks.

Lazy-loads the Anthropic client (same pattern as the reranker's lazy model load).
Raises a clear `RuntimeError` if `ANTHROPIC_API_KEY` is not set rather than silently
returning empty.

**Done when:**
- `decompose(CANARY_TEXT)` returns a list with 3–4 items.
- Each item is a `(str, str)` tuple with non-empty label and query.
- Unit test using `unittest.mock.patch` on the Anthropic client call passes without
  a live API key.

---

### Step 3 — Wire classifier + decomposer into `understanding/query.py`

Update `query()` to:

```
classify(user_input)
│
├─ "single" → [existing Phase 4 path unchanged]
│             QueryResponse(mode="single", groups=[ConceptGroup(label=user_input, ...)])
│
└─ "multi"  → decompose(user_input)
              → for each (label, clean_query):
                    embed([clean_query])
                    → search(k=50)
                    → rerank(candidates, clean_query)
                    → top 10 as RankedResult(is_interpretation=True)
                    → ConceptGroup(label=label, results=[...])
              → QueryResponse(mode="grouped", groups=[...])
```

The per-concept queries run sequentially (not parallel) in Phase 5. Parallelism is an
optimisation for Phase 8+.

`is_interpretation=True` is set on **all** results from the multi-concept path. This
is the honest-framing invariant from the architecture doc.

**Done when:**
- `query("the smell of rain on dry earth").mode == "single"` (regression check).
- `query(CANARY_TEXT).mode == "grouped"`.
- `len(query(CANARY_TEXT).groups) >= 2`.
- All results in the grouped response have `is_interpretation=True`.
- `scripts/query.py` still returns petrichor rank 1 for the petrichor query.

---

### Step 4 — Add long-passage test cases to `eval/test_cases.jsonl`

Add 12–15 new test cases:

- 4–5 **multi-concept, identifiable target**: passages where one concept has a clear
  dictionary word (e.g. a passage describing petrichor alongside something else; the
  expected word is petrichor). These test that the grouped path still finds the word
  in one of its groups.
- 4–5 **single evocative hard**: short poetic descriptions of a real word (tests that
  the classifier does NOT over-fire on short poetic queries).
- 3–4 **long single-concept**: verbose rephrasing of a known word (tests that
  classifier doesn't fire on long-but-single-concept text).

Format addition: add `"multi": true` field to multi-concept cases. This is purely
informational metadata — it does not change how the eval computes metrics.

**Done when:**
- `eval/test_cases.jsonl` has ≥ 192 cases total.
- New cases have been spot-checked: the expected word is confirmed present in the
  corpus (`python scripts/query.py "<description>"` returns it in top 20).

---

### Step 5 — Update `eval/eval.py` to handle grouped responses

Current `run_eval()` checks only `response.groups[0].results[:k]`. This is correct for
"single" responses. For "grouped" responses, the expected word may be in any group.

Change: for each test case, flatten all groups' results and check if the expected word
appears in the top 10 of **any single group** (not the flattened union — a word found
at rank 8 in group 2 is still rank 8, not rank 18).

```python
# Pseudocode for updated hit detection
rank = None
for group in response.groups:
    for j, rr in enumerate(group.results[:k], 1):
        if rr.word.lower() == expected:
            rank = j
            break
    if rank is not None:
        break
```

This is backwards-compatible: for `mode="single"` with one group, behaviour is
identical to Phase 4.

Also add a `multi` column to the per-case report table to flag which cases were
routed through the grouped path.

**Done when:**
- Existing 180 single-concept cases produce identical results to Phase 4 (numbers match
  exactly before any new cases are included).
- New multi-concept cases are correctly evaluated.

---

### Step 6 — Unit tests in `tests/test_understanding.py`

New file covering:

1. `classify` — short queries return "single"; the canary passage returns "multi";
   edge cases (empty string, 1-char input) return "single" safely.
2. `decompose` — with mocked Anthropic client, correct JSON response is parsed into
   `[(label, query), ...]`; malformed LLM response raises clearly; missing API key
   raises `RuntimeError`.
3. `query` routing — with mocked `classify` returning "single", the existing Phase 4
   path is exercised; with mocked `classify` returning "multi" and mocked `decompose`,
   the grouped path returns `mode="grouped"` with `is_interpretation=True` on all
   results.

**Done when:** `pytest tests/test_understanding.py` passes without a live API key or
loaded index (all external calls mocked).

---

## Eval Impact

**Yes — this changes the quality path.**

- Run `python eval/eval.py` **before** (Phase 4 baseline: 0.5611 / 0.4039).
- After Step 3 (routing wired), run again. Existing single-concept cases must not
  regress — the classifier must return "single" for all 180 existing cases. If any
  regress, the classifier threshold is too aggressive — tighten it before proceeding.
- After Step 4 (new cases added), record the new baseline with
  `python eval/eval.py --save-baseline --phase 5`.
- Gate: Phase 5 baseline must show recall@10 ≥ 0.5611 and MRR ≥ 0.4039 on the full
  (expanded) test set. The new multi-concept cases will likely drag the overall number
  slightly; the gate is that single-concept sub-group numbers don't move.

---

## Files to Create or Modify

| File | Change |
|---|---|
| `understanding/classifier.py` | Implement `classify(text) -> "single" \| "multi"` (replaces stub) |
| `understanding/decomposer.py` | **New.** `decompose(text) -> list[tuple[str, str]]` — LLM concept extractor |
| `understanding/query.py` | Wire `classify` + `decompose` into `query()`; handle "single" and "multi" routing |
| `eval/test_cases.jsonl` | Add 12–15 new cases (multi-concept + long evocative) |
| `eval/eval.py` | Update `run_eval()` hit detection to check across all groups |
| `tests/test_understanding.py` | **New.** Unit tests for classifier, decomposer, and routing |
| `requirements.txt` | Add `anthropic` if not already present |

All changes are inside the understanding layer or the orthogonal eval/tests directories.
No cross-layer seam violations.

---

## Risks / Open Questions

### 1. LLM choice — MUST confirm before implementing

**Recommendation: `claude-haiku-4-5-20251001` via the Anthropic Python SDK.**

Reasons: cheapest + fastest Claude model; JSON instruction following is reliable;
consistent with the project's cloud target (AWS + Anthropic); no new provider
dependency beyond what's already implied by Claude Code usage.

**Alternatives if rejected:**
- `gpt-4o-mini` (requires OpenAI key — adds a second provider)
- Local `flan-t5-base` via HuggingFace (free but weaker instruction following; JSON
  output fragile)

Decision needed from user before Step 2.

### 2. Graceful degradation when `ANTHROPIC_API_KEY` is absent

If the key is missing, `decompose()` raises `RuntimeError`. Then `query()` catches it
and falls back to `mode="single"` with a logged warning. This means the system still
works without a key — it just can't route multi-concept queries. The fallback must be
explicit, not silent.

### 3. Classifier precision — regression risk on existing eval cases

Every one of the 180 existing test cases must classify as "single". The thresholds in
Step 1 are conservative but need empirical verification. Run the classifier over all
180 cases as part of Step 1 verification before wiring routing in Step 3.

### 4. Multi-concept eval format

New test cases with `"multi": true` have one `expected_word`. For the eval to be
meaningful, that expected word must be retrievable in one of the groups. This means
the LLM decomposer must produce a sub-query that targets that concept. If the
decomposer consistently misses a concept, that's a prompt-tuning problem, not a
structural one.

### 5. LLM structured output approach

Two options for getting JSON from the LLM:
- **Tool use / `tool_choice="any"`**: reliable, but adds SDK complexity.
- **System prompt with JSON instruction + `response.content[0].text` parse**: simpler,
  but needs a try/except for malformed output with a retry or fallback.

Recommendation: system-prompt JSON with one retry on parse failure. Keeps the
decomposer simple. Can upgrade to tool use if reliability is a problem in practice.

### 6. `requirements.txt` — `anthropic` package

Check whether `anthropic` is already in the venv. If not, add it. The package is
small and pure-Python.

---

## Estimated Scope

**Large — plan for 2 sessions.**

Suggested split:

**Session A (Steps 1–3 + 6):** Classifier + decomposer + routing + unit tests.
Deliverable: `query(CANARY_TEXT)` returns grouped results; `pytest` green; no eval
regression on existing 180 cases.

**Session B (Steps 4–5):** New eval test cases + eval harness update + baseline record.
Deliverable: full Phase 5 baseline in `baselines.json`; canary manually verified.
