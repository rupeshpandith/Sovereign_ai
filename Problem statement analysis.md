# Problem Statement Analysis — PS 26117
## Sovereign On-Premise Agentic AI Workbench for Confidential Industrial Work

---

## 1. What This Problem Statement Is Asking

MRPL (Mangalore Refinery and Petrochemicals Limited) wants a private AI system — like ChatGPT/Claude, but running entirely inside their own infrastructure, with no internet connection. Employees handle confidential data (P&IDs, financial data, vendor negotiations, unreleased designs). They cannot send this data to cloud AI tools. They also cannot go back to fully manual work because it is slow.

The system must:
- Run 100% on local hardware (no internet dependency)
- Use multiple open-weight AI models (not just one)
- Automatically pick the right model for each task
- Understand text, scanned documents, images, and drawings (multimodal)
- Act as an agent: plan → use tools → verify → produce a real output file
- Prove, visibly, that no data ever leaves the organization

---

## 2. Who Uses This

**Primary users:**
- Engineers (inspection, maintenance)
- Plant operators
- Officers who write/approve documents
- Internal software teams
- Finance/procurement staff

**Secondary stakeholders:**
- IT/security administrators (must trust the system)
- Management (needs measurable productivity gain)
- Compliance/CISO teams

---

## 3. Why This Problem Matters

Today, an engineer might spend hours reading a scanned inspection report, searching old SOPs manually, and writing an approval note by hand. Cloud AI could do this in minutes — but the data is confidential, so it's off-limits. The result is wasted engineer time and slow approvals. A sovereign AI workbench recovers that lost productivity without breaking security rules.

---

## 4. Current Challenges

| Challenge | Why It Happens |
|---|---|
| Can't use ChatGPT/Claude/etc. | Confidential data cannot leave the org |
| Local chatbots are too basic | They only answer questions, don't do work |
| One model can't do everything well | Coding, vision, and reasoning need different models |
| Manuals/SOPs are scattered | No searchable local knowledge base |
| Scanned documents are hard to process | Needs OCR + vision understanding |
| Giving AI the ability to act is risky | Needs sandboxing and permission limits |

---

## 5. Our Proposed Solution — In Simple Terms

We are building a **Sovereign Agent Workbench**: a local web application where an employee uploads a document (or types a request), and an AI agent:

1. Reads/understands the document (using OCR + vision if scanned)
2. Searches the organization's own knowledge base (SOPs, past reports)
3. Picks the right AI model for the task (reasoning model for writing, coding model for scripts, vision model for images)
4. Uses safe, limited tools (read files, search knowledge, run code in a sandbox, generate Word/Excel files)
5. Shows exactly where each fact came from (evidence/citations)
6. Asks a human to approve before anything sensitive happens
7. Produces a real, usable output file (e.g., an approval note in `.docx`)

All of this happens with the internet **physically disconnected** to prove there is zero data leakage.

---

## 6. How the Complete Project Works (User Journey)

**Step 1 — Login**
User logs into the local web app (simple username/password, or role-based).

**Step 2 — Upload / Ask**
User uploads a document (PDF, scanned image, photo) or types a request like:
> "Review this inspection report and draft an approval note."

**Step 3 — Understanding**
- If the file is scanned/an image → OCR + vision model extracts the text/data.
- If it's a normal PDF/text → parsed directly.

**Step 4 — Agent Planning**
The Agent Manager decides what steps are needed: Does it need to search SOPs? Does it need a calculation? Does it need to generate a file?

**Step 5 — Model Routing**
A Task Classifier picks the right model:
- Reasoning/document tasks → Reasoning LLM
- Coding tasks → Coding LLM
- Image/drawing tasks → Vision LLM

**Step 6 — Knowledge Retrieval (RAG)**
The agent searches the local knowledge base (SOPs, manuals, past approval notes) and pulls only relevant, cited chunks.

**Step 7 — Tool Use**
The agent may: run a Python calculation in a sandbox, search documents, or generate a Word/Excel/PPT file. It **cannot** browse the internet, access random files, or run unrestricted commands.

**Step 8 — Evidence Display**
Every claim the agent makes is shown next to its source document and page number.

**Step 9 — Human Approval**
For sensitive actions (e.g., finalizing an approval note, deleting a file), the system pauses and asks a human to click Approve/Reject.

**Step 10 — Deliverable**
The user downloads the final file (e.g., `Approval_Note.docx`).

**Step 11 — Sovereignty Proof**
A dashboard shows: External calls = 0, Internet = Blocked, Local model calls = N. This can be demonstrated with the internet physically unplugged.

---

## 7. Major Modules of the Project

1. **Frontend Workbench UI** — chat + file upload + dashboard
2. **Agent Manager** — plans tasks, decides tool usage
3. **Model Router** — chooses the right local model per task
4. **Local Knowledge Base (RAG)** — SOPs, manuals, reports, embeddings, vector search
5. **Tool Layer** — sandboxed code execution, file read/write, DOCX/XLSX/PPTX generation
6. **Evidence/Citation Engine** — links every answer back to its source
7. **Human Approval Layer** — approval gates for sensitive actions
8. **Sovereignty Dashboard** — proves zero external network calls
9. **Auth & Roles** — login, basic role-based permissions
10. **Local Model Serving** — hosts the actual open-weight LLMs

---

## 8. Expected Benefits

- Confidential data never leaves the organization
- Engineers get AI-assisted drafting instead of fully manual work
- One platform handles documents, images, and code — not separate tools
- Every AI output is traceable to a real source (less hallucination risk)
- Sensitive actions always require a human decision
- Architecture can scale from one laptop to an enterprise GPU cluster later

---

## 9. What to Build at Each SIH Stage

### Internal Round (MVP) — "Prove the Core Loop Works"
- One flagship workflow: Upload inspection report → OCR/parse → search local SOP → draft approval note → export `.docx`
- At least 2 models being routed to (reasoning + coding OR vision)
- Basic RAG over 10–15 sample documents
- Basic sandboxed Python execution for one calculation task
- A simple sovereignty indicator (even a static "0 external calls" panel is fine at this stage)
- Basic login (single role is acceptable)

### National Round — "Make It Convincing and Robust"
- Full model router with 3+ model classes (reasoning, coding, vision/OCR)
- Real vector database RAG with citations shown in the UI
- Human-approval gate before finalizing/exporting documents
- Live sovereignty dashboard with real network telemetry (not static)
- Multimodal input: scanned PDFs, photos, and a sample P&ID
- Multiple output formats: DOCX + XLSX
- Role-based access (engineer vs approver vs admin)

### Grand Finale — "Show the Platform Vision"
- Mini knowledge graph connecting equipment ↔ SOPs ↔ past reports (Architecture 2 elements)
- Multiple specialized agents (Document Agent, Coding Agent, Engineering Agent) coordinated by one orchestrator
- Policy engine defining exactly what each agent/tool is allowed to do
- P&ID tag extraction as a research-flavored stretch feature
- Full audit log + admin dashboard
- Demonstrated on a disconnected machine, live, in front of judges

---

## 10. Assumptions Made

1. No real MRPL confidential data will be used — synthetic/public sample documents will substitute (as the PS explicitly allows).
2. Hardware for the hackathon is a single workstation/laptop with a mid-range GPU (or CPU-only fallback with smaller models).
3. Open-weight models available via Hugging Face/Ollama will be used — no model training from scratch.
4. "Air-gapped" is demonstrated as network isolation at the OS/firewall level, not merely an app setting.
5. Authentication can start as basic (single admin login) for the internal round and expand to full RBAC later.
6. The flagship demo workflow (inspection report → approval note) is the single most important deliverable; all other features are secondary.
