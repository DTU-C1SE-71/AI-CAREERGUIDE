export interface ChatConnectionStatus {
  available: boolean
  code: string
  message: string
  checked_at: string
  latency_ms: number
  revision_token: string
}

export type ConnectionState =
  | { state: "checking" }
  | { state: "online"; revisionToken: string; checkedAt: string }
  | { state: "offline"; message: string }

export type CachedAIConnectionRecord =
  | { state: "online"; revisionToken: string; checkedAt: string; cachedAtMs: number }
  | { state: "offline"; message: string; cachedAtMs: number }

export const AI_CONNECTION_CACHE_KEY = "career-guide:ai-connection:v1"
export const AI_ONLINE_CACHE_TTL_MS = 10 * 60 * 1000
export const AI_OFFLINE_CACHE_TTL_MS = 60 * 1000
export const AI_CONNECTION_TIMEOUT_MS = 90_000
export const AI_CONNECTION_CHECK_FAILED =
  "Không xác minh được kết nối AI. Thử kiểm tra lại trước khi gửi câu hỏi."

export function parseCachedAIConnection(
  raw: string | null,
  nowMs = Date.now(),
): ConnectionState | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Partial<CachedAIConnectionRecord> | null
    if (!parsed || typeof parsed !== "object") return null
    const cachedAtMs = parsed.cachedAtMs
    if (typeof cachedAtMs !== "number" || !Number.isFinite(cachedAtMs) || nowMs < cachedAtMs) {
      return null
    }
    if (parsed.state === "online") {
      if (
        typeof parsed.revisionToken !== "string" ||
        !parsed.revisionToken.trim() ||
        nowMs - cachedAtMs >= AI_ONLINE_CACHE_TTL_MS
      ) {
        return null
      }
      return {
        state: "online",
        revisionToken: parsed.revisionToken,
        checkedAt: typeof parsed.checkedAt === "string" ? parsed.checkedAt : "",
      }
    }
    if (parsed.state === "offline") {
      if (
        typeof parsed.message !== "string" ||
        nowMs - cachedAtMs >= AI_OFFLINE_CACHE_TTL_MS
      ) {
        return null
      }
      return {
        state: "offline",
        message: parsed.message || AI_CONNECTION_CHECK_FAILED,
      }
    }
    return null
  } catch {
    return null
  }
}

export function serializeCachedAIConnection(
  state: ConnectionState,
  nowMs = Date.now(),
): string | null {
  if (state.state === "checking") return null
  const record: CachedAIConnectionRecord =
    state.state === "online"
      ? {
          state: "online",
          revisionToken: state.revisionToken,
          checkedAt: state.checkedAt,
          cachedAtMs: nowMs,
        }
      : {
          state: "offline",
          message: state.message,
          cachedAtMs: nowMs,
        }
  return JSON.stringify(record)
}
