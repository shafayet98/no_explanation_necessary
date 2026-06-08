"""Index layer engine. Phase 7: numpy brute-force replaced with FAISS IndexFlatIP.
Signatures of build/load/search are identical — zero changes above this layer."""

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from data.models import WordRecord

_CACHE_DIR = Path(__file__).parent / "cache"
_FAISS_PATH = _CACHE_DIR / "index.faiss"
_RECORDS_PATH = _CACHE_DIR / "records.pkl"
_META_PATH = _CACHE_DIR / "meta.json"

# Module-level index state — populated by load()
_index: faiss.Index | None = None
_records: list[WordRecord] | None = None


@dataclass
class SearchResult:
    record: WordRecord
    score: float    # cosine similarity, range -1 to 1 (L2-normalised → inner product)


def build(vectors: np.ndarray, records: list[WordRecord]) -> None:
    """Persist the index + records to disk (index/cache/).

    Writes index.faiss, records.pkl, and meta.json (storing MODEL_ID).
    Run once via scripts/build_index.py.
    """
    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    idx = faiss.IndexFlatIP(EMBEDDING_DIM)
    idx.add(vectors.astype(np.float32))
    faiss.write_index(idx, str(_FAISS_PATH))

    with _RECORDS_PATH.open("wb") as fh:
        pickle.dump(records, fh, protocol=pickle.HIGHEST_PROTOCOL)

    meta = {
        "model_id": MODEL_ID,
        "embedding_dim": EMBEDDING_DIM,
        "count": len(records),
    }
    with _META_PATH.open("w") as fh:
        json.dump(meta, fh, indent=2)


def load() -> None:
    """Load the persisted index into memory.

    Idempotent — safe to call multiple times; skips reload if already loaded.
    Validates that the stored model_id matches embedding.MODEL_ID and that the
    stored dim matches EMBEDDING_DIM. Mismatch raises RuntimeError — never
    silently re-embeds.
    """
    global _index, _records

    if _index is not None:
        return

    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    if not _FAISS_PATH.exists():
        raise FileNotFoundError(
            f"No index found at {_FAISS_PATH}. "
            "Run `python scripts/build_index.py` first."
        )

    with _META_PATH.open() as fh:
        meta = json.load(fh)

    if meta["model_id"] != MODEL_ID:
        raise RuntimeError(
            f"Index was built with model '{meta['model_id']}' but current "
            f"model is '{MODEL_ID}'. Delete index/cache/ and re-run build_index.py."
        )
    if meta["embedding_dim"] != EMBEDDING_DIM:
        raise RuntimeError(
            f"Index dim {meta['embedding_dim']} != current EMBEDDING_DIM {EMBEDDING_DIM}."
        )

    _index = faiss.read_index(str(_FAISS_PATH))
    with _RECORDS_PATH.open("rb") as fh:
        _records = pickle.load(fh)


def record_count() -> int:
    """Return the number of records currently loaded in the index.

    Returns 0 if load() has not been called yet.
    """
    return len(_records) if _records is not None else 0


def search(query_vector: np.ndarray, k: int = 50) -> list[SearchResult]:
    """Return up to k SearchResults sorted by cosine similarity descending.

    Requires load() to have been called first. Cosine similarity equals the inner
    product because both the index vectors and query_vector are L2-normalised.

    Deduplicates by word — when multiple senses of the same word appear in the
    shortlist, only the highest-scoring sense is returned.
    """
    if _index is None or _records is None:
        raise RuntimeError("Index not loaded. Call index.engine.load() first.")

    # Oversample to ensure k unique words survive deduplication
    raw_k = min(k * 5, _index.ntotal)
    q = query_vector.reshape(1, -1).astype(np.float32)
    distances, indices = _index.search(q, raw_k)
    scores = distances[0]
    idx = indices[0]

    seen_words: set[str] = set()
    results: list[SearchResult] = []
    for i, score in zip(idx, scores):
        if i == -1:  # FAISS sentinel for not-found
            break
        word = _records[i].word
        if word not in seen_words:
            seen_words.add(word)
            results.append(SearchResult(record=_records[i], score=float(score)))
            if len(results) == k:
                break

    return results
