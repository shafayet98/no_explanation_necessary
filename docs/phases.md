Phase 0 — Project skeleton & decisions
Goal: A repo you can run, with the layer boundaries stubbed out.

Set up project structure (folders per layer), virtual environment, dependency file.
Lock the foundational decisions:

Word source: WordNet (free, sense-split, POS-tagged, definitions included).
Embedding model: local sentence-transformers / all-MiniLM-L6-v2 to start (384-dim, fast, free).
Index: in-memory numpy brute force to start.


Write empty module stubs with the function signatures each layer exposes. Nothing implemented yet — just the seams.

Done when: python -m project runs and prints "skeleton alive" through all five stubbed layers.

Phase 1 — The thin vertical slice
Goal: A working reverse dictionary end to end, ugly but real.

Data layer (minimal): Load ~3,000–5,000 common words from WordNet with their definitions. One vector per word for now (sense-splitting comes later). Keep a parallel list mapping row index → (word, definition).
Embedding layer: Thin wrapper: embed(texts) -> vectors. Embed word + ": " + definition for each entry. Cache the resulting matrix to disk so you don't re-embed every run.
Index layer: Hold vectors in a numpy array. search(query_vector, k) -> [(row_index, score)] via cosine similarity against all rows, sorted descending.
Query path: embed(query) → index.search → map rows back to words → print top 10.

Done when: You type "the smell of rain on dry earth" in the terminal and petrichor appears in the top 10.

Phase 2 — Evaluation harness (do NOT skip)
Goal: Turn quality from a vibe into a number. This is what separates "feels okay" from "actually good."

Hand-write a test set: 150–300 (description → expected word) pairs. Cover easy ones (synonyms), medium (definitions in your own words), and hard (evocative/poetic descriptions). This is tedious and it is the highest-leverage work in the project.
Implement two metrics:

Recall@10 — fraction of test cases where the expected word is in the top 10.
MRR (Mean Reciprocal Rank) — rewards ranking the right word higher (1/rank, averaged).


Build a one-command eval run that prints both numbers.
Record the Phase 1 baseline. Every later change is judged against it.

Done when: python eval.py prints recall@10 and MRR for your current system.

Phase 3 — Index quality: sense-splitting
Goal: Fix the multi-sense blur ("bank" = river edge vs. money place).

Re-do the data layer to emit one record per (word, sense, POS, definition) triple instead of one per word. WordNet gives you this for free.
Embed each sense separately → more, sharper points in space.
Dedupe at the result stage: if multiple senses of the same word rank, collapse to one result (keep the best-scoring sense, optionally show which sense matched).
Re-run eval. Expect recall and MRR to climb.

Done when: Eval numbers beat the Phase 1 baseline, and multi-sense words retrieve correctly for each sense.

Phase 4 — Two-stage retrieve-then-rerank
Goal: The single biggest quality lever. Embeddings retrieve broadly; a smarter model orders the final list.

Retrieve: vector search pulls top ~50 candidates (recall-focused, cheap).
Rerank: score those 50 against the query with something more precise:

Option A — a cross-encoder reranker model (reads query + candidate together, far more accurate than cosine).
Option B — an LLM scoring/ordering the shortlist.


Return the reranked top 10.
Re-run eval after each option; keep whichever wins on MRR.

Done when: MRR improves meaningfully over Phase 3 and the top-3 results are noticeably more relevant by eye.

Phase 5 — The understanding layer (handle messy input)
Goal: Route around the averaging problem. Make poetic paragraphs work instead of returning mush.

Classify input: single word-hunt vs. multi-concept passage vs. mood. (Length/sentence heuristics first; LLM classifier if needed.)
Single concept → straight to retrieve+rerank.
Multi-concept passage → LLM extracts 2–3 distinct concepts, run each as its own clean query, return grouped results ("for the smell → petrichor; for the feeling → catharsis; for the mood → saudade").
Honest framing: label mood-interpretations as interpretations, never return a single word with false confidence.
Add the relevant test cases (long passages) to the eval set and confirm they now produce sensible grouped output.

Done when: The long rainy-paragraph input returns useful grouped concepts instead of one averaged guess.

Phase 6 — Filters & query refinement
Goal: Let users constrain the hunt the way real tip-of-the-tongue searches work.

Filter by part of speech ("it's a noun").
Filter by starting letter / word length ("starts with P, about 9 letters").
"Feeling lucky" mode — one bold single guess.
Multi-word phrase handling.
These mostly operate on candidate metadata you already carry — cheap to add, high perceived value.

Done when: Filters demonstrably narrow results and the eval set (with filter-constrained cases) still passes.

Phase 7 — Scale the index (only if/when needed)
Goal: Stay fast as the word list grows to the full WordNet (100k+ senses).

Swap the numpy brute-force index for FAISS behind the same search() interface — ideally zero changes above the index layer.
Confirm eval numbers are unchanged (FAISS is approximate; verify recall didn't regress) and query latency dropped.

Done when: Full word list searches in well under a second and eval recall holds.

Phase 8 — Interface
Goal: Make it delightful. Thin layer, all intelligence already lives below.

Clean web UI: single input box, keyboard-first, instant results, definition-on-hover, copy button.
Show why a word matched (the sense/definition that scored).
Grouped display for multi-concept results from Phase 5.
API endpoint so the UI (and future browser extension) are just clients.

Done when: A first-time user can describe a word and get the answer without instructions.

Stretch goals (each is a self-contained project)

Crossword-clue mode — solve clues with a length/pattern constraint.
Rhyming filter — "means X, rhymes with Y."
Obscurity slider — "more common ↔ more obscure" reranking by word frequency.
Browser extension — double-click any selection → reverse-lookup.
Model A/B harness — because the embedding layer is swappable, systematically compare models on your eval set.


The discipline that keeps it solid

Every layer behind a narrow interface. If a change forces edits in three places, the seam is wrong.
Never ship a change you didn't eval. Number goes up = keep. Number goes down = revert.
Build the slice before the features. A working ugly thing beats a half-built elegant one.
The eval set is the product. Grow it whenever you find a query that fails — that failure becomes a permanent test.
