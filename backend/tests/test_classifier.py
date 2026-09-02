"""Unit tests for the Task Classifier — Phase 9 (Plan.md §9, §7.2).

Covers the rule-based classification paths, the file-extension heuristic, the
low-confidence LLM fallback stub, and the ambiguous / no-signal edge case
(TODO.md Phase 9: "ambiguous task type").

These tests are pure and offline — the classifier makes no network calls.
"""

from __future__ import annotations

from app.agent.task_classifier import (
    TaskClassifier,
    TaskType,
    classify_task,
)


def test_coding_goal_classified_as_coding():
    result = TaskClassifier().classify("Write a python function to parse the log file")
    assert result.task_type == TaskType.CODING
    assert result.confidence > 0.0
    assert any("coding" in s for s in result.signals)


def test_vision_keyword_classified_as_vision():
    result = TaskClassifier().classify("OCR this scanned drawing and read the stamp")
    assert result.task_type == TaskType.VISION


def test_pdf_extension_drives_vision_even_without_keywords():
    # No vision keyword in the goal; the .pdf extension alone should win.
    result = TaskClassifier().classify("process this document", filename="report.pdf")
    assert result.task_type == TaskType.VISION
    assert any("file extension" in s for s in result.signals)


def test_industrial_reasoning_goal_classified_as_reasoning():
    result = TaskClassifier().classify(
        "Assess the vibration inspection findings against SOP and draft an approval note"
    )
    assert result.task_type == TaskType.REASONING


def test_ambiguous_or_empty_goal_defaults_to_reasoning():
    """Ambiguous task type edge case: nothing matches -> safe default REASONING."""
    result = TaskClassifier().classify("zzzz qwerty")
    assert result.task_type == TaskType.REASONING
    assert result.confidence == 0.30
    assert any("no signals matched" in s for s in result.signals)


def test_empty_string_goal_does_not_crash():
    result = TaskClassifier().classify("")
    assert result.task_type == TaskType.REASONING
    assert result.confidence == 0.30


def test_llm_fallback_stub_fires_on_low_confidence():
    # A single weak generic-reasoning keyword scores 0.20 (< 0.40 threshold).
    result = TaskClassifier().classify("what", allow_llm_fallback=True)
    assert result.fallback_used is True
    assert result.task_type == TaskType.REASONING
    assert result.confidence == 0.45
    assert any("fallback" in s for s in result.signals)


def test_no_fallback_when_disabled():
    result = TaskClassifier().classify("what", allow_llm_fallback=False)
    assert result.fallback_used is False


def test_confidence_is_capped_at_one():
    # Stack several strong signals; normalisation must keep confidence <= 1.0.
    result = TaskClassifier().classify(
        "debug and refactor this python unit test script function",
        filename="thing.py",
    )
    assert 0.0 <= result.confidence <= 1.0


def test_latency_is_recorded_and_nonnegative():
    result = TaskClassifier().classify("summarise the report")
    assert result.latency_ms >= 0.0


def test_module_level_wrapper_matches_class():
    a = classify_task("Write a python script")
    b = TaskClassifier().classify("Write a python script")
    assert a.task_type == b.task_type == TaskType.CODING
