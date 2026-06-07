"""Understanding layer — input classification (Phase 5).

Decides whether user input is a single clean concept (route straight to
retrieve+rerank) or a multi-concept passage (decompose into clean sub-queries).
Internal to the understanding layer; callers go through query.query().
"""


def classify(user_input: str) -> str:
    """Return the input type, e.g. "single" or "multi". Stub for now."""
    raise NotImplementedError("classifier not implemented yet (skeleton)")
