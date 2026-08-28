// Canonical mock fixtures. Shapes mirror Architecture 5 exactly; values use the
// flagship demo entities (run 101 / doc 42, pump P-204, inspection_892.pdf p.3,
// SOP-17.pdf p.1, >7 mm/s, Approval_Note_101.docx) so Phase 6 wiring is seamless.

// --- auth: mirrors the three seeded backend users (all password demo1234) ---
export const DEMO_USERS = {
  engineer1: { password: 'demo1234', role: 'engineer' },
  approver1: { password: 'demo1234', role: 'approver' },
  admin1: { password: 'demo1234', role: 'admin' },
}

export function mockLogin(username, password) {
  const user = DEMO_USERS[username]
  if (!user || user.password !== password) return null
  return { access_token: `mock.${username}.${user.role}`, role: user.role }
}

// --- documents: list is built from upload responses (no GET /documents in Phase 4) ---
export const INITIAL_DOCUMENTS = [
  { document_id: 42, filename: 'inspection_892.pdf', status: 'parsed' },
]

let _nextDocId = 43
export function mockUpload(filename) {
  return { document_id: _nextDocId++, filename, status: 'parsed' }
}

// --- agent run: canonical id + a poll progression that tells the P-204 story ---
export const MOCK_RUN_ID = 101

// Evidence includes sourced rows plus a low-confidence and an unsourced-reasoning
// row, to exercise the states Architecture 16/9 require in the evidence UI.
const EVIDENCE_FULL = [
  { claim: 'Pump P-204 shows vibration above threshold', source: 'inspection_892.pdf', page: 3 },
  { claim: 'SOP-17 requires shutdown at >7 mm/s', source: 'SOP-17.pdf', page: 1 },
  {
    claim: 'Bearing DE reading measured at 8.2 mm/s',
    source: 'inspection_892.pdf',
    page: 3,
    confidence: 'low',
  },
  { claim: 'Recommend immediate shutdown pending re-inspection', kind: 'reasoning' },
]

// Successive poll frames: in_progress -> in_progress -> awaiting_approval.
const STATUS_FRAMES = [
  {
    status: 'in_progress',
    steps_completed: ['ocr'],
    model_used: { extract: 'vision-llm' },
    evidence: [],
  },
  {
    status: 'in_progress',
    steps_completed: ['ocr', 'retrieve_sop'],
    model_used: { extract: 'vision-llm', retrieve_sop: 'embed-local' },
    evidence: EVIDENCE_FULL.slice(0, 2),
  },
  {
    status: 'awaiting_approval',
    steps_completed: ['ocr', 'retrieve_sop', 'draft_note'],
    model_used: { extract: 'vision-llm', retrieve_sop: 'embed-local', draft_note: 'reasoning-llm' },
    evidence: EVIDENCE_FULL,
  },
]

let _pollIndex = 0
export function resetMockRun() {
  _pollIndex = 0
}
export function mockRunStatus() {
  const frame = STATUS_FRAMES[Math.min(_pollIndex, STATUS_FRAMES.length - 1)]
  _pollIndex += 1
  return frame
}

// --- approvals: no backend list endpoint (Phase 4); demo queue only ---
export const MOCK_APPROVALS = [
  {
    approval_id: 501,
    agent_run_id: 101,
    action: 'Export approval note — P-204 shutdown recommendation',
    status: 'pending',
    requested_by: 'engineer1',
    created_at: '2026-08-27T09:14:00Z',
  },
  {
    approval_id: 502,
    agent_run_id: 104,
    action: 'Export approval note — V-11 relief-valve re-test',
    status: 'pending',
    requested_by: 'engineer1',
    created_at: '2026-08-27T10:02:00Z',
  },
]

export function mockDecide(approvalId, decision) {
  const status = decision === 'approve' ? 'approved' : 'rejected'
  const output_file = decision === 'approve' ? `/outputs/Approval_Note_${approvalId}.docx` : null
  return { status, output_file }
}

// --- sovereignty: the numbers judges watch ---
export const MOCK_SOVEREIGNTY = {
  external_calls: 0,
  internet_status: 'blocked',
  local_model_calls: 17,
  documents_processed: 4,
  sandbox_executions: 1,
}

// --- admin: mock-only surface (no Phase 4 endpoint backs it) ---
export const MOCK_ADMIN_USERS = [
  { username: 'engineer1', role: 'engineer', status: 'active' },
  { username: 'approver1', role: 'approver', status: 'active' },
  { username: 'admin1', role: 'admin', status: 'active' },
]

export const MOCK_AUDIT_LOG = [
  { timestamp: '2026-08-27T09:12:41Z', event_type: 'document_upload', detail: 'inspection_892.pdf', external_attempt_blocked: false },
  { timestamp: '2026-08-27T09:13:02Z', event_type: 'local_model_call', detail: 'vision-llm · extract', external_attempt_blocked: false },
  { timestamp: '2026-08-27T09:13:20Z', event_type: 'local_model_call', detail: 'embed-local · retrieve_sop', external_attempt_blocked: false },
  { timestamp: '2026-08-27T09:13:44Z', event_type: 'sandbox_execution', detail: 'vibration threshold check', external_attempt_blocked: false },
  { timestamp: '2026-08-27T09:14:00Z', event_type: 'external_call_blocked', detail: 'egress denied by network guard', external_attempt_blocked: true },
]
