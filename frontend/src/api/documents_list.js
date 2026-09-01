// Fetch uploaded documents from the backend database.
// GET /documents → [{document_id, filename, status}]
export async function listDocuments() {
  // Built from localStorage only — no backend list endpoint in Phase 4.
  // Documents are stored via saveDocuments() after each upload.
  return null  // use localStorage only (see useWorkbenchState)
}
