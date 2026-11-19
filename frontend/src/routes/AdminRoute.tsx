import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router"
import { useAuth } from "../context/AuthContext"

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user, checking, sessionError, refreshSession, logout } = useAuth()
  const location = useLocation()
  if (checking) return <div role="status" className="p-8 text-slate-700">Đang xác minh quyền quản trị…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location, message: sessionError }} />
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />
  if (sessionError) return <div className="mx-auto max-w-xl p-8"><h1 className="text-xl font-bold">Chưa xác minh được quyền quản trị</h1><p role="alert" className="my-4">{sessionError}</p><button className="admin-button" onClick={() => void refreshSession()}>Thử lại</button><button className="admin-button ml-3" onClick={logout}>Đăng xuất</button></div>
  return children
}
