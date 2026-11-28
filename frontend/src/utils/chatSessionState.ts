export type ChatEffort = "auto" | "low" | "medium" | "high" | "extra_high"

export interface PersistedAdvisorMessage {
  id: string
  role: "assistant" | "user"
  content: string
  source?: "verified_guidance" | "offline_guidance"
  lengthMode?: "short" | "medium" | "detailed" | "extra_high"
  createdAt?: string
}

export interface PersistedActiveChat {
  sessionId: string | null
  messages: PersistedAdvisorMessage[]
  context: string
  effort: ChatEffort
  activePrompts?: string[]
}

export const MAX_PERSISTED_ACTIVE_MESSAGES = 40

const VALID_EFFORTS = new Set<ChatEffort>(["auto", "low", "medium", "high", "extra_high"])
const VALID_LENGTH_MODES = new Set(["short", "medium", "detailed", "extra_high"])

export function activeChatStorageKey(accountKey: string): string {
  return `career-guide:chat-active:${accountKey || "guest"}`
}

export function parsePersistedActiveChat(raw: string | null): PersistedActiveChat | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedActiveChat> | null
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.messages)) {
      return null
    }
    const messages: PersistedAdvisorMessage[] = parsed.messages
      .filter(
        (m): m is PersistedAdvisorMessage =>
          Boolean(m) &&
          typeof m === "object" &&
          typeof m.id === "string" &&
          (m.role === "assistant" || m.role === "user") &&
          typeof m.content === "string",
      )
      .slice(-MAX_PERSISTED_ACTIVE_MESSAGES)
      .map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        ...(m.source === "verified_guidance" || m.source === "offline_guidance"
          ? { source: m.source }
          : {}),
        ...(typeof m.lengthMode === "string" && VALID_LENGTH_MODES.has(m.lengthMode)
          ? { lengthMode: m.lengthMode }
          : {}),
        ...(typeof m.createdAt === "string" ? { createdAt: m.createdAt } : {}),
      }))

    if (messages.length === 0) return null

    const effort: ChatEffort =
      typeof parsed.effort === "string" && VALID_EFFORTS.has(parsed.effort as ChatEffort)
        ? (parsed.effort as ChatEffort)
        : "auto"

    const activePrompts = Array.isArray(parsed.activePrompts)
      ? parsed.activePrompts.filter((p): p is string => typeof p === "string" && p.trim() !== "")
      : undefined

    return {
      sessionId: typeof parsed.sessionId === "string" && parsed.sessionId ? parsed.sessionId : null,
      messages,
      context: typeof parsed.context === "string" ? parsed.context : "",
      effort,
      ...(activePrompts && activePrompts.length > 0 ? { activePrompts } : {}),
    }
  } catch {
    return null
  }
}

export function serializePersistedActiveChat(data: PersistedActiveChat): string {
  const cappedMessages = data.messages.slice(-MAX_PERSISTED_ACTIVE_MESSAGES)
  return JSON.stringify({
    sessionId: data.sessionId || null,
    messages: cappedMessages,
    context: data.context || "",
    effort: data.effort || "auto",
    ...(data.activePrompts && data.activePrompts.length > 0
      ? { activePrompts: data.activePrompts }
      : {}),
  })
}
