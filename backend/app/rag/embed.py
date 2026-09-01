"""RAG Embed Pipeline — Phase 7.4 (Plan.md §7.4).

Converts DocumentChunk objects (from ingest.py) into dense vector embeddings
using the all-MiniLM-L6-v2 sentence-transformers model and stores them in a
local ChromaDB collection.

Design decisions:
  - all-MiniLM-L6-v2 is CPU-based and PERMANENT (see model_registry.yaml
    embedding entry). It is unaffected by the hardware constraint.
  - ChromaDB persists to ``data/vector_store/`` (``settings.vector_db_path``).
  - A single shared Chroma collection ("sovereign_knowledge") holds all
    document types; doc_type and equipment_tag metadata allow filtered search.
  - Chunk IDs are deterministic: ``<source_file>__p<page>__c<chunk_index>``.
    Re-ingesting the same file is therefore idempotent (Chroma upserts).

Sovereignty: embedding runs 100% locally; ChromaDB is a local file store.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.rag.ingest import DocumentChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_NAME = "sovereign_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # pulled from model_registry.yaml; CPU-only
BATCH_SIZE = 32   # number of chunks to embed + upsert in one call


# ---------------------------------------------------------------------------
# Lazy singletons — initialised on first use, not at import time.
# This avoids loading heavy models when the module is merely imported for
# type-checking or during the FastAPI startup sequence before the DB is ready.
# ---------------------------------------------------------------------------

_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_fn():
    """Return the ChromaDB-compatible embedding function (lazy init).

    ``local_files_only=True`` tells sentence-transformers to use only the
    local HuggingFace cache and never attempt an outbound HEAD request to
    huggingface.co for config/adapter files.  This is mandatory because the
    Phase-8 network guard blocks all non-local connections at the OS socket
    level — without this flag the library would retry 5× and crash startup.
    """
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            _embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL,
                # Never phone home — weights must already be in the local cache.
                # Run: python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"  # noqa: E501
                # once (with internet) to populate the cache before enabling the guard.
                local_files_only=True,
            )
            logger.info("EMBED_MODEL_LOADED | model=%s | local_files_only=True", EMBEDDING_MODEL)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load embedding model '{EMBEDDING_MODEL}' from local cache. "
                "Run the following command once (with internet, guard off) to download:\n"
                "  python -c \"from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer('{EMBEDDING_MODEL}')\"\n"
                "Then restart the server with the guard enabled."
            ) from exc
    return _embedding_fn


def _get_collection():
    """Return (or create) the persistent ChromaDB collection (lazy init)."""
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        persist_path = str(Path(settings.vector_db_path).resolve())
        Path(persist_path).mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=persist_path)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "CHROMA_COLLECTION_READY | name=%s | path=%s | count=%d",
            COLLECTION_NAME, persist_path, _collection.count(),
        )
    return _collection


# ---------------------------------------------------------------------------
# Chunk ID
# ---------------------------------------------------------------------------

def _chunk_id(chunk: DocumentChunk) -> str:
    """Deterministic, collision-resistant chunk ID for Chroma upsert."""
    raw = f"{chunk.source_file}__p{chunk.page_number}__c{chunk.chunk_index}"
    # Hash to keep IDs short and safe for Chroma's internal storage.
    digest = hashlib.sha1(raw.encode()).hexdigest()[:12]
    return f"{digest}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_chunks(chunks: list[DocumentChunk]) -> int:
    """Embed and upsert *chunks* into ChromaDB in batches.

    Returns the number of chunks successfully stored.
    Already-present chunks (same ID) are updated in place (idempotent).
    """
    if not chunks:
        return 0

    collection = _get_collection()
    stored = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for chunk in batch:
            cid = _chunk_id(chunk)
            chunk.embedding_id = cid   # write back so callers / DB rows can store it
            ids.append(cid)
            documents.append(chunk.text)
            metadatas.append({
                "source_file":    chunk.source_file,
                "doc_type":       chunk.doc_type,
                "page_number":    chunk.page_number,
                "chunk_index":    chunk.chunk_index,
                "section_title":  chunk.section_title or "",
                "equipment_tags": ",".join(chunk.equipment_tags),  # Chroma metadata is str/int/float/bool only
            })

        try:
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            stored += len(batch)
            logger.info(
                "EMBED_BATCH_UPSERT | batch=%d-%d | count=%d | collection_total=%d",
                batch_start, batch_start + len(batch) - 1, len(batch), collection.count(),
            )
        except Exception as exc:
            logger.error(
                "EMBED_BATCH_FAILED | batch_start=%d | error=%s", batch_start, exc
            )
            raise

    return stored


def collection_count() -> int:
    """Return the number of chunks currently in the vector store."""
    return _get_collection().count()


def reset_collection() -> None:
    """Delete and recreate the collection — useful for re-ingesting from scratch.

    WARNING: all existing embeddings are lost. Call ingest + add_chunks again.
    """
    global _collection
    import chromadb
    persist_path = str(Path(settings.vector_db_path).resolve())
    client = chromadb.PersistentClient(path=persist_path)
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("EMBED_COLLECTION_RESET | name=%s", COLLECTION_NAME)
    except Exception:
        pass
    _collection = None   # force re-init on next _get_collection() call


def ingest_and_embed(docs_dir: Optional[Path] = None) -> int:
    """Convenience wrapper: ingest a directory and embed all chunks.

    Returns the number of chunks stored.
    """
    from app.rag.ingest import ingest_directory, DEFAULT_DOCS_DIR
    directory = docs_dir or DEFAULT_DOCS_DIR
    chunks = ingest_directory(directory)
    if not chunks:
        logger.info("EMBED_NOTHING | dir=%s | reason=no chunks produced by ingest", directory)
        return 0
    return add_chunks(chunks)
