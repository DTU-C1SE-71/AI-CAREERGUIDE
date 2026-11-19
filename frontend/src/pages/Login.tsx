import { useGoogleLogin } from "@react-oauth/google"
import { AnimatePresence, motion } from "framer-motion"
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Mail,
  RotateCcw,
  School,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react"
import { type FormEvent, useEffect, useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Button } from "../components/common/Button"
import { useAuth } from "../context/AuthContext"
import { authPost } from "../services/api"
import type { UserRole } from "../types/user"
import {
  checkPasswordPolicy,
  getFirstPasswordError,
  isStrongPassword,
} from "../utils/passwordPolicy"

const DEFAULT_GOOGLE_CLIENT_ID =
  "1095956825384-f8n2bj0ott0u1sokbegksf7n32tlpn51.apps.googleusercontent.com"

interface LoginApiResponse {
  access_token: string
  token_type: string
  role?: "STUDENT" | "ADMIN"
  user?: {
    id: string
    email: string
    full_name: string
    role: "STUDENT" | "ADMIN"
  }
}

interface OTPActionApiResponse {
  message: string
  email: string
  expires_in_minutes: number
  cooldown_seconds: number
}

interface MessageApiResponse {
  message: string
}

type AuthMode = "login" | "register" | "forgot"

function PasswordStrengthChecklist({ password }: { password: string }) {
  const rules = useMemo(() => checkPasswordPolicy(password), [password])
  const passedCount = rules.filter((r) => r.passed).length
  const allPassed = passedCount === rules.length

  return (
    <div className="mt-2.5 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3">
      <div className="mb-2 flex items-center justify-between text-[11px] font-bold">
        <span className="text-slate-600">Yêu cầu mật khẩu an toàn</span>
        <span className={allPassed ? "text-emerald-600" : "text-slate-500"}>
          {passedCount}/{rules.length} tiêu chí
        </span>
      </div>
      <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {rules.map((rule) => (
          <li
            key={rule.id}
            className={`flex items-center gap-1.5 text-[11px] font-semibold transition-colors ${
              rule.passed ? "text-emerald-700" : "text-slate-500"
            }`}
          >
            <span
              className={`grid size-4 shrink-0 place-items-center rounded-full ${
                rule.passed
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-slate-200/80 text-slate-400"
              }`}
            >
              <Check size={10} strokeWidth={3} />
            </span>
            <span>{rule.label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function redirectToGoogleOAuth() {
  const clientId =
    import.meta.env.VITE_GOOGLE_CLIENT_ID || DEFAULT_GOOGLE_CLIENT_ID
  const redirectUri =
    import.meta.env.VITE_GOOGLE_REDIRECT_URI ||
    `${window.location.origin}/login/callback`

  const oauthEndpoint = "https://accounts.google.com/o/oauth2/v2/auth"
  const state = crypto.randomUUID()
  const payload = JSON.stringify({ state, redirectUri, created: Date.now() })
  sessionStorage.setItem("career-guide:oauth-state", payload)
  localStorage.setItem("career-guide:oauth-state", payload)
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    state,
    scope: "openid email profile",
    prompt: "select_account",
  })
  window.location.href = `${oauthEndpoint}?${params.toString()}`
}

function GoogleSignInButton({
  onTokenSuccess,
  onError,
  disabled,
}: {
  onTokenSuccess: (accessToken: string) => Promise<void>
  onError: (msg: string) => void
  disabled?: boolean
}) {
  const [googleBusy, setGoogleBusy] = useState(false)

  const googlePopupLogin = useGoogleLogin({
    flow: "auth-code",
    onSuccess: async (tokenResponse) => {
      try {
        setGoogleBusy(true)
        await onTokenSuccess(tokenResponse.code)
      } catch (err: unknown) {
        onError(
          err instanceof Error
            ? err.message
            : "Đăng nhập Google thất bại. Vui lòng thử lại.",
        )
      } finally {
        setGoogleBusy(false)
      }
    },
    onError: () => {
      // Fallback to standard OAuth 2.0 redirect flow if popup fails or is blocked
      redirectToGoogleOAuth()
    },
  })

  const handleClick = () => {
    // Google Cloud Console Web Client ID whitelists http://localhost:5173
    // If accessed via 127.0.0.1, switch to localhost to unify origins and cookies
    if (window.location.hostname === "127.0.0.1") {
      window.location.href = window.location.href.replace("127.0.0.1", "localhost")
      return
    }
    googlePopupLogin()
  }

  return (
    <button
      type="button"
      disabled={disabled || googleBusy}
      onClick={handleClick}
      className="inline-flex min-h-12 w-full items-center justify-center gap-3 rounded-2xl border border-slate-200/90 bg-white px-5 py-3 text-sm font-bold text-slate-700 shadow-xs transition-all duration-200 hover:border-sky-300 hover:bg-sky-50/50 hover:shadow-sm focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-500/15 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {googleBusy ? (
        <LoaderCircle className="size-5 animate-spin text-sky-600" />
      ) : (
        <svg className="size-5 shrink-0" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
      )}
      <span>
        {googleBusy ? "Đang kết nối Google..." : "Tiếp tục với tài khoản Google"}
      </span>
    </button>
  )
}

export function Login() {
  const [searchParams] = useSearchParams()
  const [mode, setMode] = useState<AuthMode>(() =>
    searchParams.get("tab") === "register" ? "register" : "login",
  )
  const [registerStep, setRegisterStep] = useState<"form" | "otp">("form")
  const [forgotStep, setForgotStep] = useState<"email" | "reset">("email")

  const [fullName, setFullName] = useState("")
  const [gender, setGender] = useState<string>("Nam")
  const [gradeLevel, setGradeLevel] = useState<string>("Lớp 12")
  const [schoolClass, setSchoolClass] = useState("")
  const [schoolName, setSchoolName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [otpCode, setOtpCode] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)

  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const { login, sessionError } = useAuth()
  const navigate = useNavigate()

  const isRegister = mode === "register"
  const isForgot = mode === "forgot"

  useEffect(() => {
    if (resendCooldown <= 0) return
    const timer = window.setInterval(() => {
      setResendCooldown((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [resendCooldown])

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode)
    setRegisterStep("form")
    setForgotStep("email")
    setOtpCode("")
    setConfirmPassword("")
    setErrorMsg(null)
    setSuccessMsg(null)
  }

  const applyLoginResponse = (data: LoginApiResponse) => {
    const rawRole = (
      data.user?.role ||
      data.role ||
      "STUDENT"
    ).toLowerCase()
    const mappedRole: UserRole = rawRole === "admin" ? "admin" : "student"
    const userEmail = data.user?.email || email.trim()
    const userName =
      data.user?.full_name || fullName.trim() || userEmail.split("@")[0]
    const userGender = (data.user as any)?.gender || gender
    const userGradeLevel = (data.user as any)?.grade_level || gradeLevel
    const userSchoolClass = (data.user as any)?.school_class || schoolClass
    const userSchoolName = (data.user as any)?.school_name || schoolName

    login(
      mappedRole,
      {
        id: String(data.user?.id || userEmail),
        name: userName,
        email: userEmail,
        role: mappedRole,
        gender: userGender,
        grade_level: userGradeLevel,
        school_class: userSchoolClass,
        school_name: userSchoolName,
        grade: userGradeLevel === "Lớp 11" ? 11 : 12,
      },
      data.access_token,
    )
    setSuccessMsg("Đăng nhập thành công! Đang chuyển hướng...")
    window.setTimeout(() => {
      navigate(mappedRole === "admin" ? "/admin" : "/dashboard", {
        replace: true,
      })
    }, 450)
  }

  const handleResendOtp = async () => {
    if (resendCooldown > 0 || loading) return
    setErrorMsg(null)
    setSuccessMsg(null)
    const trimmedEmail = email.trim()
    setLoading(true)
    try {
      if (isRegister) {
        const res = await authPost<OTPActionApiResponse>("/identity/register/request-otp", {
          email: trimmedEmail,
          password,
          full_name: fullName.trim(),
          gender,
          grade_level: gradeLevel,
          school_class: schoolClass.trim() || undefined,
          school_name: schoolName.trim() || undefined,
          role: "STUDENT",
        })
        setResendCooldown(res.cooldown_seconds || 60)
        setSuccessMsg(res.message || "Đã gửi lại mã xác nhận 6 chữ số tới email của bạn.")
      } else if (isForgot) {
        const res = await authPost<OTPActionApiResponse>("/identity/forgot-password", {
          email: trimmedEmail,
        })
        setResendCooldown(res.cooldown_seconds || 60)
        setSuccessMsg(res.message || "Đã gửi lại mã đặt lại mật khẩu tới email của bạn.")
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Không thể gửi lại mã xác nhận.")
    } finally {
      setLoading(false)
    }
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setErrorMsg(null)
    setSuccessMsg(null)

    const trimmedEmail = email.trim()

    // 1. Luồng Quên mật khẩu (2 bước: Email -> OTP + Mật khẩu mới)
    if (isForgot) {
      if (!trimmedEmail) {
        setErrorMsg("Vui lòng nhập địa chỉ email đã đăng ký.")
        return
      }
      if (forgotStep === "email") {
        setLoading(true)
        try {
          const res = await authPost<OTPActionApiResponse>("/identity/forgot-password", {
            email: trimmedEmail,
          })
          setForgotStep("reset")
          setOtpCode("")
          setPassword("")
          setConfirmPassword("")
          setResendCooldown(res.cooldown_seconds || 60)
          setSuccessMsg(res.message)
        } catch (err: unknown) {
          setErrorMsg(err instanceof Error ? err.message : "Không thể gửi yêu cầu đặt lại mật khẩu.")
        } finally {
          setLoading(false)
        }
        return
      }

      if (!/^[0-9]{6}$/.test(otpCode.trim())) {
        setErrorMsg("Vui lòng nhập đủ mã xác nhận gồm 6 chữ số từ email.")
        return
      }
      const pwError = getFirstPasswordError(password)
      if (pwError) {
        setErrorMsg(pwError)
        return
      }
      if (password !== confirmPassword) {
        setErrorMsg("Mật khẩu xác nhận không khớp.")
        return
      }

      setLoading(true)
      try {
        const res = await authPost<MessageApiResponse>("/identity/reset-password", {
          email: trimmedEmail,
          otp_code: otpCode.trim(),
          new_password: password,
        })
        setMode("login")
        setForgotStep("email")
        setOtpCode("")
        setPassword("")
        setConfirmPassword("")
        setSuccessMsg(res.message || "Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay.")
      } catch (err: unknown) {
        setErrorMsg(err instanceof Error ? err.message : "Không thể đặt lại mật khẩu. Vui lòng kiểm tra mã OTP.")
      } finally {
        setLoading(false)
      }
      return
    }

    // 2. Luồng Đăng ký thường kèm mã xác nhận Email OTP (2 bước)
    if (isRegister) {
      if (registerStep === "form") {
        if (!trimmedEmail || !password) {
          setErrorMsg("Vui lòng nhập đầy đủ địa chỉ email và mật khẩu.")
          return
        }
        if (fullName.trim().length < 2) {
          setErrorMsg("Vui lòng nhập họ và tên tối thiểu 2 ký tự.")
          return
        }
        if (!gender || !gender.trim()) {
          setErrorMsg("Vui lòng chọn giới tính.")
          return
        }
        if (!gradeLevel || !gradeLevel.trim()) {
          setErrorMsg("Vui lòng chọn khối lớp bạn đang học hoặc đã tốt nghiệp.")
          return
        }
        const pwError = getFirstPasswordError(password)
        if (pwError) {
          setErrorMsg(pwError)
          return
        }
        if (password !== confirmPassword) {
          setErrorMsg("Mật khẩu xác nhận không khớp.")
          return
        }

        setLoading(true)
        try {
          const res = await authPost<OTPActionApiResponse>("/identity/register/request-otp", {
            email: trimmedEmail,
            password,
            full_name: fullName.trim(),
            gender,
            grade_level: gradeLevel,
            school_class: schoolClass.trim() || undefined,
            school_name: schoolName.trim() || undefined,
            role: "STUDENT",
          })
          setRegisterStep("otp")
          setOtpCode("")
          setResendCooldown(res.cooldown_seconds || 60)
          setSuccessMsg(res.message)
        } catch (err: unknown) {
          setErrorMsg(err instanceof Error ? err.message : "Không thể gửi mã xác nhận đăng ký.")
        } finally {
          setLoading(false)
        }
        return
      }

      if (!/^[0-9]{6}$/.test(otpCode.trim())) {
        setErrorMsg("Vui lòng nhập đủ mã xác nhận gồm 6 chữ số đã gửi về email.")
        return
      }

      setLoading(true)
      try {
        const data = await authPost<LoginApiResponse>("/identity/register/verify-otp", {
          email: trimmedEmail,
          otp_code: otpCode.trim(),
        })
        if (data && data.access_token) {
          applyLoginResponse(data)
        } else {
          setErrorMsg("Không thể kích hoạt tài khoản. Vui lòng thử lại.")
        }
      } catch (err: unknown) {
        setErrorMsg(err instanceof Error ? err.message : "Mã xác nhận không đúng hoặc đã hết hạn.")
      } finally {
        setLoading(false)
      }
      return
    }

    // 3. Luồng Đăng nhập thông thường
    if (!trimmedEmail || !password) {
      setErrorMsg("Vui lòng nhập đầy đủ địa chỉ email và mật khẩu.")
      return
    }

    setLoading(true)
    try {
      const data = await authPost<LoginApiResponse>("/identity/login", {
        email: trimmedEmail,
        password,
      })

      if (data && data.access_token) {
        applyLoginResponse(data)
      } else {
        setErrorMsg("Không thể xác thực tài khoản. Vui lòng thử lại.")
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ""
      setErrorMsg(
        msg || "Email hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại.",
      )
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleAccessToken = async (authorizationCode: string) => {
    setErrorMsg(null)
    setSuccessMsg(null)

    // Backend xác minh token Google; không tin email do trình duyệt khai báo.
    const data = await authPost<LoginApiResponse>("/identity/google/callback", {
      code: authorizationCode,
      redirect_uri: "postmessage",
    })

    if (data && data.access_token) {
      applyLoginResponse(data)
    } else {
      throw new Error("Không nhận được phản hồi xác thực từ hệ thống.")
    }
  }

  return (
    <section className="relative flex min-h-[calc(100vh-72px)] items-center justify-center p-4 sm:p-6 lg:p-10">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -left-20 top-10 size-80 rounded-full bg-sky-200/40 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-1/4 size-96 rounded-full bg-cyan-200/35 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 size-72 rounded-full bg-blue-200/30 blur-3xl" />

      {/* Main Adaptive Auth Card Container */}
      <div className="relative mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200/90 bg-white/80 shadow-2xl shadow-sky-950/10 backdrop-blur-2xl lg:grid-cols-12">
        {/* Left Branding Showcase Panel (desktop only) */}
        <div className="hidden border-r border-slate-200/80 bg-gradient-to-br from-sky-50 via-sky-50/50 to-cyan-50/70 p-10 lg:col-span-5 lg:flex lg:flex-col lg:justify-between">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-2xl bg-sky-600 text-white shadow-md shadow-sky-600/25">
              <BrainCircuit size={22} />
            </span>
            <div>
              <span className="text-base font-black tracking-tight text-slate-900">
                AI CareerGuide
              </span>
              <p className="text-xs font-semibold text-sky-700">
                Định hướng tương lai
              </p>
            </div>
          </div>

          <div className="my-auto py-8">
            <h1 className="text-3xl font-black leading-tight tracking-tight text-slate-900 xl:text-4xl">
              Mọi lựa chọn tốt đều bắt đầu bằng câu hỏi đúng.
            </h1>

            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              Khám phá sở thích cá nhân, đối chiếu năng lực học tập và nhận đề
              xuất ngành học với tỷ lệ tương thích minh bạch.
            </p>

            <div className="mt-8 space-y-3 pt-2">
              {[
                "Trắc nghiệm Holland RIASEC 30 câu hỏi",
                "Chuẩn hóa Z-Score với 435 ngành học",
                "Giải thích AI minh bạch kèm lộ trình 4 tuần",
              ].map((point) => (
                <div
                  key={point}
                  className="flex items-start gap-2.5 text-xs font-semibold text-slate-700"
                >
                  <span className="mt-0.5 grid size-4.5 shrink-0 place-items-center rounded-full bg-sky-100 text-sky-700">
                    <Check size={12} strokeWidth={3} />
                  </span>
                  <span>{point}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-200/70 pt-4 text-xs font-medium text-slate-500">
            Hệ thống tư vấn tuyển sinh & hướng nghiệp thông minh
          </div>
        </div>

        {/* Right Auth Form Panel */}
        <div className="flex items-center justify-center p-6 sm:p-10 lg:col-span-7 lg:p-12">
          <div className="w-full max-w-md">
            {/* Mobile Brand Header */}
            <div className="mb-6 flex items-center gap-2.5 font-black text-slate-900 lg:hidden">
              <span className="grid size-9 place-items-center rounded-xl bg-sky-600 text-white shadow-sm">
                <BrainCircuit size={18} />
              </span>
              <span className="text-lg">AI CareerGuide</span>
            </div>

            {/* Login vs Register Switcher (hidden during Forgot Password mode) */}
            {!isForgot ? (
              <div className="mb-6 flex min-h-11 rounded-2xl border border-slate-200/90 bg-slate-100/80 p-1">
                <button
                  type="button"
                  onClick={() => switchMode("login")}
                  className={`flex-1 rounded-xl py-2.5 text-xs sm:text-sm font-bold transition-all duration-200 ${
                    mode === "login"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Đăng nhập
                </button>
                <button
                  type="button"
                  onClick={() => switchMode("register")}
                  className={`flex-1 rounded-xl py-2.5 text-xs sm:text-sm font-bold transition-all duration-200 ${
                    mode === "register"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Đăng ký tài khoản
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => switchMode("login")}
                className="mb-5 inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 transition hover:bg-slate-50 hover:text-sky-700"
              >
                <ArrowLeft size={14} />
                Quay lại đăng nhập
              </button>
            )}

            {/* Header Title */}
            <div>
              <h2 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
                {isForgot
                  ? forgotStep === "email"
                    ? "Quên mật khẩu"
                    : "Đặt lại mật khẩu mới"
                  : isRegister
                    ? registerStep === "otp"
                      ? "Xác nhận Email đăng ký"
                      : "Tạo tài khoản mới"
                    : "Chào mừng trở lại"}
              </h2>
              <p className="mt-1.5 text-xs sm:text-sm text-slate-500">
                {isForgot
                  ? forgotStep === "email"
                    ? "Nhập email đã đăng ký để nhận mã xác nhận 6 chữ số."
                    : `Nhập mã 6 chữ số đã gửi tới ${email.trim()} và tạo mật khẩu mới.`
                  : isRegister
                    ? registerStep === "otp"
                      ? `Nhập mã xác nhận 6 chữ số đã gửi tới ${email.trim()} để kích hoạt tài khoản.`
                      : "Bắt đầu hành trình định hướng ngành học cá nhân hóa."
                    : "Đăng nhập để tiếp tục lộ trình và tra cứu đề xuất ngành học."}
              </p>
            </div>

            {/* Error Message */}
            {(errorMsg || sessionError) && (
              <div
                role="alert"
                className="mt-5 flex items-start gap-2.5 rounded-2xl border border-rose-200 bg-rose-50/90 p-3.5 text-xs sm:text-sm font-medium text-rose-700 backdrop-blur-sm"
              >
                <AlertCircle
                  size={18}
                  className="mt-0.5 shrink-0 text-rose-600"
                />
                <span>{errorMsg || sessionError}</span>
              </div>
            )}

            {/* Success Message */}
            {successMsg && (
              <div
                role="status"
                className="mt-5 flex items-start gap-2.5 rounded-2xl border border-emerald-200 bg-emerald-50/90 p-3.5 text-xs sm:text-sm font-medium text-emerald-800 backdrop-blur-sm"
              >
                <CheckCircle2
                  size={18}
                  className="mt-0.5 shrink-0 text-emerald-600"
                />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Auth Form with Smooth State Transition */}
            <form className="mt-6 space-y-4" onSubmit={submit}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={`${mode}-${isRegister ? registerStep : forgotStep}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                  className="space-y-4"
                >
                  {isRegister && registerStep === "form" && (
                    <>
                      {/* Full Name */}
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-700">
                          Họ và tên <span className="text-rose-500">*</span>
                        </span>
                        <div className="relative">
                          <UserIcon
                            size={18}
                            className="absolute left-4 top-3.5 text-slate-400"
                          />
                          <input
                            required
                            type="text"
                            placeholder="Nhập họ và tên đầy đủ của bạn"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                          />
                        </div>
                      </label>

                      {/* Gender Selection */}
                      <div className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-700">
                          Giới tính <span className="text-rose-500">*</span>
                        </span>
                        <div className="grid grid-cols-3 gap-2">
                          {(["Nam", "Nữ", "Khác"] as const).map((g) => (
                            <button
                              key={g}
                              type="button"
                              onClick={() => setGender(g)}
                              className={`flex min-h-11 items-center justify-center rounded-xl border text-xs sm:text-sm font-bold transition-all duration-200 ${
                                gender === g
                                  ? "border-sky-500 bg-sky-50 text-sky-700 shadow-xs ring-2 ring-sky-500/20"
                                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                              }`}
                            >
                              {g}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Grade Level Selection */}
                      <div className="block">
                        <div className="mb-1.5 flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-700">
                            Hiện đang học lớp mấy{" "}
                            <span className="text-rose-500">*</span>
                          </span>
                          <span className="text-xs text-slate-500">
                            Cá nhân hóa đề xuất AI
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                          {(
                            [
                              "Lớp 10",
                              "Lớp 11",
                              "Lớp 12",
                              "Đã tốt nghiệp",
                            ] as const
                          ).map((lvl) => {
                            const actualValue =
                              lvl === "Đã tốt nghiệp"
                                ? "Đã tốt nghiệp cấp 3"
                                : lvl
                            return (
                              <button
                                key={lvl}
                                type="button"
                                onClick={() => setGradeLevel(actualValue)}
                                className={`flex min-h-11 items-center justify-center rounded-xl border px-2 text-center text-xs font-bold transition-all duration-200 ${
                                  gradeLevel === actualValue
                                    ? "border-sky-500 bg-sky-50 text-sky-700 shadow-xs ring-2 ring-sky-500/20"
                                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                                }`}
                              >
                                {lvl}
                              </button>
                            )
                          })}
                        </div>
                      </div>

                      {/* Class and School Information */}
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <label className="block">
                          <span className="mb-1.5 block text-xs font-bold text-slate-700">
                            Lớp học (tùy chọn)
                          </span>
                          <div className="relative">
                            <GraduationCap
                              size={18}
                              className="absolute left-4 top-3.5 text-slate-400"
                            />
                            <input
                              type="text"
                              placeholder="Ví dụ: 12A1"
                              value={schoolClass}
                              onChange={(e) => setSchoolClass(e.target.value)}
                              className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                            />
                          </div>
                        </label>

                        <label className="block">
                          <span className="mb-1.5 block text-xs font-bold text-slate-700">
                            Trường THPT (tùy chọn)
                          </span>
                          <div className="relative">
                            <School
                              size={18}
                              className="absolute left-4 top-3.5 text-slate-400"
                            />
                            <input
                              type="text"
                              placeholder="Ví dụ: THPT Lê Hồng Phong"
                              value={schoolName}
                              onChange={(e) => setSchoolName(e.target.value)}
                              className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                            />
                          </div>
                        </label>
                      </div>
                    </>
                  )}

                  {/* Register Step 2 OR Forgot Step 2: 6-digit OTP Input */}
                  {((isRegister && registerStep === "otp") ||
                    (isForgot && forgotStep === "reset")) && (
                    <div className="space-y-3 rounded-2xl border border-sky-200/80 bg-sky-50/50 p-4">
                      <div className="flex items-center gap-2 text-xs font-bold text-sky-800">
                        <ShieldCheck size={16} className="shrink-0 text-sky-600" />
                        <span>Mã xác nhận 6 chữ số đã gửi tới {email.trim()}</span>
                      </div>
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-bold text-slate-700">
                          Nhập mã OTP <span className="text-rose-500">*</span>
                        </span>
                        <div className="relative">
                          <KeyRound
                            size={18}
                            className="absolute left-4 top-3.5 text-slate-400"
                          />
                          <input
                            required
                            type="text"
                            inputMode="numeric"
                            autoComplete="one-time-code"
                            maxLength={6}
                            placeholder="000000"
                            value={otpCode}
                            onChange={(e) =>
                              setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                            }
                            className="h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-center text-lg font-black tracking-[0.35em] text-slate-900 outline-none transition-all placeholder:tracking-[0.25em] placeholder:text-slate-300 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                          />
                        </div>
                      </label>
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                        <button
                          type="button"
                          onClick={handleResendOtp}
                          disabled={resendCooldown > 0 || loading}
                          className="inline-flex items-center gap-1.5 font-bold text-sky-700 transition hover:text-sky-800 disabled:cursor-not-allowed disabled:text-slate-400"
                        >
                          <RotateCcw size={13} />
                          {resendCooldown > 0
                            ? `Gửi lại mã sau ${resendCooldown}s`
                            : "Gửi lại mã xác nhận"}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (isRegister) setRegisterStep("form")
                            if (isForgot) setForgotStep("email")
                            setErrorMsg(null)
                            setSuccessMsg(null)
                          }}
                          className="font-semibold text-slate-500 transition hover:text-slate-800"
                        >
                          Đổi email / Quay lại
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Email Field (Login, Register step 1, Forgot step 1) */}
                  {(mode === "login" ||
                    (isRegister && registerStep === "form") ||
                    (isForgot && forgotStep === "email")) && (
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-bold text-slate-700">
                        Địa chỉ Email <span className="text-rose-500">*</span>
                      </span>
                      <div className="relative">
                        <Mail
                          size={18}
                          className="absolute left-4 top-3.5 text-slate-400"
                        />
                        <input
                          required
                          type="email"
                          placeholder="tenban@example.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-4 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                        />
                      </div>
                    </label>
                  )}

                  {/* Password Field (Login, Register step 1, Forgot step 2) */}
                  {(mode === "login" ||
                    (isRegister && registerStep === "form") ||
                    (isForgot && forgotStep === "reset")) && (
                    <div className="block">
                      <div className="mb-1.5 flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-700">
                          {isForgot ? "Mật khẩu mới" : "Mật khẩu"}{" "}
                          <span className="text-rose-500">*</span>
                        </span>
                        {mode === "login" && (
                          <button
                            type="button"
                            onClick={() => switchMode("forgot")}
                            className="text-xs font-bold text-sky-600 transition hover:text-sky-700 hover:underline"
                          >
                            Quên mật khẩu?
                          </button>
                        )}
                      </div>
                      <div className="relative">
                        <LockKeyhole
                          size={18}
                          className="absolute left-4 top-3.5 text-slate-400"
                        />
                        <input
                          required
                          type={showPassword ? "text" : "password"}
                          placeholder={
                            mode === "login"
                              ? "Nhập mật khẩu"
                              : "Tối thiểu 8 ký tự, chữ hoa, số, ký tự đặc biệt"
                          }
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-11 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword((v) => !v)}
                          aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                          className="absolute right-3.5 top-3 text-slate-400 transition hover:text-slate-700"
                        >
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>

                      {/* Realtime Password Strength Checklist for Register & Reset Password */}
                      {(isRegister || isForgot) && (
                        <PasswordStrengthChecklist password={password} />
                      )}
                    </div>
                  )}

                  {/* Confirm Password Field (Register step 1 & Forgot step 2) */}
                  {((isRegister && registerStep === "form") ||
                    (isForgot && forgotStep === "reset")) && (
                    <label className="block">
                      <span className="mb-1.5 block text-xs font-bold text-slate-700">
                        Xác nhận mật khẩu <span className="text-rose-500">*</span>
                      </span>
                      <div className="relative">
                        <LockKeyhole
                          size={18}
                          className="absolute left-4 top-3.5 text-slate-400"
                        />
                        <input
                          required
                          type={showConfirmPassword ? "text" : "password"}
                          placeholder="Nhập lại mật khẩu giống phía trên"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          className="h-11 sm:h-12 w-full rounded-2xl border border-slate-200 bg-white pl-11 pr-11 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-sky-500 focus:ring-4 focus:ring-sky-500/15"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword((v) => !v)}
                          aria-label={showConfirmPassword ? "Ẩn mật khẩu xác nhận" : "Hiện mật khẩu xác nhận"}
                          className="absolute right-3.5 top-3 text-slate-400 transition hover:text-slate-700"
                        >
                          {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                      {confirmPassword && confirmPassword !== password && (
                        <p className="mt-1.5 text-xs font-semibold text-rose-600">
                          Mật khẩu xác nhận chưa khớp.
                        </p>
                      )}
                    </label>
                  )}
                </motion.div>
              </AnimatePresence>

              {/* Submit CTA */}
              <div className="pt-2">
                <Button
                  type="submit"
                  size="lg"
                  className="w-full min-h-12"
                  icon={ArrowRight}
                  loading={loading}
                  disabled={
                    loading ||
                    (((isRegister && registerStep === "form") ||
                      (isForgot && forgotStep === "reset")) &&
                      password.length > 0 &&
                      !isStrongPassword(password))
                  }
                >
                  {loading
                    ? "Đang xử lý..."
                    : isForgot
                      ? forgotStep === "email"
                        ? "Gửi mã xác nhận đặt lại mật khẩu"
                        : "Xác nhận & Đặt lại mật khẩu"
                      : isRegister
                        ? registerStep === "form"
                          ? "Gửi mã xác nhận qua Email"
                          : "Xác nhận & Tạo tài khoản"
                        : "Đăng nhập ngay"}
                </Button>
              </div>
            </form>

            {!isForgot && (
              <>
                {/* Quick divider */}
                <div className="my-6 flex items-center gap-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <span className="h-px flex-1 bg-slate-200/90" />
                  <span>Hoặc tiếp tục với</span>
                  <span className="h-px flex-1 bg-slate-200/90" />
                </div>

                {/* Google OAuth Login */}
                <GoogleSignInButton
                  onTokenSuccess={handleGoogleAccessToken}
                  onError={(msg) => setErrorMsg(msg)}
                  disabled={loading}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
