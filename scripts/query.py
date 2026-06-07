"""Terminal query runner — Phase 1 thin interface.

Usage (single query):
    python scripts/query.py "the smell of rain on dry earth"

Usage (interactive REPL loop):
    python scripts/query.py

Loads the index once, then embeds the query and prints the top 10 results.
No business logic here — routing and reranking arrive in later phases.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))


def _print_results(results, query: str) -> None:
    print(f'\nQuery: "{query}"')
    print("-" * 60)
    for rank, r in enumerate(results, 1):
        print(f"  {rank:2}. {r.record.word:<20} [{r.record.pos}]  score={r.score:.4f}")
        # wrap definition at 70 chars for readability
        defn = r.record.definition
        if len(defn) > 70:
            defn = defn[:67] + "..."
        print(f"      {defn}")
    print()


def main() -> None:
    print("Loading index...", flush=True)
    from index.engine import load, search
    load()

    from embedding.embedder import embed

    args = sys.argv[1:]
    if args:
        query = " ".join(args)
        vec = embed([query])[0]
        results = search(vec, k=10)
        _print_results(results, query)
    else:
        print("Reverse Dictionary — enter a description to find the word.")
        print("(Ctrl-C or empty line to quit)\n")
        while True:
            try:
                query = input("Description: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not query:
                break
            vec = embed([query])[0]
            results = search(vec, k=10)
            _print_results(results, query)


if __name__ == "__main__":
    main()
