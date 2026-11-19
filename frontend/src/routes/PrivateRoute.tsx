import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router"
import { useAuth } from "../context/AuthContext"

export function PrivateRoute({ children }: { children: ReactNode }) {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) return <p role="status" className="p-8">Đang xác minh phiên đăng nhập…</p>
  return user ? (
    children
  ) : (
    <Navigate to="/login" replace state={{ from: location }} />
  )
}

export function StudentRoute({ children }: { children: ReactNode }) {
  const { user, checking } = useAuth()
  if (checking) return <p role="status" className="p-8">Đang xác minh phiên đăng nhập…</p>
  if (!user) return <Navigate to="/login" replace />
  return user.role === "student" ? children : <Navigate to="/admin" replace />
}
