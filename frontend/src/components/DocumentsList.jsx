// Local document register. In Phase 4 there is no GET /documents endpoint, so this
// list is built from upload responses — each row's DB-assigned document_id is the
// proof that the file round-tripped to the backend.
const STATUS_STATE = {
  parsed: 'nominal',
  uploaded: 'accent',
  processing: 'caution',
  failed: 'trip',
}

export default function DocumentsList({ documents = [], selectedId, onSelect }) {
  if (!documents.length) {
    return <div className="text-sm text-muted py-4">No documents yet. Upload a scanned report to begin.</div>
  }

  return (
    <ul className="flex flex-col gap-1">
      {documents.map((doc) => {
        const selected = doc.document_id === selectedId
        return (
          <li key={doc.document_id}>
            <button
              type="button"
              onClick={() => onSelect?.(doc)}
              className={`w-full text-left rounded border px-3 py-2 flex items-center gap-3 transition-colors ${
                selected ? 'border-accent bg-panel2' : 'border-border hover:border-steel'
              }`}
            >
              <span className={`led led-${STATUS_STATE[doc.status] || 'accent'}`} aria-hidden="true" />
              <span className="text-sm text-text truncate">{doc.filename}</span>
              <span className="chip ml-auto shrink-0">
                <span className="text-muted">#</span>
                {doc.document_id}
              </span>
              <span className="mono text-xs text-muted shrink-0">{doc.status}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
