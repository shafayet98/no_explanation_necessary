"""Understanding layer — reranking (Phase 4).

Takes the broad shortlist from index.search() and reorders it precisely with a
stronger model (cross-encoder or LLM). The single biggest quality lever in the
project. Internal to the understanding layer; callers go through query.query().
"""


def rerank(candidates: list, query_text: str) -> list:
    """Reorder retrieval candidates by precise relevance to query_text. Stub."""
    raise NotImplementedError("reranker not implemented yet (skeleton)")
