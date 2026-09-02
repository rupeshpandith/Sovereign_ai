"""Pytest configuration for the backend test suite (Phase 9).

Ensures ``import app...`` resolves regardless of the directory pytest is
launched from (repo root, ``backend/``, or ``backend/tests/``) by putting the
``backend/`` directory on ``sys.path``.

Also pins the process to offline behaviour so no test can accidentally reach
the network — consistent with the project's sovereignty constraint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# backend/ is the parent of this tests/ directory.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Belt-and-braces: keep any library that respects these vars offline.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
