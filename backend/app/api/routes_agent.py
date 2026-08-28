"""Agent run routes (Architecture.md §5).

Phase 4 creates and reports agent-run records. The actual agent pipeline
(task classification, RAG retrieval, model routing, tool calls) is built in Phase 7;
until then a run is created ``in_progress`` and its status endpoint returns the stored
status with empty step / model / evidence collections.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.database import get_db
from app.models.db_models import AgentRun, User
from app.models.schemas import AgentRunRequest, AgentRunResponse, AgentRunStatusResponse

router = APIRouter(tags=["agent"])


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("engineer")),
) -> AgentRunResponse:
    run = AgentRun(user_id=user.id, task_type=None, model_used=None, status="in_progress")
    db.add(run)
    db.commit()
    db.refresh(run)
    return AgentRunResponse(agent_run_id=run.id, status=run.status)


@router.get("/agent/run/{run_id}/status", response_model=AgentRunStatusResponse)
def agent_run_status(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunStatusResponse:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    # steps_completed / model_used / evidence are populated once the Phase 7 pipeline runs.
    return AgentRunStatusResponse(
        status=run.status,
        steps_completed=[],
        model_used={},
        evidence=[],
    )
