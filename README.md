# Reverse Dictionary

A semantic search tool that inverts a normal dictionary: describe a meaning, get
the word. Type *"the smell of rain on dry earth"* → get **petrichor**.

See [CLAUDE.md](CLAUDE.md) for the full project brief and build discipline, and
[docs/architecture.md](docs/architecture.md) for the five-layer architecture and
interface contracts.

## Status

Skeleton — every layer exists as an importable stub; nothing is implemented yet.

## Layout

```
data/          Data layer        — WordNet loader → WordRecord per sense
embedding/     Embedding layer   — embed(texts) → normalised vectors
index/         Index layer       — build / load / search (numpy now, FAISS later)
understanding/ Understanding      — classify → route → rerank (the intelligence)
interface/     Interface layer   — FastAPI API + React frontend (thin client)
eval/          Eval harness      — recall@10 + MRR against a fixed test set
scripts/       One-shot scripts  — build_index.py
infra/         Terraform (AWS)   — stubbed; services not yet chosen
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Plans

Implementation plans live in [docs/plan/](docs/plan/). Use `/plan` to write one
and `/execute` to build it.
