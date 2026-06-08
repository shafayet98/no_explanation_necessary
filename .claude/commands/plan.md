---
description: Produce an implementation plan for a task (plan only, no code).
argument-hint: [task to plan]
---

You are about to plan a task for the Reverse Dictionary project. Do NOT write any code or make any file changes — produce a plan only and wait for approval.

The task to plan: $ARGUMENTS

Produce a structured plan in this format:

---

## Goal
One sentence: what will be true when this task is done.

## Which layers are touched
List only the layers from `docs/architecture.md` that this task requires changes in. If a change touches more than one layer, flag it and explain why — it may mean the seam is in the wrong place.

## Current phase check
State the current build phase (run `/phase-status` logic mentally or read the codebase). Flag if this task is out of phase order — e.g. don't plan Phase 5 work while Phase 3 is incomplete.

## Steps
Numbered list. Each step must:
- Belong to exactly one layer
- Be independently testable
- State what "done" looks like for that step

## Eval impact
Will this change affect recall@10 or MRR? If yes: specify that `python eval.py` must be run before and after, and note the baseline to compare against. If no: explain why not.

## Files to create or modify
List each file with one line describing what changes. Flag any new files that cross a layer boundary (a red flag).

## Risks / open questions
Anything that needs a decision before implementation starts, or that could cause a regression. If the plan requires a confirmed design choice (e.g. an AWS service, a framework), flag it here — do not assume.

## Estimated scope
Small (< 1 hour) / Medium (half day) / Large (multiple sessions). If Large, suggest breaking into sub-tasks.

---
After making the plan always write the plan to `docs/plan`.   

When recording the plan in `docs/plan/`, name the file for what it does using a
descriptive slug (e.g. `thin_vertical_slice.md`) — never include a phase number in
the filename (no `phase_1_*.md`). See `.claude/rules/build-discipline.md` → Naming Discipline.

After producing the plan, ask: "Does this plan look right? Any changes before I start?"
Do not proceed with implementation until the user explicitly approves.
