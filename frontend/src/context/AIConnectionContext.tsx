import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { requestJSON } from "../services/api"
import {
  AI_CONNECTION_CACHE_KEY,
  AI_CONNECTION_CHECK_FAILED,
  AI_CONNECTION_TIMEOUT_MS,
  type ChatConnectionStatus,
  type ConnectionState,
  parseCachedAIConnection,
  serializeCachedAIConnection,
} from "../utils/aiConnectionCache"

const REVISION_EVENT = "career-guide:ai-revision"

interface AIConnectionContextValue {
  connection: ConnectionState
  checkConnection: (options?: { force?: boolean }) => Promise<void>
  markOffline: (message: string) => void
}

const AIConnectionContext = createContext<AIConnectionContextValue | null>(null)

let inFlightProbe: Promise<ConnectionState> | null = null

function readSessionCache(): ConnectionState | null {
  try {
    if (typeof window === "undefined") return null
    return parseCachedAIConnection(window.sessionStorage.getItem(AI_CONNECTION_CACHE_KEY))
  } catch {
    return null
  }
}

function writeSessionCache(state: ConnectionState): void {
  try {
    if (typeof window === "undefined") return
    const serialized = serializeCachedAIConnection(state)
    if (serialized) {
      window.sessionStorage.setItem(AI_CONNECTION_CACHE_KEY, serialized)
    }
  } catch {
    // Ignore storage quota or private browsing errors
  }
}

function clearSessionCache(): void {
  try {
    if (typeof window === "undefined") return
    window.sessionStorage.removeItem(AI_CONNECTION_CACHE_KEY)
  } catch {
    // Ignore storage errors
  }
}

async function executeConnectionProbe(force: boolean): Promise<ConnectionState> {
  try {
    const endpoint = force
      ? "/rag-governance/chat/connection?force=true"
      : "/rag-governance/chat/connection"
    const result = await requestJSON<ChatConnectionStatus>(
      endpoint,
      { method: "POST" },
      AI_CONNECTION_TIMEOUT_MS,
    )
    if (!result?.available || !result.revision_token) {
      const offline: ConnectionState = {
        state: "offline",
        message: result?.message || AI_CONNECTION_CHECK_FAILED,
      }
      writeSessionCache(offline)
      return offline
    }
    const online: ConnectionState = {
      state: "online",
      revisionToken: result.revision_token,
      checkedAt: result.checked_at,
    }
    writeSessionCache(online)
    return online
  } catch {
    const offline: ConnectionState = {
      state: "offline",
      message: AI_CONNECTION_CHECK_FAILED,
    }
    writeSessionCache(offline)
    return offline
  }
}

async function runSharedProbe(force: boolean): Promise<ConnectionState> {
  if (!force && inFlightProbe) {
    return inFlightProbe
  }

  let currentPromise: Promise<ConnectionState> | null = null
  currentPromise = executeConnectionProbe(force).finally(() => {
    if (inFlightProbe === currentPromise) {
      inFlightProbe = null
    }
  })

  inFlightProbe = currentPromise
  return currentPromise
}

export function AIConnectionProvider({ children }: { children: ReactNode }) {
  const [connection, setConnection] = useState<ConnectionState>(() => {
    return readSessionCache() ?? { state: "checking" }
  })
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const checkConnection = useCallback(async (options?: { force?: boolean }) => {
    const force = Boolean(options?.force)
    if (!force) {
      const cached = readSessionCache()
      if (cached) {
        if (mountedRef.current) setConnection(cached)
        return
      }
    } else {
      clearSessionCache()
    }

    if (mountedRef.current) {
      setConnection({ state: "checking" })
    }
    const nextState = await runSharedProbe(force)
    if (mountedRef.current) {
      setConnection(nextState)
    }
  }, [])

  const markOffline = useCallback((message: string) => {
    const nextState: ConnectionState = {
      state: "offline",
      message: message || AI_CONNECTION_CHECK_FAILED,
    }
    writeSessionCache(nextState)
    if (mountedRef.current) {
      setConnection(nextState)
    }
  }, [])

  // Auto-check AI connection once when the app first loads if cache is absent/expired.
  useEffect(() => {
    if (!readSessionCache()) {
      void checkConnection({ force: false })
    }

    const handleRevisionChange = () => {
      clearSessionCache()
      void checkConnection({ force: true })
    }
    const handleStorage = (event: StorageEvent) => {
      if (event.key === REVISION_EVENT) {
        handleRevisionChange()
      }
    }

    window.addEventListener(REVISION_EVENT, handleRevisionChange)
    window.addEventListener("storage", handleStorage)
    return () => {
      window.removeEventListener(REVISION_EVENT, handleRevisionChange)
      window.removeEventListener("storage", handleStorage)
    }
  }, [checkConnection])

  const value = useMemo<AIConnectionContextValue>(
    () => ({ connection, checkConnection, markOffline }),
    [connection, checkConnection, markOffline],
  )

  return (
    <AIConnectionContext.Provider value={value}>
      {children}
    </AIConnectionContext.Provider>
  )
}

export function useAIConnection(): AIConnectionContextValue {
  const ctx = useContext(AIConnectionContext)
  if (!ctx) {
    throw new Error("useAIConnection must be used within AIConnectionProvider")
  }
  return ctx
}
