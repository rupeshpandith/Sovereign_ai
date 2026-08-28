// App routes + RBAC composition (Architecture §6). Public /login; everything else is
// inside the AppShell behind ProtectedRoute, with per-route role gating on top.
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppShell from './components/AppShell'
import LoginPage from './pages/LoginPage'
import WorkbenchPage from './pages/WorkbenchPage'
import ApprovalsPage from './pages/ApprovalsPage'
import SovereigntyDashboard from './pages/SovereigntyDashboard'
import AdminPage from './pages/AdminPage'

const ALL = ['engineer', 'approver', 'admin']

// Already signed in? Skip the login screen.
function LoginRoute() {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/workbench" replace /> : <LoginPage />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />

        <Route
          element={
            <ProtectedRoute allow={ALL}>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/workbench" replace />} />
          <Route path="/workbench" element={<WorkbenchPage />} />
          <Route
            path="/approvals"
            element={
              <ProtectedRoute allow={['approver', 'admin']}>
                <ApprovalsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/sovereignty"
            element={
              <ProtectedRoute allow={['admin']}>
                <SovereigntyDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allow={['admin']}>
                <AdminPage />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/workbench" replace />} />
      </Routes>
    </AuthProvider>
  )
}
