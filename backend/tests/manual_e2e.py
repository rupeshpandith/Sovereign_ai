"""Manual end-to-end test script for the flagship workflow — Phase 9 (Plan.md §9).

This is NOT a pytest test (the filename has no ``test_`` prefix so pytest skips
it). It drives a LIVE, running backend over HTTP to exercise the full flagship
demo path end to end:

    login (engineer) -> upload inspection report -> run agent
        -> poll until awaiting_approval -> inspect steps + evidence
        -> login (admin) -> sovereignty dashboard shows zero external calls

Per Plan.md §9 the flagship demo must run 3 times consecutively without failure;
use ``--runs 3`` to do exactly that.

Prerequisites (this script does not start them):
    1. Backend running:   cd backend && uvicorn app.main:app --reload
    2. Ollama running with the model from model_registry.yaml pulled
       (otherwise the pipeline finishes as "failed" — the script reports it).

Usage:
    cd backend
    python tests/manual_e2e.py                 # one run against localhost:8000
    python tests/manual_e2e.py --runs 3         # judge-criterion: 3x consecutive
    python tests/manual_e2e.py --doc data/sample_docs/inspection_report_811.txt

Exit code is 0 only if every requested run reaches "awaiting_approval" AND the
sovereignty dashboard reports zero external calls.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

# Demo credentials are seeded locally by app.core.security.seed_demo_users.
ENGINEER = ("engineer1", "demo1234")
ADMIN = ("admin1", "demo1234")

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_DOC = "data/sample_docs/inspection_report_745.txt"
DEFAULT_GOAL = (
    "Analyse this inspection report against the applicable SOP and draft an "
    "equipment continued-operation approval note."
)

# ANSI helpers (safe to leave on; Windows terminals handle these in modern shells).
_OK = "\033[92m"
_FAIL = "\033[91m"
_DIM = "\033[2m"
_END = "\033[0m"


def _say(msg: str) -> None:
    print(msg, flush=True)


def _login(client: httpx.Client, base: str, username: str, password: str) -> str:
    resp = client.post(f"{base}/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def _upload(client: httpx.Client, base: str, token: str, doc_path: Path) -> int:
    with doc_path.open("rb") as fh:
        files = {"file": (doc_path.name, fh, "text/plain")}
        resp = client.post(
            f"{base}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
    resp.raise_for_status()
    body = resp.json()
    _say(f"   uploaded '{doc_path.name}' -> document_id={body['document_id']} "
         f"(status={body['status']})")
    return body["document_id"]


def _run_agent(client: httpx.Client, base: str, token: str, document_id: int, goal: str) -> int:
    resp = client.post(
        f"{base}/agent/run",
        headers={"Authorization": f"Bearer {token}"},
        json={"goal": goal, "document_id": document_id},
    )
    resp.raise_for_status()
    return resp.json()["agent_run_id"]


def _poll(client: httpx.Client, base: str, token: str, run_id: int, timeout_s: float) -> dict:
    deadline = time.time() + timeout_s
    headers = {"Authorization": f"Bearer {token}"}
    last: dict = {}
    while time.time() < deadline:
        resp = client.get(f"{base}/agent/run/{run_id}/status", headers=headers)
        resp.raise_for_status()
        last = resp.json()
        status = last.get("status")
        steps = last.get("steps_completed") or []
        _say(f"   {_DIM}status={status} | steps={len(steps)}: {', '.join(steps)}{_END}")
        if status != "in_progress":
            return last
        time.sleep(2.0)
    _say(f"   {_FAIL}timed out after {timeout_s:.0f}s waiting for run {run_id}{_END}")
    return last


def _one_run(client: httpx.Client, base: str, doc_path: Path, goal: str, timeout_s: float, idx: int) -> bool:
    _say(f"\n=== FLAGSHIP RUN {idx} ===")

    _say(" 1. login (engineer)…")
    eng_token = _login(client, base, *ENGINEER)

    _say(" 2. upload inspection report…")
    document_id = _upload(client, base, eng_token, doc_path)

    _say(" 3. run agent pipeline…")
    run_id = _run_agent(client, base, eng_token, document_id, goal)
    _say(f"   agent_run_id={run_id}")

    _say(" 4. poll for completion…")
    final = _poll(client, base, eng_token, run_id, timeout_s)
    status = final.get("status")
    evidence = final.get("evidence") or []
    models = final.get("model_used") or {}

    _say(f"   final status: {status}")
    _say(f"   models used: {models}")
    _say(f"   evidence items: {len(evidence)}")
    for ev in evidence[:5]:
        _say(f"     - {_DIM}{ev.get('claim', '')[:100]}{_END}")

    if status != "awaiting_approval":
        _say(f"   {_FAIL}RUN {idx} did not reach awaiting_approval (got {status!r}).{_END}")
        _say(f"   {_DIM}Hint: is Ollama running with the model from "
             f"model_registry.yaml pulled?{_END}")
        return False

    _say(f"   {_OK}RUN {idx} reached awaiting_approval.{_END}")
    return True


def _check_sovereignty(client: httpx.Client, base: str) -> bool:
    _say("\n=== SOVEREIGNTY CHECK (admin) ===")
    admin_token = _login(client, base, *ADMIN)
    resp = client.get(
        f"{base}/sovereignty/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp.raise_for_status()
    s = resp.json()
    external = s.get("external_api_calls", -1)
    cloud = s.get("cloud_llm_calls", -1)
    local_calls = s.get("local_model_calls", -1)
    _say(f"   internet_status      = {s.get('internet_status')}")
    _say(f"   external_api_calls   = {external}")
    _say(f"   cloud_llm_calls      = {cloud}")
    _say(f"   local_model_calls    = {local_calls}")
    _say(f"   documents_processed  = {s.get('documents_processed')}")
    _say(f"   data_residency       = {s.get('data_residency')}")

    ok = external == 0 and cloud == 0
    if ok:
        _say(f"   {_OK}Zero external / cloud calls — sovereignty holds.{_END}")
    else:
        _say(f"   {_FAIL}Non-zero external calls detected!{_END}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Flagship end-to-end manual test.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--doc", default=DEFAULT_DOC, help="path to the document to upload")
    parser.add_argument("--goal", default=DEFAULT_GOAL)
    parser.add_argument("--runs", type=int, default=1, help="consecutive flagship runs")
    parser.add_argument("--poll-timeout", type=float, default=180.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    doc_path = Path(args.doc)
    if not doc_path.exists():
        _say(f"{_FAIL}Document not found: {doc_path.resolve()}{_END}")
        _say(f"{_DIM}Run this script from the backend/ directory, or pass --doc.{_END}")
        return 1

    try:
        with httpx.Client(timeout=30.0) as client:
            # Fail fast with a clear message if the backend isn't up.
            try:
                health = client.get(f"{base}/health")
                health.raise_for_status()
            except Exception as exc:
                _say(f"{_FAIL}Backend not reachable at {base} ({exc}).{_END}")
                _say(f"{_DIM}Start it: cd backend && uvicorn app.main:app --reload{_END}")
                return 1

            run_results: list[bool] = []
            for i in range(1, args.runs + 1):
                run_results.append(
                    _one_run(client, base, doc_path, args.goal, args.poll_timeout, i)
                )

            sovereignty_ok = _check_sovereignty(client, base)
    except httpx.HTTPStatusError as exc:
        _say(f"{_FAIL}HTTP error: {exc.response.status_code} {exc.response.text[:200]}{_END}")
        return 1
    except Exception as exc:  # noqa: BLE001
        _say(f"{_FAIL}Unexpected error: {exc}{_END}")
        return 1

    passed = sum(run_results)
    _say("\n============================================")
    _say(f" flagship runs: {passed}/{len(run_results)} reached awaiting_approval")
    _say(f" sovereignty:   {'PASS' if sovereignty_ok else 'FAIL'}")
    all_ok = passed == len(run_results) and sovereignty_ok
    _say(f" OVERALL:       {(_OK + 'PASS') if all_ok else (_FAIL + 'FAIL')}{_END}")
    _say("============================================")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
