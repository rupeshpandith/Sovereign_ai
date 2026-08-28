// Approve / reject dialog (Architecture §8 approver flow). Human-in-the-loop gate before
// any deliverable is produced. Optional comment; shows the returned output_file on approve.
import { useEffect, useState } from 'react'

export default function ApprovalModal({ open, onClose, onDecide, item, busy = false, result }) {
  const [comment, setComment] = useState('')

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape' && !busy) onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, busy, onClose])

  useEffect(() => {
    if (open) setComment('')
  }, [open, item])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 p-4"
      onClick={() => !busy && onClose?.()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Approval decision"
        className="panel w-full max-w-lg p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="eyebrow mb-1">Approval required</div>
        <h2 className="text-lg text-text mb-3">{item?.action || 'Review agent output'}</h2>

        <dl className="grid grid-cols-2 gap-2 text-sm mb-4">
          <div>
            <dt className="field-label">Run</dt>
            <dd className="mono text-text">#{item?.agent_run_id ?? '—'}</dd>
          </div>
          <div>
            <dt className="field-label">Requested by</dt>
            <dd className="mono text-text">{item?.requested_by ?? '—'}</dd>
          </div>
        </dl>

        {result ? (
          <div className="rounded border border-border bg-panel2 p-3 text-sm">
            <div className="flex items-center gap-2">
              <span
                className={`led ${result.status === 'approved' ? 'led-nominal' : 'led-trip'}`}
                aria-hidden="true"
              />
              <span className="mono uppercase tracking-wide text-text">{result.status}</span>
            </div>
            {result.output_file && (
              <p className="mt-2 text-muted">
                Deliverable: <span className="mono text-accent">{result.output_file}</span>
              </p>
            )}
            <div className="mt-4 flex justify-end">
              <button className="btn btn-ghost" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        ) : (
          <>
            <label className="field-label" htmlFor="approval-comment">
              Comment (optional)
            </label>
            <textarea
              id="approval-comment"
              className="input mb-4"
              rows={3}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Note for the audit trail…"
            />
            <div className="flex items-center justify-end gap-2">
              <button className="btn btn-ghost" onClick={onClose} disabled={busy}>
                Cancel
              </button>
              <button
                className="btn btn-reject"
                onClick={() => onDecide?.('reject', comment)}
                disabled={busy}
              >
                Reject
              </button>
              <button
                className="btn btn-approve"
                onClick={() => onDecide?.('approve', comment)}
                disabled={busy}
              >
                {busy ? 'Submitting…' : 'Approve'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
