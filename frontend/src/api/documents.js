// Documents endpoint. Live: POST /documents/upload (multipart `file`)
// -> { document_id, filename, status }. Phase 4 has no list endpoint, so the
// documents list is assembled client-side from these upload responses.
import { api, USE_MOCKS, delay } from './client'
import { INITIAL_DOCUMENTS, mockUpload } from './mocks'

export function initialDocuments() {
  return USE_MOCKS ? [...INITIAL_DOCUMENTS] : []
}

export async function uploadDocument(file) {
  if (USE_MOCKS) {
    await delay(500)
    return mockUpload(file?.name ?? 'document.pdf')
  }
  const form = new FormData()
  form.append('file', file)
  // Let the browser set the multipart boundary; don't force Content-Type.
  const { data } = await api.post('/documents/upload', form)
  return data // { document_id, filename, status }
}
