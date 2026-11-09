import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { readStorage, writeStorage } from "../services/storage"
import type { User, UserRole } from "../types/user"

interface AuthContextValue {
  user: User | null
  token: string | null
  login: (role?: UserRole, customUser?: User, authToken?: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function getInitialUser(): User | null {
  const stored = readStorage<User | null>("career-guide:user", null)
  if (!stored) return null
  // Purge any leftover demo user from previous sessions
  if (
    stored.id === "student-1" ||
    stored.id === "admin-1" ||
    stored.name?.includes("Trải nghiệm") ||
    stored.name?.includes("Kiểm duyệt (Admin)")
  ) {
    localStorage.removeItem("career-guide:user")
    localStorage.removeItem("career-guide:token")
    return null
  }
  return stored
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getInitialUser)
  const [token, setToken] = useState<string | null>(() =>
    readStorage("career-guide:token", null),
  )

  const login = (
    _role: UserRole = "student",
    customUser?: User,
    authToken?: string,
  ) => {
    if (!customUser) return
    setUser(customUser)
    writeStorage("career-guide:user", customUser)
    if (authToken) {
      setToken(authToken)
      writeStorage("career-guide:token", authToken)
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem("career-guide:user")
    localStorage.removeItem("career-guide:token")
  }

  const value = useMemo(() => ({ user, token, login, logout }), [user, token])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used within AuthProvider")
  return context
}
