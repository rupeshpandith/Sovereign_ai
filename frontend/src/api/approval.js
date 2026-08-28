// Approval endpoints. Live: POST /approval/{id}/decide { decision } ->
// { status, output_file }. Phase 4 has no pending-queue list endpoint, so the
// queue is a mock/demo surface; the decide call is wired for both modes.
import { api, USE_MOCKS, delay } from './client'
import { MOCK_APPROVALS, mockDecide } from './mocks'

export async function listPendingApprovals() {
  if (USE_MOCKS) {
    await delay(250)
    return MOCK_APPROVALS.filter((a) => a.status === 'pending')
  }
  // No Phase 4 list endpoint yet — nothing to show in live mode until Phase 7.
  return []
}

export async function decideApproval(approvalId, decision) {
  if (USE_MOCKS) {
    await delay(400)
    return mockDecide(approvalId, decision)
  }
  const { data } = await api.post(`/approval/${approvalId}/decide`, { decision })
  return data // { status, output_file }
}
