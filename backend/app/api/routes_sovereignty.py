"""Sovereignty status route (Architecture.md §5 contract, §6 — admin role).

Counts are derived from local tables (``documents``, ``sovereignty_log``). The network
guard that actively intercepts, logs, and blocks outbound attempts is added in Phase 8;
until then ``internet_status`` reports the intended sovereign default, ``"blocked"``.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.database import get_db
from app.models.db_models import Document, SovereigntyLog, User
from app.models.schemas import SovereigntyStatusResponse

router = APIRouter(tags=["sovereignty"])


def _count_events(db: Session, event_type: str) -> int:
    stmt = select(func.count()).select_from(SovereigntyLog).where(
        SovereigntyLog.event_type == event_type
    )
    return db.execute(stmt).scalar_one()


@router.get("/sovereignty/status", response_model=SovereigntyStatusResponse)
def sovereignty_status(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> SovereigntyStatusResponse:
    documents_processed = db.execute(select(func.count()).select_from(Document)).scalar_one()
    return SovereigntyStatusResponse(
        external_calls=_count_events(db, "external_call"),  # non-blocked egress; should stay 0
        internet_status="blocked",
        local_model_calls=_count_events(db, "local_model_call"),
        documents_processed=documents_processed,
        sandbox_executions=_count_events(db, "sandbox_execution"),
    )
