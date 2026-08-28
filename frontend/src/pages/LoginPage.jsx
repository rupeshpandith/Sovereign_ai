// Secure terminal sign-in. Role comes from the login response and drives RBAC.
// Demo credentials are shown as click-to-fill chips for the judging walkthrough.
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import SovereigntyBadge from '../components/SovereigntyBadge'

const DEMO = [
  { username: 'engineer1', role: 'engineer' },
  { username: 'approver1', role: 'approver' },
  { username: 'admin1', role: 'admin' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/workbench'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err?.status === 401 ? 'Invalid username or password.' : 'Sign-in failed. Is the backend running?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="led led-accent" aria-hidden="true" />
            <span className="mono text-sm tracking-widest text-text">SOVEREIGN WORKBENCH</span>
          </div>
          <SovereigntyBadge externalCalls={0} />
        </div>

        <div className="panel p-6">
          <div className="eyebrow mb-1">Secure terminal · on-premise</div>
          <h1 className="text-xl text-text mb-5">Sign in</h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="field-label" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                className="input"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className="field-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="input"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-trip">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={busy || !username || !password}>
              {busy ? 'Authenticating…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-border">
            <div className="field-label mb-2">Demo access · password demo1234</div>
            <div className="flex flex-wrap gap-2">
              {DEMO.map((d) => (
                <button
                  key={d.username}
                  type="button"
                  className="chip hover:border-accent"
                  onClick={() => {
                    setUsername(d.username)
                    setPassword('demo1234')
                    setError(null)
                  }}
                >
                  <span className="text-accent uppercase">{d.role}</span>
                  <span className="text-steel">·</span>
                  {d.username}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-muted">
          All processing is local. No cloud LLM, OCR, or embedding calls.
        </p>
      </div>
    </div>
  )
}
