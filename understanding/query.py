"""Understanding layer. The interface layer calls only query() — never embed(),
search(), or load_records() directly."""

from dataclasses import dataclass
from typing import Literal


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


def query(user_input: str, filters: QueryFilters | None = None) -> QueryResponse:
    """The one entry point into the understanding layer.

    Phase 4: single-concept path — retrieve top 50 via vector search,
    rerank with a cross-encoder, return top 10.
    Multi-concept routing and classifier arrive in Phase 5.
    """
    import index.engine as engine
    from embedding.embedder import embed
    from understanding.reranker import rerank

    engine.load()

    query_vec = embed([user_input])[0]
    candidates = engine.search(query_vec, k=50)
    reranked = rerank(candidates, user_input)
    top10 = reranked[:10]

    results = [
        RankedResult(
            word=sr.record.word,
            pos=sr.record.pos,
            definition=sr.record.definition,
            score=sr.score,
            is_interpretation=False,
        )
        for sr in top10
    ]

    return QueryResponse(
        mode="single",
        groups=[ConceptGroup(label=user_input, results=results)],
    )
