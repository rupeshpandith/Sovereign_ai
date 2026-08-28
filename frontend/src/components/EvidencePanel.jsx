// Evidence / citations panel (Architecture §9 grounded answers, §16 evidence UI).
// Every claim shows where it came from. Two honesty states are called out explicitly:
//   - unsourced reasoning  (kind: 'reasoning' or no source) -> "model's own reasoning"
//   - low confidence       (confidence: 'low')             -> caution tag
// Extracted document text is rendered as DATA only — never executed (untrusted input).

function SourceTag({ item }) {
  const unsourced = item.kind === 'reasoning' || !item.source
  if (unsourced) {
    return (
      <span className="chip text-caution" title="Not grounded in a source document">
        <span className="led led-caution" aria-hidden="true" />
        model reasoning · unsourced
      </span>
    )
  }
  return (
    <span className="chip text-accent">
      {item.source}
      {item.page != null && <span className="text-muted"> · p.{item.page}</span>}
    </span>
  )
}

export default function EvidencePanel({ evidence = [], emptyMessage }) {
  if (!evidence.length) {
    return (
      <div className="text-sm text-muted py-6 text-center">
        {emptyMessage || 'No evidence yet — run the agent to generate grounded findings.'}
      </div>
    )
  }

  return (
    <ul className="flex flex-col gap-2">
      {evidence.map((item, i) => {
        const lowConf = item.confidence === 'low'
        return (
          <li key={i} className="rounded border border-border bg-panel2 p-3">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-text">{item.claim}</p>
              {lowConf && (
                <span className="chip text-caution shrink-0" title="Model flagged this reading as uncertain">
                  low confidence
                </span>
              )}
            </div>
            <div className="mt-2">
              <SourceTag item={item} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
