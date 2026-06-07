"""Phase 1 unit tests: embedding layer and index engine.

The data-layer test (load_records) is intentionally corpus-dependent and lives
at the bottom of this file marked with a skip when the corpus hasn't been built.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Embedding layer
# ---------------------------------------------------------------------------

def test_embed_shape_and_dtype():
    from embedding.embedder import embed, EMBEDDING_DIM

    vecs = embed(["hello", "world"])
    assert vecs.shape == (2, EMBEDDING_DIM), f"Expected (2, {EMBEDDING_DIM}), got {vecs.shape}"
    assert vecs.dtype == np.float32


def test_embed_l2_normalised():
    from embedding.embedder import embed

    vecs = embed(["the smell of rain on dry earth", "nostalgia"])
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5,
                               err_msg="Vectors must be L2-normalised")


def test_embed_single_text():
    from embedding.embedder import embed, EMBEDDING_DIM

    vecs = embed(["petrichor"])
    assert vecs.shape == (1, EMBEDDING_DIM)


# ---------------------------------------------------------------------------
# Index layer — synthetic matrix (no real corpus required)
# ---------------------------------------------------------------------------

def _make_synthetic_index(tmp_path: Path):
    """Build a tiny index in a temp dir and return (vectors, records)."""
    import pickle, json
    from data.models import WordRecord
    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    rng = np.random.default_rng(42)
    n = 10
    vecs = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
    # L2-normalise each row
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)

    records = [
        WordRecord(id=i, word=f"word{i}", sense=0, pos="n",
                   definition=f"def {i}", embed_text=f"word{i}: def {i}")
        for i in range(n)
    ]

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    np.save(cache_dir / "vectors.npy", vecs)
    with (cache_dir / "records.pkl").open("wb") as fh:
        pickle.dump(records, fh)
    with (cache_dir / "meta.json").open("w") as fh:
        json.dump({"model_id": MODEL_ID, "embedding_dim": EMBEDDING_DIM,
                   "count": n}, fh)

    return cache_dir, vecs, records


def test_index_build_and_load(tmp_path, monkeypatch):
    """build() writes cache; load() reads it back and validates MODEL_ID."""
    import index.engine as eng

    from data.models import WordRecord
    from embedding.embedder import MODEL_ID, EMBEDDING_DIM

    rng = np.random.default_rng(0)
    n = 5
    vecs = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    records = [
        WordRecord(id=i, word=f"w{i}", sense=0, pos="n",
                   definition=f"d{i}", embed_text=f"w{i}: d{i}")
        for i in range(n)
    ]

    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(eng, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(eng, "_VECTORS_PATH", cache_dir / "vectors.npy")
    monkeypatch.setattr(eng, "_RECORDS_PATH", cache_dir / "records.pkl")
    monkeypatch.setattr(eng, "_META_PATH", cache_dir / "meta.json")
    monkeypatch.setattr(eng, "_vectors", None)
    monkeypatch.setattr(eng, "_records", None)

    eng.build(vecs, records)
    assert (cache_dir / "vectors.npy").exists()
    assert (cache_dir / "records.pkl").exists()
    assert (cache_dir / "meta.json").exists()

    eng.load()
    assert eng._vectors is not None
    assert eng._records is not None
    assert len(eng._records) == n


def test_index_search_returns_sorted(tmp_path, monkeypatch):
    """search() returns results sorted by score descending."""
    import index.engine as eng
    from embedding.embedder import EMBEDDING_DIM

    cache_dir, vecs, records = _make_synthetic_index(tmp_path)
    monkeypatch.setattr(eng, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(eng, "_VECTORS_PATH", cache_dir / "vectors.npy")
    monkeypatch.setattr(eng, "_RECORDS_PATH", cache_dir / "records.pkl")
    monkeypatch.setattr(eng, "_META_PATH", cache_dir / "meta.json")
    monkeypatch.setattr(eng, "_vectors", None)
    monkeypatch.setattr(eng, "_records", None)

    eng.load()

    query_vec = vecs[0].copy()  # search for the first vector — should rank #1
    results = eng.search(query_vec, k=5)

    assert len(results) == 5
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by score desc"
    assert results[0].record.id == 0, "Exact match should be top result"
    assert abs(results[0].score - 1.0) < 1e-5, "Self-similarity should be ~1.0"


def test_index_model_mismatch_raises(tmp_path, monkeypatch):
    """load() must raise RuntimeError if the stored model_id doesn't match."""
    import json, pickle
    import index.engine as eng
    from embedding.embedder import EMBEDDING_DIM

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    vecs = np.ones((2, EMBEDDING_DIM), dtype=np.float32)
    np.save(cache_dir / "vectors.npy", vecs)
    with (cache_dir / "records.pkl").open("wb") as fh:
        pickle.dump([], fh)
    with (cache_dir / "meta.json").open("w") as fh:
        json.dump({"model_id": "WRONG-MODEL", "embedding_dim": EMBEDDING_DIM,
                   "count": 2}, fh)

    monkeypatch.setattr(eng, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(eng, "_VECTORS_PATH", cache_dir / "vectors.npy")
    monkeypatch.setattr(eng, "_RECORDS_PATH", cache_dir / "records.pkl")
    monkeypatch.setattr(eng, "_META_PATH", cache_dir / "meta.json")
    monkeypatch.setattr(eng, "_vectors", None)
    monkeypatch.setattr(eng, "_records", None)

    with pytest.raises(RuntimeError, match="model"):
        eng.load()


# ---------------------------------------------------------------------------
# Data layer — requires data/raw/corpus.jsonl (produced by fetch_corpus.py)
# ---------------------------------------------------------------------------

_CORPUS = Path(__file__).parent.parent / "data" / "raw" / "corpus.jsonl"


@pytest.mark.skipif(not _CORPUS.exists(), reason="corpus.jsonl not yet built")
def test_load_records_basic():
    from data.loader import load_records

    records = load_records()
    assert len(records) >= 1000, f"Expected at least 1000 records, got {len(records)}"

    # IDs must be 0..N-1 contiguous
    ids = [r.id for r in records]
    assert ids == list(range(len(records))), "Record IDs must be 0..N-1 contiguous"

    # every record has required fields
    for r in records[:10]:
        assert r.word and r.definition and r.embed_text
        assert r.embed_text.startswith(r.word + ":")
        assert r.sense == 0
        assert r.pos in ("n", "v", "a", "r")


@pytest.mark.skipif(not _CORPUS.exists(), reason="corpus.jsonl not yet built")
def test_load_records_contains_petrichor():
    from data.loader import load_records

    records = load_records()
    words = {r.word.lower() for r in records}
    assert "petrichor" in words, "petrichor must be in the corpus"
