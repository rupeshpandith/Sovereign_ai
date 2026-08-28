// Role-gated route (Architecture §6 RBAC). Unauthenticated -> /login (remembers where
// you were headed). Authenticated but wrong role -> /workbench (the shared landing).
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ allow, children }) {
  const { isAuthenticated, role } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (allow && !allow.includes(role)) {
    return <Navigate to="/workbench" replace />
  }
  return children
}
