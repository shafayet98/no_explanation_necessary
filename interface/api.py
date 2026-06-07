"""Interface layer — FastAPI app. Thin by design: it shapes requests, calls
understanding.query.query(), and serialises QueryResponse. No business logic.

Run (once implemented): uvicorn interface.api:app --reload
"""

from fastapi import FastAPI

app = FastAPI(title="Reverse Dictionary", version="0.0.0")

PHASE = 0  # current build phase, reported by /health


@app.post("/query")
def post_query() -> dict:
    """Embed → retrieve → rerank → grouped results. Delegates to the
    understanding layer; this handler stays thin."""
    raise NotImplementedError("interface layer not implemented yet (skeleton)")


@app.get("/health")
def get_health() -> dict:
    """Liveness + index/model metadata."""
    raise NotImplementedError("interface layer not implemented yet (skeleton)")
