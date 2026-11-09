import { createBrowserRouter } from "react-router"
import { MainLayout } from "../components/layout/MainLayout"
import { AdminHITLDashboard } from "../pages/AdminHITLDashboard"
import { AssessmentWizard } from "../pages/AssessmentWizard"
import { Dashboard } from "../pages/Dashboard"
import { GoogleCallback } from "../pages/GoogleCallback"
import { Home } from "../pages/Home"
import { Login } from "../pages/Login"
import { MajorDetail } from "../pages/MajorDetail"
import { RoadmapView } from "../pages/RoadmapView"
import { AdminRoute } from "./AdminRoute"
import { StudentRoute } from "./PrivateRoute"

export const router = createBrowserRouter([
  {
    path: "/",
    Component: MainLayout,
    children: [
      { index: true, Component: Home },
      { path: "assessment", Component: AssessmentWizard },
      {
        path: "dashboard",
        element: (
          <StudentRoute>
            <Dashboard />
          </StudentRoute>
        ),
      },
      {
        path: "majors/:id",
        element: (
          <StudentRoute>
            <MajorDetail />
          </StudentRoute>
        ),
      },
      {
        path: "roadmap",
        element: (
          <StudentRoute>
            <RoadmapView />
          </StudentRoute>
        ),
      },
      { path: "login", Component: Login },
      { path: "login/callback", Component: GoogleCallback },
      {
        path: "admin",
        element: (
          <AdminRoute>
            <AdminHITLDashboard />
          </AdminRoute>
        ),
      },
      {
        path: "*",
        element: (
          <div className="grid min-h-[60vh] place-items-center p-8 text-center">
            <div>
              <p className="text-7xl font-black text-sky-100">404</p>
              <h1 className="mt-3 text-2xl font-black">Không tìm thấy trang</h1>
            </div>
          </div>
        ),
      },
    ],
  },
])
