export type UserRole = "student" | "admin"

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  grade?: 10 | 11 | 12
  gender?: string // "Nam" | "Nữ" | "Khác"
  grade_level?: string // "Lớp 10" | "Lớp 11" | "Lớp 12" | "Đã tốt nghiệp THPT"
  school_class?: string // e.g. "12A1"
  school_name?: string // e.g. "THPT Chuyên"
}
