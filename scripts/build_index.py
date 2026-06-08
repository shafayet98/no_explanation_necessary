"""One-shot indexing script: load → embed → build → save.

INVARIANT (see .claude/rules/build-discipline.md #4): this script MUST check for a
valid cached index before embedding. If index/cache/ exists and the stored
MODEL_ID matches embedding.MODEL_ID, load it and exit. Re-embedding the full
dictionary on every run is a bug, not a feature.

Usage:
    python scripts/build_index.py           # build index (skips if cache is valid)
    python scripts/build_index.py --force   # delete cache and rebuild
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

_CACHE_DIR = Path(__file__).parent.parent / "index" / "cache"
_META_PATH = _CACHE_DIR / "meta.json"
_FAISS_PATH = _CACHE_DIR / "index.faiss"


def _cache_is_valid(model_id: str) -> bool:
    """Return True if a valid index cache exists for the given model_id."""
    if not _FAISS_PATH.exists() or not _META_PATH.exists():
        return False
    try:
        with _META_PATH.open() as fh:
            meta = json.load(fh)
        return meta.get("model_id") == model_id
    except (json.JSONDecodeError, KeyError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Delete existing cache and rebuild from scratch.")
    args = parser.parse_args()

    from embedding.embedder import MODEL_ID

    if args.force:
        import shutil
        if _CACHE_DIR.exists():
            shutil.rmtree(_CACHE_DIR)
        print("Cache cleared.")

    if _cache_is_valid(MODEL_ID):
        with _META_PATH.open() as fh:
            meta = json.load(fh)
        print(
            f"Cache hit: index/{_CACHE_DIR.name}/ already exists "
            f"(model={meta['model_id']}, {meta['count']} records). Nothing to do."
        )
        return

    print("No valid cache found — building index.")
    t0 = time.time()

    print("  Loading records...", flush=True)
    from data.loader import load_records
    records = load_records()
    print(f"  {len(records)} records loaded.")

    print(f"  Embedding with {MODEL_ID}...", flush=True)
    from embedding.embedder import embed
    texts = [r.embed_text for r in records]
    vectors = embed(texts)
    print(f"  Embedded {vectors.shape[0]} vectors, dim={vectors.shape[1]}.")

    print("  Persisting index to disk...", flush=True)
    from index.engine import build
    build(vectors, records)

    elapsed = time.time() - t0
    print(f"Done. Index built in {elapsed:.1f}s → {_CACHE_DIR}/")


if __name__ == "__main__":
    main()
