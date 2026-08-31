"""FastAPI application entry point (Phase 2 — backend foundation).

Thin composition layer per Architecture.md §4.2: this module wires middleware
and mounts the API routers. Business logic lives under ``app/agent``,
``app/rag``, ``app/agent/tools`` and ``app/db``.

Run locally from the ``backend/`` directory:

    uvicorn app.main:app --reload
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_agent,
    routes_approval,
    routes_auth,
    routes_documents,
    routes_sovereignty,
)
from app.core.config import settings
from app.core.security import seed_demo_users
from app.db.database import SessionLocal, init_db

logger = logging.getLogger(__name__)


async def _startup_ingest() -> None:
    """Populate the vector store from sample_docs/ if the collection is empty.

    Runs in a thread pool so the heavy sentence-transformers load does not
    block the asyncio event loop during server startup.
    """
    try:
        from app.rag.embed import collection_count, ingest_and_embed
        count = await asyncio.to_thread(collection_count)
        if count > 0:
            logger.info("RAG_STARTUP_SKIP | reason=collection already has %d chunks", count)
            return
        logger.info("RAG_STARTUP_INGEST | reason=collection is empty, ingesting sample_docs/")
        stored = await asyncio.to_thread(ingest_and_embed)
        logger.info("RAG_STARTUP_INGEST_DONE | chunks_stored=%d", stored)
    except Exception as exc:
        # Non-fatal: the server still starts; RAG just won't work until fixed.
        logger.error(
            "RAG_STARTUP_INGEST_FAILED | error=%s | "
            "hint=ensure sentence-transformers and chromadb are installed",
            exc,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Auto-create the schema and seed local demo users on startup
    #    (Architecture.md §4.3 schema, §6 RBAC; SQLite MVP).
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()

    # 2. Populate the RAG vector store from sample_docs/ (Phase 7.4).
    #    Runs only if the collection is empty — idempotent across restarts.
    await _startup_ingest()

    yield


app = FastAPI(title="Sovereign AI Workbench", version="0.1.0", lifespan=lifespan)

# Mount the API routers (Architecture.md §5 contracts).
app.include_router(routes_auth.router)
app.include_router(routes_documents.router)
app.include_router(routes_agent.router)
app.include_router(routes_approval.router)
app.include_router(routes_sovereignty.router)

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
