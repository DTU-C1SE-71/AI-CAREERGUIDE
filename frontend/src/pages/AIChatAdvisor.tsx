import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowUp,
  Bot,
  Brain,
  Check,
  ChevronDown,
  FilePlus2,
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
    content: `## Chào Linh, mình là AI Career Advisor

Mình đang sử dụng **Guidance RAG** để đối chiếu hồ sơ của bạn với dữ liệu ngành học chuẩn hóa.

### Ba tín hiệu nổi bật
- **RIASEC:** Investigative (I) — 92/100
- **Học lực:** A00 có Z-Score **+1.18**
- **Nhận thức:** Tư duy phân tích và học qua thực hành

Bạn muốn bắt đầu từ việc giải thích một ngành hay xây lộ trình 4 tuần?`,
  },
]

const quickPrompts = [
  "Giải thích vì sao ngành Kỹ thuật phần mềm đạt mức TARGET với điểm A00 của mình?",
  "Tạo kế hoạch tự học Tuần 1 cho ngành Khoa học dữ liệu",
  "Các kỹ năng còn thiếu (Competency Gaps) cần bổ sung?",
]

function buildAnswer(question: string) {
  const value = question.toLowerCase()
  if (value.includes("kỹ thuật phần mềm") || value.includes("target"))
    return `## Vì sao Kỹ thuật phần mềm là TARGET?

Mức **TARGET 91%** được hình thành từ ba thành phần:

| Trụ cột | Điểm | Giải thích |
| --- | ---: | --- |
| RIASEC | 94% | Nhóm **Investigative** phù hợp công việc phân tích và giải quyết vấn đề |
| Z-Score A00 | 89% | Toán và Vật lý đang cao hơn nhóm tham chiếu |
| Nhận thức | 90% | Bạn học tốt qua dự án và phản hồi nhanh |

### Bước tiếp theo
1. Trải nghiệm một bài toán thuật toán trong 45 phút.
2. Hoàn thành mini project trong tuần 3.
3. So sánh mức hứng thú trước và sau trải nghiệm.

> TARGET nghĩa là khả thi cao ở thời điểm hiện tại, không phải cam kết trúng tuyển.`
  if (value.includes("tuần 1") || value.includes("kế hoạch"))
    return `## Kế hoạch Tuần 1 · Khoa học dữ liệu

**Mục tiêu:** Hiểu dữ liệu được thu thập, làm sạch và dùng để ra quyết định như thế nào.

- **Ngày 1:** Xem video tổng quan nghề Data Scientist — 30 phút
- **Ngày 2:** Ôn trung bình, trung vị và độ lệch chuẩn — 45 phút
- **Ngày 3:** Làm quen Google Colab và Python — 45 phút
- **Ngày 4:** Khám phá một bộ dữ liệu điểm thi — 60 phút
- **Cuối tuần:** Viết nhật ký phản tư: *Điều gì khiến mình tò mò nhất?*

Hoàn thành **4/5 nhiệm vụ** là đạt mục tiêu tuần.`
  if (value.includes("kỹ năng") || value.includes("gap"))
    return `## Competency Gaps ưu tiên

1. **Tư duy thuật toán** — ưu tiên cao  
   Thực hành bài toán chia nhỏ vấn đề 3 buổi/tuần.
2. **Python nền tảng** — ưu tiên cao  
   Tập trung biến, vòng lặp, hàm và xử lý danh sách.
3. **Tiếng Anh chuyên ngành** — ưu tiên vừa  
   Tạo bộ 20 từ khóa ngành mỗi tuần.

### Cách đo tiến bộ
- Tự giải thích lại khái niệm không nhìn tài liệu.
- Hoàn thành một sản phẩm nhỏ có thể chia sẻ.
- Nhận phản hồi từ ít nhất một người có kinh nghiệm.`
  return `## Góc nhìn từ hồ sơ của bạn

Câu hỏi này nên được xem qua cả ba lớp dữ liệu: **sở thích RIASEC**, **học lực chuẩn hóa Z-Score** và **phong cách nhận thức**.

Hiện tại, tín hiệu mạnh nhất của bạn là khả năng phân tích và sự tò mò khoa học. Mình đề xuất bạn chọn một trải nghiệm thực tế ngắn trước khi đưa ra quyết định cuối cùng.

Bạn muốn mình so sánh hai ngành cụ thể hay tạo một nhiệm vụ thử sức?`
}

export function AIChatAdvisor({ open, onClose }: AIChatAdvisorProps) {
  const { assessment } = useAssessment()
  const [fullscreen, setFullscreen] = useState(false)
  const [context, setContext] = useState("Khoa học máy tính · 7480101")
  const [messages, setMessages] = useState<AdvisorMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [typing, setTyping] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, typing])

  const send = async (raw: string) => {
    const question = raw.trim()
    if (!question || typing) return
    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", content: question },
    ])
    setInput("")
    setTyping(true)

    const majorCodeMatch = context.match(/\d{7}/)
    const activeMajorCode = majorCodeMatch ? majorCodeMatch[0] : "7480101"

    try {
      const data = await apiRequest<{ reply: string } | null>(
        "/rag-governance/chat",
        null,
        {
          method: "POST",
          body: JSON.stringify({
            message: question,
            major_code: activeMajorCode,
          }),
        },
      )
      if (data && data.reply) {
        setMessages((current) => [
          ...current,
          {
            id: Date.now() + 1,
            role: "assistant",
            content: data.reply,
          },
        ])
        setTyping(false)
        return
      }
    } catch (err) {
      console.log("Chat API fallback:", err)
    }

    // Local fallback
    window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: buildAnswer(question),
        },
      ])
      setTyping(false)
    }, 600)
  }

  useEffect(() => {
    const onPromptEvent = (e: Event) => {
      const custom = e as CustomEvent<{ prompt?: string }>
      if (custom.detail?.prompt) {
        send(custom.detail.prompt)
      }
    }
    window.addEventListener("open-ai-advisor-prompt", onPromptEvent)
    return () =>
      window.removeEventListener("open-ai-advisor-prompt", onPromptEvent)
  })

  const attachStudentProfile = () => {
    const scoresStr =
      assessment.scores && assessment.scores.length > 0
        ? assessment.scores.map((s) => `${s.subject}: ${s.score}`).join(", ")
        : "Toán: 8.8, Lý: 8.4, Anh: 8.5 (Z-Score A00 +1.18)"
    setInput(
      `[Đính kèm hồ sơ: ${scoresStr} · Ngành quan tâm: ${context}] Hãy phân tích độ khả thi và lộ trình ôn luyện giúp mình.`,
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
          <motion.button
            aria-label="Đóng AI Career Advisor"
            className="fixed inset-0 z-[80] bg-sky-950/10 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.section
            className={`glass-chat fixed z-[90] flex flex-col overflow-hidden ${
              fullscreen
                ? "inset-3 rounded-[30px]"
                : "bottom-3 right-3 top-3 w-[min(680px,calc(100vw-24px))] rounded-[30px]"
            }`}
            initial={{ opacity: 0, x: 80, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <header className="border-b border-white/70 bg-white/35 px-4 py-4 sm:px-6">
              <div className="flex items-center gap-3">
                <span className="relative grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-400 via-sky-500 to-cyan-500 text-white shadow-lg shadow-sky-200">
                  <Bot size={22} />
                  <i className="absolute -right-0.5 -top-0.5 size-3 rounded-full border-2 border-white bg-emerald-400" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-black text-slate-900">
                      AI Career Advisor
                    </h2>
                    <span className="rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-extrabold text-emerald-700">
                      Guidance RAG Active
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[9px] font-extrabold text-amber-700 ring-1 ring-amber-200">
                      <ShieldCheck size={10} />
                      Zero-PII Protected
                    </span>
                  </div>
                  <p className="mt-1 truncate text-[10px] font-medium text-slate-500">
                    Dữ liệu cá nhân nhạy cảm được tự động ẩn theo Luật 91/2025
                  </p>
                </div>
                <button
                  onClick={() => setFullscreen((value) => !value)}
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
                  onClick={onClose}
                  className="sidebar-icon-button"
                  aria-label="Đóng chat"
                >
                  <X size={18} />
                </button>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl border border-white/80 bg-white/55 p-2">
                <span className="grid size-8 place-items-center rounded-xl bg-sky-100 text-sky-700">
                  <GraduationCap size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">
                    Ngữ cảnh đang thảo luận
                  </p>
                  <select
                    value={context}
                    onChange={(event) => setContext(event.target.value)}
                    className="w-full appearance-none bg-transparent text-xs font-extrabold text-slate-700 outline-none"
                  >
                    <option>Khoa học máy tính · 7480101</option>
                    <option>Khoa học dữ liệu · 7460108</option>
                    <option>Marketing số · 7340115</option>
                  </select>
                </div>
                <ChevronDown size={15} className="text-slate-400" />
              </div>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              <div
                className={`mx-auto space-y-5 ${
                  fullscreen ? "max-w-4xl" : "max-w-2xl"
                }`}
              >
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${
                      message.role === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    <span
                      className={`grid size-8 shrink-0 place-items-center rounded-xl ${
                        message.role === "assistant"
                          ? "bg-gradient-to-br from-sky-100 to-cyan-100 text-sky-700"
                          : "bg-sky-600 text-white"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <Sparkles size={15} />
                      ) : (
                        <User size={14} />
                      )}
                    </span>
                    <div
                      className={`max-w-[88%] rounded-2xl px-4 py-3 text-xs leading-6 ${
                        message.role === "assistant"
                          ? "rounded-tl-md border border-sky-100/80 bg-white/55 text-slate-700 shadow-sm backdrop-blur-lg"
                          : "rounded-tr-md bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-lg shadow-sky-200/60"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <div className="markdown advisor-markdown">
                          <Markdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </Markdown>
                        </div>
                      ) : (
                        message.content
                      )}
                    </div>
                  </motion.div>
                ))}
                {typing && (
                  <div className="flex items-center gap-3">
                    <span className="grid size-8 place-items-center rounded-xl bg-sky-100 text-sky-700">
                      <Sparkles size={15} />
                    </span>
                    <span className="glass-card flex items-center gap-1 rounded-2xl rounded-tl-md px-4 py-3">
                      {[0, 1, 2].map((index) => (
                        <motion.i
                          key={index}
                          className="size-1.5 rounded-full bg-sky-400"
                          animate={{ y: [0, -5, 0], opacity: [0.45, 1, 0.45] }}
                          transition={{
                            duration: 0.75,
                            repeat: Infinity,
                            delay: index * 0.12,
                          }}
                        />
                      ))}
                    </span>
                  </div>
                )}
                <div ref={endRef} />
              </div>
            </div>

            <div className="border-t border-white/70 bg-white/30 p-3 sm:p-4">
              <div
                className={`mx-auto ${fullscreen ? "max-w-4xl" : "max-w-2xl"}`}
              >
                <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => send(prompt)}
                      className="shrink-0 rounded-full border border-sky-200/70 bg-white/60 px-3 py-2 text-[10px] font-bold text-sky-800 shadow-sm backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-sky-50/80"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
                <form
                  onSubmit={submit}
                  className="flex items-end gap-2 rounded-[22px] border border-sky-200/70 bg-white/60 p-2 shadow-sm backdrop-blur-xl"
                >
                  <button
                    type="button"
                    onClick={attachStudentProfile}
                    title="Đính kèm điểm số hoặc hồ sơ"
                    className="grid size-10 shrink-0 place-items-center rounded-xl text-slate-400 transition hover:bg-sky-50 hover:text-sky-600"
                  >
                    <Paperclip size={18} />
                  </button>
                  <textarea
                    rows={1}
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault()
                        send(input)
                      }
                    }}
                    placeholder="Hỏi AI về ngành học, điểm số hoặc lộ trình..."
                    className="max-h-28 min-h-10 flex-1 resize-none bg-transparent px-1 py-2.5 text-xs leading-5 text-slate-700 outline-none placeholder:text-slate-400"
                  />
                  <motion.button
                    type="submit"
                    disabled={!input.trim() || typing}
                    whileTap={{ scale: 0.88 }}
                    className="relative grid size-10 shrink-0 overflow-hidden rounded-xl bg-gradient-to-r from-sky-400 to-blue-500 text-white shadow-md disabled:opacity-40"
                  >
                    <ArrowUp size={17} />
                  </motion.button>
                </form>
                <div className="mt-2 flex items-center justify-center gap-3 text-[9px] font-medium text-slate-400">
                  <span className="flex items-center gap-1">
                    <Check size={10} className="text-emerald-500" /> RAG có
                    nguồn
                  </span>
                  <span className="flex items-center gap-1">
                    <Brain size={10} className="text-sky-400" /> XAI giải thích
                    được
                  </span>
                  <span className="flex items-center gap-1">
                    <Target size={10} className="text-cyan-400" /> Không thay
                    thế tư vấn chính thức
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
