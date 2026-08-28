// Session + role state (Architecture §6 RBAC). Persists to localStorage so a reload
// keeps you logged in, and registers the 401 handler so an expired token logs you out.
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { getToken, setToken, setUnauthorizedHandler } from '../api/client'
import { login as apiLogin } from '../api/auth'

const ROLE_KEY = 'sov_role'
const USER_KEY = 'sov_user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken())
  const [role, setRole] = useState(() => localStorage.getItem(ROLE_KEY) || null)
  const [user, setUser] = useState(() => localStorage.getItem(USER_KEY) || null)

  const logout = useMemo(
    () => () => {
      setToken(null)
      localStorage.removeItem(ROLE_KEY)
      localStorage.removeItem(USER_KEY)
      setTokenState(null)
      setRole(null)
      setUser(null)
    },
    [],
  )

  // A 401 from any call (expired/invalid token) drops the session.
  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  async function login(username, password) {
    const { access_token, role: nextRole } = await apiLogin(username, password)
    setToken(access_token)
    localStorage.setItem(ROLE_KEY, nextRole)
    localStorage.setItem(USER_KEY, username)
    setTokenState(access_token)
    setRole(nextRole)
    setUser(username)
    return nextRole
  }

  const value = useMemo(
    () => ({ token, role, user, isAuthenticated: Boolean(token), login, logout }),
    [token, role, user, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
