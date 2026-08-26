"""FastAPI application entry point (Phase 2 — backend foundation).

Thin composition layer per Architecture.md §4.2: this module only wires middleware
and (in later phases) mounts routers. Business logic lives under ``app/agent``,
``app/rag``, ``app/agent/tools`` and ``app/db``.

Run locally from the ``backend/`` directory:

    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create the database schema on startup (Architecture.md §4.3, SQLite MVP).
    init_db()
    yield


app = FastAPI(title="Sovereign AI Workbench", version="0.1.0", lifespan=lifespan)

# CORS is restricted to the local frontend origin(s) only. No wildcard: the backend
# must not accept cross-origin traffic from anywhere off the local machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: always returns 200 with a static payload."""
    return {"status": "ok"}
