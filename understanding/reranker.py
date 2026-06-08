"""Understanding layer — reranking (Phase 4).

Takes the broad shortlist from index.search() and reorders it precisely with a
cross-encoder blended with the bi-encoder score. Internal to the understanding
layer; callers go through query.query().

Score blending rationale: ms-marco is a retrieval model that excels at literal
relevance (easy/paraphrase queries) but can override the bi-encoder's semantic
judgment on evocative/poetic queries where definitions don't literally echo the
query. Min-max normalising both scores and blending them preserves cross-encoder
precision wins on easy cases while preventing it from pushing correct answers out
of the top-10 on hard cases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from index.engine import SearchResult

_model = None

# Blend weight for the bi-encoder score (1 - BI_WEIGHT goes to cross-encoder).
BI_WEIGHT = 0.5


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def _minmax(arr: np.ndarray) -> np.ndarray:
    mn, mx = arr.min(), arr.max()
    return (arr - mn) / (mx - mn) if mx > mn else np.zeros_like(arr)


def rerank(candidates: list[SearchResult], query_text: str) -> list[SearchResult]:
    """Reorder candidates by a blend of cross-encoder and bi-encoder scores.

    Both scores are min-max normalised to [0, 1] within the batch before blending,
    so neither scale dominates. Returns the full list sorted descending — no
    truncation; caller decides how many to keep.
    """
    if not candidates:
        return []

    model = _get_model()
    pairs = [(query_text, sr.record.embed_text) for sr in candidates]
    cross_raw = np.array(model.predict(pairs), dtype=float)
    bi_raw = np.array([sr.score for sr in candidates], dtype=float)

    cross_norm = _minmax(cross_raw)
    bi_norm = _minmax(bi_raw)

    final_scores = BI_WEIGHT * bi_norm + (1.0 - BI_WEIGHT) * cross_norm

    ranked = sorted(zip(final_scores, candidates), key=lambda x: x[0], reverse=True)
    return [sr for _, sr in ranked]
