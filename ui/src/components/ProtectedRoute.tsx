import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  requiredRoles?: string[]
}

export default function ProtectedRoute({ requiredRoles }: ProtectedRouteProps) {
  const { user, loading, hasRole } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="loading loading-spinner loading-lg text-primary" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (requiredRoles && requiredRoles.length > 0 && !hasRole(...requiredRoles)) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-base-content/70">You do not have permission to view this page.</p>
        </div>
      </div>
    )
  }

  return <Outlet />
}
