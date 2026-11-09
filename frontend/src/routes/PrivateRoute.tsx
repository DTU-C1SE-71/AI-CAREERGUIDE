import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router"
import { useAuth } from "../context/AuthContext"

export function PrivateRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  return user ? (
    children
  ) : (
    <Navigate to="/login" replace state={{ from: location }} />
  )
}

export function StudentRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return user.role === "student" ? children : <Navigate to="/admin" replace />
}
