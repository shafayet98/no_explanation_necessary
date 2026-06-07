"""One-shot indexing script: load -> embed -> build -> save.

INVARIANT (see .claude/rules/build-discipline.md #4): this script MUST check for a
valid cached index before embedding. If index/cache/ exists and the stored
MODEL_ID matches embedding.MODEL_ID, load it and exit. Re-embedding the full
dictionary on every run is a bug, not a feature.

Indexing path (to implement):
    1. Check cache: if vectors.npy exists and meta.json MODEL_ID == embedding.MODEL_ID -> done.
    2. records = data.loader.load_records()
    3. vectors = embedding.embedder.embed([r.embed_text for r in records])
    4. index.engine.build(vectors, records)   # writes cache/vectors.npy, records.pkl, meta.json
"""


def main() -> None:
    raise NotImplementedError("build_index not implemented yet (skeleton)")


if __name__ == "__main__":
    main()
