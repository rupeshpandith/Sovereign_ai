// Sovereignty posture badge. The air-gapped LED reflects the product's deployment
// mode (network egress blocked by design, Architecture §4.1); the live external_calls
// counter is proven with real data on the Sovereignty Dashboard.
import StatusLight from './StatusLight'

export default function SovereigntyBadge({ externalCalls = 0, className = '' }) {
  const clean = externalCalls === 0
  return (
    <span className={`chip ${className}`} title="On-premise · network egress blocked">
      <StatusLight state={clean ? 'nominal' : 'trip'} />
      <span className="tracking-wide">AIR-GAPPED</span>
      <span className="text-steel">·</span>
      <span className={clean ? 'text-nominal' : 'text-trip'}>ext:{externalCalls}</span>
    </span>
  )
}
