"""Data layer models. Nothing outside the data layer constructs WordRecord
directly — records always come from data.loader.load_records()."""

from dataclasses import dataclass


@dataclass
class WordRecord:
    """One row of the dictionary, one per word sense (Phase 3+).

    Fields are the seam shared with the index and understanding layers; do not
    change them without updating docs/architecture.md and all callers.
    """

    id: int           # stable row index into the vector matrix
    word: str         # e.g. "bank"
    sense: int        # WordNet sense number (0 in Phase 1, real in Phase 3+)
    pos: str          # part of speech: "n", "v", "a", "r"
    definition: str   # the sense definition
    embed_text: str   # text sent to the embedder, e.g. "bank: a financial institution..."
