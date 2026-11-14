import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowUp,
  Bot,
  Brain,
  Check,
  ChevronDown,
  GraduationCap,
  Maximize2,
  Minimize2,
  Paperclip,
  ShieldCheck,
  Sparkles,
  Target,
  User,
  X,
} from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest } from "../services/api"

interface AIChatAdvisorProps {
  open: boolean
  onClose: () => void
}

interface AdvisorMessage {
  id: number
  role: "assistant" | "user"
  content: string
}

const initialMessages: AdvisorMessage[] = [
  {
    id: 1,
    role: "assistant",
    content: `## Chào bạn, mình là Cố vấn AI Hướng nghiệp

Mình phân tích hồ sơ năng lực 3 trụ cột (Sở thích Holland RIASEC, Học lực chuẩn hóa Z-Score, Phong cách nhận thức) kết hợp dữ liệu 435 ngành chuẩn GD&ĐT để giải thích và tư vấn định hướng.

### Bạn có thể bắt đầu với:
- Giải thích chi tiết vì sao một ngành phù hợp với tổ hợp điểm của bạn.
- Đề xuất các ngành an toàn, vừa sức và ngành thử thách.
- Xây dựng kế hoạch học tập 4 tuần để trải nghiệm ngành học.`,
  },
]

const quickPrompts = [
  "Giải thích vì sao ngành Kỹ thuật phần mềm đạt mức Khả thi cao?",
  "Tạo kế hoạch tự học Tuần 1 cho ngành Khoa học máy tính",
  "Những kỹ năng nào mình cần rèn luyện thêm?",
]

function buildAnswer(question: string) {
  const value = question.toLowerCase()
  if (value.includes("kỹ thuật phần mềm") || value.includes("công nghệ thông tin")) {
    return `### Phân tích Ngành Kỹ thuật phần mềm & CNTT

1. **Sở thích (I/R):** Năng lực nghiên cứu và tư duy kỹ thuật rất phù hợp với quy trình phát triển sản phẩm công nghệ.
2. **Học lực:** Điểm số tổ hợp các môn Toán, Tự nhiên hoặc Ngoại ngữ vượt ngưỡng điểm sàn tham chiếu an toàn.
3. **Chiến lược:** Có thể đặt làm **Nguyện vọng 1 - 2** nếu điểm thực tế đạt mức vượt chuẩn, hoặc chuẩn bị ngành dự phòng tương đồng trong nhóm CNTT.`
  }
  if (value.includes("tuần 1") || value.includes("kế hoạch") || value.includes("lộ trình")) {
    return `### Kế hoạch tuần 1: Nền tảng tư duy & Công cụ

- **Mục tiêu:** Nắm vững cấu trúc ngành, các môn học cơ sở và cài đặt môi trường thực hành.
- **Nhiệm vụ 1:** Đọc đề cương chi tiết chương trình đào tạo tại 3 trường đại học mục tiêu.
- **Nhiệm vụ 2:** Hoàn thành 1 bài giảng nhập môn cơ bản (Python hoặc thuật toán tư duy).
- **Nhiệm vụ 3:** Tự đánh giá mức độ hào hứng sau khi thử nghiệm 3 buổi học đầu tiên.`
  }
  return `### Phân tích Định hướng Cá nhân hóa

Dựa trên dữ liệu hồ sơ của bạn, hệ thống khuyến nghị:
- **Tập trung vào thế mạnh:** Phát huy các môn học có Z-Score cao nhất trong tổ hợp xét tuyển.
- **Bổ sung kỹ năng:** Rèn luyện khả năng tư duy giải quyết vấn đề và tiếng Anh chuyên ngành.
- Bạn có muốn tìm hiểu cụ thể về một ngành nào trong danh mục 435 ngành không?`
}

export function AIChatAdvisor({ open, onClose }: AIChatAdvisorProps) {
  const [messages, setMessages] = useState<AdvisorMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [typing, setTyping] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [context, setContext] = useState("Khoa học máy tính · 7480101")
  const { assessment } = useAssessment()
  const endRef = useRef<HTMLDivElement | null>(null)

  const [activePrompts, setActivePrompts] = useState<string[]>(quickPrompts)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, typing])

  const send = async (text: string) => {
    if (!text.trim() || typing) return
    const userMsg: AdvisorMessage = {
      id: Date.now(),
      role: "user",
      content: text.trim(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setTyping(true)

    try {
      const matchCode = context.match(/\b\d{7}\b/)?.[0]

      const gradesBySubject: Record<string, number> = {}
      if (Array.isArray(assessment.scores)) {
        for (const s of assessment.scores) {
          if (s.subject && typeof s.score === "number") {
            gradesBySubject[s.subject.toLowerCase()] = s.score
          }
        }
      }

      const riasecScores: Record<string, number> = {}
      if (assessment.answers && Object.keys(assessment.answers).length > 0) {
        const counts: Record<string, number> = { R: 0, I: 0, A: 0, S: 0, E: 0, C: 0 }
        const totals: Record<string, number> = { R: 0, I: 0, A: 0, S: 0, E: 0, C: 0 }
        for (const [k, v] of Object.entries(assessment.answers)) {
          const dim = k.charAt(0).toUpperCase()
          if (dim in counts && typeof v === "number") {
            counts[dim] += v
            totals[dim] += 5
          }
        }
        for (const dim of ["R", "I", "A", "S", "E", "C"]) {
          if (totals[dim] > 0) {
            riasecScores[dim] = Number((counts[dim] / totals[dim]).toFixed(2))
          }
        }
      }

      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const response = await apiRequest<{
        reply?: string
        answer?: string
        content?: string
        suggested_followups?: string[]
      }>(
        "/rag-governance/chat",
        { reply: "" },
        {
          method: "POST",
          body: JSON.stringify({
            message: text.trim(),
            major_code: matchCode || undefined,
            history,
            riasec_scores: Object.keys(riasecScores).length > 0 ? riasecScores : undefined,
            grades_by_subject: Object.keys(gradesBySubject).length > 0 ? gradesBySubject : undefined,
            cognitive_preferences:
              Object.keys(assessment.cognitive || {}).length > 0
                ? assessment.cognitive
                : undefined,
          }),
        },
      ).catch(() => null)

      const replyContent =
        response?.reply || response?.answer || response?.content || buildAnswer(text)

      if (response?.suggested_followups && response.suggested_followups.length > 0) {
        setActivePrompts(response.suggested_followups.slice(0, 3))
      }

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: replyContent,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: buildAnswer(text),
        },
      ])
    } finally {
      setTyping(false)
    }
  }

  const attachStudentProfile = () => {
    const scores = assessment.scores || []
    const summary = scores
      .map((s) => `${s.subject}: ${s.score}đ`)
      .join(", ")
    setInput(
      (prev) =>
        `${prev ? `${prev} ` : ""}Điểm số của mình: ${summary || "Toán 8.5, Lý 8.0, Hóa 8.0"}`,
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
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                        <span className="size-1.5 rounded-full bg-emerald-500" />
                        Trực tuyến
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

              <div className="mt-3.5 flex items-center gap-2.5 rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-xs">
                <GraduationCap size={16} className="text-sky-600 shrink-0" />
                <span className="font-semibold text-slate-500 shrink-0">
                  Ngành quan tâm:
                </span>
                <select
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  className="w-full bg-transparent font-bold text-slate-800 outline-none"
                >
                  <option>Khoa học máy tính · 7480101</option>
                  <option>Trí tuệ nhân tạo · 7480107</option>
                  <option>Kỹ thuật phần mềm · 7480103</option>
                  <option>Khoa học dữ liệu · 7460108</option>
                  <option>Marketing số · 7340115</option>
                  <option>Quản trị kinh doanh · 7340101</option>
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
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        message.role === "assistant"
                          ? "rounded-tl-md border border-slate-200/80 bg-white text-slate-800 shadow-xs"
                          : "rounded-tr-md bg-sky-600 text-white shadow-sm"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <div className="markdown advisor-markdown">
                          <Markdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </Markdown>
                        </div>
                      ) : (
                        <span>{message.content}</span>
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
                      className="shrink-0 rounded-full border border-sky-200/80 bg-sky-50/70 px-3 py-1.5 text-xs font-semibold text-sky-800 transition hover:bg-sky-100"
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
                    title="Đính kèm điểm học tập"
                    className="grid size-10 shrink-0 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-sky-600"
                  >
                    <Paperclip size={18} />
                  </button>
                  <textarea
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        send(input)
                      }
                    }}
                    placeholder="Hỏi AI về ngành học, điểm số hoặc lộ trình..."
                    className="max-h-28 min-h-10 flex-1 resize-none bg-transparent px-1 py-2 text-sm leading-relaxed text-slate-800 outline-none placeholder:text-slate-400"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || typing}
                    className="grid size-10 shrink-0 place-items-center rounded-xl bg-sky-600 text-white transition hover:bg-sky-700 disabled:opacity-40"
                    aria-label="Gửi tin nhắn"
                  >
                    <ArrowUp size={18} />
                  </button>
                </form>

                <div className="mt-2 flex items-center justify-center gap-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Check size={12} className="text-emerald-500" /> Dữ liệu chuẩn
                  </span>
                  <span className="flex items-center gap-1">
                    <Brain size={12} className="text-sky-500" /> Giải thích XAI
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
