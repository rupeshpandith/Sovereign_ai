"""Edge-case tests — Phase 9 (Plan.md §9 / TODO.md Phase 9).

Explicit edge cases required by the plan:
    - corrupted PDF        -> extractor returns FAILED gracefully (never raises)
    - empty document       -> extractor returns an empty-but-valid result
    - sandbox timeout      -> run_sandbox reports a timeout, never raises
    - (ambiguous task type is covered in test_classifier.py)

Everything here is offline: no model, no network, no Docker daemon required.
"""

from __future__ import annotations

import subprocess

import app.agent.tools.sandbox_tool as sandbox_tool
from app.agent.tools.document_extractor import ExtractionMethod, extract_text
from app.agent.tools.sandbox_tool import make_calculation_snippet, run_sandbox


# ---------------------------------------------------------------------------
# Corrupted / malformed documents
# ---------------------------------------------------------------------------

def test_corrupted_pdf_returns_failed_not_raises():
    # Random bytes with a .pdf extension — PyMuPDF cannot open this.
    result = extract_text(b"%PDF-1.4 this is not really a pdf \x00\x01\x02", "corrupt.pdf")
    assert result.primary_method == ExtractionMethod.FAILED
    assert result.full_text == ""
    assert result.error is not None


def test_corrupted_image_returns_failed_not_raises():
    result = extract_text(b"not-a-real-image-blob", "broken.png")
    assert result.primary_method == ExtractionMethod.FAILED
    assert result.error is not None


def test_unsupported_extension_returns_failed():
    result = extract_text(b"whatever", "notes.md")
    assert result.primary_method == ExtractionMethod.FAILED
    assert "Unsupported file type" in (result.error or "")


# ---------------------------------------------------------------------------
# Empty documents
# ---------------------------------------------------------------------------

def test_empty_txt_document_is_valid_and_empty():
    result = extract_text(b"", "empty.txt")
    assert result.primary_method == ExtractionMethod.PLAIN_TEXT
    assert result.full_text == ""
    assert result.total_chars == 0
    assert result.error is None


def test_plain_text_extraction_roundtrips():
    body = b"Inspection report 745: pump P-204 vibration 6.7 mm/s"
    result = extract_text(body, "report.txt")
    assert result.primary_method == ExtractionMethod.PLAIN_TEXT
    assert "P-204" in result.full_text


# ---------------------------------------------------------------------------
# Sandbox timeout & fail-safe
# ---------------------------------------------------------------------------

def test_sandbox_timeout_returns_error_not_raises(monkeypatch):
    """Simulate Docker being present but the container exceeding the wall clock."""
    monkeypatch.setattr(sandbox_tool, "_docker_available", lambda: True)

    def _fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="docker", timeout=sandbox_tool.SANDBOX_TIMEOUT_SECONDS)

    monkeypatch.setattr(sandbox_tool.subprocess, "run", _fake_run)

    result = run_sandbox("while True: pass")
    assert result.success is False
    assert result.method == "docker"
    assert "timed out" in (result.error or "").lower()


def test_sandbox_refuses_when_docker_unavailable(monkeypatch):
    """Fail-safe policy: no Docker => refuse (the exec() fallback is disabled)."""
    monkeypatch.setattr(sandbox_tool, "_docker_available", lambda: False)

    result = run_sandbox("print(2 + 2)")
    assert result.success is False
    assert result.method == "refused"
    assert "Docker" in (result.error or "")


def test_make_calculation_snippet_builds_runnable_source():
    snippet = make_calculation_snippet(
        "vibration + rate * hours",
        {"vibration": 6.7, "rate": 0.4, "hours": 72},
    )
    assert "vibration = 6.7" in snippet
    assert "result = vibration + rate * hours" in snippet
    assert 'print(f"result = {result}")' in snippet
