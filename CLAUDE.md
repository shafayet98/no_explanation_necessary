Project: Reverse Dictionary
A semantic search tool that inverts a normal dictionary. Instead of looking up a word to get its meaning, the user describes a meaning and gets the word. Example: the user types "the smell of rain on dry earth" and the system returns "petrichor".
This file is the source of truth for what we are building and how. Read it fully before writing code. When in doubt, follow the build discipline at the bottom over any instinct to add features quickly.
The Core Idea
Meaning can be turned into numbers (vectors), and similar meanings produce similar numbers. The whole system rests on this. We embed every word in a dictionary into a vector once, ahead of time. When a user submits a query, we embed the query with the same model and find the dictionary vectors closest to it. The closest words are the answers.
Two phases:

Indexing (done once, offline): embed every word + definition into vectors and store them in a searchable index.
Querying (done per request): embed the user's text, compare against the index, return the nearest words.

The query and the index MUST use the same embedding model, or the comparison is meaningless.
Closeness is measured with cosine similarity (the angle between vectors). Higher = more similar in meaning.
The Hard Problems (read these — they shape the architecture)

The averaging problem. Embedding compresses text into a single vector. The longer and more multi-concept the input, the muddier that vector becomes, and the more generic the results. A short clean query like "feeling of nostalgia for something that never happened" works great. A full poetic paragraph describing a whole scene does not — it smears many concepts into one point and returns mush. We do not fight this head-on; we route around it in the understanding layer by detecting messy input and breaking it into separate clean queries.
Multi-sense words. Many words have several meanings ("bank" = river edge or money place). Embedding all senses into one vector makes the word fuzzy and hard to retrieve for any single sense. We embed each sense separately (one vector per word+sense+definition) and dedupe at the result stage.
Retrieve vs. rerank. Vector search is fast but only approximately orders results. The professional pattern is two-stage: retrieve a broad shortlist (~50 candidates) cheaply with vector search, then rerank that shortlist precisely with a stronger model (a cross-encoder or an LLM). This is the single biggest quality lever in the project.
Evaluation. We cannot improve what we cannot measure. We maintain a test set of (description -> expected word) pairs and measure recall@10 and MRR. Every change is judged against the baseline number. This is non-negotiable and it is what separates "feels okay" from "actually good".

Architecture
See docs/architecture.md.

Tech Stack
Backend: Python. The data, embedding, index, and understanding layers are all Python. Expose the system through a Python web API (FastAPI preferred for async + automatic schema, but confirm before assuming). Cache embeddings to disk so we never re-embed the full dictionary on every run.
Frontend: React (JavaScript), HTML, Tailwind CSS. Single clean input box, keyboard-first, instant results. Show each result word with the sense/definition that matched and a copy button. Render grouped results when the understanding layer returns multiple concepts. The frontend is a pure client of the backend API — no business logic in it.
Cloud: AWS. Infrastructure as Code with Terraform — all infra defined in Terraform, no click-ops in the console. Keep the Terraform modular and environment-separated (dev/prod). Confirm the specific AWS services before building (likely candidates: compute for the API, object storage for the cached embedding index, a CDN/static host for the React frontend), but do not assume a design — propose it and confirm first.
Build Order (phases, not deadlines)
Build a thin working slice first, build the thing that measures it, then improve against the measurement. Do not build all five layers at once.
Phase 0 — Skeleton. Repo structure with a folder per layer, virtual environment, dependency file, empty module stubs with the function signatures each layer exposes. Nothing implemented — just the seams. Set up the Terraform project structure too (empty/stubbed).
Phase 1 — Thin vertical slice. Load ~3000-5000 common WordNet words with definitions (one vector per word for now). Embedding wrapper with a local sentence-transformers model (all-MiniLM-L6-v2 — 384-dim, fast, free). In-memory numpy index with cosine similarity. Query path: embed -> search -> print top 10 in the terminal. Done when "the smell of rain on dry earth" returns "petrichor" in the top 10.
Phase 2 — Evaluation harness. Hand-write 150-300 (description -> expected word) test pairs across easy/medium/hard. Implement recall@10 and MRR. One-command eval run. Record the Phase 1 baseline. DO NOT SKIP THIS.
Phase 3 — Sense-splitting. Re-do the data layer to emit one record per (word, sense, POS, definition). Embed each sense separately. Dedupe at the result stage. Re-run eval — expect improvement over baseline.
Phase 4 — Retrieve-then-rerank. Retrieve top ~50 with vector search, rerank with a cross-encoder or LLM, return reranked top 10. Re-run eval, keep whichever reranker wins on MRR.
Phase 5 — Understanding layer. Classify input. Single concept -> straight to retrieve+rerank. Multi-concept passage -> LLM extracts 2-3 concepts, run each as a clean query, return grouped results. Always frame mood-interpretations honestly — never return one word with false confidence for a passage that has no single answer. Add long-passage test cases to the eval set.
Phase 6 — Filters. Filter by part of speech, starting letter, word length. "Feeling lucky" single-guess mode. Multi-word phrase handling.
Phase 7 — Scale the index. Swap numpy for FAISS behind the same search() interface, ideally with zero changes above the index layer. Verify eval recall holds and latency drops.
Phase 8 — Local interface. Build the FastAPI endpoint (POST /query, GET /health) and the React/Tailwind frontend. Run everything locally. Done when the full query flow works end-to-end in a browser: type a description, get grouped results, copy a word.
Phase 9 — AWS cloud deploy. Deploy the backend API and frontend to AWS via Terraform. All infra defined as code, no click-ops. Confirm the AWS architecture design before writing any Terraform. Frontend is served from a CDN/static host; API runs on managed compute; FAISS index loaded from object storage.
Build Discipline (follow this over speed)

Every layer behind a narrow interface. If a change forces edits in three places, the seam is wrong — stop and fix the seam.
Never ship a change you did not eval. Number goes up = keep. Number goes down = revert. After Phase 2 exists, this applies to every quality change.
Build the slice before the features. A working ugly thing beats a half-built elegant one.
The eval set is the product. Whenever you find a query that fails, add it as a permanent test case.
Embeddings are cached to disk. Never silently re-embed the whole dictionary on a normal run.
Confirm infrastructure and framework choices before building them — propose a design, get agreement, then implement. Do not assume an AWS architecture.
Keep the frontend dumb and the backend smart. No business logic in React.

Canary Test Case
Keep this exact input as a permanent manual test for the understanding layer (Phase 5):
"The rain finds me before I'm ready for it, soaking through my collar as I stand frozen on the pavement, watching the gutters swell into little rivers. And somehow I don't move—I just let it come, breathing in that strange grey peace, like the sky finally said the thing I'd been too afraid to."
Before Phase 5 this should (correctly) return a generic averaged guess — that is expected, not a bug. After Phase 5 it should return grouped concepts (e.g. the rain-smell -> petrichor; the calm acceptance -> resignation/equanimity; the release -> catharsis; the grey longing -> saudade), framed as interpretations rather than one confident answer. This passage may have no single target word, and the system must be honest about that.
