import confetti from "canvas-confetti"
import { motion } from "framer-motion"
import {
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Check,
  Clock3,
  Loader2,
  RotateCcw,
  ShieldCheck,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router"
import { AcademicInputForm } from "../components/assessment/AcademicInputForm"
import { CognitiveQuestionCard } from "../components/assessment/CognitiveQuestionCard"
import { QuestionCard } from "../components/assessment/QuestionCard"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import {
  defaultCognitiveQuestions,
  type CognitiveQuestionItem,
} from "../data/cognitiveQuestions"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest } from "../services/api"

export interface QuestionItem {
  code: string
  category?: string
  dimension?: string
  dimension_badge?: string
  domain_tag?: string
  question_text: string
  order_index?: number
}

interface ActiveQuestionsResponse {
  title?: string
  riasec_questions?: QuestionItem[]
  cognitive_questions?: Array<{
    code: string
    category?: string
    dimension?: string
    dimension_badge?: string
    domain_tag?: string
    question_text?: string
    order_index?: number
    options?: Array<{
      option_key: string
      trait_code?: string
      title: string
      description: string
    }>
  }>
}

const defaultRiasecFallback: QuestionItem[] = [
  { code: "R1", dimension: "R", dimension_badge: "Nhóm R (Thực tế)", question_text: "Tôi thích lắp ráp, vận hành hoặc sửa chữa các thiết bị kỹ thuật, máy móc cơ khí, vi mạch điện tử." },
  { code: "R2", dimension: "R", dimension_badge: "Nhóm R (Thực tế)", question_text: "Tôi thích làm việc ngoài trời, tiếp xúc với thiên nhiên, cây trồng, vật nuôi hoặc công trình xây dựng thực địa." },
  { code: "R3", dimension: "R", dimension_badge: "Nhóm R (Thực tế)", question_text: "Tôi thích sử dụng các dụng cụ cầm tay, máy đo đạc hoặc thiết bị chuyên dụng để tạo ra sản phẩm cụ thể." },
  { code: "R4", dimension: "R", dimension_badge: "Nhóm R (Thực tế)", question_text: "Tôi thích tìm hiểu cấu tạo phần cứng máy tính, hệ thống mạng internet, robot hoặc các thiết bị tự động hóa." },
  { code: "R5", dimension: "R", dimension_badge: "Nhóm R (Thực tế)", question_text: "Tôi có xu hướng tự tay giải quyết sự cố kỹ thuật trong gia đình trước khi gọi thợ sửa chữa chuyên nghiệp." },
  { code: "I1", dimension: "I", dimension_badge: "Nhóm I (Nghiên cứu)", question_text: "Tôi thích nghiên cứu, tìm hiểu nguyên nhân gốc rễ và cơ chế hoạt động của các hiện tượng khoa học, tự nhiên." },
  { code: "I2", dimension: "I", dimension_badge: "Nhóm I (Nghiên cứu)", question_text: "Tôi hứng thú với việc giải các bài toán logic phức tạp, viết thuật toán hoặc phân tích mô hình dữ liệu." },
  { code: "I3", dimension: "I", dimension_badge: "Nhóm I (Nghiên cứu)", question_text: "Tôi thích thực hiện các thí nghiệm khoa học, đọc tài liệu chuyên ngành để kiểm chứng giả thuyết." },
  { code: "I4", dimension: "I", dimension_badge: "Nhóm I (Nghiên cứu)", question_text: "Khi gặp một thông tin mới, tôi thường chủ động tra cứu, đối chiếu nhiều nguồn dữ liệu để xác minh sự thật." },
  { code: "I5", dimension: "I", dimension_badge: "Nhóm I (Nghiên cứu)", question_text: "Tôi thích làm việc độc lập trong thời gian dài để đào sâu nghiên cứu một vấn đề chuyên môn trừu tượng." },
  { code: "A1", dimension: "A", dimension_badge: "Nhóm A (Nghệ thuật)", question_text: "Tôi thích sáng tạo ý tưởng hình ảnh, thiết kế giao diện đồ họa, vẽ minh họa hoặc dựng video nghệ thuật." },
  { code: "A2", dimension: "A", dimension_badge: "Nhóm A (Nghệ thuật)", question_text: "Tôi thích viết văn, sáng tác kịch bản, làm nội dung truyền thông hoặc diễn đạt cảm xúc qua ngôn từ." },
  { code: "A3", dimension: "A", dimension_badge: "Nhóm A (Nghệ thuật)", question_text: "Tôi có sự nhạy cảm cao với âm nhạc, giai điệu, màu sắc, bố cục thị giác và không gian mỹ thuật." },
  { code: "A4", dimension: "A", dimension_badge: "Nhóm A (Nghệ thuật)", question_text: "Tôi thích môi trường học tập linh hoạt, tự do thể hiện bản sắc cá nhân và không bị bó buộc bởi quy tắc cứng nhắc." },
  { code: "A5", dimension: "A", dimension_badge: "Nhóm A (Nghệ thuật)", question_text: "Tôi thường tìm tòi các giải pháp thẩm mỹ độc đáo, phá cách để giải quyết các vấn đề thường nhật." },
  { code: "S1", dimension: "S", dimension_badge: "Nhóm S (Xã hội)", question_text: "Tôi cảm thấy hứng thú và tràn đầy năng lượng khi được giảng giải, hỗ trợ người khác hiểu bài hoặc vượt qua khó khăn." },
  { code: "S2", dimension: "S", dimension_badge: "Nhóm S (Xã hội)", question_text: "Tôi lắng nghe tốt, dễ dàng đồng cảm với tâm tư, nguyện vọng của bạn bè và mọi người xung quanh." },
  { code: "S3", dimension: "S", dimension_badge: "Nhóm S (Xã hội)", question_text: "Tôi thích tham gia các hoạt động tình nguyện vì cộng đồng, công tác xã hội hoặc chăm sóc sức khỏe." },
  { code: "S4", dimension: "S", dimension_badge: "Nhóm S (Xã hội)", question_text: "Tôi thích làm việc trong môi trường hợp tác nhóm, thảo luận cởi mở và gắn kết tình cảm đồng nghiệp." },
  { code: "S5", dimension: "S", dimension_badge: "Nhóm S (Xã hội)", question_text: "Tôi có năng khiếu hòa giải các mâu thuẫn, giúp mọi người tìm được tiếng nói chung trong tập thể." },
  { code: "E1", dimension: "E", dimension_badge: "Nhóm E (Quản lý)", question_text: "Tôi thích đóng vai trò trưởng nhóm, điều phối công việc và thuyết phục các thành viên hành động vì mục tiêu chung." },
  { code: "E2", dimension: "E", dimension_badge: "Nhóm E (Quản lý)", question_text: "Tôi hứng thú với các ý tưởng kinh doanh, khởi nghiệp, bán sản phẩm hoặc tổ chức sự kiện quy mô lớn." },
  { code: "E3", dimension: "E", dimension_badge: "Nhóm E (Quản lý)", question_text: "Tôi tự tin khi phát biểu, thuyết trình ý tưởng trước đám đông hoặc đàm phán để đạt thỏa thuận có lợi." },
  { code: "E4", dimension: "E", dimension_badge: "Nhóm E (Quản lý)", question_text: "Tôi thích cạnh tranh lành mạnh, đặt mục tiêu cao và chủ động chấp nhận rủi ro có tính toán để bứt phá." },
  { code: "E5", dimension: "E", dimension_badge: "Nhóm E (Quản lý)", question_text: "Tôi thích phân tích thị trường, xu hướng người tiêu dùng và lập chiến lược để phát triển một dự án." },
  { code: "C1", dimension: "C", dimension_badge: "Nhóm C (Nghiệp vụ)", question_text: "Tôi thích làm việc với các bảng biểu, số liệu kế toán, quản lý giấy tờ hoặc dữ liệu có cấu trúc ngăn nắp." },
  { code: "C2", dimension: "C", dimension_badge: "Nhóm C (Nghiệp vụ)", question_text: "Tôi coi trọng tính chính xác, chi tiết, tuân thủ đúng quy trình, quy định và kế hoạch đã đề ra." },
  { code: "C3", dimension: "C", dimension_badge: "Nhóm C (Nghiệp vụ)", question_text: "Tôi thích sắp xếp tài liệu, lưu trữ thông tin khoa học để dễ dàng tìm kiếm và kiểm soát chất lượng." },
  { code: "C4", dimension: "C", dimension_badge: "Nhóm C (Nghiệp vụ)", question_text: "Tôi làm việc thận trọng, kiên nhẫn kiểm tra lại bài thi, hợp đồng để tránh sai sót trước khi nộp." },
  { code: "C5", dimension: "C", dimension_badge: "Nhóm C (Nghiệp vụ)", question_text: "Tôi thích môi trường làm việc ổn định, có phân cấp rõ ràng và các tiêu chuẩn đánh giá minh bạch." },
]

export function AssessmentWizard() {
  const { assessment, history, update, reset, recordCompletedAttempt } =
    useAssessment()
  const [step, setStep] = useState(1)
  const [scores, setScores] = useState<Record<string, number>>(() =>
    Object.fromEntries(assessment.scores.map((s) => [s.subject, s.score])),
  )
  const [loading, setLoading] = useState(true)
  const [selectedDimension, setSelectedDimension] = useState<string>("ALL")
  const [riasecQuestions, setRiasecQuestions] = useState<QuestionItem[]>(defaultRiasecFallback)
  const [cognitiveQuestions, setCognitiveQuestions] = useState<CognitiveQuestionItem[]>(defaultCognitiveQuestions)
  const navigate = useNavigate()

  useEffect(() => {
    let mounted = true
    async function loadQuestions() {
      try {
        setLoading(true)
        const data = await apiRequest<ActiveQuestionsResponse>(
          "/assessment/active-questions",
          {
            riasec_questions: defaultRiasecFallback,
            cognitive_questions: [],
          },
        )
        if (mounted && data) {
          if (data.riasec_questions && data.riasec_questions.length > 0) {
            setRiasecQuestions(data.riasec_questions)
          }
          if (data.cognitive_questions && data.cognitive_questions.length > 0) {
            const fallbackMap = new Map(defaultCognitiveQuestions.map((q) => [q.code, q]))
            const parsedCogs: CognitiveQuestionItem[] = data.cognitive_questions.map((q) => {
              const fb = fallbackMap.get(q.code)
              const title = fb?.title || q.dimension_badge || q.question_text?.split(":")[0]?.trim() || q.code
              const subtitle =
                fb?.subtitle ||
                (q.question_text && q.question_text.includes(":")
                  ? q.question_text.split(":").slice(1).join(":").trim()
                  : q.question_text || "")
              const options =
                q.options && q.options.length > 0
                  ? q.options.map((opt) => ({
                      option_key: opt.option_key,
                      trait_code: opt.trait_code,
                      title: opt.title,
                      description: opt.description,
                    }))
                  : fb?.options || []

              return {
                code: q.code,
                dimension: q.dimension || fb?.dimension,
                dimension_badge: fb?.dimension_badge || q.dimension_badge,
                title,
                subtitle,
                options,
              }
            })
            setCognitiveQuestions(parsedCogs)
          }
        }
      } catch (err) {
        console.error("Failed to load questions from API:", err)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    loadQuestions()
    return () => {
      mounted = false
    }
  }, [])

  const progress = step === 1 ? 25 : step === 2 ? 65 : 95

  const currentRiasecQuestions = useMemo(() => {
    if (selectedDimension === "ALL") return riasecQuestions
    return riasecQuestions.filter((q) => q.dimension === selectedDimension)
  }, [selectedDimension, riasecQuestions])

  const answeredCount = useMemo(() => {
    if (step === 1) {
      return riasecQuestions.filter((q, idx) => {
        const val = assessment.answers[q.code] ?? assessment.answers[`1-${idx}`]
        return typeof val === "number" && val > 0
      }).length
    }
    if (step === 2) {
      return cognitiveQuestions.filter((q, idx) => {
        const val = assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
        return typeof val === "string" && val.trim().length > 0
      }).length
    }
    return Object.keys(scores).length
  }, [step, riasecQuestions, cognitiveQuestions, assessment.answers, assessment.cognitive, scores])

  const canContinue =
    step === 3
      ? Object.keys(scores).length >= 3
      : step === 1
        ? answeredCount >= 3
        : answeredCount >= 1

  const next = () => {
    if (step < 3) {
      setStep(step + 1)
      setSelectedDimension("ALL")
      update({ step: step + 1 })
      window.scrollTo({ top: 0, behavior: "smooth" })
    } else {
      const normalizedScores = Object.entries(scores).map(
        ([subject, score]) => ({
          subject,
          score,
          zScore: (score - 7.1) / 1.2,
        }),
      )
      recordCompletedAttempt({
        ...assessment,
        step: 3,
        scores: normalizedScores,
        completed: true,
      })

      // Send answers to backend in background
      const riasecMap: Record<string, number> = {}
      riasecQuestions.forEach((q, idx) => {
        const val = assessment.answers[q.code] ?? assessment.answers[`1-${idx}`]
        if (val !== undefined && val !== null) riasecMap[q.code] = Number(val)
      })
      const cogMap: Record<string, string> = {}
      cognitiveQuestions.forEach((q, idx) => {
        const val = assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
        if (val) cogMap[q.code] = String(val)
      })

      apiRequest("/assessment/submit", null, {
        method: "POST",
        body: JSON.stringify({
          riasec_answers: riasecMap,
          cognitive_answers: cogMap,
        }),
      }).catch((err) => console.log("Background submit response:", err))

      if (Object.keys(scores).length > 0) {
        apiRequest("/assessment/grades", null, {
          method: "POST",
          body: JSON.stringify({
            academic_year: "2025-2026",
            semester: "HK1-L12",
            grades: scores,
          }),
        }).catch((err) => console.log("Background grades submit notice:", err))
      }

      confetti({
        particleCount: 140,
        spread: 80,
        origin: { y: 0.65 },
        colors: ["#0284c7", "#10b981", "#f59e0b"],
      })
      setTimeout(() => navigate("/dashboard"), 700)
    }
  }

  const handleReset = () => {
    reset()
    setStep(1)
    setSelectedDimension("ALL")
    setScores({})
  }

  return (
    <section className="min-h-[calc(100vh-72px)] bg-transparent py-8 sm:py-12">
      <PageContainer className="max-w-5xl">
        {/* Header */}
        <div className="mb-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-extrabold uppercase tracking-widest text-sky-600">
              AI CareerGuide · Đánh giá 3 trụ cột
            </span>
            <h1 className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">
              Trắc nghiệm định hướng cá nhân
            </h1>
          </div>
          <div className="flex items-center gap-3 text-xs font-semibold text-slate-500">
            <span className="flex items-center gap-1.5">
              <Clock3 size={14} className="text-sky-600" />
              10 phút
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-sky-600" />
              {history.length > 0
                ? `${history.length} lần đã lưu`
                : "Tự động lưu"}
            </span>
            <button
              onClick={handleReset}
              className="flex items-center gap-1 rounded-xl border border-white/80 bg-white/60 px-2.5 py-1 text-slate-600 backdrop-blur-md hover:bg-white hover:text-sky-700 transition-colors"
              title="Làm lại từ đầu"
            >
              <RotateCcw size={13} />
              <span>Làm lại</span>
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="mb-2 flex justify-between text-xs font-bold">
            <span className="text-sky-600">
              Bước {step} / 3 · {step === 1 ? "Sở thích RIASEC" : step === 2 ? "Nhận thức" : "Điểm học tập"}
            </span>
            <span className="text-slate-500">
              {step < 3
                ? `${answeredCount} / ${step === 1 ? riasecQuestions.length : cognitiveQuestions.length} câu`
                : `${progress}%`}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/70">
            <motion.div
              className="h-full rounded-full bg-sky-600"
              animate={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2.5 grid grid-cols-3 text-[11px] font-bold text-slate-400">
            <span className={step >= 1 ? "text-sky-600" : ""}>
              01 · Sở thích ({riasecQuestions.length})
            </span>
            <span className={`text-center ${step >= 2 ? "text-sky-600" : ""}`}>
              02 · Nhận thức ({cognitiveQuestions.length})
            </span>
            <span className={`text-right ${step >= 3 ? "text-sky-600" : ""}`}>
              03 · Điểm học tập
            </span>
          </div>
        </div>

        {/* Step Banner (Liquid Glass) */}
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <Card className="mb-5 overflow-hidden rounded-3xl p-5 sm:p-6">
            <div className="flex items-center gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-500/15 text-sky-600">
                <BrainCircuit size={22} />
              </span>
              <div>
                <h2 className="text-lg font-black text-slate-900 sm:text-xl">
                  {step === 1
                    ? "Bạn hứng thú với hoạt động nào nhất?"
                    : step === 2
                      ? "Phong cách tư duy & giải quyết vấn đề"
                      : "Nhập điểm học bạ hoặc điểm thi gần nhất"}
                </h2>
                <p className="mt-0.5 text-xs font-medium text-slate-500">
                  {step === 3
                    ? "Nhập tối thiểu 3 môn học (thang điểm 10)."
                    : step === 2
                      ? "Chọn phương án phản ánh đúng nhất phản xạ tự nhiên của bạn."
                      : "Chọn mức độ yêu thích từ 1 (Không thích) đến 5 (Rất thích)."}
                </p>
              </div>
            </div>
          </Card>

          {/* Dimension Tabs for Step 1 */}
          {step === 1 && (
            <div className="mb-4 flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/85 bg-white/55 p-1.5 backdrop-blur-xl">
              {[
                { key: "ALL", label: `Tất cả (${riasecQuestions.length})` },
                { key: "R", label: "R · Thực tế" },
                { key: "I", label: "I · Nghiên cứu" },
                { key: "A", label: "A · Nghệ thuật" },
                { key: "S", label: "S · Xã hội" },
                { key: "E", label: "E · Quản lý" },
                { key: "C", label: "C · Nghiệp vụ" },
              ].map((dim) => (
                <button
                  key={dim.key}
                  type="button"
                  onClick={() => setSelectedDimension(dim.key)}
                  className={`px-3 py-1 text-xs font-bold rounded-xl transition-colors ${
                    selectedDimension === dim.key
                      ? "bg-sky-600 text-white shadow-2xs"
                      : "text-slate-600 hover:bg-white/80"
                  }`}
                >
                  {dim.label}
                </button>
              ))}
            </div>
          )}

          {/* Loading Indicator */}
          {loading && step < 3 && (
            <div className="flex items-center justify-center p-8 bg-white rounded-2xl border border-slate-200 text-slate-500 gap-2">
              <Loader2 className="size-5 animate-spin text-sky-600" />
              <span className="text-xs font-semibold">Đang nạp bộ câu hỏi chuẩn hóa từ CSDL...</span>
            </div>
          )}

          {/* Step 1: Holland RIASEC */}
          {step === 1 && (
            <motion.div
              className="space-y-3"
              initial="hidden"
              animate="visible"
              variants={{ visible: { transition: { staggerChildren: 0.04 } } }}
            >
              {currentRiasecQuestions.map((q, index) => {
                const questionKey = q.code || `1-${index}`
                const currentValue =
                  assessment.answers[questionKey] ?? assessment.answers[`1-${index}`]

                return (
                  <motion.div
                    key={questionKey}
                    variants={{
                      hidden: { opacity: 0, y: 10 },
                      visible: { opacity: 1, y: 0 },
                    }}
                  >
                    <div className="relative">
                      {q.dimension_badge && (
                        <div className="absolute right-4 top-4 z-10 hidden sm:block">
                          <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-700 border border-sky-200">
                            {q.dimension_badge}
                          </span>
                        </div>
                      )}
                      <QuestionCard
                        index={index + 1}
                        question={q.question_text}
                        value={typeof currentValue === "number" ? currentValue : undefined}
                        onChange={(value) =>
                          update({
                            answers: {
                              ...assessment.answers,
                              [questionKey]: value,
                              [`1-${index}`]: value,
                            },
                          })
                        }
                      />
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>
          )}

          {/* Step 2: Cognitive Multiple Choice */}
          {step === 2 && (
            <motion.div
              className="space-y-4"
              initial="hidden"
              animate="visible"
              variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
            >
              {cognitiveQuestions.map((q, index) => {
                const questionKey = q.code || `2-${index}`
                const currentSelectedKey =
                  assessment.cognitive[questionKey] ?? assessment.cognitive[`2-${index}`]
                const selectedKeyStr =
                  currentSelectedKey !== undefined && currentSelectedKey !== null
                    ? String(currentSelectedKey)
                    : undefined

                return (
                  <motion.div
                    key={questionKey}
                    variants={{
                      hidden: { opacity: 0, y: 10 },
                      visible: { opacity: 1, y: 0 },
                    }}
                  >
                    <CognitiveQuestionCard
                      index={index + 1}
                      code={q.code}
                      title={q.title}
                      subtitle={q.subtitle}
                      dimensionBadge={q.dimension_badge}
                      options={q.options}
                      selectedKey={selectedKeyStr}
                      onSelect={(optionKey) => {
                        update({
                          cognitive: {
                            ...assessment.cognitive,
                            [questionKey]: optionKey,
                            [`2-${index}`]: optionKey,
                          },
                        })
                      }}
                    />
                  </motion.div>
                )
              })}
            </motion.div>
          )}

          {/* Step 3: Academic Input */}
          {step === 3 && (
            <Card className="p-6 sm:p-8">
              <AcademicInputForm
                scores={scores}
                onChange={(subject, value) =>
                  setScores({ ...scores, [subject]: value })
                }
              />
            </Card>
          )}
        </motion.div>

        {/* Footer Navigation */}
        <div className="mt-7 flex items-center justify-between">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            disabled={step === 1}
            onClick={() => setStep(step - 1)}
          >
            Quay lại
          </Button>
          <div className="flex items-center gap-3">
            {step < 3 && answeredCount < (step === 1 ? riasecQuestions.length : cognitiveQuestions.length) && (
              <span className="text-[11px] font-medium text-slate-400 hidden sm:inline">
                (Đã trả lời {answeredCount} câu, bạn có thể tiếp tục bất cứ lúc nào)
              </span>
            )}
            <Button
              icon={step === 3 ? Check : ArrowRight}
              disabled={!canContinue}
              onClick={next}
            >
              {step === 3 ? "Hoàn thành & Xem kết quả" : "Tiếp tục"}
            </Button>
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
