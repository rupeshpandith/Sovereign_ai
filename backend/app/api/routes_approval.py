"""Approval decision route (Architecture.md §5 contract, §6 — approver role).

A dedicated router for the ``/approval/*`` boundary (maps to the approver role and a pending-approval queue).  The deliverable file is produced by the docgen tool in Phase 7.5 and its path is stored in ``AgentRun.model_used`` (JSON blob, key ``output_file``).  This route reads it so the frontend can offer a download link.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.database import get_db
from app.models.db_models import AgentRun, ApprovalRequest, User
from app.models.schemas import ApprovalDecideRequest, ApprovalDecideResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["approval"])

_DECISION_TO_STATUS = {"approve": "approved", "reject": "rejected"}


@router.post("/approval/{approval_id}/decide", response_model=ApprovalDecideResponse)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecideRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("approver")),
) -> ApprovalDecideResponse:
    new_status = _DECISION_TO_STATUS.get(payload.decision)
    if new_status is None:
        raise HTTPException(
            status_code=422,
            detail="decision must be 'approve' or 'reject'",
        )
    req = db.get(ApprovalRequest, approval_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    req.status = new_status
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()

    # Resolve the output_file from the associated AgentRun JSON blob.
    output_file: str | None = None
    try:
        agent_run = db.get(AgentRun, req.agent_run_id)
        if agent_run and agent_run.model_used:
            meta = json.loads(agent_run.model_used)
            output_file = meta.get("output_file")
    except Exception as exc:
        logger.warning(
            "APPROVAL_OUTPUT_FILE_LOOKUP_FAILED | approval_id=%d | error=%s",
            approval_id, exc,
        )

    logger.info(
        "APPROVAL_DECIDED | approval_id=%d | decision=%s | user_id=%d | output_file=%s",
        approval_id, new_status, user.id, output_file,
    )
    return ApprovalDecideResponse(status=new_status, output_file=output_file)
