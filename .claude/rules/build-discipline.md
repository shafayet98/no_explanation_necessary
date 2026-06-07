# Build Discipline Rules

These rules govern every code change in this project. Follow them over any instinct to move fast or add features.

## The Five Rules

**1. Every layer behind a narrow interface.**
Each layer exposes a small, defined set of functions. If implementing a change requires editing code in more than one layer, stop. The seam is in the wrong place. Fix the seam first, then make the change. See `docs/architecture.md` for the interface contracts.

**2. Never ship a quality change without running eval.**
From Phase 2 onward, run `python eval.py` before AND after every change that could affect result quality (embedding, indexing, ranking, routing). Record both numbers. If recall@10 or MRR decreases, revert the change. "Feels better" is not a metric.

**3. Build the slice before the features.**
Do not build Phase 5 features while Phase 3 is incomplete. Do not add filters (Phase 6) before the understanding layer (Phase 5) works. Always complete the current phase's "Done when" condition before starting the next.

**4. Embeddings are cached — never silently re-embed.**
`scripts/build_index.py` must check for a valid cached index before embedding. If a cached index exists and the model ID matches, load it. Embedding the full dictionary on every run is a bug, not a feature.

**5. Keep the frontend dumb.**
No filtering logic, scoring, ranking, or routing in React. If you find yourself writing business logic in the frontend, move it to the understanding layer and expose it via the API instead.

## What This Means in Practice

- Before writing any code: identify which single layer the change belongs to.
- Before finishing any quality change: run eval and record the delta.
- Before starting a new phase: verify the current phase's "Done when" condition is met.
- Before any indexing script: confirm it checks for cached vectors first.
- Before adding any frontend logic: ask whether it belongs in the understanding layer instead.
