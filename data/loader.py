"""Data layer loader. The single entry point that produces WordRecords."""

import json
from pathlib import Path

from data.models import WordRecord

_CORPUS_PATH = Path(__file__).parent / "raw" / "corpus.jsonl"


def load_records() -> list[WordRecord]:
    """Load the dictionary as WordRecords from the cached corpus file.

    Phase 3+: one record per (word, sense, pos, definition). Handles the legacy
    Phase 1 single-definition format transparently. The corpus is produced once
    by scripts/fetch_corpus.py; this function is purely offline/deterministic.

    Raises FileNotFoundError if data/raw/corpus.jsonl does not exist — run
    scripts/fetch_corpus.py first.
    """
    if not _CORPUS_PATH.exists():
        raise FileNotFoundError(
            f"Corpus not found at {_CORPUS_PATH}. "
            "Run `python scripts/fetch_corpus.py` first."
        )

    records: list[WordRecord] = []
    global_id = 0
    with _CORPUS_PATH.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            word = entry["word"]
            if "senses" in entry:
                # Phase 3+ format: one record per sense
                for sense_dict in entry["senses"]:
                    records.append(WordRecord(
                        id=global_id,
                        word=word,
                        sense=sense_dict["sense"],
                        pos=sense_dict["pos"],
                        definition=sense_dict["definition"],
                        embed_text=f"{word}: {sense_dict['definition']}",
                    ))
                    global_id += 1
            else:
                # Phase 1 legacy format: single definition per word
                records.append(WordRecord(
                    id=global_id,
                    word=word,
                    sense=0,
                    pos=entry.get("pos", "n"),
                    definition=entry["definition"],
                    embed_text=f"{word}: {entry['definition']}",
                ))
                global_id += 1
    return records
