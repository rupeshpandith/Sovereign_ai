// A single status LED dot (the signature control-room element) with an optional label.
// `state` maps to the .led-* classes defined in index.css.
const STATE_CLASS = {
  idle: 'led',
  nominal: 'led led-nominal',
  caution: 'led led-caution',
  trip: 'led led-trip',
  accent: 'led led-accent',
  active: 'led led-active',
}

export default function StatusLight({ state = 'idle', label, className = '' }) {
  const dot = STATE_CLASS[state] || STATE_CLASS.idle
  if (!label) return <span className={dot} aria-hidden="true" />
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className={dot} aria-hidden="true" />
      <span className="mono text-xs text-text">{label}</span>
    </span>
  )
}
