# Layer Interface Contracts

These are the exact public interfaces each layer exposes. Do not change a signature without updating both the implementation and all callers. When in doubt, add a new function rather than changing an existing one.

## Data Layer — `data/loader.py`, `data/models.py`

```python
@dataclass
class WordRecord:
    id: int
    word: str
    sense: int
    pos: str          # "n", "v", "a", "r"
    definition: str
    embed_text: str   # pre-formatted: "word: definition"

def load_records() -> list[WordRecord]: ...
```

Nothing outside the data layer constructs WordRecords directly. They always come from `load_records()`.

## Embedding Layer — `embedding/embedder.py`

```python
MODEL_ID: str
EMBEDDING_DIM: int

def embed(texts: list[str]) -> np.ndarray:
    # shape: (len(texts), EMBEDDING_DIM), L2-normalised
```

The embedding layer has ONE public function. Swapping the model means changing the implementation of `embed()` and the values of `MODEL_ID` and `EMBEDDING_DIM`. Nothing else changes.

## Index Layer — `index/engine.py`

```python
@dataclass
class SearchResult:
    record: WordRecord
    score: float

def build(vectors: np.ndarray, records: list[WordRecord]) -> None: ...
def load() -> None: ...          # idempotent — safe to call multiple times
def search(query_vector: np.ndarray, k: int = 50) -> list[SearchResult]: ...
def record_count() -> int: ...   # returns 0 if load() not yet called (Phase 8+)
```

Swapping numpy for FAISS (Phase 7) means rewriting the internals of `build()`, `load()`, and `search()`. The signatures stay identical. Zero changes above this layer.

## Understanding Layer — `understanding/query.py`

```python
@dataclass
class QueryFilters:
    pos: str | None
    starts_with: str | None
    max_length: int | None

@dataclass
class RankedResult:
    word: str
    pos: str
    definition: str
    score: float
    is_interpretation: bool

@dataclass
class ConceptGroup:
    label: str
    results: list[RankedResult]

@dataclass
class QueryResponse:
    mode: Literal["single", "grouped", "mood"]
    groups: list[ConceptGroup]

def query(user_input: str, filters: QueryFilters | None = None) -> QueryResponse: ...
```

The interface layer calls only `query()`. It never calls `embed()`, `search()`, or `load_records()` directly.

## Interface Layer — `interface/api.py`

```
POST /query    → QueryResponse (JSON)
GET  /health   → { status, index_size, model, phase }
```

The React frontend calls only these endpoints. It receives `QueryResponse` and renders it. No other knowledge of the system.

## The Golden Rule

If you can swap the implementation of a layer and the layer above it does not need to change, the seam is correct. If the layer above needs changes too, the seam is wrong.
