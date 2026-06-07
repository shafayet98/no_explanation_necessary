"""Index layer engine. Swapping numpy for FAISS (Phase 7) means rewriting the
internals of build/load/search — the signatures stay identical and nothing above
this layer changes."""

from dataclasses import dataclass

import numpy as np

from data.models import WordRecord


@dataclass
class SearchResult:
    record: WordRecord
    score: float    # cosine similarity, range 0-1


def build(vectors: np.ndarray, records: list[WordRecord]) -> None:
    """Persist the index + records to disk (index/cache/).

    Writes vectors.npy, records.pkl, and meta.json (storing MODEL_ID). Run once
    via scripts/build_index.py.
    """
    raise NotImplementedError("index layer not implemented yet (skeleton)")


def load() -> None:
    """Load the persisted index into memory.

    Validates that the stored MODEL_ID matches embedding.MODEL_ID; mismatch is an
    error, never a silent re-embed.
    """
    raise NotImplementedError("index layer not implemented yet (skeleton)")


def search(query_vector: np.ndarray, k: int = 50) -> list[SearchResult]:
    """Return up to k SearchResults sorted by score descending."""
    raise NotImplementedError("index layer not implemented yet (skeleton)")
