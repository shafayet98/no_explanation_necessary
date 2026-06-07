"""Data layer loader. The single entry point that produces WordRecords."""

import json
from pathlib import Path

from data.models import WordRecord

_CORPUS_PATH = Path(__file__).parent / "raw" / "corpus.jsonl"


def load_records() -> list[WordRecord]:
    """Load the dictionary as WordRecords from the cached corpus file.

    Phase 1: one record per word (sense=0). Phase 3+ will emit one record per
    (word, sense, pos, definition). The corpus is produced once by
    scripts/fetch_corpus.py; this function is purely offline/deterministic.

    Raises FileNotFoundError if data/raw/corpus.jsonl does not exist — run
    scripts/fetch_corpus.py first.
    """
    if not _CORPUS_PATH.exists():
        raise FileNotFoundError(
            f"Corpus not found at {_CORPUS_PATH}. "
            "Run `python scripts/fetch_corpus.py` first."
        )

    records: list[WordRecord] = []
    with _CORPUS_PATH.open() as fh:
        for idx, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            word = entry["word"]
            pos = entry.get("pos", "n")
            definition = entry["definition"]
            records.append(WordRecord(
                id=idx,
                word=word,
                sense=0,
                pos=pos,
                definition=definition,
                embed_text=f"{word}: {definition}",
            ))
    return records
