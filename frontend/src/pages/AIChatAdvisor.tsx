import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowUp,
  Bot,
  Brain,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  GraduationCap,
  LoaderCircle,
  Maximize2,
  Minimize2,
  Paperclip,
  Sparkles,
  Target,
  User,
  X,
} from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { useSelectedAssessment } from "../hooks/useSelectedAssessment"
import { useAuth } from "../context/AuthContext"
import { useLocation } from "react-router"
import { buildEvaluateProfilePayload } from "../utils/assessmentPayload"
import { MOET_435_MAJORS } from "../data/moetMajors435"
import { ApiError, requestJSON } from "../services/api"

interface AIChatAdvisorProps {
  open: boolean
  onClose: () => void
}

interface AdvisorMessage {
  id: number
  role: "assistant" | "user"
  content: string
  source?: "verified_guidance" | "offline_guidance"
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
const CONNECTION_CHECK_FAILED = "Không xác minh được kết nối AI. Thử kiểm tra lại trước khi gửi câu hỏi."

const initialMessages: AdvisorMessage[] = [
  {
    id: 1,
    role: "assistant",
    content: `## Chào bạn, mình là Cố vấn Hướng nghiệp

Mình giúp tìm hiểu ngành học, giải thích sở thích và học lực theo hồ sơ bạn đang xem. Điểm phù hợp chỉ là gợi ý tham khảo, không phải xác suất trúng tuyển.

Bạn có thể hỏi về yêu cầu của ngành, dữ liệu còn thiếu hoặc kế hoạch trải nghiệm phù hợp thời gian của mình.`,
  },
]

const quickPrompts = [
  "Hồ sơ của mình còn thiếu dữ liệu gì để đối chiếu ngành học?",
  "Mình muốn tìm hiểu ngành Khoa học máy tính",
  "Những kỹ năng nào cần tìm hiểu khi chọn nghề?",
]
const unavailableReply = "Chưa nhận được phản hồi tư vấn. Hãy kiểm tra lại kết nối rồi gửi lại câu hỏi."

export function AIChatAdvisor({ open, onClose }: AIChatAdvisorProps) {
  const [messages, setMessages] = useState<AdvisorMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [typing, setTyping] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [context, setContext] = useState("")
  const assessment = useSelectedAssessment()
  const { user, token } = useAuth()
  const location = useLocation()
  const requestVersion = useRef(0)
  const connectionRequest = useRef<AbortController | null>(null)
  const activeRequest = useRef<AbortController | null>(null)
  const connectionVersion = useRef(0)
  const chatBusy = useRef(false)
  const probeBusy = useRef(false)
  const snapshotKey = JSON.stringify({ user: user?.id || user?.email, path: location.pathname, profile: assessment })
  const messageSequence = useRef(1)
  const endRef = useRef<HTMLDivElement | null>(null)

  const [activePrompts, setActivePrompts] = useState<string[]>(quickPrompts)

  const [connection, setConnection] = useState<ConnectionState>({ state: "checking" })

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
      if (version !== connectionVersion.current || controller.signal.aborted) return
      if (!result.available || !result.revision_token) {
        setConnection({ state: "offline", message: result.message || CONNECTION_CHECK_FAILED })
        return
      }
      setConnection({ state: "online", revisionToken: result.revision_token, checkedAt: result.checked_at })
    } catch {
      if (version !== connectionVersion.current || controller.signal.aborted) return
      setConnection({ state: "offline", message: CONNECTION_CHECK_FAILED })
    } finally {
      if (version === connectionVersion.current) probeBusy.current = false
    }
  }

  useEffect(() => {
    requestVersion.current += 1
    activeRequest.current?.abort()
    chatBusy.current = false
    setInput("")
    setContext("")
    setMessages(initialMessages)
    setActivePrompts(quickPrompts)
    setTyping(false)
  }, [snapshotKey, token])

  useEffect(() => {
    if (!open) return
    setTyping(false)
    setConnection({ state: "checking" })
    // StrictMode discards its first effect setup before this task runs.
    // Profile/topic changes do not spend tokens on another connection probe.
    const timer = window.setTimeout(() => void checkConnection(), 0)
    return () => {
      window.clearTimeout(timer)
      connectionVersion.current += 1
      requestVersion.current += 1
      connectionRequest.current?.abort()
      activeRequest.current?.abort()
      chatBusy.current = false
      probeBusy.current = false
    }
  }, [open])

  const changeTopic = (code: string) => {
    requestVersion.current += 1
    activeRequest.current?.abort()
    chatBusy.current = false
    setContext(code)
    setMessages(initialMessages)
    setActivePrompts(quickPrompts)
    setTyping(false)
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, typing])

  const send = async (text: string) => {
    if (!text.trim() || text.trim().length > 4000 || typing || chatBusy.current || connection.state !== "online") return
    const userMsg: AdvisorMessage = {
      id: ++messageSequence.current,
      role: "user",
      content: text.trim(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setTyping(true)
    chatBusy.current = true
    const version = ++requestVersion.current
    const controller = new AbortController()
    activeRequest.current = controller

    try {
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content.slice(0, 4000),
      }))

      const response = await requestJSON<{
        reply: string
        suggested_followups?: string[]
        context_major_code?: string | null
        is_ai_generated: boolean
        is_fallback: boolean
        response_source?: string
        connection_available: boolean
        connection_revision?: string | null
        connection_checked_at?: string | null
      }>("/rag-governance/chat", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          ...buildEvaluateProfilePayload(assessment),
          message: text.trim(),
          major_code: context || null,
          history,
          connection_revision: connection.revisionToken,
        }),
      }, CHAT_TIMEOUT_MS)

      if (version !== requestVersion.current || controller.signal.aborted) return
      if (typeof response.reply !== "string" || !response.reply.trim()) throw new Error("Missing guidance response")
      setContext(response?.context_major_code || "")
      if (!response.connection_available && (response.is_ai_generated || response.is_fallback)) {
        setConnection({ state: "offline", message: "Chưa nhận được phản hồi AI. Bạn có thể kiểm tra lại kết nối." })
      }

      if (response?.suggested_followups && response.suggested_followups.length > 0) {
        setActivePrompts(response.suggested_followups.slice(0, 3))
      }

      setMessages((prev) => [
        ...prev,
        {
          id: ++messageSequence.current,
          role: "assistant",
          content: response.reply,
          source: response.is_fallback ? "offline_guidance" : response.is_ai_generated ? undefined : "verified_guidance",
        },
      ])
    } catch (error) {
      if (version !== requestVersion.current || controller.signal.aborted) return
      if (error instanceof ApiError && error.status === 409) {
        setConnection({ state: "offline", message: "Kết nối AI đã thay đổi. Hãy kiểm tra lại trước khi gửi câu hỏi khác." })
      } else {
        setConnection({ state: "offline", message: unavailableReply })
      }
      setMessages((prev) => [
        ...prev,
        {
          id: ++messageSequence.current,
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

  const connectionLabel = connection.state === "checking"
    ? "Đang kiểm tra"
    : connection.state === "online" ? "Đang hoạt động" : "Chưa kết nối"
  const connectionClass = connection.state === "checking"
    ? "bg-slate-100 text-slate-600"
    : connection.state === "online" ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"

  const attachStudentProfile = () => {
    const scores = assessment.scores || []
    const summary = scores
      .map((s) => `${s.subject}: ${s.score}đ`)
      .join(", ")
    setInput(
      (prev) =>
        `${prev ? `${prev} ` : ""}Điểm số của mình: ${summary || "chưa có điểm được nhập"}`,
    )
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    send(input)
  }

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
                : "bottom-3 right-3 top-3 w-[min(720px,calc(100vw-24px))] rounded-3xl"
            }`}
            initial={{ opacity: 0, x: 80, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.98 }}
            transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Header */}
            <header className="border-b border-slate-200/80 bg-white/80 px-5 py-4 backdrop-blur-md">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-sm">
                    <Bot size={22} />
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-slate-900">
                        Cố vấn AI Hướng nghiệp
                      </h2>
                      <span role="status" aria-live="polite" className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${connectionClass}`}>
                        {connection.state === "checking" ? <LoaderCircle size={13} className="animate-spin" aria-hidden="true" /> : connection.state === "online" ? <CircleCheck size={13} aria-hidden="true" /> : <CircleAlert size={13} aria-hidden="true" />}
                        {connectionLabel}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Tư vấn giải thích chọn ngành và lộ trình học tập
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setFullscreen((v) => !v)}
                    className="sidebar-icon-button hidden sm:grid"
                    aria-label={fullscreen ? "Thu nhỏ" : "Toàn màn hình"}
                  >
                    {fullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
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
                <div role="status" className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
                  <span>{connection.message}</span>
                  <button type="button" onClick={() => void checkConnection()} className="inline-flex shrink-0 items-center gap-1.5 font-semibold underline underline-offset-2" aria-label="Kiểm tra lại kết nối AI">
                    Kiểm tra lại
                  </button>
                </div>
              )}

              <div className="mt-3.5 flex items-center gap-2.5 rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-xs">
                <GraduationCap size={16} className="text-sky-600 shrink-0" />
                <span className="font-semibold text-slate-500 shrink-0">
                  Ngành quan tâm:
                </span>
                <select
                  value={context}
                  onChange={(e) => changeTopic(e.target.value)}
                  aria-label="Ngành quan tâm"
                  className="w-full bg-transparent font-bold text-slate-800 outline-none"
                >
                  <option value="">Chưa chọn ngành / hỏi hướng nghiệp chung</option>
                  {MOET_435_MAJORS.map(major => <option key={major.major_code} value={major.major_code}>{major.name_vi} · {major.major_code}</option>)}
                </select>
                <ChevronDown size={14} className="text-slate-400 shrink-0" />
              </div>
            </header>

            {/* Messages Body */}
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
                          {message.source && <p className={`mb-2 text-[11px] font-semibold ${message.source === "offline_guidance" ? "text-amber-700" : "text-slate-500"}`}>{message.source === "offline_guidance" ? "Hướng dẫn có sẵn — AI chưa kết nối" : "Hướng dẫn từ dữ liệu hệ thống"}</p>}
                          <div className="markdown advisor-markdown min-w-0 max-w-full">
                            <Markdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                pre: ({ children }) => (
                                  <div className="my-2.5 max-w-full overflow-x-auto rounded-xl border border-slate-200/90 bg-slate-900 text-slate-100 shadow-2xs">
                                    <pre className="m-0 w-max min-w-full p-3.5 text-xs leading-relaxed font-mono">
                                      {children}
                                    </pre>
                                  </div>
                                ),
                                code: ({ className, children, ...props }) => (
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
                        <span className="whitespace-pre-wrap break-words">{message.content}</span>
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
                          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
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
            <div className="border-t border-slate-200/80 bg-white/90 p-3 sm:p-4 backdrop-blur-md">
              <div
                className={`mx-auto ${fullscreen ? "max-w-4xl" : "max-w-2xl"}`}
              >
                <div className="mb-2.5 flex gap-2 overflow-x-auto pb-1">
                  {activePrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => send(prompt)}
                      disabled={connection.state !== "online" || typing}
                      className="shrink-0 rounded-full border border-sky-200/80 bg-sky-50/70 px-3 py-1.5 text-xs font-semibold text-sky-800 transition hover:bg-sky-100 disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                <form
                  onSubmit={submit}
                  className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-500/15"
                >
                  <button
                    type="button"
                    onClick={attachStudentProfile}
                    disabled={connection.state !== "online" || typing}
                    title="Đính kèm điểm học tập"
                    className="grid size-10 shrink-0 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-sky-600"
                  >
                    <Paperclip size={18} />
                  </button>
                  <textarea
                    rows={1}
                    maxLength={4000}
                    aria-label="Câu hỏi hướng nghiệp"
                    value={input}
                    disabled={connection.state !== "online" || typing}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                        e.preventDefault()
                        send(input)
                      }
                    }}
                    placeholder="Hỏi AI về ngành học, điểm số hoặc lộ trình..."
                    className="max-h-28 min-h-10 flex-1 resize-none bg-transparent px-1 py-2 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || typing || connection.state !== "online"}
                    className="grid size-10 shrink-0 place-items-center rounded-xl bg-sky-600 text-white transition hover:bg-sky-700 disabled:opacity-40"
                    aria-label="Gửi tin nhắn"
                  >
                    <ArrowUp size={18} />
                  </button>
                </form>

                <div className="mt-2 flex items-center justify-center gap-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Check size={12} className="text-emerald-500" /> Thông tin tham khảo
                  </span>
                  <span className="flex items-center gap-1">
                    <Brain size={12} className="text-sky-500" /> Giải thích theo hồ sơ
                  </span>
                  <span className="flex items-center gap-1">
                    <Target size={12} className="text-cyan-500" /> Định hướng cá nhân
                  </span>
                </div>
              </div>
            </div>
          </motion.section>
        </>
      )}
    </AnimatePresence>
  )
}
