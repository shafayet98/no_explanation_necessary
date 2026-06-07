# Skill: Debug a Failed Retrieval

Use when a query is not returning the expected word in the top 10.

## Diagnosis Steps

**Step 1 — Is the word in the index at all?**
Search `index/cache/records.pkl` (or query the data layer directly) for the expected word.
- If missing: the data layer is not loading it. Check `data/loader.py` filtering logic.
- If present: proceed to Step 2.

**Step 2 — How many senses are indexed?**
Count how many records exist for the word (Phase 3+: should be one per WordNet sense).
- If only one record exists but the word has multiple senses: sense-splitting is not working. Check `data/loader.py`.
- If records exist: check their `embed_text` values — are they meaningful definitions or empty/generic?

**Step 3 — What is the cosine similarity of the word to the query?**
```python
from embedding.embedder import embed
from index.engine import load, search
import pickle, numpy as np

load()
with open("index/cache/records.pkl", "rb") as f:
    records = pickle.load(f)

query_vec = embed(["<the failing query>"])[0]
word_records = [r for r in records if r.word == "<expected word>"]

for r in word_records:
    word_vec = embed([r.embed_text])[0]
    score = float(np.dot(query_vec, word_vec))
    print(f"sense {r.sense} ({r.pos}): {score:.4f} — {r.definition[:60]}")
```
- If score < 0.3: the word's definition doesn't semantically overlap with the query. The query may need rephrasing, or a better definition text.
- If score is reasonable (> 0.4) but word still doesn't appear in top 10: a large number of other words are scoring higher. Proceed to Step 4.

**Step 4 — What IS ranking above it?**
Run the query and inspect the top 20 results with scores. Look for patterns:
- Are results thematically related but too broad/generic? → Reranker may be needed (Phase 4).
- Are results from a completely different semantic domain? → The query embedding may be picking up the wrong aspect of the description.

**Step 5 — Is the understanding layer misrouting?**
If Phase 5 is complete, check which mode the classifier assigned:
```python
from understanding.classifier import classify
print(classify("<the failing query>"))
```
- If a single-concept query is being treated as multi-concept, the extracted sub-queries may not cover the intended word.

## Common Causes and Fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Word not in index | Data layer filtering | Check `load_records()` filtering |
| Word in index, score < 0.2 | Definition doesn't match query semantics | Add a richer definition or alternate sense |
| Word scores well but ranks low | Too many similar words outrank it | Enable reranker (Phase 4) |
| Word appears at rank 12–20 | Retrieval k too small | Increase `k` in `index.search()` call |
| Completely wrong domain results | Averaging problem on long query | Understanding layer needed (Phase 5) |

## After Debugging

If the failing query is not in `eval/test_cases.jsonl`, add it. Run `/add-test-case` with the query and expected word. This is how the eval set grows.
