"""Task Classifier — Phase 7.2 (Plan.md §7.2).

Classifies a user goal + optional document context into one of the canonical
task types understood by the model router:

    reasoning      — analysis, report drafting, approval notes, Q&A over docs
    coding         — code generation, debugging, script writing
    vision         — scanned images / PDFs that need OCR or visual understanding
    embedding      — not a user-facing task type; used internally by the RAG pipeline

Classification strategy (two-stage):
    1. Rule-based pass: fast, deterministic keyword and file-extension signals.
       Covers the vast majority of industrial-workbench requests.
    2. (Future, Phase 7.6+) Fallback to a small local model via ModelRouter when
       the rule-based pass returns low confidence. Kept as a stub for now so the
       planner can call it unconditionally.

Sovereignty: no external network calls. Classification runs fully in-process.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task type taxonomy
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    REASONING = "reasoning"
    CODING = "coding"
    VISION = "vision"
    EMBEDDING = "embedding"   # internal/RAG use; rarely returned to callers

    def __str__(self) -> str:          # makes f-strings / logging cleaner
        return self.value


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TaskClassification:
    task_type: TaskType
    confidence: float                  # 0.0 - 1.0
    signals: list[str] = field(default_factory=list)   # human-readable reasons
    fallback_used: bool = False        # True when the LLM fallback fired
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

# File extensions that imply a vision/OCR task
_VISION_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
)

# Keyword patterns -> (task_type, confidence_boost, signal_label)
_RULES: list[tuple[re.Pattern[str], TaskType, float, str]] = [
    # --- coding signals ---
    (re.compile(r"\b(code|script|function|def |class |debug|fix.?bug|implement|refactor|unit.?test|pytest|python|javascript)\b", re.I),
     TaskType.CODING, 0.35, "coding keyword"),

    # --- vision / OCR signals ---
    (re.compile(r"\b(scan(ned)?|ocr|image|photo|drawing|diagram|handwrit|figure|plate|stamp)\b", re.I),
     TaskType.VISION, 0.35, "vision keyword"),

    # --- reasoning signals (inspection / industrial / approval) ---
    (re.compile(r"\b(inspect(ion)?|report|finding|anomal|vibration|pressure|temperature|sop|manual|standard|clause|complian|assess|approv(al|e)|reject|draft|summary|reason|analys|evaluat|recommend)\b", re.I),
     TaskType.REASONING, 0.30, "reasoning/industrial keyword"),

    # --- generic reasoning catch-all ---
    (re.compile(r"\b(summariz|explain|what|why|how|describe|review|check|verif)\b", re.I),
     TaskType.REASONING, 0.20, "reasoning generic keyword"),
]

# Minimum confidence threshold to accept rule-based result without LLM fallback
_CONFIDENCE_THRESHOLD = 0.40


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class TaskClassifier:
    """Stateless, synchronous task classifier.

    Usage::

        clf = TaskClassifier()
        result = clf.classify(goal="Analyse pump P-204 vibration report",
                              filename="p204_inspection.pdf")
        print(result.task_type, result.confidence, result.signals)
    """

    def classify(
        self,
        goal: str,
        filename: Optional[str] = None,
        *,
        allow_llm_fallback: bool = False,   # Phase 7.6+ stub
    ) -> TaskClassification:
        """Classify *goal* (and optional uploaded *filename*) into a TaskType.

        Logs task_type, confidence, signals, and latency for every call so the
        sovereignty dashboard can count local model invocations.
        """
        t0 = time.perf_counter()

        scores: dict[TaskType, float] = {t: 0.0 for t in TaskType}
        signals: list[str] = []

        # --- Stage 1a: file-extension heuristic ---
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in _VISION_EXTENSIONS:
                scores[TaskType.VISION] += 0.50
                signals.append(f"file extension '{ext}' -> vision/OCR")

        # --- Stage 1b: keyword rules ---
        text = goal.strip()
        for pattern, task_type, boost, label in _RULES:
            if pattern.search(text):
                scores[task_type] += boost
                signals.append(label)

        # Normalise so scores don't exceed 1.0
        for t in scores:
            scores[t] = min(scores[t], 1.0)

        # Pick the winner
        best_type = max(scores, key=lambda t: scores[t])
        confidence = scores[best_type]

        # --- Stage 2: LLM fallback (stub for Phase 7.6) ---
        fallback_used = False
        if confidence < _CONFIDENCE_THRESHOLD and allow_llm_fallback:
            # Placeholder: will call ModelRouter(TaskType.REASONING) and ask the
            # model to classify the goal. For now falls back to REASONING which
            # is the safest default for industrial workbench tasks.
            best_type = TaskType.REASONING
            confidence = 0.45
            signals.append("low-confidence rule pass -> LLM fallback (stub) -> default: reasoning")
            fallback_used = True

        # Default: if everything scored 0, reasoning is the safest choice
        if confidence == 0.0:
            best_type = TaskType.REASONING
            confidence = 0.30
            signals.append("no signals matched -> default: reasoning")

        latency_ms = (time.perf_counter() - t0) * 1000

        result = TaskClassification(
            task_type=best_type,
            confidence=round(confidence, 3),
            signals=signals,
            fallback_used=fallback_used,
            latency_ms=round(latency_ms, 2),
        )

        logger.info(
            "TASK_CLASSIFIED | task_type=%s | confidence=%.3f | fallback=%s "
            "| latency_ms=%.2f | signals=%s | goal=%.120r",
            result.task_type,
            result.confidence,
            result.fallback_used,
            result.latency_ms,
            result.signals,
            goal,
        )

        return result


# ---------------------------------------------------------------------------
# Module-level singleton (import and call directly)
# ---------------------------------------------------------------------------

_classifier = TaskClassifier()


def classify_task(
    goal: str,
    filename: Optional[str] = None,
    *,
    allow_llm_fallback: bool = False,
) -> TaskClassification:
    """Convenience wrapper around the module-level TaskClassifier singleton."""
    return _classifier.classify(goal, filename, allow_llm_fallback=allow_llm_fallback)
