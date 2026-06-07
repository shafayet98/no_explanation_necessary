# Progress Log

> Read this at the start of every session before making changes. It is the
> running record of what has been built, the current state, and what's next.
> Newest entries at the top. Keep it updated as work lands.

## Current state (at a glance)

- **Phase:** Phase 1 complete. PR #2 open, not yet merged. Next up is **Phase 2**
  (evaluation harness — 150–300 test pairs, recall@10 + MRR, baseline recorded).
- **Branch model:** work off `main`, branch per change, PR into `main`.
- **Runnable today:**
  - `pytest tests/` → 13/13 pass.
  - `python scripts/build_index.py` → cache hit (index already built, 3,787 vectors).
  - `python scripts/query.py "the smell of rain on dry earth"` → **petrichor rank 1**.
- **Environment:** `venv/` with full deps (numpy, torch, sentence-transformers,
  fastapi, nltk, wordfreq, pytest). Activate with `source venv/bin/activate`.
- **Next action:** Plan and build Phase 2 — hand-write 150–300 `(description →
  expected word)` test pairs, implement `recall@10` + `MRR` in `eval/eval.py`,
  one-command run, record Phase 1 baseline. **Eval gate activates from Phase 2 — do not skip.**

---

## PR #2 — Thin vertical slice (open, branch `phase-1/thin-vertical-slice`)

PR: https://github.com/shafayet98/no_explanation_necessary/pull/2
Plan: `docs/plan/thin_vertical_slice.md`

### What was built
Implemented the full query path from corpus → vectors → search → terminal output.

- **scripts/fetch_corpus.py** — one-time corpus builder: `wordfreq` top-5000
  common words **∪** curated eval targets (petrichor, saudade, etc.), definitions
  from the Free Dictionary API (Wiktionary-backed), concurrent fetch (20 workers),
  resumable. Writes `data/raw/corpus.jsonl` (gitignored). **3,787 words** after
  API filtering.
- **data/loader.py** — `load_records()` implemented: reads `corpus.jsonl` offline,
  emits one `WordRecord` per word (Phase 1: `sense=0`, primary POS + definition,
  `embed_text = "word: definition"`).
- **embedding/embedder.py** — `embed()` implemented: lazy singleton loading
  `all-MiniLM-L6-v2` via `sentence-transformers`; returns L2-normalised
  `(N, 384) float32` ndarray.
- **index/engine.py** — `build()/load()/search()` implemented: writes/reads
  `index/cache/{vectors.npy, records.pkl, meta.json}`; `load()` validates
  `MODEL_ID` match (mismatch → `RuntimeError`, never silent re-embed); `search()`
  uses dot product (= cosine sim because vectors are normalised), `argpartition`
  for efficiency.
- **scripts/build_index.py** — cache-before-embed invariant enforced: if cache
  valid and model matches, prints "cache hit" and exits. Otherwise: load → embed →
  build.
- **scripts/query.py** — thin terminal interface: loads index, embeds query,
  `search(k=10)`, prints ranked results with score + definition. No business logic.
- **tests/test_phase1.py** — 8 new unit tests (3 embed shape/norm/single,
  3 index build/load/search/mismatch, 2 data-layer corpus tests). 13/13 total pass.

### Tooling / process changes
- **Plan naming discipline** — plan files in `docs/plan/` must use descriptive
  slugs (e.g. `thin_vertical_slice.md`), never phase numbers (`phase_1_*.md`).
  Codified in `.claude/rules/build-discipline.md` and the `/plan` command
  (`.claude/commands/plan.md`).
- **wordfreq~=3.1** added to `requirements.txt` (frequency-ranked word list for
  corpus selection).
- **`data/raw/`** added to `.gitignore` — corpus cache is generated, not source.
- Plan recorded in `docs/plan/thin_vertical_slice.md`.

### Key decision recorded
WordNet has 0 synsets for *petrichor*. Switched dictionary source to the **Free
Dictionary API** (Wiktionary-backed, verified to contain petrichor). Full kaikki
Wiktionary dump (~3 GB) rejected as too heavy for a thin slice. Curated eval-target
words are placed first in the word list so they are never dropped by a frequency cutoff.

### Verification (all conditions met)
- `pytest tests/` → **13/13 passed** (5 skeleton + 8 phase-1).
- `python scripts/build_index.py` (second run) → "Cache hit" — cache-before-embed
  invariant confirmed.
- `python scripts/query.py "the smell of rain on dry earth"` → **petrichor rank 1,
  score 0.5454**. Phase 1 "done when" condition met.
- Eval gate: **not active** — harness doesn't exist until Phase 2.

### Confirmed decisions (do not re-litigate without reason)
- **Dictionary source:** Free Dictionary API (Wiktionary-backed), not WordNet.
- **Corpus size:** ~3,787 words (after API filtering of 5,029 candidates).
- **Model:** `all-MiniLM-L6-v2` (384-dim, L2-normalised).
- **Index:** numpy brute-force cosine (dot product on normalised vecs). Swaps to
  FAISS at Phase 7 with zero contract changes above the index layer.
- **Word selection:** `wordfreq` top-5000 ∪ curated eval targets; curated words
  fetched first.

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
