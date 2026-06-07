# Architecture

## Overview

Five independent layers connected through narrow interfaces. The governing rule: a change to one layer touches only that layer. If you find yourself editing three files for one logical change, the seam is in the wrong place — stop and fix the seam first.

---

## Layer Stack

```
┌──────────────────────────────────────────────────────────────┐
│                      Interface Layer                         │
│               FastAPI (REST) + React/Tailwind                │
│    Thin. No business logic. Shapes requests, renders results.│
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP JSON
┌────────────────────────────▼─────────────────────────────────┐
│                    Understanding Layer                        │
│         Input classification → routing → reranking           │
│  This is where the intelligence lives. Everything else is    │
│  plumbing. Single concept → straight to retrieve+rerank.     │
│  Multi-concept → LLM decomposes → run N clean sub-queries.   │
└─────────────┬───────────────────────────┬────────────────────┘
              │ clean single query        │ N decomposed queries
              │                           │ (run in parallel)
┌─────────────▼───────────────────────────▼────────────────────┐
│                       Index Layer                            │
│         Vector search (retrieve) + reranker (rerank)         │
│  search(query_vector, k) → [(record_id, score)]              │
│  Phase 1–6: numpy brute force. Phase 7+: FAISS.              │
│  Same interface. Zero changes above this layer on swap.      │
└────────────────────────────┬─────────────────────────────────┘
                             │ text → vectors
┌────────────────────────────▼─────────────────────────────────┐
│                     Embedding Layer                          │
│     Thin wrapper: embed(texts: list[str]) → np.ndarray       │
│  Model: all-MiniLM-L6-v2 (384-dim) to start. Swappable.     │
│  Always L2-normalised so cosine sim == dot product.          │
└────────────────────────────┬─────────────────────────────────┘
                             │ (word, sense, pos, definition)
┌────────────────────────────▼─────────────────────────────────┐
│                       Data Layer                             │
│       WordNet loader → one WordRecord per word sense         │
│  Splits senses, normalises definitions, formats embed_text.  │
│  Phase 1: one record/word. Phase 3+: one record/sense.       │
└──────────────────────────────────────────────────────────────┘
```

---

## Interface Contracts

These signatures are the seams. Do not change them without updating both sides.

### Data Layer

```python
# data/models.py
@dataclass
class WordRecord:
    id: int           # stable row index into the vector matrix
    word: str         # e.g. "bank"
    sense: int        # WordNet sense number (0 in Phase 1, real in Phase 3+)
    pos: str          # "n", "v", "a", "r"
    definition: str   # e.g. "a financial institution that accepts deposits"
    embed_text: str   # text sent to the embedder: "bank: a financial institution..."

# data/loader.py
def load_records() -> list[WordRecord]: ...
```

### Embedding Layer

```python
# embedding/embedder.py
MODEL_ID: str          # e.g. "all-MiniLM-L6-v2" — stored with the index
EMBEDDING_DIM: int     # 384 for MiniLM — checked on index load

def embed(texts: list[str]) -> np.ndarray:
    # Returns shape (len(texts), EMBEDDING_DIM), L2-normalised.
    # This is the entire public interface of this layer.
    ...
```

### Index Layer

```python
# index/engine.py
@dataclass
class SearchResult:
    record: WordRecord
    score: float    # cosine similarity, range 0–1

def build(vectors: np.ndarray, records: list[WordRecord]) -> None:
    # Persists index + records to disk. Run once via scripts/build_index.py.
    ...

def load() -> None:
    # Loads persisted index into memory. Validates MODEL_ID matches.
    ...

def search(query_vector: np.ndarray, k: int = 50) -> list[SearchResult]:
    # Returns up to k results sorted by score descending.
    # Phase 7: swap numpy array for FAISS IndexFlatIP. Same signature.
    ...
```

### Understanding Layer

```python
# understanding/query.py
@dataclass
class QueryFilters:
    pos: str | None          # "n", "v", "a", "r" — restrict by part of speech
    starts_with: str | None  # restrict to words beginning with this letter
    max_length: int | None   # restrict to words of at most N characters

@dataclass
class RankedResult:
    word: str
    pos: str
    definition: str          # the specific sense definition that matched
    score: float
    is_interpretation: bool  # True for mood/passage results — never hide this

@dataclass
class ConceptGroup:
    label: str               # e.g. "the smell", "the feeling of release"
    results: list[RankedResult]

@dataclass
class QueryResponse:
    mode: Literal["single", "grouped", "mood"]
    groups: list[ConceptGroup]  # length 1 for single-concept queries

def query(user_input: str, filters: QueryFilters | None = None) -> QueryResponse:
    # The one entry point into the understanding layer.
    ...
```

### Interface Layer (API contract)

```
POST /query
  Body:     { "text": string, "filters": { "pos"?: string, "starts_with"?: string, "max_length"?: int } }
  Response: QueryResponse (serialised to JSON)

GET /health
  Response: { "status": "ok", "index_size": int, "model": string, "phase": int }
```

---

## Data Flow

### Indexing path — run once offline

```
WordNet corpus
  └─► data.load_records()
        └─► [WordRecord, ...]               # one per sense (Phase 3+)
              └─► embedding.embed(embed_texts)
                    └─► np.ndarray (N × 384)
                          └─► index.build(vectors, records)
                                └─► cache/vectors.npy
                                    cache/records.pkl
                                    cache/meta.json   ← stores MODEL_ID
```

### Query path — per request

```
user_input
  └─► understanding.classify(input)
        │
        ├─[single concept]──────────────────────────────────────────────────┐
        │   embedding.embed([query])                                         │
        │   → index.search(vec, k=50)           # broad retrieve            │
        │   → reranker.rerank(candidates, query) # precision sort           │
        │   → dedupe by word                     # keep best-scoring sense  │
        │   → top 10                                                         │
        │   → QueryResponse(mode="single", groups=[ConceptGroup(...)])       │
        │                                                                    │
        └─[multi-concept]───────────────────────────────────────────────────┐
            LLM extracts 2–3 clean sub-queries with labels                  │
            → run each sub-query through single-concept path (parallel)     │
            → collect into ConceptGroup per sub-query                       │
            → QueryResponse(mode="grouped", groups=[...])                   │
            (is_interpretation=True on all results if passage is mood)      │
```

---

## Folder → Layer Mapping

```
reverse_dictionary/
├── data/                   ← Data layer
│   ├── __init__.py
│   ├── loader.py           # load_records()
│   └── models.py           # WordRecord
│
├── embedding/              ← Embedding layer
│   ├── __init__.py
│   └── embedder.py         # embed(), MODEL_ID, EMBEDDING_DIM
│
├── index/                  ← Index layer
│   ├── __init__.py
│   ├── engine.py           # build(), load(), search(), SearchResult
│   └── cache/              # vectors.npy, records.pkl, meta.json (gitignored)
│
├── understanding/          ← Understanding layer
│   ├── __init__.py
│   ├── classifier.py       # classify input type
│   ├── reranker.py         # cross-encoder / LLM reranking
│   └── query.py            # query(), QueryResponse, ConceptGroup, RankedResult
│
├── interface/              ← Interface layer
│   ├── api.py              # FastAPI app — thin, no logic
│   └── frontend/           # React + Tailwind (Phase 8)
│
├── eval/                   ← Evaluation harness (orthogonal to the 5 layers)
│   ├── eval.py             # python eval.py → recall@10 + MRR vs baseline
│   ├── test_cases.jsonl    # {"description": "...", "expected_word": "..."}
│   └── baselines.json      # {"phase": 1, "recall_at_10": 0.62, "mrr": 0.41}
│
├── scripts/
│   └── build_index.py      # one-shot: load → embed → build → save
│
└── infra/                  ← Terraform (AWS, Phase 8)
    ├── modules/
    └── envs/
        ├── dev/
        └── prod/
```

---

## Phase Evolution by Layer

| Phase | Data | Embedding | Index | Understanding | Interface |
|-------|------|-----------|-------|---------------|-----------|
| 0 | stubs | stubs | stubs | stubs | stubs |
| 1 | 3–5k words, 1 vec/word | all-MiniLM-L6-v2, cached | numpy cosine | pass-through | terminal print |
| 2 | unchanged | unchanged | unchanged | unchanged | `eval.py` added |
| 3 | 1 record/sense, dedupe | embed each sense separately | unchanged | unchanged | unchanged |
| 4 | unchanged | unchanged | retrieve top-50 + reranker | reranker integrated | unchanged |
| 5 | unchanged | unchanged | unchanged | classifier + LLM decomposition | unchanged |
| 6 | filter metadata on record | unchanged | filter by POS/letter/len | filter params wired | filter UI params |
| 7 | unchanged | unchanged | numpy → FAISS (same interface) | unchanged | unchanged |
| 8 | unchanged | unchanged | unchanged | unchanged | FastAPI + React deploy |

---

## Key Invariants

**1. Model consistency.**
The `MODEL_ID` used at index time is written to `cache/meta.json`. On `index.load()`, it is read back and checked against the current `embedding.MODEL_ID`. Mismatch raises an error — never silently re-embed.

**2. Cache before embed.**
`scripts/build_index.py` checks whether `cache/vectors.npy` exists and the model matches before running any embedding. Re-embedding the full dictionary on every run is never acceptable.

**3. Eval gate (from Phase 2).**
Every quality change must show a metric delta. Run `python eval.py` before and after. Number goes up → keep. Number goes down → revert. No exceptions.

**4. Deduplication.**
After reranking, results are deduped by `word`. Multiple senses of the same word collapse to the highest-scoring sense. The matched sense's definition is shown so the user understands why the word appeared.

**5. Honest framing for passages.**
Any result produced from a multi-concept or mood query carries `is_interpretation: True`. The interface layer must render these differently (e.g. labelled "interpretation" not "answer"). Never return a single word with false confidence for a passage that has no single target word.

**6. Frontend is dumb.**
No business logic in React. No filtering, scoring, or routing in the frontend. All of that lives in the understanding layer. The frontend is a rendering client.
