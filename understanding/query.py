"""Understanding layer. The interface layer calls only query() — never embed(),
search(), or load_records() directly."""

import logging
import re
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


def _normalize_input(text: str) -> str:
    """Strip outer whitespace/punctuation and collapse internal whitespace.

    Handles multi-word phrase inputs like '  silver lining. ' → 'silver lining'
    so stray punctuation and spaces don't bleed into the embedding.
    """
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip('.,!?')
    return text.strip()


def _passes_filter(record, filters: QueryFilters) -> bool:
    """Return True if record satisfies all active filter conditions."""
    if filters.pos is not None and record.pos != filters.pos:
        return False
    if filters.starts_with is not None and not record.word.lower().startswith(filters.starts_with.lower()):
        return False
    if filters.max_length is not None and len(record.word) > filters.max_length:
        return False
    return True


def _run_single_concept(
    clean_query: str,
    is_interpretation: bool,
    filters: QueryFilters | None = None,
) -> ConceptGroup:
    """Retrieve + rerank for one clean query. Returns a ConceptGroup.

    When filters are active, oversamples to k=100 to compensate for attrition.
    Results that survive the filter are returned (may be fewer than 10).
    """
    import index.engine as engine
    from embedding.embedder import embed
    from understanding.reranker import rerank

    engine.load()
    query_vec = embed([clean_query])[0]

    k = 100 if filters is not None else 50
    candidates = engine.search(query_vec, k=k)
    reranked = rerank(candidates, clean_query)

    if filters is not None:
        reranked = [sr for sr in reranked if _passes_filter(sr.record, filters)]

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


def query(
    user_input: str,
    filters: QueryFilters | None = None,
    lucky: bool = False,
) -> QueryResponse:
    """The one entry point into the understanding layer.

    Phase 5: classifies input as single-concept or multi-concept.
    Phase 6: applies QueryFilters (pos, starts_with, max_length) to all results.
             lucky=True truncates each group to the single top result.

    - Single-concept: retrieve top 50 (100 with filters) via vector search,
      rerank, apply filters, return top 10.
    - Multi-concept: LLM decomposes into 2–4 sub-queries, each run through the
      single-concept path, returned as grouped results with is_interpretation=True.
      Falls back to single-concept if the decomposer is unavailable (no API key).
    """
    from understanding.classifier import classify

    user_input = _normalize_input(user_input)
    if not user_input:
        return QueryResponse(mode="single", groups=[ConceptGroup(label="", results=[])])

    input_type = classify(user_input)

    if input_type == "single":
        group = _run_single_concept(user_input, is_interpretation=False, filters=filters)
        group.label = user_input
        groups = [group]
        response = QueryResponse(mode="single", groups=groups)
    else:
        # Multi-concept path
        try:
            from understanding.decomposer import decompose
            concepts = decompose(user_input)
        except RuntimeError as e:
            logger.warning("Decomposer unavailable (%s). Falling back to single-concept mode.", e)
            group = _run_single_concept(user_input, is_interpretation=False, filters=filters)
            group.label = user_input
            response = QueryResponse(mode="single", groups=[group])
        else:
            groups = []
            for label, clean_query in concepts:
                group = _run_single_concept(clean_query, is_interpretation=True, filters=filters)
                group.label = label
                groups.append(group)
            response = QueryResponse(mode="grouped", groups=groups)

    if lucky:
        for group in response.groups:
            group.results = group.results[:1]

    return response
