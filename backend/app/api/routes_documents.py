"""Document upload route (Architecture.md §5).

Uploaded files are treated as untrusted input:
  - filename is reduced to its basename (no path traversal)
  - file contents are stored on disk under data/uploads/
  - text is extracted locally using document_extractor.py (Tesseract → vision
    model fallback) and stored in Document.extracted_text so the planner can
    read it without re-running OCR on every agent run.

Phase 7: extraction is now live. Status is "extracted" on success, "uploaded"
if extraction produced no text (fallback — agent will retry in-pipeline).
"""

import logging
import os

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.database import get_db
from app.models.db_models import Document, User
from app.models.schemas import DocumentUploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])

UPLOAD_DIR = os.path.join("data", "uploads")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("engineer")),
) -> DocumentUploadResponse:
    """Upload a document, save it to disk, and extract its text locally.

    Extraction uses Tesseract OCR (Stage 1) with an automatic fallback to
    the vision model (Stage 2) for handwriting / diagrams that Tesseract
    cannot parse.  See document_extractor.py for the full strategy.
    """
    from app.agent.tools.document_extractor import extract_text

    safe_name = os.path.basename(file.filename or "upload.bin")
    doc_type = os.path.splitext(safe_name)[1].lstrip(".").lower() or None

    # Read file bytes once — used for both disk storage and extraction.
    file_bytes = await file.read()

    # Persist the DB record first so we have a document_id.
    doc = Document(filename=safe_name, doc_type=doc_type, extracted_text=None)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Write to disk (untrusted data; stored by document_id prefix to avoid collisions).
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    disk_path = os.path.join(UPLOAD_DIR, f"{doc.id}_{safe_name}")
    with open(disk_path, "wb") as out:
        out.write(file_bytes)

    # Extract text locally (Tesseract → vision fallback).
    extraction_status = "uploaded"
    try:
        result = extract_text(file_bytes, safe_name)
        if result.full_text:
            doc.extracted_text = result.full_text
            db.commit()
            extraction_status = "extracted"
            logger.info(
                "UPLOAD_EXTRACTED | doc_id=%d | file=%s | method=%s | "
                "chars=%d | vision_pages=%d",
                doc.id, safe_name, result.primary_method,
                result.total_chars, result.vision_fallback_pages,
            )
        else:
            logger.warning(
                "UPLOAD_EXTRACT_EMPTY | doc_id=%d | file=%s | error=%s | "
                "hint=agent will retry OCR in-pipeline",
                doc.id, safe_name, result.error,
            )
    except Exception as exc:
        # Non-fatal: the document is stored; the planner will attempt extraction.
        logger.error(
            "UPLOAD_EXTRACT_FAILED | doc_id=%d | file=%s | error=%s",
            doc.id, safe_name, exc,
        )

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=safe_name,
        status=extraction_status,
    )
