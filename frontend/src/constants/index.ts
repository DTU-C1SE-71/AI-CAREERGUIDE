/**
 * Các hằng số hệ thống (System Constants) cho Frontend
 */

export const RIASEC_DIMENSIONS = [
  { key: "R", name: "Thực tế", english: "Realistic", color: "#0ea5e9" },
  { key: "I", name: "Nghiên cứu", english: "Investigative", color: "#38bdf8" },
  { key: "A", name: "Nghệ thuật", english: "Artistic", color: "#ec4899" },
  { key: "S", name: "Xã hội", english: "Social", color: "#10b981" },
  { key: "E", name: "Quản lý", english: "Enterprising", color: "#f59e0b" },
  { key: "C", name: "Nghiệp vụ", english: "Conventional", color: "#8b5cf6" },
] as const

export const APP_ROUTES = {
  HOME: "/",
  ASSESSMENT: "/assessment",
  DASHBOARD: "/dashboard",
  ROADMAP: "/roadmap",
  LOGIN: "/login",
  ADMIN: "/admin",
} as const

export const MOET_REGULATIONS = {
  CIRCULAR_TT09: "Thông tư 09/2022/TT-BGDĐT",
  CIRCULAR_TT74: "Thông tư 74/2026/TT-BGDĐT",
  DATA_LAW: "Luật Dữ liệu số 91/2025/QH15",
} as const
