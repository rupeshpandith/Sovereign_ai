"""Unit tests for the RAG retrieve pipeline — Phase 9 (Plan.md §9, §7.4).

The heavy dependencies (ChromaDB + the sentence-transformers embedding model)
are never loaded: ``retrieve()`` imports ``_get_collection`` lazily from
``app.rag.embed``, so we monkeypatch that symbol with a small fake collection.
This keeps the tests fast, offline, and independent of any populated vector
store.
"""

from __future__ import annotations

import app.rag.embed as embed_mod
from app.rag.retrieve import (
    RetrievalResult,
    _build_where,
    _distance_to_confidence,
    _parse_raw,
    retrieve,
    retrieve_sop_chunks,
)


# ---------------------------------------------------------------------------
# Fake ChromaDB collection
# ---------------------------------------------------------------------------

class _FakeCollection:
    def __init__(self, count: int, raw: dict | None = None):
        self._count = count
        self._raw = raw or {}
        self.last_query_kwargs: dict | None = None

    def count(self) -> int:
        return self._count

    def query(self, **kwargs):
        self.last_query_kwargs = kwargs
        return self._raw


def _install_collection(monkeypatch, collection):
    monkeypatch.setattr(embed_mod, "_get_collection", lambda: collection)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def test_distance_to_confidence_bounds():
    assert _distance_to_confidence(0.0) == 1.0
    assert _distance_to_confidence(1.0) == 0.0
    assert _distance_to_confidence(2.0) == 0.0    # clamped, not negative
    assert _distance_to_confidence(0.3) == 0.7


def test_build_where_none_when_no_filters():
    assert _build_where(None, None) is None


def test_build_where_single_condition():
    assert _build_where("sop", None) == {"doc_type": {"$eq": "sop"}}
    assert _build_where(None, "P-204") == {"equipment_tags": {"$contains": "P-204"}}


def test_build_where_combines_with_and():
    where = _build_where("sop", "P-204")
    assert "$and" in where
    assert {"doc_type": {"$eq": "sop"}} in where["$and"]
    assert {"equipment_tags": {"$contains": "P-204"}} in where["$and"]


def test_parse_raw_sorts_by_confidence_desc():
    raw = {
        "documents": [["low conf chunk", "high conf chunk"]],
        "metadatas": [[
            {"source_file": "a.txt", "doc_type": "sop", "page_number": 2,
             "chunk_index": 1, "equipment_tags": "P-1,P-2"},
            {"source_file": "b.txt", "doc_type": "inspection_report", "page_number": 1,
             "chunk_index": 0, "equipment_tags": ""},
        ]],
        "distances": [[0.8, 0.1]],   # first is worse (lower confidence)
    }
    results = _parse_raw(raw)
    assert [r.confidence for r in results] == sorted(
        [r.confidence for r in results], reverse=True
    )
    top = results[0]
    assert isinstance(top, RetrievalResult)
    assert top.source_file == "b.txt"
    assert top.confidence == 0.9

    # equipment_tags split correctly (and empty string -> empty list)
    tagged = next(r for r in results if r.source_file == "a.txt")
    assert tagged.equipment_tags == ["P-1", "P-2"]
    assert top.equipment_tags == []


def test_parse_raw_handles_empty_output():
    assert _parse_raw({}) == []


# ---------------------------------------------------------------------------
# retrieve() behaviour
# ---------------------------------------------------------------------------

def test_retrieve_returns_empty_for_empty_store(monkeypatch):
    _install_collection(monkeypatch, _FakeCollection(count=0))
    assert retrieve("anything") == []


def test_retrieve_parses_and_returns_results(monkeypatch):
    raw = {
        "documents": [["SOP-17 vibration limit is 7.1 mm/s"]],
        "metadatas": [[{
            "source_file": "SOP-17.txt", "doc_type": "sop", "page_number": 1,
            "chunk_index": 0, "section_title": "Limits", "equipment_tags": "P-204",
        }]],
        "distances": [[0.2]],
    }
    coll = _FakeCollection(count=5, raw=raw)
    _install_collection(monkeypatch, coll)

    results = retrieve("vibration limit", n_results=3)
    assert len(results) == 1
    assert results[0].doc_type == "sop"
    assert results[0].confidence == 0.8
    assert results[0].section_title == "Limits"
    # n_results is clamped to the collection count in the query call
    assert coll.last_query_kwargs["n_results"] == 3


def test_retrieve_sop_filter_passed_to_query(monkeypatch):
    coll = _FakeCollection(count=3, raw={"documents": [[]], "metadatas": [[]], "distances": [[]]})
    _install_collection(monkeypatch, coll)

    retrieve_sop_chunks("valve inspection")
    assert coll.last_query_kwargs["where"] == {"doc_type": {"$eq": "sop"}}
