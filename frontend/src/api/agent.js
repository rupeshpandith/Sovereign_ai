// Agent endpoints. Live: POST /agent/run -> { agent_run_id, status };
// GET /agent/run/{id}/status -> { status, steps_completed[], model_used{}, evidence[] }.
// No websockets (Architecture §4.2) — the UI polls getRunStatus on an interval.
import { api, USE_MOCKS, delay } from './client'
import { MOCK_RUN_ID, mockRunStatus, resetMockRun } from './mocks'

export async function runAgent({ goal, document_id }) {
  if (USE_MOCKS) {
    await delay(400)
    resetMockRun()
    return { agent_run_id: MOCK_RUN_ID, status: 'in_progress' }
  }
  const { data } = await api.post('/agent/run', { goal, document_id })
  return data // { agent_run_id, status }
}

export async function getRunStatus(runId) {
  if (USE_MOCKS) {
    await delay(300)
    return mockRunStatus()
  }
  const { data } = await api.get(`/agent/run/${runId}/status`)
  return data // { status, steps_completed, model_used, evidence }
}
