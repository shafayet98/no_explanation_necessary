"""Understanding layer. The interface layer calls only query() — never embed(),
search(), or load_records() directly."""

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class QueryFilters:
    pos: str | None          # "n", "v", "a", "r" — restrict by part of speech
    starts_with: str | None  # restrict to words beginning with this letter
    max_length: int | None   # restrict to words of at most N characters


@dataclass
class RankedResult:
    word: str
    pos: str
    definition: str          # the specific sense definition that matched
    score: float
    is_interpretation: bool  # True for mood/passage results — never hide this


@dataclass
class ConceptGroup:
    label: str               # e.g. "the smell", "the feeling of release"
    results: list[RankedResult]


@dataclass
class QueryResponse:
    mode: Literal["single", "grouped", "mood"]
    groups: list[ConceptGroup]  # length 1 for single-concept queries


def _run_single_concept(clean_query: str, is_interpretation: bool) -> ConceptGroup:
    """Retrieve + rerank for one clean query. Returns a ConceptGroup."""
    import index.engine as engine
    from embedding.embedder import embed
    from understanding.reranker import rerank

    engine.load()
    query_vec = embed([clean_query])[0]
    candidates = engine.search(query_vec, k=50)
    reranked = rerank(candidates, clean_query)
    top10 = reranked[:10]

    results = [
        RankedResult(
            word=sr.record.word,
            pos=sr.record.pos,
            definition=sr.record.definition,
            score=sr.score,
            is_interpretation=is_interpretation,
        )
        for sr in top10
    ]
    return ConceptGroup(label=clean_query, results=results)


def query(user_input: str, filters: QueryFilters | None = None) -> QueryResponse:
    """The one entry point into the understanding layer.

    Phase 5: classifies input as single-concept or multi-concept.
    - Single-concept: retrieve top 50 via vector search, rerank, return top 10.
    - Multi-concept: LLM decomposes into 2–4 sub-queries, each run through the
      single-concept path, returned as grouped results with is_interpretation=True.
      Falls back to single-concept if the decomposer is unavailable (no API key).
    """
    from understanding.classifier import classify

    input_type = classify(user_input)

    if input_type == "single":
        group = _run_single_concept(user_input, is_interpretation=False)
        group.label = user_input
        return QueryResponse(mode="single", groups=[group])

    # Multi-concept path
    try:
        from understanding.decomposer import decompose
        concepts = decompose(user_input)
    except RuntimeError as e:
        # API key not set — degrade gracefully to single-concept
        logger.warning("Decomposer unavailable (%s). Falling back to single-concept mode.", e)
        group = _run_single_concept(user_input, is_interpretation=False)
        group.label = user_input
        return QueryResponse(mode="single", groups=[group])

    groups = []
    for label, clean_query in concepts:
        group = _run_single_concept(clean_query, is_interpretation=True)
        group.label = label
        groups.append(group)

    return QueryResponse(mode="grouped", groups=groups)
