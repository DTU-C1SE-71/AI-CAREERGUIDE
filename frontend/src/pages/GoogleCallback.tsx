import { AnimatePresence, motion } from "framer-motion"
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  LoaderCircle,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Button } from "../components/common/Button"
import { PROFILE_SETUP_STORAGE_KEY } from "../components/profile/UserProfileModal"
import { useAuth } from "../context/AuthContext"
import { authPost } from "../services/api"
import type { UserRole } from "../types/user"

interface GoogleLoginApiResponse {
  access_token: string
  token_type: string
  role?: string
  needs_profile_setup?: boolean
  user?: {
    id: string
    email: string
    full_name: string
    role: string
    gender?: string | null
    grade_level?: string | null
    school_class?: string | null
    school_name?: string | null
  }
}

export function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const requestRef = useRef<Promise<GoogleLoginApiResponse> | null>(null)
  const incoming = useRef({ code: searchParams.get("code"), state: searchParams.get("state"), error: searchParams.get("error") })

  useEffect(() => {
    let mounted = true
    if (!requestRef.current) {
      const { code, state, error } = incoming.current
      let saved: { state?: string; redirectUri?: string; created?: number } = {}
      try {
        saved = JSON.parse(
          sessionStorage.getItem("career-guide:oauth-state") ||
          localStorage.getItem("career-guide:oauth-state") ||
          "{}"
        )
      } catch { /* Phiên OAuth không hợp lệ. */ }
      sessionStorage.removeItem("career-guide:oauth-state")
      localStorage.removeItem("career-guide:oauth-state")
      window.history.replaceState(null, "", window.location.pathname)

      if (error || !code) {
        setErrorMsg("Đăng nhập Google bị hủy hoặc không thành công. Vui lòng thử lại.")
        return
      }

      if (state && saved.state && state !== saved.state) {
        setErrorMsg("Phiên đăng nhập Google không hợp lệ hoặc đã hết hạn. Quay lại trang đăng nhập để thử lại.")
        return
      }

      const redirectUri = saved.redirectUri || `${window.location.origin}/login/callback`
      requestRef.current = authPost<GoogleLoginApiResponse>("/identity/google/callback", {
        code,
        redirect_uri: redirectUri,
      })
    }
    requestRef.current.then(data => {
      if (!mounted || !data.access_token || !data.user) return
      const mappedRole: UserRole = data.user.role.toUpperCase() === "ADMIN" ? "admin" : "student"
      const userGender = data.user.gender?.trim() || undefined
      const userGradeLevel = data.user.grade_level?.trim() || undefined
      const shouldSetupProfile =
        mappedRole === "student" &&
        (Boolean(data.needs_profile_setup) || !userGender || !userGradeLevel)

      if (shouldSetupProfile) {
        sessionStorage.setItem(PROFILE_SETUP_STORAGE_KEY, "1")
      } else {
        sessionStorage.removeItem(PROFILE_SETUP_STORAGE_KEY)
      }

      login(
        mappedRole,
        {
          id: String(data.user.id),
          name: data.user.full_name,
          email: data.user.email,
          role: mappedRole,
          gender: userGender,
          grade_level: userGradeLevel,
          school_class: data.user.school_class || undefined,
          school_name: data.user.school_name || undefined,
          grade:
            userGradeLevel === "Lớp 10"
              ? 10
              : userGradeLevel === "Lớp 11"
                ? 11
                : userGradeLevel
                  ? 12
                  : undefined,
        },
        data.access_token,
      )
      setIsSuccess(true)
      navigate(mappedRole === "admin" ? "/admin" : "/dashboard", { replace: true })
    }).catch((error: unknown) => {
      if (mounted) setErrorMsg(error instanceof Error ? error.message : "Xác thực Google thất bại. Vui lòng thử lại.")
    })
    return () => { mounted = false }
  }, [login, navigate])

  return (
    <section className="relative flex min-h-[calc(100vh-72px)] items-center justify-center p-4 sm:p-6 lg:p-10">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -left-20 top-10 size-80 rounded-full bg-sky-200/40 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-1/4 size-96 rounded-full bg-cyan-200/35 blur-3xl" />

      {/* Centered Callback State Card */}
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-slate-200/90 bg-white/85 p-8 text-center shadow-2xl shadow-sky-950/10 backdrop-blur-2xl sm:p-10">
        {/* Brand Header */}
        <div className="mb-6 flex items-center justify-center gap-2.5 font-black text-slate-900">
          <span className="grid size-9 place-items-center rounded-xl bg-sky-600 text-white shadow-sm">
            <BrainCircuit size={18} />
          </span>
          <span className="text-base tracking-tight">AI CareerGuide</span>
        </div>

        <AnimatePresence mode="wait">
          {errorMsg ? (
            <motion.div
              key="error-state"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="space-y-4"
            >
              <div className="mx-auto flex size-14 items-center justify-center rounded-full border border-rose-200 bg-rose-50 text-rose-600 shadow-xs">
                <AlertCircle size={28} />
              </div>

              <div>
                <h2 className="text-xl font-black tracking-tight text-slate-900">
                  Đăng nhập Google không thành công
                </h2>
                <p className="mt-2 text-xs sm:text-sm text-slate-500">
                  Đã xảy ra vấn đề trong quá trình đồng bộ tài khoản của bạn.
                </p>
              </div>

              <div
                role="alert"
                className="rounded-2xl border border-rose-200 bg-rose-50/80 p-3.5 text-xs sm:text-sm font-medium leading-relaxed text-rose-700"
              >
                {errorMsg}
              </div>

              <div className="pt-2">
                <Button
                  onClick={() => navigate("/login", { replace: true })}
                  className="w-full min-h-11"
                  size="md"
                >
                  Quay lại trang Đăng nhập
                </Button>
              </div>
            </motion.div>
          ) : isSuccess ? (
            <motion.div
              key="success-state"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="space-y-4"
            >
              <div className="mx-auto flex size-14 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-600 shadow-xs">
                <CheckCircle2 size={28} />
              </div>

              <div>
                <h2 className="text-xl font-black tracking-tight text-slate-900">
                  Đăng nhập Google thành công!
                </h2>
                <p className="mt-2 text-xs sm:text-sm text-slate-600 font-medium">
                  Đang chuyển hướng tới không gian hướng nghiệp của bạn...
                </p>
              </div>

              <div className="mx-auto h-1.5 w-32 overflow-hidden rounded-full bg-slate-100">
                <motion.div
                  className="h-full bg-sky-600"
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{ duration: 0.65, ease: "easeInOut" }}
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="loading-state"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="space-y-4"
            >
              <div className="mx-auto flex size-14 items-center justify-center rounded-full border border-sky-100 bg-sky-50 text-sky-600">
                <LoaderCircle className="size-7 animate-spin" />
              </div>

              <div>
                <h2 className="text-xl font-black tracking-tight text-slate-900">
                  Đang đồng bộ tài khoản Google
                </h2>
                <p className="mt-2 text-xs sm:text-sm text-slate-500">
                  Hệ thống đang bảo mật phiên làm việc và chuẩn bị lộ trình của bạn.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
