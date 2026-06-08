# Plan: Local Interface (Phase 8)

## Goal

A user can open a browser, type a description, press Enter, and see ranked word
results with definitions, grouped results for multi-concept queries, copy buttons,
and optional filter controls — all powered by a local FastAPI backend and a
React/Tailwind frontend.

---

## Which layers are touched

**Primarily interface** (`interface/api.py`, `interface/frontend/`), plus a small
additive change to the **index layer** (`index/engine.py`).

The index layer change (Step 1a) adds one new public function — `record_count()` —
so the health endpoint doesn't reach into private internals. No existing signatures
change. All other steps are interface-only. The FastAPI handler calls
`understanding.query.query()` through its published interface — the seam is correct.

---

## Current phase check

Phase 7 is complete (FAISS swap, eval passes, 80/80 tests). Phase 8 is next in
sequence. No phase-order violation.

---

## Steps

### Step 1a — Add `record_count()` to the index layer

**Layer:** Index (`index/engine.py`)

Add a single public function to the index layer's interface so the API health
endpoint can report corpus size without reaching into private internals.

```python
def record_count() -> int:
    """Return the number of records currently loaded in the index."""
```

Returns `len(_records)`. Raises nothing if called before `load()` — returns 0.

Also update `docs/architecture.md` and `.claude/rules/layer-contracts.md` to
document the new function alongside `build()`, `load()`, and `search()`.

**Done when:** `import index.engine as e; e.load(); e.record_count()` returns 48647
in the project venv.

---

### Step 1b — Implement `interface/api.py`

**Layer:** Interface

Wire the two endpoints and add startup index loading. No business logic goes here.

- Add a FastAPI lifespan handler that calls `index.engine.load()` on startup so
  the FAISS index is warm before the first request.
- Add CORS middleware allowing `http://localhost:5173` (Vite dev server) so the
  frontend can call the backend without browser errors during local dev.
- `POST /query`:
  - Define a Pydantic `BaseModel` for the request body (not prose — FastAPI needs
    a model to parse JSON and emit automatic 422s):
    ```python
    class FiltersRequest(BaseModel):
        pos: str | None = None
        starts_with: str | None = None
        max_length: int | None = None

    class QueryRequest(BaseModel):
        text: str
        filters: FiltersRequest | None = None
        lucky: bool = False
    ```
  - Build a `QueryFilters` (or `None`) from `req.filters`, then call
    `understanding.query.query(req.text, filters, req.lucky)` — pass all three
    arguments explicitly including `lucky`. Convert the returned `QueryResponse`
    dataclass to a dict with `dataclasses.asdict()` (safe here: all nested types
    are plain dataclasses with primitive fields — no custom serialiser needed) and
    return it.
  - Return HTTP 422 automatically for malformed input (FastAPI handles via Pydantic).
- `GET /health`:
  - Return `{ "status": "ok", "index_size": <number of loaded records>,
    "model": embedding.MODEL_ID, "phase": 8 }`.
  - `index_size` comes from `index.engine.record_count()` (added in Step 1a above).
- Set `PHASE = 8`.
- Run locally: `uvicorn interface.api:app --reload` — verify `/health` returns 200
  and `/query` returns results for a test payload via curl.

**Done when:** `curl -X POST http://localhost:8000/query -H 'Content-Type: application/json' -d '{"text":"the smell of rain on dry earth"}'` returns petrichor in the top result, and `curl http://localhost:8000/health` returns `index_size: 48647`.

---

### Step 2 — Scaffold the React/Tailwind frontend

**Layer:** Interface (frontend)

Bootstrap the project inside `interface/frontend/` using Vite + React + Tailwind.

- `npm create vite@latest . -- --template react` inside `interface/frontend/`.
- Install and configure Tailwind CSS (`npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`).
- Add a Vite dev-server proxy in `vite.config.js` using an `/api` prefix:
  proxy all requests to `/api` → `http://localhost:8000`. Backend routes will be
  mounted at `/api/query` and `/api/health`. Using a single prefix (not
  per-route entries) means new endpoints are covered automatically with no
  proxy changes.
  ```js
  server: { proxy: { '/api': 'http://localhost:8000' } }
  ```
- Delete the Vite boilerplate content from `App.jsx`; replace with a blank shell
  component.
- Confirm `npm run dev` opens without errors in the browser.

**Done when:** `npm run dev` opens a blank page without console errors; `fetch('/health')` from the browser console returns `{ status: "ok", ... }`.

---

### Step 3 — Build the query UI

**Layer:** Interface (frontend)

Implement the core query flow in `App.jsx` (and small sub-components if needed).

- **Input box**: full-width, autofocused on load, submit on Enter. Show a subtle
  loading state (disabled + spinner) while the request is in flight.
- **Results rendering**:
  - For `mode="single"`: render one flat list of results.
  - For `mode="grouped"`: render each `ConceptGroup` under its label as a section
    header. If the group's results have `is_interpretation=true`, show a small
    "interpretation" badge on the group header — never hide this per the architecture
    rules.
  - Each result card: word (large, bold), POS badge (noun/verb/adj/adv readable
    label), definition text, copy button that copies the word to clipboard.
  - Empty state: if `groups[0].results` is empty, show "No matches found."
- **Error state**: if the API returns non-200, show a brief error message.

**Done when:** typing "the smell of rain on dry earth" returns petrichor as the first result; typing the canary passage returns grouped results with interpretation badges.

---

### Step 4 — Add filter controls and lucky mode

**Layer:** Interface (frontend)

Expose the filters and lucky toggle that the understanding layer already supports.

- A "Filters" row always visible below the input box.
- Controls in the row:
  - **Part of speech**: dropdown — All / Noun (n) / Verb (v) / Adjective (a) /
    Adverb (r).
  - **Starts with**: single text input (prefix match, passed as `starts_with`).
  - **Max word length**: number input.
  - **Feeling lucky**: toggle switch.
- Filters and the `lucky` flag are passed in the POST body when the user submits.
  Null/empty values are omitted. **The frontend does not truncate results itself** —
  it passes `"lucky": true` to the backend and renders whatever comes back. All
  truncation logic lives in `understanding.query.query()`.
- A "Clear" button resets all controls to their default (no filter) state.

**Done when:** selecting "Noun" and typing "sadness" returns only noun results; enabling lucky mode returns exactly one result per group.

---

### Step 5 — Write API tests

**Layer:** Interface

Add `tests/test_api.py` using FastAPI's `TestClient` (ships with `httpx`, no live
server needed).

- `GET /health` returns 200 with `status == "ok"` and `phase == 8`.
- `POST /query` with `{"text": "the smell of rain on dry earth"}` returns 200 and
  `groups[0].results[0].word == "petrichor"` (requires the FAISS index to be built).
- `POST /query` with an empty body returns 422.
- `POST /query` with `{"text": "...", "lucky": true}` returns at most 1 result per
  group.

Note: these tests load the real index, so they require `python scripts/build_index.py`
to have been run. Add a pytest mark (`@pytest.mark.integration`) so they can be
skipped in CI if the index is not present.

**Done when:** `pytest tests/test_api.py` passes (with the index built).

---

## Eval impact

**No impact on recall@10 or MRR.** This phase touches only the interface layer —
no changes to embedding, index, understanding, or data. The query path through
`understanding.query.query()` is unchanged.

No eval run required before or after.

---

## Files to create or modify

| File | Change |
|------|--------|
| `index/engine.py` | Add `record_count() -> int` public function |
| `docs/architecture.md` | Document `record_count()` in the index layer contract |
| `.claude/rules/layer-contracts.md` | Add `record_count()` to the index layer interface |
| `interface/api.py` | Full implementation — lifespan loader, `/api/query`, `/api/health`, CORS |
| `interface/frontend/` | New Vite + React project scaffolded here |
| `interface/frontend/vite.config.js` | Proxy `/api` prefix to port 8000 (single entry, covers all routes) |
| `interface/frontend/src/App.jsx` | Main UI: input, results, filters, lucky toggle |
| `interface/frontend/src/components/ResultCard.jsx` | Word / POS / definition / copy button |
| `interface/frontend/src/components/ConceptGroupSection.jsx` | Group header + result list |
| `interface/frontend/src/components/FilterPanel.jsx` | Always-visible filter controls row |
| `interface/frontend/tailwind.config.js` | Tailwind setup |
| `tests/test_api.py` | New — FastAPI TestClient tests (integration-marked) |
| `requirements.txt` | Add `httpx~=0.28` (TestClient dependency) |

No file crosses a layer boundary. All changes are in the interface layer or the test
directory (orthogonal to the layers).

---

## Risks / open questions

1. **`httpx` for TestClient**: FastAPI's `TestClient` requires `httpx`. Currently not
   in `requirements.txt`. Adding it is safe and small.

2. **`record_count()` touches the index layer**: Step 1a is the only step that
   changes a layer other than Interface. It is a minimal, additive change (new
   public function, no signature changes) and is required to keep the health
   endpoint from reaching into private internals. Seam is now correct.

3. **`interface/frontend/` in `.gitignore`**: `node_modules/` inside the frontend
   must be gitignored. Will add `interface/frontend/node_modules/` to `.gitignore`.

4. **Python env and Node env side by side**: `uvicorn` must be running (in the venv)
   at the same time as `npm run dev`. Two terminals needed. No conflict, just a
   workflow note.

5. **`load()` idempotency — critical**: `understanding/query.py`'s
   `_run_single_concept()` calls `engine.load()` on every invocation (line 77).
   The current `load()` implementation unconditionally overwrites `_index` and
   `_records` — it has no "already loaded" guard. This means every sub-query in a
   multi-concept request reloads the 48K-record FAISS index from disk, making the
   lifespan preload pointless and adding significant per-request latency. **Fix
   required in Step 1a (alongside `record_count()`)**: add an early-return guard
   to `load()`:
   ```python
   if _index is not None:
       return
   ```
   This is an additive, safe fix — load is now idempotent.

6. **POS labels**: the backend uses `"n"`, `"v"`, `"a"`, `"r"`. The UI will map
   these to Noun / Verb / Adjective / Adverb. Confirm these are the only four values
   in the corpus.

---

## Estimated scope

**Large (multiple sessions).** Suggested breakdown:

- **Session A**: Steps 1 + 2 — backend wired, frontend scaffolded, proxy working.
  Done when curl returns petrichor and `npm run dev` opens without errors.
- **Session B**: Steps 3 + 4 — full query UI, grouped results, filters, lucky mode.
  Done when the canary passage returns grouped interpretations in the browser.
- **Session C**: Step 5 — API tests, polish, integration check.
  Done when `pytest tests/` is 80+/80+ and the full flow is smoke-tested.
