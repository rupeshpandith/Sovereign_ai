"""Database engine, session factory, and schema initialization.

MVP uses SQLite (Architecture.md §4.3: "MVP: SQLite. National round: PostgreSQL.").
Moving to PostgreSQL later requires changing only ``DATABASE_URL`` — the ORM models
stay the same. The database URL is always local; no field here points off-machine.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _connect_args() -> dict:
    # SQLite + FastAPI share the connection across threads, so relax the same-thread check.
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_dir() -> None:
    # For sqlite:///<path>, create the parent directory first, otherwise SQLite
    # raises "unable to open database file".
    prefix = "sqlite:///"
    if settings.database_url.startswith(prefix):
        db_path = settings.database_url[len(prefix):]
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)


_ensure_sqlite_dir()

engine = create_engine(settings.database_url, connect_args=_connect_args())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session and closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Imports the models module so mappers register on Base.metadata."""
    from app.models import db_models  # noqa: F401  (import for registration side effect)

    Base.metadata.create_all(bind=engine)
