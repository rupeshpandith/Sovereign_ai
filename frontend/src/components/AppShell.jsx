// Persistent app shell: the signature telemetry bar + role-aware nav (Architecture §6).
// The bar asserts the air-gapped posture on every screen; the Sovereignty Dashboard
// proves the external_calls count with live data.
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import SovereigntyBadge from './SovereigntyBadge'

const NAV = [
  { to: '/workbench', label: 'Workbench', roles: ['engineer', 'approver', 'admin'] },
  { to: '/approvals', label: 'Approvals', roles: ['approver', 'admin'] },
  { to: '/sovereignty', label: 'Sovereignty', roles: ['admin'] },
  { to: '/admin', label: 'Admin', roles: ['admin'] },
]

export default function AppShell() {
  const { role, user, logout } = useAuth()
  const navigate = useNavigate()
  const items = NAV.filter((n) => n.roles.includes(role))

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-full flex flex-col">
      {/* Telemetry bar */}
      <header className="sticky top-0 z-40 border-b border-border bg-bg/95 backdrop-blur">
        <div className="mx-auto max-w-[1400px] px-5 h-12 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="led led-accent" aria-hidden="true" />
            <span className="mono text-sm tracking-widest text-text">SOVEREIGN WORKBENCH</span>
          </div>
          <SovereigntyBadge externalCalls={0} className="hidden sm:inline-flex" />
          <div className="ml-auto flex items-center gap-3">
            <span className="chip">
              <span className="text-muted">{user || 'operator'}</span>
              <span className="text-steel">·</span>
              <span className="text-accent uppercase">{role || '—'}</span>
            </span>
            <button className="btn btn-ghost" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </div>
        {/* Nav tabs */}
        <nav className="mx-auto max-w-[1400px] px-5 flex items-center gap-1 -mb-px">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `px-3 py-2 text-sm border-b-2 transition-colors ${
                  isActive
                    ? 'border-accent text-text'
                    : 'border-transparent text-muted hover:text-text'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="flex-1 mx-auto w-full max-w-[1400px] px-5 py-6">
        <Outlet />
      </main>
    </div>
  )
}
