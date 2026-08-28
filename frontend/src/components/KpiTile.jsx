// A single KPI readout tile for the Sovereignty Dashboard. Big monospace value
// (instrument readout), small uppercase label, optional status tone + sparkbar.
const TONE_TEXT = {
  nominal: 'text-nominal',
  caution: 'text-caution',
  trip: 'text-trip',
  accent: 'text-accent',
  neutral: 'text-text',
}

export default function KpiTile({ label, value, unit, tone = 'neutral', note, bars }) {
  return (
    <div className="panel p-4 flex flex-col gap-3">
      <div className="eyebrow">{label}</div>
      <div className="flex items-baseline gap-1.5">
        <span className={`mono text-3xl leading-none ${TONE_TEXT[tone] || TONE_TEXT.neutral}`}>
          {value}
        </span>
        {unit && <span className="mono text-sm text-muted">{unit}</span>}
      </div>
      {bars && (
        <div className="flex items-end gap-1 h-8" aria-hidden="true">
          {bars.map((h, i) => (
            <span
              key={i}
              className="flex-1 rounded-sm bg-accent/40"
              style={{ height: `${Math.max(6, Math.min(100, h))}%` }}
            />
          ))}
        </div>
      )}
      {note && <div className="text-xs text-muted">{note}</div>}
    </div>
  )
}
