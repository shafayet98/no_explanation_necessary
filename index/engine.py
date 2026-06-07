"""Index layer engine. Swapping numpy for FAISS (Phase 7) means rewriting the
internals of build/load/search — the signatures stay identical and nothing above
this layer changes."""

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from data.models import WordRecord

_CACHE_DIR = Path(__file__).parent / "cache"
_VECTORS_PATH = _CACHE_DIR / "vectors.npy"
_RECORDS_PATH = _CACHE_DIR / "records.pkl"
_META_PATH = _CACHE_DIR / "meta.json"

# Module-level index state — populated by load()
_vectors: np.ndarray | None = None
_records: list[WordRecord] | None = None


@dataclass
class SearchResult:
    record: WordRecord
    score: float    # cosine similarity, range -1 to 1 (L2-normalised → dot product)


def build(vectors: np.ndarray, records: list[WordRecord]) -> None:
    """Persist the index + records to disk (index/cache/).

    Writes vectors.npy, records.pkl, and meta.json (storing MODEL_ID).
    Run once via scripts/build_index.py.
    """
    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    np.save(_VECTORS_PATH, vectors)

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

    Validates that the stored model_id matches embedding.MODEL_ID and that the
    stored dim matches EMBEDDING_DIM. Mismatch raises RuntimeError — never
    silently re-embeds.
    """
    global _vectors, _records

    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    if not _VECTORS_PATH.exists():
        raise FileNotFoundError(
            f"No index found at {_VECTORS_PATH}. "
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

    _vectors = np.load(_VECTORS_PATH)  # shape (N, EMBEDDING_DIM), float32
    with _RECORDS_PATH.open("rb") as fh:
        _records = pickle.load(fh)


def search(query_vector: np.ndarray, k: int = 50) -> list[SearchResult]:
    """Return up to k SearchResults sorted by cosine similarity descending.

    Requires load() to have been called first. Cosine similarity equals the dot
    product because both the index vectors and query_vector are L2-normalised.

    Deduplicates by word — when multiple senses of the same word appear in the
    shortlist, only the highest-scoring sense is returned.
    """
    if _vectors is None or _records is None:
        raise RuntimeError("Index not loaded. Call index.engine.load() first.")

    scores = _vectors @ query_vector.astype(np.float32)

    # Oversample to ensure k unique words survive deduplication
    raw_k = min(k * 5, len(scores))
    idx = np.argpartition(scores, -raw_k)[-raw_k:]
    idx = idx[np.argsort(scores[idx])[::-1]]

    seen_words: set[str] = set()
    results: list[SearchResult] = []
    for i in idx:
        word = _records[i].word
        if word not in seen_words:
            seen_words.add(word)
            results.append(SearchResult(record=_records[i], score=float(scores[i])))
            if len(results) == k:
                break

    return results
