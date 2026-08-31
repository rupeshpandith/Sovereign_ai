"""Sandbox Code Runner — Plan.md §7.5.

Executes untrusted Python calculation snippets in a restricted subprocess so the
agent can safely evaluate numerical claims (e.g. "is 6.7 mm/s within the 72-hour
tolerance given a 0.4 mm/s/day degradation rate?") without giving the model direct
access to the host shell.

Security model
--------------
Primary path — Docker container (production):
    Runs the snippet inside a minimal Python container with:
      --network none     no network egress
      --memory 128m      OOM guard
      --cpus 0.5         CPU cap
      --read-only        immutable filesystem
    Docker isolation ensures the sandbox has zero access to:
      • the host filesystem (only the snippet is bind-mounted in)
      • the network
      • other containers or processes

Fallback path — restricted subprocess (dev / Docker not available):
    Wraps the snippet in a very tight allowed-builtins exec() context.
    This is NOT as strong as Docker but is safe enough for numeric calculations
    that only use standard math operations.  The allowlist explicitly excludes
    __import__, open, exec, eval, compile, and all OS-related builtins.

Both paths:
    • Enforce a hard wall-clock timeout (default 10 s).
    • Capture stdout and limit output to 4 KB.
    • Return SandboxResult — never raise into the planner.
    • Log event_type="sandbox_execution" to SovereigntyLog so the dashboard
      shows real counts.

Sovereignty constraint
----------------------
The sandbox never makes network calls.  Docker enforces this at the kernel
network namespace level.  The subprocess fallback enforces it by omitting
socket/urllib/requests from the allowed namespace.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum wall-clock seconds allowed for one sandbox run.
SANDBOX_TIMEOUT_SECONDS = 10

# Maximum bytes read from the subprocess stdout.
SANDBOX_MAX_OUTPUT_BYTES = 4096

# Docker image used for the strong isolation path.
DOCKER_IMAGE = "python:3.12-slim"

# Allowlist for the restricted exec() fallback.
# Intentionally minimal — only math builtins + safe types.
_SAFE_BUILTINS = {
    "abs": abs, "bool": bool, "divmod": divmod, "float": float,
    "int": int, "len": len, "max": max, "min": min, "pow": pow,
    "print": print, "range": range, "round": round, "str": str,
    "sum": sum, "tuple": tuple, "list": list, "dict": dict,
    "True": True, "False": False, "None": None,
    "isinstance": isinstance, "type": type,
    "zip": zip, "enumerate": enumerate, "sorted": sorted,
    "reversed": reversed, "map": map, "filter": filter,
}


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class SandboxResult:
    """Outcome of one sandbox execution."""
    success: bool
    output: str              # captured stdout (truncated to SANDBOX_MAX_OUTPUT_BYTES)
    error: Optional[str]     # exception / timeout message if not successful
    method: str              # "docker" | "restricted_exec" | "failed"
    latency_ms: float
    code_snippet: str        # the snippet that was run (for audit trail)


# ---------------------------------------------------------------------------
# Docker path (strong isolation)
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    """Return True if docker CLI is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_in_docker(snippet: str) -> SandboxResult:
    """Execute *snippet* inside a Docker container with --network none."""
    t0 = time.perf_counter()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(snippet)
        tmp_path = tmp.name

    try:
        proc = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "128m",
                "--cpus", "0.5",
                "--read-only",
                # Run as an unprivileged user — never as root.
                # Architecture.md §10: sandbox must enforce least-privilege.
                "--user", "1000:1000",
                "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL",
                "-v", f"{tmp_path}:/sandbox/run.py:ro",
                DOCKER_IMAGE,
                "python", "/sandbox/run.py",
            ],
            capture_output=True,
            timeout=SANDBOX_TIMEOUT_SECONDS,
            text=True,
        )
        output = (proc.stdout or "")[:SANDBOX_MAX_OUTPUT_BYTES]
        err = proc.stderr.strip() if proc.stderr else None
        success = proc.returncode == 0

        if not success and err:
            logger.warning("SANDBOX_DOCKER_ERR | returncode=%d | stderr=%s", proc.returncode, err)

        return SandboxResult(
            success=success,
            output=output,
            error=err if not success else None,
            method="docker",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            code_snippet=snippet,
        )

    except subprocess.TimeoutExpired:
        return SandboxResult(
            success=False, output="",
            error=f"Sandbox timed out after {SANDBOX_TIMEOUT_SECONDS}s (Docker)",
            method="docker",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            code_snippet=snippet,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Restricted exec() fallback
# ---------------------------------------------------------------------------

def _run_restricted_exec(snippet: str) -> SandboxResult:
    """Execute *snippet* in a tightly restricted exec() context.

    Only safe math/type builtins are available.  __import__, open, os, sys,
    socket, and all shell-access functions are absent from the namespace.
    This is suitable for numeric calculations but NOT as strong as Docker.
    """
    t0 = time.perf_counter()
    namespace: dict = {"__builtins__": _SAFE_BUILTINS}

    # Redirect print() to a buffer
    import io
    buf = io.StringIO()

    safe_builtins_with_print = dict(_SAFE_BUILTINS)
    safe_builtins_with_print["print"] = lambda *a, **kw: buf.write(" ".join(str(x) for x in a) + "\n")
    namespace["__builtins__"] = safe_builtins_with_print

    try:
        exec(compile(snippet, "<sandbox>", "exec"), namespace)  # noqa: S102
        output = buf.getvalue()[:SANDBOX_MAX_OUTPUT_BYTES]
        return SandboxResult(
            success=True, output=output, error=None,
            method="restricted_exec",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            code_snippet=snippet,
        )
    except Exception as exc:  # noqa: BLE001
        return SandboxResult(
            success=False, output=buf.getvalue()[:SANDBOX_MAX_OUTPUT_BYTES],
            error=f"{type(exc).__name__}: {exc}",
            method="restricted_exec",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            code_snippet=snippet,
        )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_sandbox(snippet: str, db_session=None) -> SandboxResult:
    """Execute *snippet* in the safest available sandbox.

    Tries Docker first (strong isolation, network=none).
    Falls back to restricted exec() if Docker is not available.

    Logs a SovereigntyLog row with event_type="sandbox_execution" so the
    dashboard can display a real count.

    Args:
        snippet:    Python source code to execute.
        db_session: Optional SQLAlchemy session for sovereignty logging.
                    If None, the sovereignty log entry is skipped.

    Returns:
        SandboxResult — never raises.
    """
    logger.info(
        "SANDBOX_START | method=auto | snippet_len=%d", len(snippet)
    )

    try:
        if _docker_available():
            logger.info("SANDBOX_METHOD | docker=available | using Docker isolation")
            result = _run_in_docker(snippet)
        else:
            # SECURITY: The restricted exec() fallback has been intentionally disabled.
            # Python's exec() with a restricted __builtins__ dict is NOT safe against
            # determined attackers — object hierarchy traversal can escape the sandbox
            # (see Architecture.md §10, Plan.md §7.5 "no-network Docker container").
            #
            # If Docker is unavailable we fail hard rather than run insecurely.
            # This means the sandbox step surfaces an error to the planner, which
            # will surface it to the human approver — the correct outcome when the
            # environment is not correctly configured.
            logger.error(
                "SANDBOX_REFUSED | reason=Docker_unavailable | "
                "policy=fail-safe (exec() fallback disabled for security) | "
                "action=return_error_to_planner"
            )
            result = SandboxResult(
                success=False,
                output="",
                error=(
                    "Sandbox execution refused: Docker is not available and the "
                    "restricted-exec fallback is disabled (security policy). "
                    "Install Docker and ensure the daemon is running."
                ),
                method="refused",
                latency_ms=0.0,
                code_snippet=snippet,
            )
    except Exception as exc:  # noqa: BLE001
        result = SandboxResult(
            success=False, output="",
            error=f"Sandbox setup error: {exc}",
            method="failed",
            latency_ms=0.0,
            code_snippet=snippet,
        )

    logger.info(
        "SANDBOX_DONE | method=%s | success=%s | output_len=%d | latency_ms=%.1f | error=%s",
        result.method, result.success, len(result.output), result.latency_ms, result.error,
    )

    # Write to sovereignty log
    if db_session is not None:
        try:
            from app.models.db_models import SovereigntyLog
            db_session.add(SovereigntyLog(
                event_type="sandbox_execution",
                external_attempt_blocked=False,
            ))
            db_session.commit()
        except Exception as log_exc:
            logger.warning("SANDBOX_SOVEREIGNTY_LOG_FAILED | error=%s", log_exc)

    return result


# ---------------------------------------------------------------------------
# Convenience: generate a calculation snippet from a plain-English expression
# ---------------------------------------------------------------------------

def make_calculation_snippet(expression: str, variables: dict[str, float]) -> str:
    """Build a simple Python snippet that assigns *variables* and prints *expression*.

    Example:
        make_calculation_snippet("vibration + degradation_rate * hours", {"vibration": 6.7, ...})
        →
        vibration = 6.7
        ...
        result = vibration + degradation_rate * hours
        print(f"result = {result}")
    """
    lines = [f"{k} = {v!r}" for k, v in variables.items()]
    lines.append(f"result = {expression}")
    lines.append('print(f"result = {result}")')
    return "\n".join(lines)
