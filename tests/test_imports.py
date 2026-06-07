"""Skeleton smoke test: every layer module imports and exposes its contract.

This is the Phase 0 "done when": all seams import cleanly. It deliberately does
NOT call any stub (they raise NotImplementedError by design).
"""


def test_data_layer_imports():
    from data.models import WordRecord
    from data.loader import load_records

    assert WordRecord.__dataclass_fields__.keys() >= {
        "id", "word", "sense", "pos", "definition", "embed_text"
    }
    assert callable(load_records)


def test_embedding_layer_imports():
    from embedding.embedder import embed, MODEL_ID, EMBEDDING_DIM

    assert callable(embed)
    assert isinstance(MODEL_ID, str)
    assert EMBEDDING_DIM == 384


def test_index_layer_imports():
    from index.engine import build, load, search, SearchResult

    assert callable(build) and callable(load) and callable(search)
    assert SearchResult.__dataclass_fields__.keys() >= {"record", "score"}


def test_understanding_layer_imports():
    from understanding.query import (
        query, QueryResponse, ConceptGroup, RankedResult, QueryFilters,
    )

    assert callable(query)
    for dc in (QueryResponse, ConceptGroup, RankedResult, QueryFilters):
        assert hasattr(dc, "__dataclass_fields__")


def test_interface_layer_imports():
    from interface.api import app

    assert app is not None
