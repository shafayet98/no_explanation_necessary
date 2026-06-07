# Thin Vertical Slice

Status: **implemented** ✓
Phase: 1
Branch: `phase-1/thin-vertical-slice`
Date: 2026-06-07

---

## Goal
A user can run one terminal command, type a description, and get the 10 nearest
dictionary words back — and `"the smell of rain on dry earth"` returns
**petrichor** in the top 10.

## Which layers are touched
This is the first real implementation, so by design Phase 1 fills in the bottom
of the stack. Each change stays inside its own layer behind the existing
contract — no signatures change.

- **Data layer** — implement `load_records()`.
- **Embedding layer** — implement `embed()`.
- **Index layer** — implement `build()` / `load()` / `search()`.
- **Scripts** — implement `build_index.py` (orchestrates data → embed → build).
- **Interface (thin terminal entry only)** — a tiny CLI query runner. *Not* the
  FastAPI app (that is Phase 8). This is the "terminal print" interface the
  architecture table lists for Phase 1.

No edits to `understanding/`, `interface/api.py`, the frontend, or `infra/`.
All the dataclass seams (`WordRecord`, `SearchResult`) are already defined and
stay unchanged.

## Current phase check
- Skeleton (Phase 0) is complete and merged (`aefcc45`). Every layer function is
  a `NotImplementedError` stub.
- Eval harness does **not** exist yet (that is Phase 2). So the eval gate is
  **not active** during Phase 1 — there is no baseline to regress against.
- This task **is** the correct next phase. In order.

---

## Decisions confirmed for this phase

1. **Dictionary source → a larger source than WordNet.**
   `petrichor` is **not in WordNet** (verified: 0 synsets). It **is** in the
   Wiktionary-backed **Free Dictionary API** (verified). The full Wiktionary
   dump (kaikki, ~3 GB) is too heavy for a 3–5k thin slice, so we fetch only the
   words we need from the Free Dictionary API and cache them.

2. **Word selection → `wordfreq` top-N ∪ eval targets (recommended).**
   - Take the top ~5000 most frequent English words via the `wordfreq` package
     (new dependency, offline after install).
   - **Union** with a small curated list of evocative eval-target words
     (`petrichor`, `saudade`, `sonder`, `defenestration`, …) so that rare target
     words survive the frequency cut. Their *definitions still come from the real
     source* — this is selection logic, not a hand-written dictionary.
   - Net corpus: ~3–5k words after dropping any the API has no entry for.

3. **One-time corpus fetch is separated from loading.**
   A one-time, networked prep script writes a cached raw corpus file; the data
   layer reads that file offline and deterministically. Network/IO never touches
   the per-run query path.

---

## Steps

### 1. Add the `wordfreq` dependency — *(tooling)*
- Add `wordfreq~=3.1` to `requirements.txt`; `pip install` it into `venv/`.
- **Done when:** `python -c "import wordfreq"` succeeds and
  `wordfreq.top_n_list('en', 10)` returns words.

### 2. One-time corpus fetch → cached raw file — *(data layer, prep)*
- New `scripts/fetch_corpus.py`: build the word list (`wordfreq` top ~5000 ∪
  curated eval targets), fetch each word's entry from the Free Dictionary API
  with light concurrency + retry/backoff, skip words with no entry, and write
  `data/raw/corpus.jsonl` (one JSON object per word: word, pos, definitions).
- Idempotent: if `data/raw/corpus.jsonl` already exists, do nothing unless
  `--force`.
- **Done when:** `data/raw/corpus.jsonl` exists with ~3–5k lines and
  `grep '"word": "petrichor"'` finds it.

### 3. Implement `load_records()` — *(data layer)*
- Read `data/raw/corpus.jsonl` (offline, deterministic). For Phase 1, emit
  **one `WordRecord` per word**: `sense=0`, primary POS, primary definition,
  `embed_text = f"{word}: {definition}"`, stable incrementing `id`.
- **Done when:** `load_records()` returns ~3–5k `WordRecord`s, ids are
  `0..N-1` contiguous, and the petrichor record is present with a sane
  definition. Add a unit test.

### 4. Implement `embed()` — *(embedding layer)*
- Load `all-MiniLM-L6-v2` via `sentence-transformers` (lazy module-level
  singleton so the model loads once). Return an L2-normalised
  `(len(texts), 384)` `float32` array. `MODEL_ID` / `EMBEDDING_DIM` already set.
- **Done when:** `embed(["hello","world"]).shape == (2, 384)` and each row has
  L2 norm ≈ 1.0. Add a unit test.

### 5. Implement the numpy index — `build()` / `load()` / `search()` — *(index layer)*
- `build(vectors, records)`: write `index/cache/vectors.npy`,
  `records.pkl`, and `meta.json` (storing `MODEL_ID`, count, dim).
- `load()`: read them into module-level state; **validate** stored `MODEL_ID`
  matches `embedding.MODEL_ID` and dim matches — mismatch raises, never
  silently re-embeds.
- `search(query_vector, k=50)`: cosine similarity via dot product against the
  normalised matrix (`vectors @ q`), return top-k `SearchResult` sorted
  descending.
- **Done when:** build → load → `search(embed(["bank"])[0], k=5)` returns 5
  sensible results with scores in `[-1, 1]` descending. Add a unit test on a
  tiny synthetic matrix.

### 6. Implement `scripts/build_index.py` — *(scripts)*
- Enforce the **cache-before-embed** invariant: if `index/cache/vectors.npy`
  exists and `meta.json` `MODEL_ID == embedding.MODEL_ID`, print "cache hit" and
  exit. Otherwise: `load_records()` → `embed()` → `build()`.
- **Done when:** first run embeds and writes the cache; second run prints a cache
  hit and does **not** re-embed.

### 7. Terminal query entry point — *(thin interface)*
- New `scripts/query.py` (or `query.py` at root): `index.load()` once, then read
  a description (CLI arg or REPL loop), `embed()` it, `search(k=10)`, print the
  10 words with score + definition. **No business logic** beyond wiring — true
  routing/rerank comes in later phases.
- **Done when:** `python scripts/query.py "the smell of rain on dry earth"`
  prints **petrichor** within the top 10. *(This is the Phase 1 "done when".)*

### 8. Update progress log + housekeeping
- Update `.claude/progress.md` with Phase 1 outcome.
- Ensure `data/raw/` cache artifacts are gitignored as appropriate (commit the
  fetch script and loader; do not commit large generated caches).

---

## Eval impact
**No automated eval gate this phase** — the harness (`eval.py`) does not exist
until Phase 2, so there is no baseline to compare against and the eval-gate rule
is not yet active. Quality is judged this phase by the single manual "done when"
canary (`smell of rain on dry earth → petrichor in top 10`). Phase 2 will
formalize measurement and record the first baseline.

## Files to create or modify
- `requirements.txt` — add `wordfreq~=3.1`. *(modify)*
- `scripts/fetch_corpus.py` — **new**, one-time networked corpus fetch → cache. *(data-layer prep; feeds the data layer, not a cross-layer leak)*
- `data/raw/corpus.jsonl` — **new** generated cache (gitignore policy decided in step 8).
- `data/loader.py` — implement `load_records()`. *(modify)*
- `embedding/embedder.py` — implement `embed()`. *(modify)*
- `index/engine.py` — implement `build()/load()/search()`. *(modify)*
- `scripts/build_index.py` — implement `main()`. *(modify)*
- `scripts/query.py` — **new** terminal query runner (thin). *(interface seam — terminal only)*
- `tests/` — add unit tests for loader, embedder, index. *(new/modify)*
- `.claude/progress.md` — record Phase 1 outcome. *(modify)*

No new file crosses a layer boundary: each lives in exactly one layer's folder
and talks only through the existing contracts.

## Risks / open questions
- **Free Dictionary API robustness.** It is a free community API and can rate-limit
  or be briefly down. Mitigation: one-time fetch, on-disk cache, retry/backoff,
  skip-missing. Once `corpus.jsonl` is cached, normal runs never hit the network.
  *(Long-term, Phase 8+ may vendor a static dataset for reproducibility.)*
- **License/attribution.** Wiktionary data is CC BY-SA / GPL. Fine for this
  project; note attribution in the README when we ship publicly.
- **Coverage of the frequency list.** A handful of `wordfreq` top words may lack a
  clean API entry (function words, inflections). We skip them; the corpus may
  land slightly under 5k. Acceptable for a thin slice.
- **One record per word loses senses.** Intentional for Phase 1; Phase 3 fixes it
  by emitting one record per sense.
- **First run is slow** (model download + ~5k API fetches + embedding). All
  cached afterward.

## Estimated scope
**Medium** (roughly a half day). The fetch + caching plumbing is the bulk; the
embedding and numpy search are small. Each step is independently testable.

---

### TL;DR
Bottom-up build of the real query path: pull a ~5k common-word corpus (wordfreq +
forced eval targets) with definitions from the Wiktionary-backed Free Dictionary
API (because WordNet lacks *petrichor*), cache it, implement `load_records` →
`embed` (MiniLM) → numpy cosine `search`, wire `build_index.py` with
cache-before-embed, and add a terminal query runner. Done when
`"the smell of rain on dry earth"` returns **petrichor** in the top 10.
