"""Index layer — vector storage + nearest-neighbour search.

Public interface (see docs/architecture.md):
    from index.engine import build, load, search, SearchResult

Phase 1-6: numpy brute-force cosine. Phase 7: FAISS behind the same signatures.
"""
