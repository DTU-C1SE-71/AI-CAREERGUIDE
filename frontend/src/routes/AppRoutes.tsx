import { AssessmentWizard, Login, GoogleCallback, MajorsCatalog, MajorDetail, RoadmapView, AdminGovernance, AdminCatalog, AdminImport, AdminTrends, AdminAI } from "./LazyPages"
import { Suspense, type ReactNode } from "react"
import { createBrowserRouter, Navigate } from "react-router"
import { MainLayout } from "../components/layout/MainLayout"
import { AdminLayout } from "../components/admin/AdminLayout"
import { Home } from "../pages/Home"
import { AdminRoute } from "./AdminRoute"
import { StudentRoute } from "./PrivateRoute"
import { RecommendationsRoute } from "./RecommendationsRoute"
const screen = (children: ReactNode) => <Suspense fallback={<p role="status" className="p-8 text-slate-600">Đang tải trang…</p>}>{children}</Suspense>
const notFound = <div className="p-8"><h1 className="text-2xl font-semibold">Không tìm thấy trang</h1><p className="mt-3">Kiểm tra địa chỉ hoặc chọn một mục trong thanh điều hướng.</p></div>
export const router = createBrowserRouter([
  { path: "/admin", element: <AdminRoute><AdminLayout /></AdminRoute>, children: [
    { index: true, element: <Navigate to="/admin/governance" replace /> },
    { path: "governance", element: screen(<AdminGovernance />) },
    { path: "catalog", element: screen(<AdminCatalog />) },
    { path: "import", element: screen(<AdminImport />) },
    { path: "trends", element: screen(<AdminTrends />) },
    { path: "ai-settings", element: screen(<AdminAI />) },
    { path: "*", element: notFound },
  ] },
  { path: "/", Component: MainLayout, children: [
    { index: true, Component: Home },
    { path: "assessment", element: screen(<AssessmentWizard />) },
    { path: "dashboard", element: <StudentRoute><RecommendationsRoute /></StudentRoute> },
    { path: "majors", element: <StudentRoute>{screen(<MajorsCatalog />)}</StudentRoute> },
    { path: "majors/:id", element: <StudentRoute>{screen(<MajorDetail />)}</StudentRoute> },
    { path: "roadmap", element: <StudentRoute>{screen(<RoadmapView />)}</StudentRoute> },
    { path: "login", element: screen(<Login />) },
    { path: "login/callback", element: screen(<GoogleCallback />) },
    { path: "*", element: notFound },
  ] },
])
