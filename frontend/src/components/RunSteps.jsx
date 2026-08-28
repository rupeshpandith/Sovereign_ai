// Left run-steps rail. Renders the canonical agent pipeline as LED-marked steps and
// shows which local model ran each step (model routing, Architecture §4.2 / §7).
// Truth comes from the API: a step is "done" only if it's in steps_completed.
import StatusLight from './StatusLight'

const PIPELINE = [
  { key: 'ocr', label: 'OCR extract', modelKey: 'extract' },
  { key: 'retrieve_sop', label: 'Retrieve SOP', modelKey: 'retrieve_sop' },
  { key: 'draft_note', label: 'Draft approval note', modelKey: 'draft_note' },
]

export default function RunSteps({ status, steps_completed = [], model_used = {} }) {
  const running = status === 'in_progress'
  const firstPendingIdx = PIPELINE.findIndex((s) => !steps_completed.includes(s.key))

  return (
    <ol className="flex flex-col gap-1">
      {PIPELINE.map((step, idx) => {
        const done = steps_completed.includes(step.key)
        const active = running && idx === firstPendingIdx
        const state = done ? 'nominal' : active ? 'active' : 'idle'
        const model = model_used?.[step.modelKey]
        return (
          <li key={step.key} className="flex items-center gap-3 py-1.5">
            <StatusLight state={state} />
            <span className={`text-sm ${done || active ? 'text-text' : 'text-muted'}`}>
              {step.label}
            </span>
            {model && <span className="chip ml-auto text-accent">{model}</span>}
            {active && !model && <span className="mono ml-auto text-xs text-accent">running…</span>}
          </li>
        )
      })}
    </ol>
  )
}
