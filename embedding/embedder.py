"""Embedding layer. ONE public function: embed().

Swapping the model means changing the implementation of embed() and the values
of MODEL_ID and EMBEDDING_DIM. Nothing else in the system changes.
"""

import numpy as np

MODEL_ID: str = "all-MiniLM-L6-v2"   # stored with the index; checked on load
EMBEDDING_DIM: int = 384             # MiniLM output dimensionality


def embed(texts: list[str]) -> np.ndarray:
    """Embed texts into L2-normalised vectors.

    Returns shape (len(texts), EMBEDDING_DIM). Normalised so cosine similarity
    equals the dot product. This is the entire public interface of this layer.
    """
    raise NotImplementedError("embedding layer not implemented yet (skeleton)")
