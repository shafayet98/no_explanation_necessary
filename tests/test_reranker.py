"""Unit/integration tests for understanding.reranker (Phase 4)."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _make_result(word: str, definition: str, pos: str = "n", score: float = 0.5):
    """Build a SearchResult with a minimal WordRecord — no index needed."""
    from data.models import WordRecord
    from index.engine import SearchResult

    record = WordRecord(
        id=0,
        word=word,
        sense=0,
        pos=pos,
        definition=definition,
        embed_text=f"{word}: {definition}",
    )
    return SearchResult(record=record, score=score)


def test_rerank_empty_input_returns_empty():
    from understanding.reranker import rerank

    assert rerank([], "any query") == []


def test_rerank_preserves_all_candidates():
    from understanding.reranker import rerank

    candidates = [
        _make_result("petrichor", "the smell of rain on dry earth"),
        _make_result("ozone", "a pungent gas with a sharp smell"),
        _make_result("rain", "water falling from clouds"),
    ]
    result = rerank(candidates, "earthy smell after rainfall")
    assert len(result) == len(candidates), (
        f"rerank dropped candidates: got {len(result)}, expected {len(candidates)}"
    )
    result_words = {r.record.word for r in result}
    assert result_words == {"petrichor", "ozone", "rain"}


def test_rerank_changes_order():
    """Cross-encoder should prefer petrichor over ozone for a rain-smell query.

    Bi-encoder scores are deliberately equal so the cross-encoder is the sole
    signal that changes the order. With the blended scorer (BI_WEIGHT * bi +
    (1 - BI_WEIGHT) * cross), equal bi scores normalise to the same value, leaving
    only the cross-encoder difference to determine rank.
    """
    from understanding.reranker import rerank

    # All bi-encoder scores identical — cross-encoder is the only differentiator
    candidates = [
        _make_result("ozone", "a gas with a sharp chemical smell", score=0.5),
        _make_result("aroma", "a pleasant but unspecific smell", score=0.5),
        _make_result("petrichor", "the distinctive scent of rain on dry earth", score=0.5),
    ]
    reranked = rerank(candidates, "the smell of rain on dry earth")
    top_word = reranked[0].record.word
    assert top_word == "petrichor", (
        f"Expected petrichor at rank 1 after reranking, got '{top_word}'"
    )
