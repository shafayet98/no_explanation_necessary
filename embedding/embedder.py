"""Embedding layer. ONE public function: embed().

Swapping the model means changing the implementation of embed() and the values
of MODEL_ID and EMBEDDING_DIM. Nothing else in the system changes.
"""

from __future__ import annotations

import numpy as np

MODEL_ID: str = "all-MiniLM-L6-v2"
EMBEDDING_DIM: int = 384

_model = None  # lazy singleton — loaded on first call to embed()


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_ID)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Embed texts into L2-normalised vectors.

    Returns shape (len(texts), EMBEDDING_DIM), dtype float32. Vectors are
    L2-normalised so cosine similarity equals the dot product — a requirement
    for the index layer's search implementation.
    """
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.astype(np.float32)
