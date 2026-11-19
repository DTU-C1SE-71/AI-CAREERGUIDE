import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { readStorage, writeStorage } from "../services/storage"
import { ApiError, currentToken, requestJSON, SESSION_CHANGED_EVENT, SESSION_INVALID_EVENT } from "../services/api"
import type { User, UserRole } from "../types/user"

interface AuthContextValue {
  user: User | null
  token: string | null
  checking: boolean
  sessionError: string | null
  refreshSession: () => Promise<void>
  login: (role?: UserRole, customUser?: User, authToken?: string) => void
  logout: () => void
  updateUser: (updates: Partial<User>) => void
}
interface ProfileResponse {
  id: string; email: string; full_name: string; role: string
  gender?: string; grade_level?: string; school_class?: string; school_name?: string
}
const AuthContext = createContext<AuthContextValue | null>(null)

function storedUser(): User | null {
  const stored = readStorage<User | null>("career-guide:user", null)
  const token = currentToken()
  if (!stored || !token || token.split(".").length !== 3) return null
  return stored
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(storedUser)
  const [token, setToken] = useState<string | null>(currentToken)
  const [checking, setChecking] = useState(Boolean(currentToken()))
  const [sessionError, setSessionError] = useState<string | null>(null)
  const generation = useRef(0)

  const logout = useCallback(() => {
    generation.current += 1
    localStorage.removeItem("career-guide:user")
    localStorage.removeItem("career-guide:token")
    localStorage.removeItem("career-guide:assessment:guest")
    localStorage.removeItem("career-guide:assessment-history:guest")
    localStorage.removeItem("career-guide:profile:grade_level")
    localStorage.removeItem("career-guide:profile:gender")
    localStorage.removeItem("career-guide:saved-roadmaps")
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith("career-guide:roadmap:guest") || key.startsWith("career-guide:roadmap:u:guest")) {
        localStorage.removeItem(key)
      }
    }
    sessionStorage.clear()
    window.dispatchEvent(new Event("career-guide:logout"))
    setUser(null); setToken(null); setChecking(false)
  }, [])

  const refreshSession = useCallback(async () => {
    const expectedToken = currentToken()
    const version = ++generation.current
    if (!expectedToken) { setUser(null); setToken(null); setChecking(false); return }
    try {
      const profile = await requestJSON<ProfileResponse>("/identity/me")
      if (version !== generation.current || currentToken() !== expectedToken) return
      const next: User = { id: String(profile.id), email: profile.email, name: profile.full_name,
        role: profile.role.toUpperCase() === "ADMIN" ? "admin" : "student", gender: profile.gender,
        grade_level: profile.grade_level, school_class: profile.school_class, school_name: profile.school_name }
      setUser(next); setToken(expectedToken); setSessionError(null)
      writeStorage("career-guide:user", next)
    } catch (error) {
      if (version !== generation.current) return
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        logout(); setSessionError("Phiên đăng nhập đã hết hạn hoặc tài khoản không còn quyền truy cập.")
      } else if (!(error instanceof DOMException && error.name === "AbortError")) {
        setSessionError("Chưa xác minh được phiên đăng nhập. Kiểm tra kết nối rồi thử lại.")
      }
    } finally {
      if (version === generation.current) setChecking(false)
    }
  }, [logout])

  const login = useCallback((_role: UserRole = "student", customUser?: User, authToken?: string) => {
    if (!customUser || !authToken || authToken.split(".").length !== 3) return
    generation.current += 1
    writeStorage("career-guide:user", customUser)
    writeStorage("career-guide:token", authToken)
    setUser(customUser); setToken(authToken); setChecking(false); setSessionError(null)
  }, [])

  const updateUser = useCallback((updates: Partial<User>) => {
    setUser(current => {
      if (!current) return null
      const updated = { ...current, ...updates }
      writeStorage("career-guide:user", updated)
      return updated
    })
  }, [])

  useEffect(() => {
    // Xóa cache cũ có thể chứa mật khẩu demo hoặc phản hồi thuộc tài khoản trước.
    for (const key of Object.keys(localStorage)) {
      if (key === "career-guide:local-users" || key.startsWith("career-guide:/")) localStorage.removeItem(key)
    }
    const invalid = (event: Event) => {
      const detail = (event as CustomEvent<{ token: string; message: string }>).detail
      if (detail?.token === currentToken()) { logout(); setSessionError(detail.message) }
    }
    const storage = (event: StorageEvent) => {
      if (event.key === "career-guide:token") {
        generation.current += 1
        setUser(null); setToken(currentToken()); setChecking(Boolean(currentToken()))
        void refreshSession()
      }
    }
    const verify = () => { if (document.visibilityState === "visible") void refreshSession() }
    window.addEventListener(SESSION_INVALID_EVENT, invalid)
    window.addEventListener(SESSION_CHANGED_EVENT, verify)
    window.addEventListener("storage", storage)
    window.addEventListener("focus", verify)
    void refreshSession()
    const timer = window.setInterval(verify, 30000)
    return () => {
      generation.current += 1
      window.clearInterval(timer)
      window.removeEventListener(SESSION_INVALID_EVENT, invalid)
      window.removeEventListener(SESSION_CHANGED_EVENT, verify)
      window.removeEventListener("storage", storage)
      window.removeEventListener("focus", verify)
    }
  }, [logout, refreshSession])

  const value = useMemo(() => ({ user, token, checking, sessionError, refreshSession, login, logout, updateUser }),
    [user, token, checking, sessionError, refreshSession, login, logout, updateUser])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used within AuthProvider")
  return context
}
