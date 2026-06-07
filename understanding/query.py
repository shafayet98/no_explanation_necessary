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

    Classifies the input, routes single concepts straight to retrieve+rerank and
    multi-concept passages through decomposition, and returns grouped results.
    """
    raise NotImplementedError("understanding layer not implemented yet (skeleton)")
