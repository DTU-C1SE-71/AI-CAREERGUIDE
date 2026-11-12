import { AnimatePresence, motion } from "framer-motion"
import {
  AlertCircle,
  Check,
  GraduationCap,
  Loader2,
  Mail,
  School,
  ShieldCheck,
  User as UserIcon,
  X,
} from "lucide-react"
import { type FormEvent, useEffect, useState } from "react"
import { Button } from "../common/Button"
import { useAuth } from "../../context/AuthContext"
import { authPut } from "../../services/api"

interface UserProfileModalProps {
  isOpen: boolean
  onClose: () => void
}

export function UserProfileModal({ isOpen, onClose }: UserProfileModalProps) {
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState("")
  const [gender, setGender] = useState<string>("Nam")
  const [gradeLevel, setGradeLevel] = useState<string>("Lớp 12")
  const [schoolClass, setSchoolClass] = useState("")
  const [schoolName, setSchoolName] = useState("")
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  useEffect(() => {
    if (user && isOpen) {
      setFullName(user.name || "")
      setGender(user.gender || "Nam")
      setGradeLevel(user.grade_level || "Lớp 12")
      setSchoolClass(user.school_class || "")
      setSchoolName(user.school_name || "")
      setErrorMsg(null)
      setSuccessMsg(null)
    }
  }, [user, isOpen])

  if (!isOpen || !user) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)

    if (fullName.trim().length < 2) {
      setErrorMsg("Họ và tên cần có tối thiểu 2 ký tự.")
      return
    }
    if (!gender || !gender.trim()) {
      setErrorMsg("Vui lòng chọn giới tính (không được để trống).")
      return
    }
    if (!gradeLevel || !gradeLevel.trim()) {
      setErrorMsg("Vui lòng chọn lớp bạn đang học hoặc đã tốt nghiệp.")
      return
    }

    setLoading(true)
    try {
      const payload = {
        full_name: fullName.trim(),
        gender,
        grade_level: gradeLevel,
        school_class: schoolClass.trim() || undefined,
        school_name: schoolName.trim() || undefined,
      }
      await authPut("/identity/profile", payload)

      updateUser({
        name: fullName.trim(),
        gender,
        grade_level: gradeLevel,
        school_class: schoolClass.trim() || undefined,
        school_name: schoolName.trim() || undefined,
        grade: gradeLevel === "Lớp 11" ? 11 : 12,
      })

      setSuccessMsg("Cập nhật thông tin hồ sơ thành công!")
      window.setTimeout(() => {
        onClose()
      }, 900)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể cập nhật hồ sơ. Vui lòng thử lại."
      setErrorMsg(msg)
    } finally {
      setLoading(false)
    }
  }

  const initials = user.name ? user.name.slice(0, 2).toUpperCase() : "YU"

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          className="relative z-10 w-full max-w-xl overflow-hidden rounded-3xl border border-white/90 bg-white/90 p-6 sm:p-8 shadow-[0_24px_60px_rgba(14,165,233,0.18)] backdrop-blur-2xl"
        >
          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            className="absolute right-5 top-5 grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          >
            <X size={18} />
          </button>

          {/* Header Profile Badge */}
          <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
            <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-lg font-black text-white shadow-md">
              {initials}
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-black text-slate-900 sm:text-2xl">
                {user.name}
              </h2>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span className="truncate text-xs font-medium text-slate-500">
                  {user.email}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[10px] font-extrabold text-sky-700">
                  <ShieldCheck size={12} />
                  {user.role === "admin" ? "Quản trị viên" : "Hồ sơ Học sinh THPT"}
                </span>
              </div>
            </div>
          </div>

          {errorMsg && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50/90 p-3 text-xs font-bold text-rose-700">
              <AlertCircle size={16} className="shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50/90 p-3 text-xs font-bold text-sky-800">
              <Check size={16} className="shrink-0 text-sky-600" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Edit Form */}
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            {/* Họ và tên */}
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold text-slate-700">
                Họ và tên <span className="text-rose-500">*</span>
              </span>
              <div className="relative">
                <UserIcon
                  size={17}
                  className="absolute left-3.5 top-3 text-slate-400"
                />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nhập họ và tên của bạn"
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white/90 pl-10 pr-3 text-sm font-semibold outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                />
              </div>
            </label>

            {/* Email (Readonly) */}
            <label className="block">
              <span className="mb-1.5 block text-xs font-bold text-slate-700">
                Email tài khoản
              </span>
              <div className="relative">
                <Mail
                  size={17}
                  className="absolute left-3.5 top-3 text-slate-400"
                />
                <input
                  type="email"
                  disabled
                  value={user.email}
                  className="h-11 w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-100/80 pl-10 pr-3 text-sm font-medium text-slate-500 outline-none"
                />
              </div>
            </label>

            {/* Giới tính (Bắt buộc) */}
            <div>
              <span className="mb-1.5 block text-xs font-bold text-slate-700">
                Giới tính <span className="text-rose-500">*</span>
              </span>
              <div className="grid grid-cols-3 gap-2">
                {(["Nam", "Nữ", "Khác"] as const).map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGender(g)}
                    className={`flex h-10 items-center justify-center rounded-xl border text-xs font-bold transition-all ${
                      gender === g
                        ? "border-sky-500 bg-sky-50 text-sky-700 shadow-xs ring-2 ring-sky-500/20"
                        : "border-slate-200 bg-white text-slate-600 hover:border-sky-200 hover:bg-slate-50"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>

            {/* Hiện đang học lớp mấy (Bắt buộc) */}
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700">
                  Hiện đang học lớp mấy <span className="text-rose-500">*</span>
                </span>
                <span className="text-[10px] text-slate-500">
                  Phục vụ cá nhân hóa đề xuất AI
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(["Lớp 10", "Lớp 11", "Lớp 12", "Đã tốt nghiệp cấp 3"] as const).map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setGradeLevel(lvl)}
                    className={`flex h-10 items-center justify-center rounded-xl border px-2 text-center text-xs font-bold transition-all ${
                      gradeLevel === lvl
                        ? "border-sky-500 bg-sky-50 text-sky-700 shadow-xs ring-2 ring-sky-500/20"
                        : "border-slate-200 bg-white text-slate-600 hover:border-sky-200 hover:bg-slate-50"
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>

            {/* Lớp & Trường THPT */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-xs font-bold text-slate-700">
                  Lớp học
                </span>
                <div className="relative">
                  <GraduationCap
                    size={17}
                    className="absolute left-3.5 top-3 text-slate-400"
                  />
                  <input
                    type="text"
                    value={schoolClass}
                    onChange={(e) => setSchoolClass(e.target.value)}
                    placeholder="Ví dụ: 12A1"
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white/90 pl-10 pr-3 text-sm font-semibold outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-bold text-slate-700">
                  Trường THPT
                </span>
                <div className="relative">
                  <School
                    size={17}
                    className="absolute left-3.5 top-3 text-slate-400"
                  />
                  <input
                    type="text"
                    value={schoolName}
                    onChange={(e) => setSchoolName(e.target.value)}
                    placeholder="Ví dụ: THPT Chuyên Lê Hồng Phong"
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white/90 pl-10 pr-3 text-sm font-semibold outline-none focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                  />
                </div>
              </label>
            </div>

            {/* Footer Buttons */}
            <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-xs font-bold text-slate-600 transition hover:bg-slate-100 hover:text-slate-800"
              >
                Hủy
              </button>
              <Button
                type="submit"
                loading={loading}
                disabled={loading}
                icon={Check}
              >
                {loading ? "Đang lưu..." : "Lưu thay đổi"}
              </Button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
