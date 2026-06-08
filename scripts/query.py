"""Terminal query runner — routes through the full understanding layer pipeline.

Usage (single query):
    python scripts/query.py "the smell of rain on dry earth"

Usage (interactive REPL loop):
    python scripts/query.py

Loads the model once, then routes each query through understanding.query.query()
— embedding, vector search, cross-encoder reranking — and prints the top 10.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def _print_response(response, query: str) -> None:
    from understanding.query import QueryResponse

    print(f'\nQuery: "{query}"')
    print("-" * 60)
    for group in response.groups:
        results = group.results
        for rank, r in enumerate(results, 1):
            print(f"  {rank:2}. {r.word:<20} [{r.pos}]  score={r.score:.4f}")
            defn = r.definition
            if len(defn) > 70:
                defn = defn[:67] + "..."
            print(f"      {defn}")
    print()


def main() -> None:
    print("Loading models...", flush=True)
    from understanding.query import query

    args = sys.argv[1:]
    if args:
        user_input = " ".join(args)
        response = query(user_input)
        _print_response(response, user_input)
    else:
        print("Reverse Dictionary — enter a description to find the word.")
        print("(Ctrl-C or empty line to quit)\n")
        while True:
            try:
                user_input = input("Description: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not user_input:
                break
            response = query(user_input)
            _print_response(response, user_input)


if __name__ == "__main__":
    main()
