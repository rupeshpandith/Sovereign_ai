"""Approval decision route (Architecture.md §5 contract, §6 — approver role).

A dedicated router for the ``/approval/*`` boundary (maps to the approver role and a
future pending-approval queue). The deliverable file is produced by the docgen tool in
Phase 7.5, so ``output_file`` is null until then.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.database import get_db
from app.models.db_models import ApprovalRequest, User
from app.models.schemas import ApprovalDecideRequest, ApprovalDecideResponse

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
            status_code=422,  # Unprocessable Content
            detail="decision must be 'approve' or 'reject'",
        )
    req = db.get(ApprovalRequest, approval_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    req.status = new_status
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()

    # output_file is produced by the docgen tool (Phase 7.5); null until then.
    return ApprovalDecideResponse(status=new_status, output_file=None)
