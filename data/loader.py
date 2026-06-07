"""Data layer loader. The single entry point that produces WordRecords."""

from data.models import WordRecord


def load_records() -> list[WordRecord]:
    """Load the dictionary as WordRecords.

    Phase 1: ~3-5k common WordNet words, one record per word.
    Phase 3+: one record per (word, sense, pos, definition).
    """
    raise NotImplementedError("data layer not implemented yet (skeleton)")
