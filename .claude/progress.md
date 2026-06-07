# Progress Log

> Read this at the start of every session before making changes. It is the
> running record of what has been built, the current state, and what's next.
> Newest entries at the top. Keep it updated as work lands.

## Current state (at a glance)

- **Phase:** Skeleton complete. Next up is **Phase 1** (thin vertical slice).
- **Branch model:** work off `main`, branch per change, PR into `main`.
- **Runnable today:** only `pytest tests/test_imports.py` (5/5 pass). Every layer
  function is a stub that raises `NotImplementedError` — there is no working
  query path yet.
- **Environment:** `venv/` exists with the full dependency install
  (numpy, torch, sentence-transformers, fastapi, nltk, pytest). Activate with
  `source venv/bin/activate`.

---

## PR #1 — Project skeleton (merged into `main`, commit `1dd95df`)

Branch: `setup/project-skeleton` → merged via merge commit `aefcc45`.

### What was built
Laid down the whole repo as importable seams with **no implementation** — every
layer module exists with signatures matching the contracts in
`docs/architecture.md`; all stubs raise `NotImplementedError`.

- **data/** — `WordRecord` dataclass + `load_records()`
- **embedding/** — `embed()`, `MODEL_ID="all-MiniLM-L6-v2"`, `EMBEDDING_DIM=384`
- **index/** — `SearchResult` + `build()/load()/search()`; `cache/` gitignored
- **understanding/** — `query()` + `QueryFilters`/`RankedResult`/`ConceptGroup`/
  `QueryResponse`; `classifier.py` and `reranker.py` stubs
- **interface/** — FastAPI `app` with `POST /query` + `GET /health` placeholders;
  empty `frontend/` (Phase 8)
- **eval/** — harness stub, empty `test_cases.jsonl`, `baselines.json` = `[]`
- **scripts/build_index.py** — indexing-path outline with the cache-before-embed
  invariant documented in comments
- **infra/** — Terraform tree (`modules/`, `envs/dev`, `envs/prod`). **AWS
  services deliberately NOT chosen** — to be proposed/confirmed before Phase 8.
- `requirements.txt`, `README.md`, `tests/test_imports.py`

### Tooling / process changes
- Fixed slash commands not showing in the `/` picker — root cause: the files in
  `.claude/commands/` had **no YAML frontmatter**. Added `description` (+
  `argument-hint`) to each.
- Added the **`/execute`** command (counterpart to `/plan`: builds an approved
  plan from `docs/plan/`).
- Recorded the skeleton plan in `docs/plan/project_skeleton_decision.md`.

### Confirmed decisions (do not re-litigate without reason)
- **Package layout:** flat top-level packages (no `src/`).
- **Dependency install:** full install up front (incl. sentence-transformers).
- **Web framework:** FastAPI for the interface layer.
- **AWS architecture:** undecided — must be confirmed before Phase 8.

### Verification
- `pytest tests/test_imports.py` → 5/5 passed.
- Stubs confirmed to raise `NotImplementedError`.
- No eval impact (everything is a stub; the eval gate is not active yet).

---

## Next action
Plan and build **Phase 1**: implement `load_records()` (~3-5k WordNet words, one
vector/word), the real `embed()`, the numpy `search()`, `build_index.py`, and a
terminal query entry point. **Done when** "the smell of rain on dry earth"
returns *petrichor* in the top 10.
