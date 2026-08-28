"""Document upload route (Architecture.md §5).

Uploaded files are untrusted input: the filename is reduced to its basename (no path
traversal) and stored under a local uploads directory. OCR / text extraction is wired
in Phase 7 — for now the document row is created with status ``uploaded``.
"""

import os

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.database import get_db
from app.models.db_models import Document, User
from app.models.schemas import DocumentUploadResponse

router = APIRouter(tags=["documents"])

UPLOAD_DIR = os.path.join("data", "uploads")


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("engineer")),
) -> DocumentUploadResponse:
    safe_name = os.path.basename(file.filename or "upload.bin")
    doc_type = os.path.splitext(safe_name)[1].lstrip(".").lower() or None

    doc = Document(filename=safe_name, doc_type=doc_type, extracted_text=None)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(UPLOAD_DIR, f"{doc.id}_{safe_name}"), "wb") as out:
        out.write(await file.read())

    return DocumentUploadResponse(document_id=doc.id, filename=safe_name, status="uploaded")
