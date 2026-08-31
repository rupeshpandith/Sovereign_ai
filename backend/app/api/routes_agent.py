"""Agent run routes (Architecture.md §5).

Phase 7.6: POST /agent/run now launches the full planner pipeline
(OCR -> task classification -> RAG -> reasoning -> grounding verification
-> docgen -> awaiting_approval) in a background thread so the endpoint
returns immediately with the run ID while the pipeline executes.

GET /agent/run/{id}/status reads the DB row that the background task
updates when each step completes.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.database import SessionLocal, get_db
from app.models.db_models import AgentRun, Document, User
from app.models.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunStatusResponse,
    Evidence,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent"])


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline(run_id: int, goal: str, document_id: int | None) -> None:
    """Execute the planner pipeline and write results back to the DB.

    This runs in a thread-pool thread (launched via BackgroundTasks).
    It opens its own DB session so it doesn't share the request session.
    """
    from app.agent.planner import get_planner

    db = SessionLocal()
    try:
        # Resolve document text and disk path
        doc_text = ""
        doc_filename = None
        doc_path = None
        if document_id is not None:
            doc = db.get(Document, document_id)
            if doc:
                doc_text = doc.extracted_text or ""
                doc_filename = doc.filename
                # Locate the file on disk so the planner can re-run extraction
                # if the DB text is absent (e.g. extraction failed at upload time).
                from pathlib import Path
                upload_dir = Path("data/uploads")
                if upload_dir.exists():
                    matches = list(upload_dir.glob(f"{doc.id}_{doc.filename}"))
                    if not matches:
                        matches = list(upload_dir.glob(f"*_{doc.filename}"))
                    doc_path = matches[0] if matches else None

        planner = get_planner()
        result = planner.execute(
            goal=goal,
            document_text=doc_text,
            run_id=run_id,
            document_filename=doc_filename,
            document_path=doc_path,
        )

        # Persist results back to AgentRun
        run = db.get(AgentRun, run_id)
        if run:
            run.status = result.status
            run.task_type = "inspection_approval"
            # Store model_used + steps + evidence + flags as JSON in model_used column
            # (reusing the text column; a dedicated JSON column can be added later)
            run.model_used = json.dumps({
                "models": result.model_used,
                "steps_completed": result.steps_completed,
                "output_file": result.output_file,
                "verification_flags": [
                    {"claim_type": f.claim_type, "value": f.value, "note": f.note}
                    for f in result.verification_flags
                ],
                "error": result.error,
            })
            db.commit()
            logger.info(
                "AGENT_RUN_UPDATED | run_id=%d | status=%s | flags=%d | file=%s",
                run_id, result.status, len(result.verification_flags), result.output_file,
            )
    except Exception as exc:
        logger.error("AGENT_RUN_BG_FAILED | run_id=%d | error=%s", run_id, exc, exc_info=True)
        try:
            run = db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.model_used = json.dumps({"error": str(exc)})
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("engineer")),
) -> AgentRunResponse:
    """Create an AgentRun record and launch the planner pipeline in the background.

    Returns immediately with the run ID; clients poll
    GET /agent/run/{id}/status for progress.
    """
    run = AgentRun(
        user_id=user.id,
        task_type="inspection_approval",
        model_used=None,
        status="in_progress",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(
        _run_pipeline,
        run_id=run.id,
        goal=payload.goal,
        document_id=payload.document_id,
    )

    logger.info(
        "AGENT_RUN_STARTED | run_id=%d | user=%d | document_id=%s | goal=%.80r",
        run.id, user.id, payload.document_id, payload.goal,
    )
    return AgentRunResponse(agent_run_id=run.id, status=run.status)


@router.get("/agent/run/{run_id}/status", response_model=AgentRunStatusResponse)
def agent_run_status(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunStatusResponse:
    """Return the current status of an agent run, including pipeline steps and evidence."""
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")

    # Parse the JSON blob stored in model_used (populated by the background task)
    meta: dict = {}
    if run.model_used:
        try:
            meta = json.loads(run.model_used)
        except (json.JSONDecodeError, TypeError):
            meta = {}

    steps_completed: list[str] = meta.get("steps_completed") or []
    model_used_map: dict[str, str] = meta.get("models") or {}

    # Build evidence list from verification flags (simplified — full evidence
    # is embedded in the DOCX; the API returns flag summaries for the UI panel)
    evidence: list[Evidence] = []
    for flag in meta.get("verification_flags") or []:
        evidence.append(Evidence(
            claim=f"[NEEDS REVIEW] {flag['claim_type']}: {flag['value']}",
            source="grounding_verifier",
            page=0,
        ))

    return AgentRunStatusResponse(
        status=run.status,
        steps_completed=steps_completed,
        model_used=model_used_map,
        evidence=evidence,
    )
