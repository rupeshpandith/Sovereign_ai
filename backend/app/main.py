"""FastAPI application entry point (Phase 2 — backend foundation).

Thin composition layer per Architecture.md §4.2: this module wires middleware
and mounts the API routers. Business logic lives under ``app/agent``,
``app/rag``, ``app/agent/tools`` and ``app/db``.

Run locally from the ``backend/`` directory:

    uvicorn app.main:app --reload
"""

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create the schema and seed local demo users on startup
    # (Architecture.md §4.3 schema, §6 RBAC; SQLite MVP).
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()
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
