import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowUp,
  Bot,
  Brain,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Clock,
  GraduationCap,
  History,
  Info,
  LoaderCircle,
  Maximize2,
  MessageSquare,
  Minimize2,
  Paperclip,
  Sparkles,
  SquarePen,
  Trash2,
  User,
  X,
} from "lucide-react"
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { useSelectedAssessment } from "../hooks/useSelectedAssessment"
import { useAuth } from "../context/AuthContext"
import { buildEvaluateProfilePayload } from "../utils/assessmentPayload"
import { MOET_435_MAJORS } from "../data/moetMajors435"
import { ApiError, requestJSON } from "../services/api"

interface AIChatAdvisorProps {
  open: boolean
  onClose: () => void
}

type ReasoningEffort = "auto" | "low" | "medium" | "high" | "extra_high"
type ResponseLengthMode = "short" | "medium" | "detailed" | "extra_high"

interface AdvisorMessage {
  id: string
  role: "assistant" | "user"
  content: string
  source?: "verified_guidance" | "offline_guidance"
  lengthMode?: ResponseLengthMode
  createdAt?: string
}

interface ChatSessionItem {
  id: string
  title: string
  major_code?: string | null
  message_count: number
  last_message_preview: string
  created_at: string
  updated_at: string
  localMessages?: AdvisorMessage[]
}

interface ChatSessionDetailResponse {
  id: string
  title: string
  major_code?: string | null
  created_at: string
  updated_at: string
  messages: Array<{
    id: string
    role: "user" | "assistant"
    content: string
    response_source?: string | null
    created_at: string
  }>
}

interface ChatConnectionStatus {
  available: boolean
  code: string
  message: string
  checked_at: string
  latency_ms: number
  revision_token: string
}

type ConnectionState =
  | { state: "checking" }
  | { state: "online"; revisionToken: string; checkedAt: string }
  | { state: "offline"; message: string }

const CHAT_TIMEOUT_MS = 330_000
const CONNECTION_TIMEOUT_MS = 90_000
const CONNECTION_CHECK_FAILED =
  "Không xác minh được kết nối AI. Thử kiểm tra lại trước khi gửi câu hỏi."
const GUEST_CHAT_HISTORY_KEY = "career-guide:chat-history:guest"
const MAX_GUEST_SESSIONS = 20
const MAX_GUEST_MESSAGES = 40

const EFFORT_OPTIONS: Array<{
  value: ReasoningEffort
  label: string
}> = [
  { value: "auto", label: "Tự động" },
  { value: "low", label: "Thấp" },
  { value: "medium", label: "Trung bình" },
  { value: "high", label: "Cao" },
  { value: "extra_high", label: "Rất cao" },
]

const LENGTH_MODE_LABELS: Record<ResponseLengthMode, string> = {
  short: "Thấp",
  medium: "Trung bình",
  detailed: "Cao",
  extra_high: "Rất cao",
}

const initialMessages: AdvisorMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    content: `### Chào bạn, mình là Cố vấn AI

Hỏi mình về ngành học, điểm số, sở thích hoặc lộ trình học tập nhé.`,
  },
]

const quickPrompts = [
  "Cách dùng AI CareerGuide",
  "Hồ sơ còn thiếu gì?",
  "So sánh CNTT & AI",
  "Ngành ATTT học gì?",
]

const unavailableReply =
  "Chưa nhận được phản hồi tư vấn. Hãy kiểm tra lại kết nối rồi gửi lại câu hỏi."

function makePreview(text: string): string {
  const clean = text.replace(/[#*`>_]/g, "").replace(/\s+/g, " ").trim()
  return clean.length > 110 ? `${clean.slice(0, 107).trimEnd()}...` : clean
}

function makeTitle(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim()
  if (!clean) return "Cuộc trò chuyện hướng nghiệp"
  return clean.length > 80 ? `${clean.slice(0, 77).trimEnd()}...` : clean
}

function formatSessionTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  if (sameDay) {
    return date.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    })
  }
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })
}

function readGuestSessions(): ChatSessionItem[] {
  try {
    const raw = localStorage.getItem(GUEST_CHAT_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeGuestSessions(sessions: ChatSessionItem[]) {
  try {
    const bounded = sessions.slice(0, MAX_GUEST_SESSIONS).map((s) => ({
      ...s,
      localMessages: s.localMessages?.slice(-MAX_GUEST_MESSAGES),
    }))
    localStorage.setItem(GUEST_CHAT_HISTORY_KEY, JSON.stringify(bounded))
  } catch {
    // Ignore storage quota errors for guest cache
  }
}

function mapResponseSource(
  source?: string | null,
): AdvisorMessage["source"] {
  if (source === "offline_guidance") return "offline_guidance"
  if (source === "verified_guidance") return "verified_guidance"
  return undefined
}

export function AIChatAdvisor({ open, onClose }: AIChatAdvisorProps) {
  const [messages, setMessages] = useState<AdvisorMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [typing, setTyping] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [context, setContext] = useState("")
  const [effort, setEffort] = useState<ReasoningEffort>("auto")
  const [effortMenuOpen, setEffortMenuOpen] = useState(false)
  const [effortInfoOpen, setEffortInfoOpen] = useState(false)

  const [historyOpen, setHistoryOpen] = useState(false)
  const [sessions, setSessions] = useState<ChatSessionItem[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [confirmClearAll, setConfirmClearAll] = useState(false)

  const assessment = useSelectedAssessment()
  const { user, token } = useAuth()
  const isAuthenticated = Boolean(user && token)
  const accountKey = isAuthenticated ? `u:${user?.id || user?.email}` : "guest"

  const requestVersion = useRef(0)
  const connectionRequest = useRef<AbortController | null>(null)
  const activeRequest = useRef<AbortController | null>(null)
  const connectionVersion = useRef(0)
  const chatBusy = useRef(false)
  const probeBusy = useRef(false)
  const messageSequence = useRef(1)
  const endRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const effortMenuRef = useRef<HTMLDivElement | null>(null)

  const focusInput = useCallback(() => {
    window.requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true })
    })
  }, [])

  const [activePrompts, setActivePrompts] = useState<string[]>(quickPrompts)
  const [connection, setConnection] = useState<ConnectionState>({
    state: "checking",
  })

  const loadSessions = useCallback(async () => {
    if (!isAuthenticated) {
      setSessions(readGuestSessions())
      return
    }
    setSessionsLoading(true)
    try {
      const data = await requestJSON<ChatSessionItem[]>(
        "/rag-governance/chat/sessions",
        { method: "GET" },
        20_000,
      )
      setSessions(Array.isArray(data) ? data : [])
    } catch {
      // Keep current list on transient failure
    } finally {
      setSessionsLoading(false)
    }
  }, [isAuthenticated])

  const checkConnection = async () => {
    if (probeBusy.current) return
    connectionRequest.current?.abort()
    const controller = new AbortController()
    connectionRequest.current = controller
    const version = ++connectionVersion.current
    probeBusy.current = true
    setConnection({ state: "checking" })
    try {
      const result = await requestJSON<ChatConnectionStatus>(
        "/rag-governance/chat/connection",
        { method: "POST", signal: controller.signal },
        CONNECTION_TIMEOUT_MS,
      )
      if (version !== connectionVersion.current || controller.signal.aborted) {
        return
      }
      if (!result.available || !result.revision_token) {
        setConnection({
          state: "offline",
          message: result.message || CONNECTION_CHECK_FAILED,
        })
        return
      }
      setConnection({
        state: "online",
        revisionToken: result.revision_token,
        checkedAt: result.checked_at,
      })
    } catch {
      if (version !== connectionVersion.current || controller.signal.aborted) {
        return
      }
      setConnection({ state: "offline", message: CONNECTION_CHECK_FAILED })
    } finally {
      if (version === connectionVersion.current) probeBusy.current = false
    }
  }

  // Only reset conversation state when switching account (login / logout),
  // never when the student simply navigates between pages.
  useEffect(() => {
    requestVersion.current += 1
    activeRequest.current?.abort()
    chatBusy.current = false
    setInput("")
    setContext("")
    setActiveSessionId(null)
    setMessages(initialMessages)
    setActivePrompts(quickPrompts)
    setTyping(false)
    setConfirmClearAll(false)
    setSessions(isAuthenticated ? [] : readGuestSessions())
  }, [accountKey, isAuthenticated])

  useEffect(() => {
    if (!open) return
    setTyping(false)
    setConnection({ state: "checking" })
    const timer = window.setTimeout(() => {
      void checkConnection()
      void loadSessions()
    }, 0)
    return () => {
      window.clearTimeout(timer)
      connectionVersion.current += 1
      requestVersion.current += 1
      connectionRequest.current?.abort()
      activeRequest.current?.abort()
      chatBusy.current = false
      probeBusy.current = false
    }
  }, [open, loadSessions])

  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 112)}px`
  }, [input])

  useEffect(() => {
    if (open && !typing) {
      focusInput()
    }
  }, [open, typing, focusInput])

  useEffect(() => {
    if (!effortMenuOpen) return
    const handlePointerDown = (event: MouseEvent) => {
      if (
        effortMenuRef.current &&
        !effortMenuRef.current.contains(event.target as Node)
      ) {
        setEffortMenuOpen(false)
        setEffortInfoOpen(false)
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setEffortMenuOpen(false)
        setEffortInfoOpen(false)
      }
    }
    document.addEventListener("mousedown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("mousedown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [effortMenuOpen])

  const startNewChat = () => {
    requestVersion.current += 1
    activeRequest.current?.abort()
    chatBusy.current = false
    setActiveSessionId(null)
    setMessages(initialMessages)
    setActivePrompts(quickPrompts)
    setInput("")
    setTyping(false)
    setConfirmClearAll(false)
    if (!fullscreen) setHistoryOpen(false)
    focusInput()
  }

  const changeTopic = (code: string) => {
    setContext(code)
  }

  const selectSession = async (session: ChatSessionItem) => {
    if (loadingSessionId === session.id) return
    requestVersion.current += 1
    activeRequest.current?.abort()
    chatBusy.current = false
    setTyping(false)
    setConfirmClearAll(false)

    if (!isAuthenticated) {
      setActiveSessionId(session.id)
      setContext(session.major_code || "")
      setMessages(
        session.localMessages && session.localMessages.length > 0
          ? session.localMessages
          : initialMessages,
      )
      if (!fullscreen) setHistoryOpen(false)
      focusInput()
      return
    }

    setLoadingSessionId(session.id)
    try {
      const detail = await requestJSON<ChatSessionDetailResponse>(
        `/rag-governance/chat/sessions/${session.id}`,
        { method: "GET" },
        20_000,
      )
      setActiveSessionId(detail.id)
      setContext(detail.major_code || "")
      const loaded: AdvisorMessage[] = detail.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        source: mapResponseSource(m.response_source),
        createdAt: m.created_at,
      }))
      setMessages(loaded.length > 0 ? loaded : initialMessages)
      if (!fullscreen) setHistoryOpen(false)
      focusInput()
    } catch {
      // Keep current state if loading failed
    } finally {
      setLoadingSessionId(null)
    }
  }

  const deleteSession = async (sessionId: string) => {
    if (!isAuthenticated) {
      const next = sessions.filter((s) => s.id !== sessionId)
      setSessions(next)
      writeGuestSessions(next)
      if (activeSessionId === sessionId) startNewChat()
      return
    }
    try {
      await requestJSON<void>(
        `/rag-governance/chat/sessions/${sessionId}`,
        { method: "DELETE" },
        20_000,
      )
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      if (activeSessionId === sessionId) startNewChat()
    } catch {
      // Ignore transient error
    }
  }

  const clearAllSessions = async () => {
    setConfirmClearAll(false)
    if (!isAuthenticated) {
      setSessions([])
      localStorage.removeItem(GUEST_CHAT_HISTORY_KEY)
      startNewChat()
      return
    }
    try {
      await requestJSON<{ deleted: number }>(
        "/rag-governance/chat/sessions",
        { method: "DELETE" },
        20_000,
      )
      setSessions([])
      startNewChat()
    } catch {
      // Ignore transient error
    }
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, typing])

  const send = async (text: string) => {
    const trimmed = text.trim()
    if (
      !trimmed ||
      trimmed.length > 4000 ||
      typing ||
      chatBusy.current ||
      connection.state !== "online"
    ) {
      return
    }

    const nowIso = new Date().toISOString()
    const userMsg: AdvisorMessage = {
      id: `local-u-${++messageSequence.current}-${Date.now()}`,
      role: "user",
      content: trimmed,
      createdAt: nowIso,
    }
    const baseMessages =
      messages.length === 1 && messages[0].id === "welcome" ? [] : messages
    const nextWithUser = [...messages, userMsg]
    setMessages(nextWithUser)
    setInput("")
    setTyping(true)
    chatBusy.current = true
    focusInput()
    const version = ++requestVersion.current
    const controller = new AbortController()
    activeRequest.current = controller

    try {
      const history = baseMessages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content.slice(0, 4000),
      }))

      const response = await requestJSON<{
        reply: string
        suggested_followups?: string[]
        context_major_code?: string | null
        session_id?: string | null
        session_title?: string | null
        response_length_mode?: ResponseLengthMode | null
        is_ai_generated: boolean
        is_fallback: boolean
        response_source?: string
        connection_available: boolean
        connection_revision?: string | null
        connection_checked_at?: string | null
      }>(
        "/rag-governance/chat",
        {
          method: "POST",
          signal: controller.signal,
          body: JSON.stringify({
            ...buildEvaluateProfilePayload(assessment),
            message: trimmed,
            major_code: context || null,
            session_id: isAuthenticated ? activeSessionId : null,
            history,
            connection_revision: connection.revisionToken,
            response_length: effort,
          }),
        },
        CHAT_TIMEOUT_MS,
      )

      if (version !== requestVersion.current || controller.signal.aborted) {
        return
      }
      if (typeof response.reply !== "string" || !response.reply.trim()) {
        throw new Error("Missing guidance response")
      }
      const nextMajorCode = response?.context_major_code || context || ""
      setContext(nextMajorCode)
      if (
        !response.connection_available &&
        (response.is_ai_generated || response.is_fallback)
      ) {
        setConnection({
          state: "offline",
          message: "Chưa nhận được phản hồi AI. Bạn có thể kiểm tra lại kết nối.",
        })
      }

      if (
        response?.suggested_followups &&
        response.suggested_followups.length > 0
      ) {
        setActivePrompts(response.suggested_followups.slice(0, 3))
      }

      const replyIso = new Date().toISOString()
      const assistantMsg: AdvisorMessage = {
        id: `local-a-${++messageSequence.current}-${Date.now()}`,
        role: "assistant",
        content: response.reply,
        source: response.is_fallback
          ? "offline_guidance"
          : response.is_ai_generated
            ? undefined
            : "verified_guidance",
        lengthMode: response.response_length_mode || undefined,
        createdAt: replyIso,
      }
      const finalMessages = [...nextWithUser, assistantMsg]
      setMessages(finalMessages)

      // Update session history immediately
      if (isAuthenticated && response.session_id) {
        const sid = response.session_id
        setActiveSessionId(sid)
        setSessions((prev) => {
          const existing = prev.find((s) => s.id === sid)
          const updatedItem: ChatSessionItem = {
            id: sid,
            title:
              response.session_title ||
              existing?.title ||
              makeTitle(trimmed),
            major_code: nextMajorCode || existing?.major_code || null,
            message_count: (existing?.message_count || 0) + 2,
            last_message_preview: makePreview(response.reply),
            created_at: existing?.created_at || nowIso,
            updated_at: replyIso,
          }
          return [updatedItem, ...prev.filter((s) => s.id !== sid)]
        })
      } else if (!isAuthenticated) {
        const sid = activeSessionId || `guest-${Date.now()}`
        setActiveSessionId(sid)
        const storedMessages = finalMessages.filter((m) => m.id !== "welcome")
        setSessions((prev) => {
          const existing = prev.find((s) => s.id === sid)
          const updatedItem: ChatSessionItem = {
            id: sid,
            title: existing?.title || makeTitle(trimmed),
            major_code: nextMajorCode || existing?.major_code || null,
            message_count: storedMessages.length,
            last_message_preview: makePreview(response.reply),
            created_at: existing?.created_at || nowIso,
            updated_at: replyIso,
            localMessages: storedMessages,
          }
          const next = [updatedItem, ...prev.filter((s) => s.id !== sid)]
          writeGuestSessions(next)
          return next
        })
      }
    } catch (error) {
      if (version !== requestVersion.current || controller.signal.aborted) {
        return
      }
      if (error instanceof ApiError && error.status === 409) {
        setConnection({
          state: "offline",
          message:
            "Kết nối AI đã thay đổi. Hãy kiểm tra lại trước khi gửi câu hỏi khác.",
        })
      } else {
        setConnection({ state: "offline", message: unavailableReply })
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `local-err-${++messageSequence.current}-${Date.now()}`,
          role: "assistant",
          content: unavailableReply,
        },
      ])
    } finally {
      if (version === requestVersion.current) {
        chatBusy.current = false
        setTyping(false)
      }
    }
  }

  const connectionLabel =
    connection.state === "checking"
      ? "Đang kiểm tra"
      : connection.state === "online"
        ? "Đang hoạt động"
        : "Chưa kết nối"
  const connectionClass =
    connection.state === "checking"
      ? "bg-slate-100 text-slate-600"
      : connection.state === "online"
        ? "bg-emerald-50 text-emerald-700"
        : "bg-rose-50 text-rose-700"

  const attachStudentProfile = () => {
    const scores = assessment.scores || []
    const summary = scores
      .map((s) => `${s.subject}: ${s.score}đ`)
      .join(", ")
    setInput(
      (prev) =>
        `${prev ? `${prev} ` : ""}Điểm số của mình: ${summary || "chưa có điểm được nhập"}`,
    )
    focusInput()
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (typing || chatBusy.current || connection.state !== "online") return
    void send(input)
  }

  const currentEffortOption =
    EFFORT_OPTIONS.find((item) => item.value === effort) || EFFORT_OPTIONS[0]

  const historySidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200/80 px-4 py-3">
        <div className="flex items-center gap-2">
          <History size={15} className="text-sky-600" />
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-700">
            Lịch sử ({sessions.length})
          </h3>
        </div>
        <button
          type="button"
          onClick={startNewChat}
          className="inline-flex items-center gap-1 rounded-lg bg-sky-600 px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-sky-700"
        >
          <SquarePen size={12} />
          Chat mới
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2.5">
        {sessionsLoading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-slate-500">
            <LoaderCircle size={15} className="animate-spin text-sky-600" />
            <span>Đang tải lịch sử...</span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-4 py-10 text-center">
            <span className="mb-2.5 grid size-10 place-items-center rounded-2xl bg-slate-100 text-slate-400">
              <MessageSquare size={18} />
            </span>
            <p className="text-xs font-semibold text-slate-600">
              Chưa có cuộc trò chuyện nào
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
              {isAuthenticated
                ? "Các cuộc trò chuyện của bạn sẽ tự động được lưu vào tài khoản."
                : "Các cuộc trò chuyện tạm được lưu trên trình duyệt này."}
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {sessions.map((session) => {
              const isActive = activeSessionId === session.id
              const isLoading = loadingSessionId === session.id
              return (
                <div
                  key={session.id}
                  onClick={() => void selectSession(session)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      void selectSession(session)
                    }
                  }}
                  className={`group relative flex cursor-pointer items-start justify-between gap-2 rounded-xl border p-2.5 transition ${
                    isActive
                      ? "border-sky-200 bg-sky-50/90 text-sky-950 shadow-2xs"
                      : "border-transparent bg-white/70 text-slate-700 hover:border-slate-200 hover:bg-white"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-bold leading-snug">
                      {session.title}
                    </p>
                    {session.last_message_preview && (
                      <p className="mt-0.5 line-clamp-1 text-[11px] text-slate-500">
                        {session.last_message_preview}
                      </p>
                    )}
                    <div className="mt-1.5 flex items-center gap-2 text-[10px] font-medium text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Clock size={10} />
                        {formatSessionTime(session.updated_at)}
                      </span>
                      <span>·</span>
                      <span>{session.message_count} tin</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      void deleteSession(session.id)
                    }}
                    title="Xóa cuộc trò chuyện"
                    aria-label="Xóa cuộc trò chuyện"
                    className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg text-slate-400 opacity-70 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"
                  >
                    {isLoading ? (
                      <LoaderCircle size={13} className="animate-spin text-sky-600" />
                    ) : (
                      <Trash2 size={13} />
                    )}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {sessions.length > 0 && (
        <div className="border-t border-slate-200/80 p-2.5">
          {confirmClearAll ? (
            <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50 px-2.5 py-2 text-xs">
              <span className="font-semibold text-rose-800">Xóa tất cả?</span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setConfirmClearAll(false)}
                  className="rounded-lg px-2 py-1 text-[11px] font-semibold text-slate-600 hover:bg-white"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => void clearAllSessions()}
                  className="rounded-lg bg-rose-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-rose-700"
                >
                  Xóa hết
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmClearAll(true)}
              className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
            >
              <Trash2 size={13} />
              Xóa toàn bộ lịch sử
            </button>
          )}
        </div>
      )}
    </div>
  )

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-[80] bg-slate-950/30 backdrop-blur-xs"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.section
            className={`glass-chat fixed z-[90] flex flex-col overflow-hidden ${
              fullscreen
                ? "inset-3 rounded-3xl"
                : "bottom-3 right-3 top-3 w-[min(760px,calc(100vw-24px))] rounded-3xl"
            }`}
            initial={{ opacity: 0, x: 80, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.98 }}
            transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Header */}
            <header className="border-b border-slate-200/80 bg-white/85 px-4 py-3 backdrop-blur-md sm:px-5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-sm sm:size-10 sm:rounded-2xl">
                    <Bot size={20} />
                  </span>
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <h2 className="truncate text-sm font-bold text-slate-900 sm:text-base">
                      Cố vấn AI
                    </h2>
                    <span
                      role="status"
                      aria-live="polite"
                      className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${connectionClass}`}
                    >
                      {connection.state === "checking" ? (
                        <LoaderCircle
                          size={12}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                      ) : connection.state === "online" ? (
                        <CircleCheck size={12} aria-hidden="true" />
                      ) : (
                        <CircleAlert size={12} aria-hidden="true" />
                      )}
                      {connectionLabel}
                    </span>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setHistoryOpen((v) => !v)}
                    title="Lịch sử trò chuyện"
                    aria-label="Lịch sử trò chuyện"
                    className={`inline-flex h-9 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-semibold transition ${
                      historyOpen
                        ? "border-sky-300 bg-sky-50 text-sky-700"
                        : "border-slate-200/90 bg-white text-slate-600 hover:border-sky-200 hover:bg-sky-50/60 hover:text-sky-700"
                    }`}
                  >
                    <History size={15} />
                    <span className="hidden sm:inline">Lịch sử</span>
                    {sessions.length > 0 && (
                      <span className="rounded-full bg-sky-100 px-1.5 py-0.2 text-[10px] font-bold text-sky-700">
                        {sessions.length}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={startNewChat}
                    title="Cuộc trò chuyện mới"
                    aria-label="Cuộc trò chuyện mới"
                    className="sidebar-icon-button"
                  >
                    <SquarePen size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setFullscreen((v) => !v)}
                    className="sidebar-icon-button hidden sm:grid"
                    aria-label={fullscreen ? "Thu nhỏ" : "Toàn màn hình"}
                  >
                    {fullscreen ? (
                      <Minimize2 size={17} />
                    ) : (
                      <Maximize2 size={17} />
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    className="sidebar-icon-button"
                    aria-label="Đóng chat"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              {connection.state === "offline" && (
                <div
                  role="status"
                  className="mt-2.5 flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
                >
                  <span>{connection.message}</span>
                  <button
                    type="button"
                    onClick={() => void checkConnection()}
                    className="inline-flex shrink-0 items-center gap-1.5 font-semibold underline underline-offset-2"
                    aria-label="Kiểm tra lại kết nối AI"
                  >
                    Kiểm tra lại
                  </button>
                </div>
              )}

              <div className="relative mt-2.5 flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white/90 px-3 py-1.5 text-xs">
                <GraduationCap
                  size={15}
                  className="shrink-0 text-sky-600"
                />
                <span className="shrink-0 font-semibold text-slate-500">
                  Ngành:
                </span>
                <select
                  value={context}
                  onChange={(e) => changeTopic(e.target.value)}
                  aria-label="Ngành quan tâm"
                  className="w-full min-w-0 appearance-none bg-transparent pr-5 font-bold text-slate-800 outline-none"
                >
                  <option value="">Hướng nghiệp chung</option>
                  {MOET_435_MAJORS.map((major) => (
                    <option key={major.major_code} value={major.major_code}>
                      {major.name_vi} · {major.major_code}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={14}
                  className="pointer-events-none shrink-0 text-slate-400"
                />
              </div>
            </header>

            {/* Body with collapsible History Panel */}
            <div className="relative flex min-h-0 flex-1 overflow-hidden">
              {/* Fullscreen docked History Sidebar */}
              <AnimatePresence initial={false}>
                {historyOpen && fullscreen && (
                  <motion.aside
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 288, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
                    className="h-full shrink-0 overflow-hidden border-r border-slate-200/80 bg-slate-50/90"
                  >
                    <div className="h-full w-72">{historySidebarContent}</div>
                  </motion.aside>
                )}
              </AnimatePresence>

              {/* Drawer History Overlay when not fullscreen */}
              <AnimatePresence>
                {historyOpen && !fullscreen && (
                  <>
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onClick={() => setHistoryOpen(false)}
                      className="absolute inset-0 z-10 bg-slate-900/20 backdrop-blur-[1px]"
                    />
                    <motion.aside
                      initial={{ x: -300, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      exit={{ x: -300, opacity: 0 }}
                      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                      className="absolute inset-y-0 left-0 z-20 w-[min(300px,86%)] border-r border-slate-200 bg-white/95 shadow-xl backdrop-blur-md"
                    >
                      {historySidebarContent}
                    </motion.aside>
                  </>
                )}
              </AnimatePresence>

              {/* Messages + Footer Column */}
              <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
                  <div
                    className={`mx-auto space-y-5 ${
                      fullscreen ? "max-w-4xl" : "max-w-2xl"
                    }`}
                  >
                    {messages.map((message) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.2 }}
                        className={`flex gap-3.5 ${
                          message.role === "user" ? "flex-row-reverse" : ""
                        }`}
                      >
                        <span
                          className={`grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold ${
                            message.role === "assistant"
                              ? "bg-sky-100 text-sky-700"
                              : "bg-sky-600 text-white"
                          }`}
                        >
                          {message.role === "assistant" ? (
                            <Sparkles size={16} />
                          ) : (
                            <User size={15} />
                          )}
                        </span>
                        <div
                          className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-3 text-sm leading-relaxed break-words ${
                            message.role === "assistant"
                              ? "rounded-tl-md border border-slate-200/80 bg-white text-slate-800 shadow-xs"
                              : "rounded-tr-md bg-sky-600 text-white shadow-sm"
                          }`}
                        >
                          {message.role === "assistant" ? (
                            <>
                              {(message.source || message.lengthMode) && (
                                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                                  {message.source && (
                                    <span
                                      className={`text-[11px] font-semibold ${
                                        message.source === "offline_guidance"
                                          ? "text-amber-700"
                                          : "text-slate-500"
                                      }`}
                                    >
                                      {message.source === "offline_guidance"
                                        ? "Hướng dẫn có sẵn — AI chưa kết nối"
                                        : "Hướng dẫn từ dữ liệu hệ thống"}
                                    </span>
                                  )}
                                  {message.lengthMode && (
                                    <span
                                      title="Mức độ suy luận"
                                      className="inline-flex items-center gap-1 rounded-full border border-sky-200/80 bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-700"
                                    >
                                      <Brain size={10} />
                                      {LENGTH_MODE_LABELS[message.lengthMode]}
                                    </span>
                                  )}
                                </div>
                              )}
                              <div className="markdown advisor-markdown min-w-0 max-w-full">
                                <Markdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    pre: ({ children }) => (
                                      <div className="my-2.5 max-w-full overflow-x-auto rounded-xl border border-slate-200/90 bg-slate-900 text-slate-100 shadow-2xs">
                                        <pre className="m-0 w-max min-w-full p-3.5 font-mono text-xs leading-relaxed">
                                          {children}
                                        </pre>
                                      </div>
                                    ),
                                    code: ({
                                      className,
                                      children,
                                      ...props
                                    }) => (
                                      <code className={className} {...props}>
                                        {children}
                                      </code>
                                    ),
                                    table: ({ children }) => (
                                      <div className="my-3 max-w-full overflow-x-auto rounded-xl border border-slate-200/80">
                                        <table className="w-full min-w-max border-collapse text-xs sm:text-sm">
                                          {children}
                                        </table>
                                      </div>
                                    ),
                                  }}
                                >
                                  {message.content}
                                </Markdown>
                              </div>
                            </>
                          ) : (
                            <span className="whitespace-pre-wrap break-words">
                              {message.content}
                            </span>
                          )}
                        </div>
                      </motion.div>
                    ))}

                    {typing && (
                      <div className="flex items-center gap-3">
                        <span className="grid size-9 place-items-center rounded-xl bg-sky-100 text-sky-700">
                          <Sparkles size={16} />
                        </span>
                        <span className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-slate-200/80 bg-white px-4 py-3 shadow-xs">
                          {[0, 1, 2].map((i) => (
                            <motion.span
                              key={i}
                              className="size-2 rounded-full bg-sky-500"
                              animate={{
                                y: [0, -5, 0],
                                opacity: [0.4, 1, 0.4],
                              }}
                              transition={{
                                duration: 0.7,
                                repeat: Infinity,
                                delay: i * 0.12,
                              }}
                            />
                          ))}
                        </span>
                      </div>
                    )}
                    <div ref={endRef} />
                  </div>
                </div>

                {/* Footer Input */}
                <div className="border-t border-slate-200/80 bg-white/90 px-3 py-2.5 backdrop-blur-md sm:px-4 sm:py-3">
                  <div
                    className={`mx-auto ${fullscreen ? "max-w-4xl" : "max-w-2xl"}`}
                  >
                    <div className="mb-2 flex gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                      {activePrompts.map((prompt) => (
                        <button
                          key={prompt}
                          type="button"
                          onClick={() => void send(prompt)}
                          disabled={connection.state !== "online" || typing}
                          className="shrink-0 rounded-full border border-sky-200/80 bg-sky-50/70 px-3 py-1 text-xs font-semibold text-sky-800 transition hover:bg-sky-100 disabled:opacity-50"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>

                    <form
                      onSubmit={submit}
                      className="rounded-2xl border border-slate-200 bg-white px-3 pt-2 pb-1.5 shadow-2xs transition focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-500/15"
                    >
                      <textarea
                        ref={inputRef}
                        rows={1}
                        maxLength={4000}
                        aria-label="Câu hỏi hướng nghiệp"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (
                            e.key === "Enter" &&
                            !e.shiftKey &&
                            !e.nativeEvent.isComposing
                          ) {
                            e.preventDefault()
                            if (
                              !typing &&
                              !chatBusy.current &&
                              connection.state === "online" &&
                              input.trim()
                            ) {
                              void send(input)
                            }
                          }
                        }}
                        placeholder="Nhập câu hỏi..."
                        className="max-h-28 min-h-9 w-full resize-none bg-transparent px-1 py-1 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
                      />

                      <div className="mt-1 flex items-center justify-between gap-2 pt-1">
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={attachStudentProfile}
                            title="Đính kèm điểm học tập"
                            aria-label="Đính kèm điểm học tập"
                            className="grid size-8 shrink-0 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-sky-600"
                          >
                            <Paperclip size={16} />
                          </button>

                          <div ref={effortMenuRef} className="relative">
                            <AnimatePresence>
                              {effortMenuOpen && (
                                <motion.div
                                  initial={{ opacity: 0, y: 6, scale: 0.97 }}
                                  animate={{ opacity: 1, y: 0, scale: 1 }}
                                  exit={{ opacity: 0, y: 4, scale: 0.97 }}
                                  transition={{
                                    duration: 0.15,
                                    ease: [0.22, 1, 0.36, 1],
                                  }}
                                  role="menu"
                                  aria-label="Mức độ suy luận"
                                  className="absolute bottom-full left-0 z-30 mb-2 w-56 rounded-2xl border border-slate-200/90 bg-white p-1.5 shadow-xl ring-1 ring-slate-900/5"
                                >
                                  <div className="flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-500">
                                    <span>Mức độ suy luận</span>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        setEffortInfoOpen((v) => !v)
                                      }
                                      aria-label="Thông tin mức độ suy luận"
                                      className="grid size-5 place-items-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-sky-600"
                                    >
                                      <Info size={13} />
                                    </button>
                                  </div>
                                  {effortInfoOpen && (
                                    <p className="mx-1.5 mb-1.5 rounded-xl bg-sky-50 px-2.5 py-2 text-[11px] leading-relaxed text-sky-900">
                                      Tự động điều chỉnh theo câu hỏi, hoặc chọn
                                      cố định từ Thấp đến Rất cao.
                                    </p>
                                  )}
                                  <div className="space-y-0.5">
                                    {EFFORT_OPTIONS.map((opt) => {
                                      const selected = effort === opt.value
                                      return (
                                        <button
                                          key={opt.value}
                                          type="button"
                                          role="menuitemradio"
                                          aria-checked={selected}
                                          onClick={() => {
                                            setEffort(opt.value)
                                            setEffortMenuOpen(false)
                                            setEffortInfoOpen(false)
                                            focusInput()
                                          }}
                                          className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition ${
                                            selected
                                              ? "bg-sky-50/90 font-bold text-slate-900"
                                              : "font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                                          }`}
                                        >
                                          <span>{opt.label}</span>
                                          {selected && (
                                            <Check
                                              size={15}
                                              className="text-sky-600"
                                            />
                                          )}
                                        </button>
                                      )
                                    })}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>

                            <button
                              type="button"
                              onClick={() => {
                                setEffortMenuOpen((v) => !v)
                                setEffortInfoOpen(false)
                              }}
                              aria-haspopup="menu"
                              aria-expanded={effortMenuOpen}
                              title="Mức độ suy luận của AI"
                              className={`inline-flex h-8 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-semibold transition ${
                                effortMenuOpen
                                  ? "border-sky-300 bg-sky-50 text-sky-800"
                                  : "border-slate-200/90 bg-slate-50/80 text-slate-700 hover:border-sky-200 hover:bg-sky-50/60 hover:text-sky-800"
                              }`}
                            >
                              <Brain size={14} className="text-sky-600" />
                              <span>{currentEffortOption.label}</span>
                              <ChevronDown
                                size={13}
                                className={`text-slate-400 transition-transform duration-150 ${
                                  effortMenuOpen ? "rotate-180" : ""
                                }`}
                              />
                            </button>
                          </div>
                        </div>

                        <button
                          type="submit"
                          disabled={
                            !input.trim() ||
                            typing ||
                            connection.state !== "online"
                          }
                          title={
                            typing
                              ? "Đang xử lý câu hỏi trước..."
                              : "Gửi tin nhắn"
                          }
                          aria-label={
                            typing
                              ? "Đang xử lý câu hỏi trước"
                              : "Gửi tin nhắn"
                          }
                          className="grid size-8 shrink-0 place-items-center rounded-xl bg-sky-600 text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-45"
                        >
                          {typing ? (
                            <LoaderCircle size={16} className="animate-spin" />
                          ) : (
                            <ArrowUp size={17} />
                          )}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          </motion.section>
        </>
      )}
    </AnimatePresence>
  )
}
