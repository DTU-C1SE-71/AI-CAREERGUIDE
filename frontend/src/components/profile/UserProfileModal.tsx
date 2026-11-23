import { AnimatePresence, motion } from "framer-motion"
import {
  AlertCircle,
  Check,
  GraduationCap,
  Mail,
  School,
  ShieldCheck,
  Sparkles,
  User as UserIcon,
  X,
} from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { Button } from "../common/Button"
import { useAuth } from "../../context/AuthContext"
import { authPut } from "../../services/api"

export const PROFILE_SETUP_STORAGE_KEY = "career-guide:open-profile-setup"

interface UserProfileModalProps {
  isOpen: boolean
  onClose: () => void
  isSetupMode?: boolean
}

export function UserProfileModal({
  isOpen,
  onClose,
  isSetupMode = false,
}: UserProfileModalProps) {
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState("")
  const [gender, setGender] = useState<string>("")
  const [gradeLevel, setGradeLevel] = useState<string>("")
  const [schoolClass, setSchoolClass] = useState("")
  const [schoolName, setSchoolName] = useState("")
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const initializedRef = useRef(false)

  useEffect(() => {
    if (!isOpen) {
      initializedRef.current = false
      return
    }
    if (user && !initializedRef.current) {
      initializedRef.current = true
      setFullName(user.name || "")
      setGender(user.gender || (isSetupMode ? "" : "Nam"))
      setGradeLevel(user.grade_level || (isSetupMode ? "" : "Lớp 12"))
      setSchoolClass(user.school_class || "")
      setSchoolName(user.school_name || "")
      setErrorMsg(null)
      setSuccessMsg(null)
    }
  }, [user, isOpen, isSetupMode])

  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [isOpen, onClose])

  if (typeof document === "undefined" || !user) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)

    if (fullName.trim().length < 2) {
      setErrorMsg("Họ và tên cần có tối thiểu 2 ký tự.")
      return
    }
    if (!gender || !gender.trim()) {
      setErrorMsg("Vui lòng chọn giới tính.")
      return
    }
    if (!gradeLevel || !gradeLevel.trim()) {
      setErrorMsg("Vui lòng chọn khối lớp hiện tại.")
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
        grade: gradeLevel === "Lớp 10" ? 10 : gradeLevel === "Lớp 11" ? 11 : 12,
      })
      sessionStorage.removeItem(PROFILE_SETUP_STORAGE_KEY)

      setSuccessMsg(
        isSetupMode
          ? "Thiết lập hồ sơ học sinh thành công!"
          : "Đã lưu thông tin hồ sơ.",
      )
      window.setTimeout(() => {
        onClose()
      }, 750)
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Không thể cập nhật hồ sơ. Vui lòng thử lại."
      setErrorMsg(msg)
    } finally {
      setLoading(false)
    }
  }

  const initials = user.name ? user.name.slice(0, 2).toUpperCase() : "HS"

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center overflow-y-auto p-4 sm:p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="relative z-10 my-auto w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200/90 bg-white p-6 shadow-2xl sm:p-7"
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Đóng"
              className="absolute right-5 top-5 grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
            >
              <X size={18} />
            </button>

            <div className="flex items-start gap-4 border-b border-slate-100 pb-5 pr-10">
              <span className="grid size-13 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-600 text-base font-bold text-white shadow-sm">
                {isSetupMode ? <Sparkles size={22} /> : initials}
              </span>
              <div className="min-w-0 flex-1">
                {isSetupMode ? (
                  <>
                    <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-semibold text-sky-700">
                      <ShieldCheck size={12} />
                      Hoàn thiện hồ sơ sau đăng nhập Google
                    </span>
                    <h2 className="mt-1.5 text-lg font-bold text-slate-900 sm:text-xl">
                      Thiết lập hồ sơ học sinh
                    </h2>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                      Cập nhật giới tính, khối lớp và thông tin trường để hệ thống cá nhân hóa gợi ý ngành học phù hợp hơn với bạn.
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="truncate text-lg font-bold text-slate-900 sm:text-xl">
                      {user.name}
                    </h2>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="truncate text-xs text-slate-500">
                        {user.email}
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">
                        <ShieldCheck size={12} />
                        {user.role === "admin" ? "Quản trị viên" : "Học sinh THPT"}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {errorMsg && (
              <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-700">
                <AlertCircle size={16} className="shrink-0 text-rose-600" />
                <span>{errorMsg}</span>
              </div>
            )}

            {successMsg && (
              <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-700">
                <Check size={16} className="shrink-0 text-emerald-600" />
                <span>{successMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
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
                    placeholder="Nhập họ và tên"
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm font-medium outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                  />
                </div>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Email
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
                    className="h-11 w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm text-slate-500 outline-none"
                  />
                </div>
              </label>

              <div>
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Giới tính <span className="text-rose-500">*</span>
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {(["Nam", "Nữ", "Khác"] as const).map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setGender(g)}
                      className={`flex h-10 items-center justify-center rounded-xl border text-xs font-semibold transition-all ${
                        gender === g
                          ? "border-sky-500 bg-sky-50 text-sky-700 ring-2 ring-sky-500/15"
                          : "border-slate-200 bg-white text-slate-600 hover:border-sky-200 hover:bg-slate-50"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Khối lớp <span className="text-rose-500">*</span>
                </span>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(
                    [
                      "Lớp 10",
                      "Lớp 11",
                      "Lớp 12",
                      "Đã tốt nghiệp cấp 3",
                    ] as const
                  ).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setGradeLevel(lvl)}
                      className={`flex h-10 items-center justify-center rounded-xl border px-2 text-center text-xs font-semibold transition-all ${
                        gradeLevel === lvl
                          ? "border-sky-500 bg-sky-50 text-sky-700 ring-2 ring-sky-500/15"
                          : "border-slate-200 bg-white text-slate-600 hover:border-sky-200 hover:bg-slate-50"
                      }`}
                    >
                      {lvl === "Đã tốt nghiệp cấp 3" ? "Đã tốt nghiệp" : lvl}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                    Lớp
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
                      placeholder="VD: 12A1"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm font-medium outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                    />
                  </div>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
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
                      placeholder="Tên trường"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm font-medium outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                    />
                  </div>
                </label>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
                <Button type="button" variant="secondary" onClick={onClose}>
                  {isSetupMode ? "Để sau" : "Hủy"}
                </Button>
                <Button
                  type="submit"
                  loading={loading}
                  disabled={loading}
                  icon={Check}
                >
                  {loading
                    ? "Đang lưu..."
                    : isSetupMode
                      ? "Hoàn tất thiết lập"
                      : "Lưu thay đổi"}
                </Button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
