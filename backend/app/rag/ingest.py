"""RAG Ingest Pipeline — Phase 7.4 (Plan.md §7.4).

Loads every document from ``data/sample_docs/`` (and any file uploaded via the
document upload endpoint), parses it into text, chunks it with rich metadata,
and hands chunks to ``embed.py`` to be vectorised and stored in ChromaDB.

Supported input types (all processed locally — no cloud OCR):
    .txt   — plain text (extracted PDF text or synthetic docs)
    .pdf   — PyMuPDF text extraction; Tesseract OCR fallback for scanned pages
    .png / .jpg / .jpeg / .tif / .tiff / .bmp / .webp — Tesseract OCR

Sovereignty: zero external calls. Every parser runs in-process.

Chunk metadata schema (matches KnowledgeChunk ORM + SKILL.md requirements):
    source_file   — basename of the original file
    doc_type      — "inspection_report" | "sop" | "approval_note" | "other"
    equipment_tag — equipment ID extracted from the text (e.g. "P-204")
    section_title — nearest heading / section detected above the chunk
    page_number   — 1-based page number (always 1 for .txt files)
    chunk_index   — 0-based position within the document
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default location of the curated knowledge base (relative to the working
# directory the server is started from, i.e. the ``backend/`` folder).
DEFAULT_DOCS_DIR = Path("data/sample_docs")

# Chunk size in characters.  Kept small enough that all-MiniLM-L6-v2 (512 token
# limit) can handle every chunk without silent truncation.
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100   # character overlap between consecutive chunks

# ---------------------------------------------------------------------------
# Document type classifier (filename-based; fast, no model needed)
# ---------------------------------------------------------------------------

_DOC_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"inspection.report", re.I), "inspection_report"),
    (re.compile(r"sop[-_]", re.I),           "sop"),
    (re.compile(r"approval.note", re.I),     "approval_note"),
]

def _classify_doc_type(filename: str) -> str:
    for pattern, label in _DOC_TYPE_PATTERNS:
        if pattern.search(filename):
            return label
    return "other"


# ---------------------------------------------------------------------------
# Equipment tag extractor
# ---------------------------------------------------------------------------

# Matches common industrial equipment tags: P-204, V-33, HX-12, C-101, FN-07…
_EQUIP_RE = re.compile(
    r"\b([A-Z]{1,4}-\d{1,4}[A-Z]?)\b"
)

def _extract_equipment_tags(text: str) -> list[str]:
    """Return deduplicated equipment tags found in *text*, in order of first appearance."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _EQUIP_RE.finditer(text):
        tag = m.group(1)
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


# ---------------------------------------------------------------------------
# Section-title detector
# ---------------------------------------------------------------------------

# Heuristic: an ALL-CAPS line, or a line matching "1. SCOPE", "§3.2 ...", etc.
_SECTION_RE = re.compile(
    r"^(?:\d+\.\s+[A-Z]|§\s*\d|[A-Z]{2}[A-Z ]{3,}$)",
    re.MULTILINE,
)

def _nearest_section(text_before: str) -> Optional[str]:
    """Return the last section heading found in *text_before* (text preceding the chunk)."""
    matches = list(_SECTION_RE.finditer(text_before))
    if not matches:
        return None
    last = matches[-1]
    return text_before[last.start(): last.end()].strip()[:120]


# ---------------------------------------------------------------------------
# Chunk data class
# ---------------------------------------------------------------------------

@dataclass
class DocumentChunk:
    """A single retrievable unit of text with full provenance metadata."""
    text: str
    source_file: str
    doc_type: str
    page_number: int
    chunk_index: int
    section_title: Optional[str] = None
    equipment_tags: list[str] = field(default_factory=list)
    # Populated by embed.py after the chunk is stored in the vector store.
    embedding_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Text parsers
# ---------------------------------------------------------------------------

def _parse_txt(path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, text)] for a plain-text file (always page 1)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(1, text)]


def _parse_pdf(path: Path) -> list[tuple[int, str]]:
    """Extract text from a PDF using PyMuPDF; fall back to Tesseract if a page
    has negligible text (i.e. it is a scanned image)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed; skipping PDF %s", path.name)
        return []

    pages: list[tuple[int, str]] = []
    doc = fitz.open(str(path))
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if len(text) < 50:
            # Likely scanned — run OCR
            text = _ocr_page_image(page)
        pages.append((i, text))
    doc.close()
    return pages


def _ocr_page_image(page) -> str:
    """Rasterise one PyMuPDF page and run Tesseract on it."""
    try:
        import pytesseract
        from PIL import Image
        import io
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, lang="eng")
    except Exception as exc:
        logger.warning("OCR failed for page: %s", exc)
        return ""


def _parse_image(path: Path) -> list[tuple[int, str]]:
    """Run Tesseract OCR on a standalone image file."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img, lang="eng")
        return [(1, text)]
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", path.name, exc)
        return []


_PARSERS: dict[str, callable] = {
    ".txt":  _parse_txt,
    ".pdf":  _parse_pdf,
    ".png":  _parse_image,
    ".jpg":  _parse_image,
    ".jpeg": _parse_image,
    ".tif":  _parse_image,
    ".tiff": _parse_image,
    ".bmp":  _parse_image,
    ".webp": _parse_image,
}


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def _chunk_text(
    text: str,
    source_file: str,
    doc_type: str,
    page_number: int,
    chunk_offset: int = 0,
) -> list[DocumentChunk]:
    """Split *text* into overlapping character-based chunks with metadata."""
    chunks: list[DocumentChunk] = []
    start = 0
    idx = chunk_offset
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end].strip()
        if chunk_text:
            section = _nearest_section(text[:start])
            tags = _extract_equipment_tags(chunk_text)
            chunks.append(DocumentChunk(
                text=chunk_text,
                source_file=source_file,
                doc_type=doc_type,
                page_number=page_number,
                chunk_index=idx,
                section_title=section,
                equipment_tags=tags,
            ))
            idx += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Main ingest function
# ---------------------------------------------------------------------------

def ingest_file(path: Path) -> list[DocumentChunk]:
    """Parse and chunk a single file.

    Returns a list of DocumentChunk objects ready to be passed to
    ``embed.add_chunks()``. Does NOT write to the DB or vector store itself
    so that callers can batch multiple files.
    """
    ext = path.suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        logger.info("INGEST_SKIP | file=%s | reason=unsupported extension %r", path.name, ext)
        return []

    logger.info("INGEST_START | file=%s | type=%s", path.name, ext)
    doc_type = _classify_doc_type(path.name)
    pages = parser(path)
    chunks: list[DocumentChunk] = []
    chunk_offset = 0
    for page_num, text in pages:
        page_chunks = _chunk_text(
            text=text,
            source_file=path.name,
            doc_type=doc_type,
            page_number=page_num,
            chunk_offset=chunk_offset,
        )
        chunks.extend(page_chunks)
        chunk_offset += len(page_chunks)

    logger.info(
        "INGEST_DONE | file=%s | pages=%d | chunks=%d",
        path.name, len(pages), len(chunks),
    )
    return chunks


def ingest_directory(docs_dir: Path = DEFAULT_DOCS_DIR) -> list[DocumentChunk]:
    """Ingest every supported file in *docs_dir* and return all chunks.

    Call this at startup (or on demand) to populate / refresh the vector store.
    """
    if not docs_dir.exists():
        logger.warning("INGEST_SKIP | dir=%s | reason=directory does not exist", docs_dir)
        return []

    all_chunks: list[DocumentChunk] = []
    files = sorted(docs_dir.iterdir())
    for f in files:
        if f.is_file() and f.suffix.lower() in _PARSERS:
            all_chunks.extend(ingest_file(f))

    logger.info(
        "INGEST_DIRECTORY_DONE | dir=%s | files=%d | total_chunks=%d",
        docs_dir,
        sum(1 for f in files if f.is_file() and f.suffix.lower() in _PARSERS),
        len(all_chunks),
    )
    return all_chunks


def ingest_text(
    text: str,
    filename: str,
    doc_type: Optional[str] = None,
) -> list[DocumentChunk]:
    """Chunk already-extracted text into DocumentChunk objects.

    Use this when the caller (e.g. the upload route) has already run OCR and
    holds the plain text — avoids re-reading the file from disk.

    Args:
        text:      The full extracted text of the document.
        filename:  Original filename (used for metadata + doc-type inference).
        doc_type:  Override the inferred doc_type if the caller already knows it.

    Returns:
        List of DocumentChunk objects ready for ``embed.add_chunks()``.
    """
    effective_doc_type = doc_type or _classify_doc_type(filename)
    chunks = _chunk_text(
        text=text,
        source_file=filename,
        doc_type=effective_doc_type,
        page_number=1,   # text strings are treated as a single page
    )
    logger.info(
        "INGEST_TEXT_DONE | file=%s | doc_type=%s | chunks=%d",
        filename, effective_doc_type, len(chunks),
    )
    return chunks

