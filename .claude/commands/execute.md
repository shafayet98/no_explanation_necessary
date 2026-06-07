---
description: Execute an approved plan from docs/plan, following build discipline.
argument-hint: [plan name or phase, optional]
---

You are about to execute (implement) an approved plan for the Reverse Dictionary project. This is the counterpart to `/plan`: `/plan` writes the plan, `/execute` builds it.

The plan to execute: $ARGUMENTS

## Before writing any code

1. Locate the plan.
   - Plans live in `docs/plan/`. If `$ARGUMENTS` names a plan or phase, use the matching file (e.g. `docs/plan/phase-0-skeleton.md`).
   - If `$ARGUMENTS` is empty, list the plans in `docs/plan/` and use the most recent / current-phase one. If it is ambiguous, ask which plan to execute before starting.
   - If no plan file exists for the request, stop and tell the user to run `/plan` first. Do not implement from scratch without a plan.
2. Read the plan fully, plus `CLAUDE.md`, `docs/architecture.md`, and `.claude/rules/`.
3. Confirm the plan is still in phase order (`/phase-status` logic). If the plan is out of phase, stop and flag it.
4. Confirm the current git branch is an appropriate feature branch — not `main`. If on `main`, create a properly named branch first.

## While executing

Follow the build discipline rules in `.claude/rules/` exactly:

- **One layer at a time.** Implement the steps in plan order. Each step belongs to exactly one layer. If a step forces edits across layer boundaries, stop — the seam is wrong; surface it before continuing.
- **Respect the layer contracts** in `.claude/rules/layer-contracts.md`. Do not change a public signature without updating the implementation and all callers.
- **Eval gate** (`.claude/rules/eval-gate.md`): from Phase 2 onward, if the change could affect result quality, run `python eval.py` BEFORE and AFTER and record both numbers. If recall@10 or MRR drops, revert.
- **Never silently re-embed.** Indexing scripts must check for a valid cached index first.
- **Keep the frontend dumb.** No business logic in React.
- Use a TODO list to track the plan's steps and mark them off as each step's "done when" condition is met.

## After executing

1. Verify each step's "done when" condition from the plan is met. State which are met and which are not.
2. If this was a quality change, report the eval delta (before → after).
3. Summarise what changed, file by file, and what the next phase / next action is.
4. Do NOT commit or push unless the user asks.
