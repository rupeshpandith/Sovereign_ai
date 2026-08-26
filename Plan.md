# Plan.md — Full Implementation Plan
## Sovereign Agentic AI Workbench (PS 26117)

This file is the primary reference for Claude Code CLI. Follow phases in order. Do not skip Phase 0.

---

## 0. Project Overview

**Goal:** A local web app where a user uploads a document or types a request, an AI agent classifies the task, routes it to the right local model, retrieves relevant internal knowledge, uses sandboxed tools, and produces a real deliverable file — with zero external network calls.

**Chosen architecture:** Hybrid of Architecture 1 (Sovereign Agent Workbench) + Architecture 2 (Industrial Copilot with lightweight knowledge graph). Full reasoning is in `Architecture.md`.

**Flagship demo workflow:** Scanned inspection report → OCR/vision → local SOP search → agent reasoning → approval note (`.docx`) → human approval → sovereignty proof.

---

## 1. Final Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TailwindCSS | Fast, beginner-friendly, good Claude Code support |
| Backend | FastAPI (Python) | Async, easy to wire to LLM/agent code, auto docs |
| Agent orchestration | Custom Python (LangGraph optional later) | Full control, avoids opaque frameworks for judges' Q&A |
| Model serving | Ollama (simplest) or vLLM (if GPU available) | Local inference, no external calls |
| Models | Reasoning: Llama-3.1-8B-Instruct or Qwen2.5-7B-Instruct; Coding: Qwen2.5-Coder-7B; Vision: Qwen2-VL-7B or LLaVA | Open-weight, runs locally |
| OCR | Tesseract or RapidOCR (local) | No cloud dependency |
| Document parsing | Docling or PyMuPDF | Handles PDFs, tables, layout |
| Embeddings | Local sentence-transformers model (e.g., bge-small) | Local, small, fast |
| Vector DB | ChromaDB (simplest) or Qdrant | Local, file-based, zero setup for MVP |
| Relational DB | SQLite (MVP) → PostgreSQL (national round) | Simplicity first |
| Sandbox | Docker container, no network | Safe code execution |
| File generation | python-docx, openpyxl, python-pptx | Real deliverables |
| Auth | JWT-based simple auth (FastAPI) | Lightweight |
| Network isolation proof | Custom middleware logging all outbound attempts + OS firewall rule | Demonstrable sovereignty |
| Deployment | Docker Compose | One-command local run |

**Do NOT use in early phases:** Kubernetes, cloud DBs, external SaaS auth providers, cloud vector DBs, cloud LLM APIs.

---

## 2. Folder Structure

```
sovereign-ai-workbench/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes_chat.py
│   │   │   ├── routes_documents.py
│   │   │   ├── routes_agent.py
│   │   │   ├── routes_auth.py
│   │   │   └── routes_sovereignty.py
│   │   ├── agent/
│   │   │   ├── planner.py
│   │   │   ├── task_classifier.py
│   │   │   ├── model_router.py
│   │   │   └── tools/
│   │   │       ├── file_tools.py
│   │   │       ├── sandbox_tool.py
│   │   │       ├── docgen_tool.py
│   │   │       └── knowledge_tool.py
│   │   ├── rag/
│   │   │   ├── ingest.py
│   │   │   ├── embed.py
│   │   │   └── retrieve.py
│   │   ├── models/
│   │   │   ├── db_models.py
│   │   │   └── schemas.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── network_guard.py
│   │   └── db/
│   │       └── database.py
│   ├── data/
│   │   ├── sample_docs/
│   │   └── vector_store/
│   ├── sandbox/
│   │   └── Dockerfile
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 3. Development Phases

### Phase 0 — Understand the Project
**What:** Read `Problem statement analysis.md` and `Architecture.md` fully before writing code.
**Why:** Prevents wrong assumptions baked into early code.
**Verify:** You can explain, out loud, the flagship demo flow without notes.

---

### Phase 1 — Setup Repository and Tools
**What to build:** Base repo skeleton, environment, tooling.
**Files/folders:** Root repo, `backend/`, `frontend/`, `.env.example`, `docker-compose.yml`.
**Commands:**
```bash
mkdir sovereign-ai-workbench && cd sovereign-ai-workbench
git init
mkdir backend frontend
```
**Backend env:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install fastapi uvicorn python-multipart sqlalchemy pydantic-settings python-jose passlib chromadb sentence-transformers python-docx openpyxl python-pptx pymupdf pytesseract pillow
pip freeze > requirements.txt
```
**Frontend env:**
```bash
cd ../frontend
npm create vite@latest . -- --template react
npm install
npm install axios tailwindcss postcss autoprefixer react-router-dom
npx tailwindcss init -p
```
**Expected output:** Both `backend/` and `frontend/` run independently with a "Hello World" page/endpoint.
**Common mistakes:** Forgetting virtual env activation; mixing global and project Python packages.
**Verify:** `uvicorn app.main:app --reload` serves `/docs`; `npm run dev` shows the Vite default page.

---

### Phase 2 — Backend Foundation
**What:** FastAPI app skeleton, config, CORS, basic health route.
**Files:** `backend/app/main.py`, `backend/app/core/config.py`.
**Example `main.py` content to have Claude Code generate:**
- FastAPI instance
- CORS middleware (only allow localhost frontend origin)
- `/health` endpoint returning `{"status": "ok"}`
**Verify:** `GET /health` returns 200 from browser and from frontend via axios.

---

### Phase 3 — Database Models
**What:** Define tables for Users, Documents, KnowledgeChunks, AgentRuns, ApprovalRequests, SovereigntyLog.
**Files:** `backend/app/models/db_models.py`, `backend/app/db/database.py`.
**Key tables:**
- `users(id, username, password_hash, role)`
- `documents(id, filename, upload_time, extracted_text, doc_type)`
- `knowledge_chunks(id, document_id, chunk_text, embedding_id, source_page)`
- `agent_runs(id, user_id, task_type, model_used, status, created_at)`
- `approval_requests(id, agent_run_id, action, status, decided_by)`
- `sovereignty_log(id, event_type, external_attempt_blocked, timestamp)`
**Commands:**
```bash
# using SQLite for MVP, no server needed
```
**Verify:** Running the app auto-creates `app.db` (SQLite) with all tables present.

---

### Phase 4 — Core APIs
**What:** Build REST endpoints.
**Endpoints (see `Architecture.md` for request/response examples):**
- `POST /auth/login`
- `POST /documents/upload`
- `POST /agent/run` (main entry: user task → agent pipeline)
- `GET /agent/run/{id}/status`
- `POST /approval/{id}/decide`
- `GET /sovereignty/status`
**Verify:** Every endpoint testable via `/docs` (Swagger UI) with dummy payloads.

---

### Phase 5 — Frontend Pages
**What:** Build UI screens.
**Pages:**
- Login page
- Workbench page (chat box + file upload + response area)
- Evidence/citations panel (source doc + page number per claim)
- Approval modal (Approve/Reject buttons)
- Sovereignty Dashboard page (external calls counter, internet status)
**Verify:** All pages render with mock/static data before wiring to backend.

---

### Phase 6 — Connect Frontend with Backend
**What:** Replace mock data with real axios calls to backend endpoints from Phase 4.
**Verify:** Upload a real PDF from the UI, see it appear in the documents list from the DB.

---

### Phase 7 — Add AI/Intelligent Features
**Step 7.1 — Model serving**
```bash
# Install Ollama, pull models locally
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull llava:7b   # vision
```
**Step 7.2 — Task Classifier** (`agent/task_classifier.py`)
- Simple rule-based + small local model classifier: input text/file type → {"document", "coding", "vision"}.
**Step 7.3 — Model Router** (`agent/model_router.py`)
- Maps task type → correct local model endpoint (Ollama API call to localhost only).
**Step 7.4 — RAG pipeline**
- `rag/ingest.py`: parse PDFs (Docling/PyMuPDF), OCR scanned pages (pytesseract), chunk text.
- `rag/embed.py`: embed chunks locally (sentence-transformers), store in ChromaDB.
- `rag/retrieve.py`: given a query, return top-k chunks + source metadata (doc name, page).
**Step 7.5 — Tools**
- `sandbox_tool.py`: runs Python code inside a no-network Docker container, returns stdout/stderr.
- `docgen_tool.py`: generates `.docx`/`.xlsx`/`.pptx` from structured agent output.
- `file_tools.py`: restricted read of uploaded documents only (no arbitrary filesystem access).
**Step 7.6 — Agent Planner**
- `planner.py`: given a user goal, decides step sequence (retrieve → reason → maybe calculate → generate file → request approval).
**Verify:** Ask "Summarize this SOP and calculate X" → see model routing logs show reasoning model + sandbox execution both firing correctly.

---

### Phase 8 — Dashboards and Analytics
**What:** Build Sovereignty Dashboard backed by real data.
**How:**
- `core/network_guard.py`: a middleware/monkeypatch that intercepts any outbound HTTP call attempt from the backend process and logs it to `sovereignty_log`. In practice, block all non-localhost destinations at the OS firewall level too.
- Dashboard queries `sovereignty_log` and `agent_runs` tables to show: total local model calls, total external attempts (should be 0), documents processed, sandbox executions.
**Verify:** Disconnect the internet cable/Wi-Fi, run the full flagship demo, confirm it still works end-to-end.

---

### Phase 9 — Testing and Debugging
**What:** Manual + automated tests.
- Unit tests for `task_classifier`, `model_router`, `retrieve.py` (backend/tests/).
- Manual end-to-end test script covering the flagship workflow.
- Edge cases: corrupted PDF, empty document, ambiguous task type, sandbox timeout.
**Commands:**
```bash
pytest backend/tests/
```
**Verify:** All tests pass; flagship demo runs 3 times consecutively without failure.

---

### Phase 10 — Deployment
**What:** One-command local deployment via Docker Compose.
**File:** `docker-compose.yml` with services: `backend`, `frontend`, `ollama`, `chromadb` (if run as a service).
**Commands:**
```bash
docker compose up --build
```
**Verify:** Fresh machine (or fresh container) can run the whole stack with one command.

---

### Phase 11 — SIH Presentation and Demo Preparation
**What to prepare:**
1. Slide deck: problem → solution → architecture → live demo → impact metrics.
2. Script for judges: "Disconnect the internet. It still works." moment.
3. Pre-recorded backup video of the full demo (in case live demo fails).
4. One-page architecture diagram (from `Architecture.md`) printed/on-screen.
5. Answers rehearsed for the anticipated Q&A in `Architecture.md`'s judge-question section.
6. Metrics table: manual time vs AI-assisted time for the flagship task, measured for real.
**Verify:** Full run-through rehearsed at least twice, timed under the demo slot length.

---

## 4. Authentication and User-Role Setup

MVP: single hardcoded admin login (JWT).
National round: roles = `engineer`, `approver`, `admin`.
- `engineer`: upload documents, run agent, cannot approve.
- `approver`: sees pending approval requests, can Approve/Reject.
- `admin`: manages users, views sovereignty logs.

---

## 5. Common Mistakes to Avoid (Project-Wide)

- Wiring in an actual external API key "just to test" — breaks the sovereignty claim permanently. Never do this, not even temporarily.
- Building the knowledge graph (Architecture 2 piece) before the core RAG + agent loop works. Sequence matters — core loop first.
- Over-investing in Kubernetes/production infra during a hackathon.
- Skipping the evidence/citation UI — judges specifically probe for hallucination-proofing.
- Giving the sandbox tool network access "temporarily for testing" and forgetting to remove it.

---

## 6. Definition of Done (Internal Round)

- [ ] Upload a scanned inspection report through the UI
- [ ] OCR/vision extracts key fields
- [ ] Agent retrieves at least one relevant SOP chunk with citation
- [ ] Agent drafts an approval note and exports `.docx`
- [ ] A human approval step is shown before final export
- [ ] Sovereignty panel shows 0 external calls during the full run
