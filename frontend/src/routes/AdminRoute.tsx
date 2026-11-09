import type { ReactNode } from "react"
import { Navigate } from "react-router"
import { useAuth } from "../context/AuthContext"

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return user.role === "admin" ? children : <Navigate to="/dashboard" replace />
}
