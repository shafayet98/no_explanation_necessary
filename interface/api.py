"""Interface layer — FastAPI app. Thin by design: shapes requests, calls
understanding.query.query(), and serialises QueryResponse. No business logic.

Run locally:
    uvicorn interface.api:app --reload
"""

import dataclasses
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PHASE = 8


# ---------------------------------------------------------------------------
# Request models (Pydantic — FastAPI uses these for body parsing + 422s)
# ---------------------------------------------------------------------------

class FiltersRequest(BaseModel):
    pos: str | None = None
    starts_with: str | None = None
    max_length: int | None = None


class QueryRequest(BaseModel):
    text: str
    filters: FiltersRequest | None = None
    lucky: bool = False


# ---------------------------------------------------------------------------
# Lifespan — warm the index once on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    import index.engine as engine
    engine.load()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Reverse Dictionary", version="0.8.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/query")
def post_query(req: QueryRequest) -> dict:
    """Embed → retrieve → rerank → grouped results. Delegates to understanding layer."""
    from understanding.query import query, QueryFilters

    filters = None
    if req.filters is not None:
        filters = QueryFilters(
            pos=req.filters.pos,
            starts_with=req.filters.starts_with,
            max_length=req.filters.max_length,
        )

    response = query(req.text, filters=filters, lucky=req.lucky)
    return dataclasses.asdict(response)


@app.get("/api/health")
def get_health() -> dict:
    """Liveness + index/model metadata."""
    import index.engine as engine
    from embedding.embedder import MODEL_ID

    return {
        "status": "ok",
        "index_size": engine.record_count(),
        "model": MODEL_ID,
        "phase": PHASE,
    }
