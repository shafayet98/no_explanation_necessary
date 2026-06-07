# Plan — Project Skeleton Decision

Status: **Proposed** (awaiting approval)
Branch: `setup/project-skeleton`

---

## Goal
The full repo structure exists — a folder per layer, a Python environment + dependency file, stubbed modules whose function signatures exactly match the layer contracts, and a stubbed Terraform tree — with **nothing implemented**, so every seam is in place and importable.

## Which layers are touched
All five layers, plus the orthogonal eval harness, scripts, and infra — but **only as empty seams, not implementations**. This is the one time where touching every layer is correct, because the whole point of the skeleton is to lay down the interfaces. No business logic crosses any boundary; each stub `raise NotImplementedError` (or returns a trivial empty value) and imports only what its own contract needs.

- Data layer — `data/models.py`, `data/loader.py`
- Embedding layer — `embedding/embedder.py`
- Index layer — `index/engine.py`
- Understanding layer — `understanding/classifier.py`, `understanding/reranker.py`, `understanding/query.py`
- Interface layer — `interface/api.py`
- Eval (orthogonal) — `eval/eval.py`, `eval/test_cases.jsonl`, `eval/baselines.json`
- Scripts — `scripts/build_index.py`
- Infra — `infra/` Terraform tree (stubbed)

## Current phase check
The repo currently has only docs, `.claude/` config, and CLAUDE.md — **no source folders exist yet**. This skeleton is the first build step and is correctly the next thing to do. Not out of order.

## Steps
Each step is one layer and is "done" when its stub files import cleanly and expose the contract signatures. No logic is implemented in any step.

1. **Project scaffolding (non-layer).** Create the Python virtual environment, `requirements.txt` (pinned deps for later phases: `numpy`, `sentence-transformers`, `nltk`/wordnet source, `fastapi`, `uvicorn`, plus dev: `pytest`), `pyproject.toml`/`setup` only if needed for package imports, `.gitignore` entries for `venv/`, `__pycache__/`, and `index/cache/`, and a top-level `README.md` pointer. **Done when:** `python -m venv` works and `pip install -r requirements.txt` is documented (install itself can be deferred to Phase 1).
2. **Data layer stubs.** `data/__init__.py`, `data/models.py` with the `WordRecord` dataclass (all 6 fields per contract), `data/loader.py` with `def load_records() -> list[WordRecord]: raise NotImplementedError`. **Done when:** `from data.loader import load_records` and `from data.models import WordRecord` succeed.
3. **Embedding layer stub.** `embedding/__init__.py`, `embedding/embedder.py` with `MODEL_ID: str = "all-MiniLM-L6-v2"`, `EMBEDDING_DIM: int = 384`, `def embed(texts: list[str]) -> np.ndarray: raise NotImplementedError`. **Done when:** `from embedding.embedder import embed, MODEL_ID, EMBEDDING_DIM` succeeds.
4. **Index layer stubs.** `index/__init__.py`, `index/engine.py` with `SearchResult` dataclass and `build()`, `load()`, `search()` stubs; create `index/cache/.gitkeep` (cache gitignored). **Done when:** `from index.engine import build, load, search, SearchResult` succeeds.
5. **Understanding layer stubs.** `understanding/__init__.py`, `understanding/query.py` with `QueryFilters`, `RankedResult`, `ConceptGroup`, `QueryResponse` dataclasses and `def query(...) -> QueryResponse` stub; `understanding/classifier.py` and `understanding/reranker.py` as empty stub modules. **Done when:** `from understanding.query import query, QueryResponse, ConceptGroup, RankedResult, QueryFilters` succeeds.
6. **Interface layer stub.** `interface/api.py` with a FastAPI app object and stubbed `POST /query` + `GET /health` routes returning placeholder/`NotImplementedError`; `interface/frontend/` left empty (Phase 8) with a `.gitkeep`. **Done when:** the module imports without executing logic.
7. **Eval harness stubs.** `eval/eval.py` stub (prints "not implemented"), empty `eval/test_cases.jsonl`, `eval/baselines.json` as `[]`. **Done when:** files exist; no metrics yet (Phase 2 fills them).
8. **Scripts stub.** `scripts/build_index.py` stub with the cache-check seam noted as a comment (`# must check cache before embedding`). **Done when:** file exists with the indexing-path outline as comments only.
9. **Terraform stub.** `infra/modules/` and `infra/envs/dev/`, `infra/envs/prod/` with empty `main.tf`/`variables.tf`/`outputs.tf` placeholders and a `README` noting AWS services are **not yet chosen** (to be confirmed before Phase 8). **Done when:** the tree exists; `terraform` is not run.
10. **Import smoke test.** A throwaway check that every layer module imports without error (manual `python -c "import ..."` or a tiny `tests/test_imports.py`). **Done when:** all imports succeed.

## Eval impact
**None.** No data, embedding, index, or ranking logic is implemented — every function is a stub. `recall@10`/`MRR` are not measurable yet, and `eval.py` is itself only a stub here. The eval gate does not apply to the skeleton. (Baselines get recorded once real retrieval and the eval harness exist.)

## Files to create or modify
- `requirements.txt` — pinned dependencies for later phases.
- `.gitignore` — add `venv/`, `__pycache__/`, `index/cache/`, `*.npy`, `*.pkl`.
- `README.md` — short pointer to CLAUDE.md and run instructions (optional, can defer).
- `data/__init__.py`, `data/models.py`, `data/loader.py` — Data layer seams.
- `embedding/__init__.py`, `embedding/embedder.py` — Embedding layer seam.
- `index/__init__.py`, `index/engine.py`, `index/cache/.gitkeep` — Index layer seams.
- `understanding/__init__.py`, `understanding/query.py`, `understanding/classifier.py`, `understanding/reranker.py` — Understanding layer seams.
- `interface/api.py`, `interface/frontend/.gitkeep` — Interface layer seam.
- `eval/eval.py`, `eval/test_cases.jsonl`, `eval/baselines.json` — Eval harness seams.
- `scripts/build_index.py` — indexing script seam (comments only).
- `infra/modules/`, `infra/envs/dev/*.tf`, `infra/envs/prod/*.tf`, `infra/README.md` — Terraform stubs.
- `tests/test_imports.py` (optional) — import smoke test.

**No file crosses a layer boundary.** Each module imports only its own contract types (e.g. `index/engine.py` imports `WordRecord` from `data.models` — that is the intended dependency direction, not a violation).

## Confirmed decisions (2026-06-07)
- **Package layout:** Flat top-level packages (`data/`, `embedding/`, …) per the architecture doc's folder map.
- **Dependency install:** Full install during Phase 0 — create the venv and `pip install -r requirements.txt` (includes `sentence-transformers`; expect a slower one-time setup + model deps download).
- **Web framework:** FastAPI — `interface/api.py` is stubbed against FastAPI (app object + route placeholders, no real logic).

## Risks / open questions
- **AWS architecture is deliberately NOT decided here.** Terraform is stubbed empty; service choices (compute/object storage/CDN) must be proposed and confirmed before Phase 8. No assumptions baked into Phase 0.

## Estimated scope
**Small (< 1 hour).** Pure scaffolding — directories, stub files, dataclasses, and `NotImplementedError` bodies. No logic, no eval, no model download.

---

*Next:* run `/execute project_skeleton_decision` after approval.
