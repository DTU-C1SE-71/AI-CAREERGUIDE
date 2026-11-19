import { Suspense, lazy } from "react"
import { Navigate, useSearchParams } from "react-router"

const Dashboard = lazy(() => import("../pages/Dashboard").then(module => ({ default: module.Dashboard })))

export function RecommendationsRoute() {
  const [searchParams] = useSearchParams()
  return searchParams.get("search") === "1"
    ? <Navigate to="/majors?search=1" replace />
    : <Suspense fallback={<p role="status" className="p-8 text-slate-600">Đang tải trang…</p>}><Dashboard /></Suspense>
}
