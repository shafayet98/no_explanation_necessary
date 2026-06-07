"""One-time corpus fetch: wordfreq top-N ∪ curated eval targets → data/raw/corpus.jsonl.

Run once before building the index. Idempotent: does nothing if corpus.jsonl already
exists unless --force is passed.

  python scripts/fetch_corpus.py
  python scripts/fetch_corpus.py --force

Each line of corpus.jsonl:
  {"word": "...", "pos": "n|v|a|r", "definition": "..."}

Source: Free Dictionary API (Wiktionary-backed, CC BY-SA).
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import requests
from wordfreq import top_n_list

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CORPUS_PATH = Path(__file__).parent.parent / "data" / "raw" / "corpus.jsonl"
API_BASE = "https://api.dictionaryapi.dev/api/v2/entries/en"

FREQ_TOP_N = 5000       # top frequent words; union with curated gives ~3-5k
MAX_WORKERS = 20        # concurrent API requests
RETRY_DELAYS = [1, 3]   # seconds between retries on transient errors

# Curated words that must be in the corpus regardless of frequency rank.
# Listed FIRST so they are fetched immediately, not at the end.
CURATED_WORDS = [
    "petrichor",
    "saudade",
    "sonder",
    "defenestration",
    "ephemeral",
    "melancholy",
    "serendipity",
    "hiraeth",
    "schadenfreude",
    "wanderlust",
    "nostalgia",
    "catharsis",
    "euphoria",
    "solitude",
    "resilience",
    "empathy",
    "solipsism",
    "quixotic",
    "ineffable",
    "liminal",
    "lacuna",
    "vellichor",
    "chrysalism",
    "solivagant",
    "kenopsia",
    "onism",
    "liberosis",
    "exulansis",
    "occhiolism",
]

_POS_MAP = {
    "noun": "n",
    "verb": "v",
    "adjective": "a",
    "adverb": "r",
    "adjective satellite": "a",
    "proper noun": "n",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_pos(raw: str) -> str:
    return _POS_MAP.get(raw.lower(), "n")


def _fetch_entry(word: str, session: requests.Session) -> dict | None:
    """Return {"word", "pos", "definition"} or None if not found."""
    url = f"{API_BASE}/{word}"
    for delay in [0] + RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            resp = session.get(url, timeout=8)
        except requests.RequestException:
            continue
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            time.sleep(5)
            continue
        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except ValueError:
            continue
        for entry in data:
            for meaning in entry.get("meanings", []):
                for defn in meaning.get("definitions", []):
                    text = defn.get("definition", "").strip()
                    if text:
                        pos = _normalise_pos(meaning.get("partOfSpeech", ""))
                        return {"word": word, "pos": pos, "definition": text}
        return None
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if corpus.jsonl already exists.")
    args = parser.parse_args()

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Word list: curated words FIRST (ensures eval targets are always present),
    # then top-N frequency words. Deduped, lowercased, order-preserving.
    word_set: dict[str, None] = {}
    for w in CURATED_WORDS:
        word_set[w.lower()] = None
    for w in top_n_list("en", FREQ_TOP_N):
        word_set[w.lower()] = None
    words = list(word_set.keys())
    print(f"Word list: {len(words)} candidates ({len(CURATED_WORDS)} curated + {FREQ_TOP_N} freq, deduped)")

    # Resume support: load words already fetched and skip them.
    already: dict[str, dict] = {}
    if CORPUS_PATH.exists() and not args.force:
        with CORPUS_PATH.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    already[entry["word"].lower()] = entry
        if already:
            print(f"Resuming: {len(already)} words already in corpus, skipping them.")
    elif args.force and CORPUS_PATH.exists():
        CORPUS_PATH.unlink()
        print("Force flag set — re-fetching all words.")

    words_to_fetch = [w for w in words if w not in already]
    print(f"Fetching {len(words_to_fetch)} remaining words...")

    # Merge already-fetched entries into results dict
    results: dict[str, dict] = dict(already)
    lock = Lock()
    done = 0
    total = len(words_to_fetch)

    def fetch_and_store(word: str) -> None:
        nonlocal done
        session = requests.Session()
        session.headers["User-Agent"] = "reverse-dictionary-project/1.0 (educational)"
        entry = _fetch_entry(word, session)
        with lock:
            done += 1
            if entry:
                results[word] = entry
            if done % 200 == 0 or done == total:
                new_found = len(results) - len(already)
                print(f"  {done}/{total} ({done/total*100:.0f}%) — "
                      f"{new_found} new, {done-new_found} skipped", flush=True)

    if words_to_fetch:
        print(f"Fetching with {MAX_WORKERS} workers...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_and_store, w): w for w in words_to_fetch}
            for f in as_completed(futures):
                exc = f.exception()
                if exc:
                    print(f"  Warning: {futures[f]}: {exc}", file=sys.stderr)

    # Write in canonical word-list order (curated first, then freq)
    with CORPUS_PATH.open("w") as fh:
        for word in words:
            if word in results:
                fh.write(json.dumps(results[word]) + "\n")

    print(f"\nDone. {len(results)} words total in {CORPUS_PATH}.")


if __name__ == "__main__":
    main()
