"""RAG Retrieve Pipeline — Phase 7.4 (Plan.md §7.4).

Given a natural-language query, returns the top-k most relevant DocumentChunk
objects from ChromaDB, each annotated with a citation and a confidence score.

Output format (SKILL.md §Output Format):
    Every RetrievalResult carries:
        - finding        : short label of the chunk (doc_type + source)
        - source_file    : original filename
        - page_number    : 1-based page
        - exact_quote    : the verbatim retrieved chunk text (or a leading excerpt)
        - confidence     : 0.0–1.0 derived from the cosine distance
        - section_title  : nearest section heading if detected
        - equipment_tags : list of equipment IDs found in the chunk
        - doc_type       : "inspection_report" | "sop" | "approval_note" | "other"

Retrieval modes:
    1. Semantic search (default): embed the query with all-MiniLM-L6-v2, find
       nearest neighbours in ChromaDB by cosine distance.
    2. Filtered search: narrow by doc_type and/or equipment_tag before ranking.
       Used by the planner to enforce "only SOPs" or "only inspection reports".

Sovereignty: all retrieval is local (ChromaDB file store + local embedding model).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum chunks returned when the caller does not specify n_results
DEFAULT_TOP_K = 5
# Cosine distance threshold above which results are considered low-confidence
LOW_CONFIDENCE_THRESHOLD = 0.45


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """One retrieved chunk with full provenance for the evidence panel (§16)."""
    finding: str
    source_file: str
    page_number: int
    exact_quote: str
    confidence: float            # 1.0 - cosine_distance
    section_title: Optional[str]
    equipment_tags: list[str]
    doc_type: str
    chunk_index: int


# ---------------------------------------------------------------------------
# Distance → confidence conversion
# ---------------------------------------------------------------------------

def _distance_to_confidence(distance: float) -> float:
    """Map ChromaDB cosine distance [0, 2] to a confidence score [0, 1].

    ChromaDB returns L2-normalised cosine distance where 0 = identical and
    2 = opposite.  We cap at 1.0 (distance 0 → 1.0, distance 1+ → 0.0).
    """
    return round(max(0.0, min(1.0, 1.0 - distance)), 3)


# ---------------------------------------------------------------------------
# Core retrieval
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    *,
    n_results: int = DEFAULT_TOP_K,
    doc_type_filter: Optional[str] = None,
    equipment_tag_filter: Optional[str] = None,
) -> list[RetrievalResult]:
    """Retrieve the top-*n_results* chunks most relevant to *query*.

    Args:
        query: Natural-language query from the planner or user goal.
        n_results: Maximum number of chunks to return.
        doc_type_filter: If given, restrict to chunks whose ``doc_type``
            matches exactly (e.g. "sop", "inspection_report").
        equipment_tag_filter: If given, restrict to chunks whose
            ``equipment_tags`` field contains this tag (substring match
            because ChromaDB metadata filtering uses ``$contains`` on strings).

    Returns:
        List of RetrievalResult ordered by descending confidence (best first).
        Returns an empty list if the collection is empty or no results pass
        the filters.
    """
    from app.rag.embed import _get_collection   # lazy import avoids circular at module level

    collection = _get_collection()

    if collection.count() == 0:
        logger.warning(
            "RETRIEVE_EMPTY | query=%.80r | reason=vector store is empty; "
            "run ingest_and_embed() first",
            query,
        )
        return []

    # Build optional ChromaDB ``where`` clause
    where: Optional[dict] = _build_where(doc_type_filter, equipment_tag_filter)

    try:
        raw = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error("RETRIEVE_ERROR | query=%.80r | error=%s", query, exc)
        raise

    results = _parse_raw(raw)

    logger.info(
        "RETRIEVE_DONE | query=%.80r | n_results=%d | returned=%d "
        "| doc_type_filter=%s | equipment_filter=%s | top_confidence=%.3f",
        query,
        n_results,
        len(results),
        doc_type_filter,
        equipment_tag_filter,
        results[0].confidence if results else 0.0,
    )

    return results


def retrieve_sop_chunks(query: str, n_results: int = DEFAULT_TOP_K) -> list[RetrievalResult]:
    """Convenience wrapper: restrict retrieval to SOP documents only."""
    return retrieve(query, n_results=n_results, doc_type_filter="sop")


def retrieve_inspection_chunks(
    query: str,
    equipment_tag: Optional[str] = None,
    n_results: int = DEFAULT_TOP_K,
) -> list[RetrievalResult]:
    """Convenience wrapper: restrict retrieval to inspection report documents."""
    return retrieve(
        query,
        n_results=n_results,
        doc_type_filter="inspection_report",
        equipment_tag_filter=equipment_tag,
    )


def retrieve_approval_examples(query: str, n_results: int = 3) -> list[RetrievalResult]:
    """Return past approval notes as structural examples for the drafting model."""
    return retrieve(query, n_results=n_results, doc_type_filter="approval_note")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_where(
    doc_type_filter: Optional[str],
    equipment_tag_filter: Optional[str],
) -> Optional[dict]:
    """Construct a ChromaDB ``where`` clause from optional filters.

    ChromaDB supports ``$eq`` for exact match and ``$contains`` for substring.
    Multiple conditions must use ``$and``.
    """
    conditions: list[dict] = []

    if doc_type_filter:
        conditions.append({"doc_type": {"$eq": doc_type_filter}})

    if equipment_tag_filter:
        # equipment_tags is stored as a comma-separated string, so use $contains
        conditions.append({"equipment_tags": {"$contains": equipment_tag_filter}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _parse_raw(raw: dict) -> list[RetrievalResult]:
    """Convert raw ChromaDB query output into RetrievalResult objects."""
    results: list[RetrievalResult] = []

    # ChromaDB wraps outputs in an extra list (one entry per query text)
    docs_outer      = raw.get("documents") or [[]]
    metas_outer     = raw.get("metadatas") or [[]]
    distances_outer = raw.get("distances") or [[]]

    docs      = docs_outer[0]
    metas     = metas_outer[0]
    distances = distances_outer[0]

    for doc_text, meta, dist in zip(docs, metas, distances):
        confidence = _distance_to_confidence(dist)
        eq_tags = [t for t in (meta.get("equipment_tags") or "").split(",") if t]
        results.append(RetrievalResult(
            finding=f"{meta.get('doc_type', 'document')} — {meta.get('source_file', 'unknown')}",
            source_file=meta.get("source_file", ""),
            page_number=int(meta.get("page_number", 1)),
            exact_quote=doc_text,
            confidence=confidence,
            section_title=meta.get("section_title") or None,
            equipment_tags=eq_tags,
            doc_type=meta.get("doc_type", "other"),
            chunk_index=int(meta.get("chunk_index", 0)),
        ))

    # Sort best-first (highest confidence = lowest distance)
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Diagnostic helper (useful from the REPL / tests)
# ---------------------------------------------------------------------------

def retrieval_summary(query: str, n_results: int = DEFAULT_TOP_K) -> None:
    """Print a human-readable retrieval report for *query* to stdout."""
    results = retrieve(query, n_results=n_results)
    print(f"\n=== Retrieval for: {query!r} ===")
    if not results:
        print("  (no results)")
        return
    for i, r in enumerate(results, 1):
        tag_str = ", ".join(r.equipment_tags) if r.equipment_tags else "—"
        conf_label = "HIGH" if r.confidence >= 0.7 else ("MED" if r.confidence >= 0.45 else "LOW")
        print(
            f"  [{i}] {conf_label} ({r.confidence:.2f}) | {r.doc_type} | "
            f"{r.source_file} p.{r.page_number} | eq: {tag_str}"
        )
        if r.section_title:
            print(f"       section: {r.section_title}")
        print(f"       quote: {r.exact_quote[:160].replace(chr(10), ' ')}…")
    print()
