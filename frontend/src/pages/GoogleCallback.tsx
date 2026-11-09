import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Button } from "../components/common/Button"
import { useAuth } from "../context/AuthContext"
import { authPost } from "../services/api"
import type { UserRole } from "../types/user"

interface GoogleLoginApiResponse {
  access_token: string
  token_type: string
  role?: string
  user?: {
    id: string
    email: string
    full_name: string
    role: string
  }
}

export function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const isCalledRef = useRef(false)

  useEffect(() => {
    if (isCalledRef.current) return
    isCalledRef.current = true

    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.substring(1)
      : window.location.hash
    const hashParams = new URLSearchParams(hash)

    const accessToken =
      hashParams.get("access_token") || searchParams.get("access_token")
    const idToken = hashParams.get("id_token") || searchParams.get("id_token")
    const code = searchParams.get("code") || hashParams.get("code")
    const error = searchParams.get("error") || hashParams.get("error")

    if (error) {
      setErrorMsg(`Google từ chối đăng nhập hoặc bạn đã hủy: ${error}`)
      return
    }

    const finalizeSession = (
      data: GoogleLoginApiResponse,
      fallbackEmail?: string,
      fallbackName?: string,
    ) => {
      const rawRole = (
        data.user?.role ||
        data.role ||
        "STUDENT"
      ).toLowerCase()
      const mappedRole: UserRole = rawRole === "admin" ? "admin" : "student"
      const email = data.user?.email || fallbackEmail || ""
      const name =
        data.user?.full_name || fallbackName || email.split("@")[0] || "Học sinh"

      login(
        mappedRole,
        {
          id: String(data.user?.id || email),
          name,
          email,
          role: mappedRole,
          grade: 12,
        },
        data.access_token,
      )
      setIsSuccess(true)
      window.setTimeout(() => {
        navigate(mappedRole === "admin" ? "/admin" : "/dashboard", {
          replace: true,
        })
      }, 700)
    }

    if (accessToken) {
      fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
        .then(async (resp) => {
          if (!resp.ok) {
            throw new Error(`Google UserInfo trả về lỗi HTTP ${resp.status}`)
          }
          return await resp.json()
        })
        .then(async (profile) => {
          const res = await authPost<GoogleLoginApiResponse>(
            "/identity/google-login",
            {
              email: profile.email,
              full_name: profile.name || profile.email?.split("@")[0],
              avatar_url: profile.picture,
              google_id: profile.sub,
              access_token: accessToken,
              credential: idToken || undefined,
            },
          )
          finalizeSession(res, profile.email, profile.name)
        })
        .catch((err: unknown) => {
          const message =
            err instanceof Error
              ? err.message
              : "Xác thực tài khoản Google thất bại. Vui lòng thử lại."
          setErrorMsg(message)
        })
      return
    }

    if (code) {
      const redirectUri = `${window.location.origin}/login/callback`
      authPost<GoogleLoginApiResponse>("/identity/google/callback", {
        code,
        redirect_uri: redirectUri,
      })
        .then((res) => {
          finalizeSession(res)
        })
        .catch((err: unknown) => {
          const message =
            err instanceof Error
              ? err.message
              : "Xác thực mã Google OAuth 2.0 thất bại. Vui lòng thử lại."
          setErrorMsg(message)
        })
      return
    }

    setErrorMsg("Không tìm thấy mã xác thực từ Google Callback.")
  }, [searchParams, login, navigate])

  return (
    <div className="flex min-h-[75vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white/90 p-8 text-center shadow-xl backdrop-blur-xl space-y-4">
        {errorMsg ? (
          <div className="space-y-4">
            <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-rose-200 bg-rose-50 text-rose-600">
              <AlertCircle size={24} />
            </div>
            <h2 className="text-lg font-black text-slate-900">
              Đăng nhập Google thất bại
            </h2>
            <p className="rounded-xl border border-rose-100 bg-rose-50/70 p-3 text-xs font-semibold leading-relaxed text-rose-600">
              {errorMsg}
            </p>
            <Button
              onClick={() => navigate("/login", { replace: true })}
              className="w-full"
            >
              Quay lại trang Đăng nhập
            </Button>
          </div>
        ) : isSuccess ? (
          <div className="space-y-3">
            <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-600">
              <CheckCircle2 size={24} />
            </div>
            <h2 className="text-lg font-black text-slate-900">
              Đăng nhập Google thành công!
            </h2>
            <p className="text-xs font-medium text-slate-500">
              Đang chuyển hướng tới không gian hướng nghiệp của bạn...
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <Loader2 className="mx-auto size-8 animate-spin text-sky-600" />
            <h2 className="text-base font-black text-slate-900">
              Đang đồng bộ tài khoản Google...
            </h2>
            <p className="text-xs font-medium text-slate-500">
              Vui lòng đợi trong giây lát.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
