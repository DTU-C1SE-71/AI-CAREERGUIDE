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
  { code: "R1", dimension: "R", dimension_badge: "Thực tế (Realistic)", domain_tag: "Cơ khí, Điện tử & Tự động hóa (Mã 51, 52)", question_text: "Tôi thích tháo lắp, sửa chữa máy móc, mạch điện tử hoặc vận hành các thiết bị kỹ thuật." },
  { code: "R2", dimension: "R", dimension_badge: "Thực tế (Realistic)", domain_tag: "Kiến trúc & Kỹ thuật Xây dựng (Mã 51, 58)", question_text: "Tôi hứng thú với việc đọc bản vẽ kỹ thuật, khảo sát công trình, đo đạc thực địa hoặc chế tạo mô hình vật lý." },
  { code: "R3", dimension: "R", dimension_badge: "Thực tế (Realistic)", domain_tag: "Nông - Lâm - Thủy sản, Thú y & Môi trường (Mã 62, 64, 85)", question_text: "Tôi thích làm việc gần gũi với thiên nhiên, chăm sóc cây trồng, vật nuôi hoặc vận hành nông trại công nghệ cao." },
  { code: "R4", dimension: "R", dimension_badge: "Thực tế (Realistic)", domain_tag: "Kỹ thuật Y học & Công nghệ Thực phẩm (Mã 54, 72)", question_text: "Tôi thích thao tác trực tiếp với dụng cụ phòng thí nghiệm, thiết bị xét nghiệm - hình ảnh y học hoặc quy trình chế biến thực phẩm." },
  { code: "R5", dimension: "R", dimension_badge: "Thực tế (Realistic)", domain_tag: "Thể thao, Vận tải & An ninh - Quốc phòng (Mã 81, 84, 86)", question_text: "Tôi yêu thích các hoạt động đòi hỏi sức bền thể chất, huấn luyện thể thao, điều khiển phương tiện vận tải hoặc nghiệp vụ thực địa." },
  { code: "I1", dimension: "I", dimension_badge: "Nghiên cứu (Investigative)", domain_tag: "Toán học & Khoa học tính toán (Mã 46)", question_text: "Tôi thích tìm hiểu nguyên lý khoa học, giải các bài toán logic phức tạp và suy luận tìm ra bản chất vấn đề." },
  { code: "I2", dimension: "I", dimension_badge: "Nghiên cứu (Investigative)", domain_tag: "Máy tính, CNTT, Khoa học dữ liệu & AI (Mã 46, 48)", question_text: "Tôi hứng thú với việc phân tích dữ liệu lớn, tìm quy luật từ biểu đồ hoặc lập trình thuật toán trí tuệ nhân tạo." },
  { code: "I3", dimension: "I", dimension_badge: "Nghiên cứu (Investigative)", domain_tag: "Y khoa, Dược học & Khoa học sự sống (Mã 42, 72)", question_text: "Tôi tò mò về cơ chế sinh học của cơ thể người, di truyền học, tác dụng của dược chất hoặc phương pháp chẩn đoán bệnh." },
  { code: "I4", dimension: "I", dimension_badge: "Nghiên cứu (Investigative)", domain_tag: "Vật lý, Hóa học, Bán dẫn & Khoa học Trái đất (Mã 44, 52)", question_text: "Tôi thích nghiên cứu về công nghệ bán dẫn, vật liệu mới, phản ứng hóa học, năng lượng tái tạo hoặc biến đổi khí hậu." },
  { code: "I5", dimension: "I", dimension_badge: "Nghiên cứu (Investigative)", domain_tag: "Kinh tế học, Tâm lý học & Khu vực học (Mã 22, 31)", question_text: "Tôi thích đọc tài liệu học thuật để phân tích sâu về hành vi tâm lý con người, lịch sử văn hóa hoặc các quy luật kinh tế vĩ mô." },
  { code: "A1", dimension: "A", dimension_badge: "Nghệ thuật (Artistic)", domain_tag: "Thiết kế Đồ họa, Thời trang & Nghệ thuật số (Mã 21)", question_text: "Tôi thích sáng tạo hình ảnh, vẽ minh họa, thiết kế đồ họa kỹ thuật số, thời trang hoặc sản phẩm mỹ thuật ứng dụng." },
  { code: "A2", dimension: "A", dimension_badge: "Nghệ thuật (Artistic)", domain_tag: "Kiến trúc, Nội thất & Cảnh quan đô thị (Mã 58)", question_text: "Tôi nhạy cảm với thẩm mỹ không gian 3D, thích thiết kế kiến trúc, trang trí nội thất hoặc quy hoạch cảnh quan." },
  { code: "A3", dimension: "A", dimension_badge: "Nghệ thuật (Artistic)", domain_tag: "Báo chí, Truyền thông đa phương tiện & Điện ảnh (Mã 21, 32)", question_text: "Tôi thích viết kịch bản, sáng tác văn học, làm báo chí, nhiếp ảnh, quay dựng phim hoặc sản xuất nội dung đa phương tiện." },
  { code: "A4", dimension: "A", dimension_badge: "Nghệ thuật (Artistic)", domain_tag: "Âm nhạc & Nghệ thuật trình diễn (Mã 21)", question_text: "Tôi có niềm đam mê lớn với âm nhạc, thanh nhạc, biểu diễn nhạc cụ, công nghệ âm thanh hoặc nghệ thuật sân khấu, diễn xuất." },
  { code: "A5", dimension: "A", dimension_badge: "Nghệ thuật (Artistic)", domain_tag: "Tư duy Đổi mới & Phá cách (Đa lĩnh vực)", question_text: "Tôi thường có những ý tưởng độc đáo khác biệt, thích tự do biểu đạt cá tính và không muốn bị gò bó trong khuôn mẫu cứng nhắc." },
  { code: "S1", dimension: "S", dimension_badge: "Xã hội (Social)", domain_tag: "Khoa học Giáo dục & Đào tạo Giáo viên (Mã 14)", question_text: "Tôi thích giảng giải kiến thức, thiết kế bài giảng và kiên nhẫn hướng dẫn người khác cùng tiến bộ trong học tập." },
  { code: "S2", dimension: "S", dimension_badge: "Xã hội (Social)", domain_tag: "Điều dưỡng, Y tế công cộng & Dinh dưỡng (Mã 72)", question_text: "Tôi giàu lòng trắc ẩn, muốn trực tiếp chăm sóc người bệnh, phục hồi chức năng hoặc tư vấn dinh dưỡng, bảo vệ sức khỏe cộng đồng." },
  { code: "S3", dimension: "S", dimension_badge: "Xã hội (Social)", domain_tag: "Tâm lý học lâm sàng & Tham vấn học đường (Mã 31)", question_text: "Tôi biết lắng nghe, dễ thấu cảm và biết cách giúp người khác giải tỏa căng thẳng, tháo gỡ khúc mắc tâm lý." },
  { code: "S4", dimension: "S", dimension_badge: "Xã hội (Social)", domain_tag: "Công tác xã hội & Du lịch - Dịch vụ (Mã 76, 81)", question_text: "Tôi hào hứng khi tham gia hoạt động cộng đồng, công tác xã hội hoặc đón tiếp, hướng dẫn và mang lại trải nghiệm tốt cho du khách." },
  { code: "S5", dimension: "S", dimension_badge: "Xã hội (Social)", domain_tag: "Ngôn ngữ nước ngoài & Quan hệ quốc tế (Mã 22, 31, 32)", question_text: "Tôi thích giao tiếp bằng ngoại ngữ, kết nối văn hóa giữa các quốc gia và làm việc trong môi trường giao lưu quốc tế." },
  { code: "E1", dimension: "E", dimension_badge: "Quản lý (Enterprising)", domain_tag: "Quản trị Kinh doanh & Quản lý Dự án (Mã 34)", question_text: "Tôi tự tin đảm nhận vai trò trưởng nhóm, điều phối công việc, ra quyết định và dẫn dắt tập thể đạt mục tiêu chung." },
  { code: "E2", dimension: "E", dimension_badge: "Quản lý (Enterprising)", domain_tag: "Kinh doanh thương mại, Quốc tế & Thương mại điện tử (Mã 34)", question_text: "Tôi có hứng thú mạnh mẽ với việc khởi nghiệp, thương mại điện tử, phát triển thị trường và nắm bắt cơ hội kinh doanh." },
  { code: "E3", dimension: "E", dimension_badge: "Quản lý (Enterprising)", domain_tag: "Pháp luật, Luật Kinh tế & Luật Quốc tế (Mã 38)", question_text: "Tôi thích lập luận sắc bén để bảo vệ lẽ phải, đàm phán hợp đồng, giải quyết tranh chấp hoặc vận dụng quy định pháp luật." },
  { code: "E4", dimension: "E", dimension_badge: "Quản lý (Enterprising)", domain_tag: "Marketing, Quan hệ công chúng & Thương hiệu (Mã 32, 34)", question_text: "Tôi thích xây dựng chiến dịch quảng bá thương hiệu, thuyết trình thu hút đám đông và tạo ảnh hưởng tích cực đến khách hàng." },
  { code: "E5", dimension: "E", dimension_badge: "Quản lý (Enterprising)", domain_tag: "Quản trị Nhân lực, Khách sạn & Quản lý công (Mã 31, 34, 81)", question_text: "Tôi thích tổ chức nhân sự, vận hành dịch vụ khách sạn - nhà hàng chuyên nghiệp hoặc hoạch định chính sách quản lý." },
  { code: "C1", dimension: "C", dimension_badge: "Nghiệp vụ (Conventional)", domain_tag: "Kế toán, Kiểm toán, Tài chính - Ngân hàng & Fintech (Mã 34)", question_text: "Tôi thích làm việc chính xác với các con số tài chính, lập bảng cân đối ngân sách, kế toán, kiểm toán hoặc phân tích đầu tư." },
  { code: "C2", dimension: "C", dimension_badge: "Nghiệp vụ (Conventional)", domain_tag: "Hệ thống thông tin quản lý, Thống kê & Lưu trữ (Mã 32, 34, 46, 48)", question_text: "Tôi thích sắp xếp cơ sở dữ liệu, phân loại hồ sơ, quản trị thông tin cẩn thận, ngăn nắp và tra cứu nhanh chóng." },
  { code: "C3", dimension: "C", dimension_badge: "Nghiệp vụ (Conventional)", domain_tag: "Đảm bảo chất lượng, Kiểm thử & An ninh mạng (Mã 48, 54)", question_text: "Tôi làm việc tỉ mỉ theo quy trình chuẩn, giỏi rà soát các chi tiết nhỏ để phát hiện lỗi sai và bảo mật hệ thống an toàn." },
  { code: "C4", dimension: "C", dimension_badge: "Nghiệp vụ (Conventional)", domain_tag: "Logistics, Chuỗi cung ứng & Khai thác vận tải (Mã 34, 51, 84)", question_text: "Tôi thích lập kế hoạch điều phối hàng hóa, tối ưu hóa lịch trình vận chuyển, quản lý kho bãi và thủ tục chuỗi cung ứng." },
  { code: "C5", dimension: "C", dimension_badge: "Nghiệp vụ (Conventional)", domain_tag: "Quản trị văn phòng, Quản lý đất đai & An toàn lao động (Mã 34, 85)", question_text: "Tôi cảm thấy hiệu quả nhất khi làm việc trong môi trường có quy định rõ ràng, tuân thủ nghiêm ngặt tiêu chuẩn pháp lý và an toàn." },
]

const RIASEC_ORDER = ["R", "I", "A", "S", "E", "C"] as const

export function AssessmentWizard() {
  const { assessment, history, update, reset, recordCompletedAttempt } =
    useAssessment()
  const [step, setStep] = useState(1)
  const [scores, setScores] = useState<Record<string, number>>(() =>
    Object.fromEntries(assessment.scores.map((s) => [s.subject, s.score])),
  )
  const [loading, setLoading] = useState(true)
  const [selectedDimension, setSelectedDimension] = useState<string>("R")
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

  const dimAnsweredCounts = useMemo(() => {
    const counts: Record<string, { answered: number; total: number }> = {
      R: { answered: 0, total: 0 },
      I: { answered: 0, total: 0 },
      A: { answered: 0, total: 0 },
      S: { answered: 0, total: 0 },
      E: { answered: 0, total: 0 },
      C: { answered: 0, total: 0 },
    }
    riasecQuestions.forEach((q, idx) => {
      const dim = (q.dimension || q.code[0] || "R").toUpperCase()
      if (counts[dim]) {
        counts[dim].total += 1
        const val = assessment.answers[q.code] ?? assessment.answers[`1-${idx}`]
        if (typeof val === "number" && val > 0) {
          counts[dim].answered += 1
        }
      }
    })
    return counts
  }, [riasecQuestions, assessment.answers])

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

  const allRiasecGroupsCovered = useMemo(() => {
    return (
      answeredCount >= 18 &&
      RIASEC_ORDER.every((dim) => (dimAnsweredCounts[dim]?.answered ?? 0) >= 2)
    )
  }, [answeredCount, dimAnsweredCounts])

  const nextRiasecDim = useMemo(() => {
    if (step !== 1 || selectedDimension === "ALL") return null
    const currIdx = RIASEC_ORDER.indexOf(
      selectedDimension as (typeof RIASEC_ORDER)[number],
    )
    if (currIdx >= 0 && currIdx < RIASEC_ORDER.length - 1) {
      return RIASEC_ORDER[currIdx + 1]
    }
    // Check if any earlier group has < 2 answers
    const incomplete = RIASEC_ORDER.find(
      (d) => (dimAnsweredCounts[d]?.answered ?? 0) < 2,
    )
    return incomplete || null
  }, [step, selectedDimension, dimAnsweredCounts])

  const canContinue = useMemo(() => {
    if (step === 3) return Object.keys(scores).length >= 3
    if (step === 2) return answeredCount >= cognitiveQuestions.length
    // Step 1: if navigating to next RIASEC group tab, require >= 2 answers in current group
    if (selectedDimension !== "ALL" && nextRiasecDim) {
      return (dimAnsweredCounts[selectedDimension]?.answered ?? 0) >= 2
    }
    return allRiasecGroupsCovered
  }, [
    step,
    scores,
    answeredCount,
    cognitiveQuestions.length,
    selectedDimension,
    nextRiasecDim,
    dimAnsweredCounts,
    allRiasecGroupsCovered,
  ])

  const next = () => {
    if (step === 1 && selectedDimension !== "ALL" && nextRiasecDim && !allRiasecGroupsCovered) {
      setSelectedDimension(nextRiasecDim)
      window.scrollTo({ top: 0, behavior: "smooth" })
      return
    }
    if (
      step === 1 &&
      selectedDimension !== "ALL" &&
      RIASEC_ORDER.indexOf(selectedDimension as (typeof RIASEC_ORDER)[number]) <
        RIASEC_ORDER.length - 1
    ) {
      const nextIdx =
        RIASEC_ORDER.indexOf(selectedDimension as (typeof RIASEC_ORDER)[number]) + 1
      setSelectedDimension(RIASEC_ORDER[nextIdx])
      window.scrollTo({ top: 0, behavior: "smooth" })
      return
    }
    if (step < 3) {
      setStep(step + 1)
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
    setSelectedDimension("R")
    setScores({})
  }

  return (
    <section className="min-h-[calc(100vh-72px)] bg-transparent py-8 sm:py-12">
      <PageContainer className="max-w-5xl">
        {/* Header */}
        <div className="mb-7 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-extrabold uppercase tracking-widest text-sky-600">
              AI CareerGuide · Đánh giá 3 trụ cột (TT74/2026)
            </span>
            <h1 className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">
              Trắc nghiệm định hướng cá nhân
            </h1>
          </div>
          <div className="flex items-center gap-3 text-xs font-semibold text-slate-500">
            <span className="flex items-center gap-1.5">
              <Clock3 size={14} className="text-sky-600" />
              6 – 8 phút (38 câu)
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
              Bước {step} / 3 · {step === 1 ? "Sở thích RIASEC (45%)" : step === 2 ? "Thiên hướng Nhận thức (20%)" : "Điểm học thuật (35%)"}
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
                    ? "Nhập tối thiểu 3 môn học (thang điểm 10) để đối chiếu tổ hợp xét tuyển."
                    : step === 2
                      ? "Hoàn thành đủ 8 câu trắc nghiệm tình huống để chuẩn hóa Ma trận Nhận thức."
                      : "Làm lần lượt từng nhóm 5 câu (R → I → A → S → E → C) từ 1 (Không thích) đến 5 (Rất thích)."}
                </p>
              </div>
            </div>
          </Card>

          {/* Dimension Tabs for Step 1 */}
          {step === 1 && (
            <div className="mb-4 flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/85 bg-white/55 p-1.5 backdrop-blur-xl">
              {[
                { key: "R", label: "R · Thực tế" },
                { key: "I", label: "I · Nghiên cứu" },
                { key: "A", label: "A · Nghệ thuật" },
                { key: "S", label: "S · Xã hội" },
                { key: "E", label: "E · Quản lý" },
                { key: "C", label: "C · Nghiệp vụ" },
                { key: "ALL", label: `Tất cả (${answeredCount}/${riasecQuestions.length})` },
              ].map((dim) => {
                const stat = dim.key !== "ALL" ? dimAnsweredCounts[dim.key] : null
                const isDone = stat && stat.total > 0 && stat.answered >= stat.total
                return (
                  <button
                    key={dim.key}
                    type="button"
                    onClick={() => setSelectedDimension(dim.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl transition-colors ${
                      selectedDimension === dim.key
                        ? "bg-sky-600 text-white shadow-2xs"
                        : isDone
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100/80"
                          : "text-slate-600 hover:bg-white/80"
                    }`}
                  >
                    <span>{dim.label}</span>
                    {stat && (
                      <span
                        className={`rounded-full px-1.5 py-0.2 text-[10px] ${
                          selectedDimension === dim.key
                            ? "bg-white/20 text-white"
                            : isDone
                              ? "bg-emerald-200/70 text-emerald-800"
                              : "bg-slate-200/70 text-slate-600"
                        }`}
                      >
                        {stat.answered}/{stat.total}
                      </span>
                    )}
                  </button>
                )
              })}
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
                const globalIndex = riasecQuestions.findIndex((item) => item.code === q.code)
                const idxKey = globalIndex >= 0 ? globalIndex : index
                const questionKey = q.code || `1-${idxKey}`
                const currentValue =
                  assessment.answers[questionKey] ?? assessment.answers[`1-${idxKey}`]

                return (
                  <motion.div
                    key={questionKey}
                    variants={{
                      hidden: { opacity: 0, y: 10 },
                      visible: { opacity: 1, y: 0 },
                    }}
                  >
                    <div className="relative">
                      {(q.domain_tag || q.dimension_badge) && (
                        <div className="absolute right-4 top-3.5 z-10 hidden sm:flex items-center gap-1.5">
                          {q.domain_tag && (
                            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-600 border border-slate-200">
                              {q.domain_tag}
                            </span>
                          )}
                          {q.dimension_badge && (
                            <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-700 border border-sky-200">
                              {q.dimension_badge}
                            </span>
                          )}
                        </div>
                      )}
                      <QuestionCard
                        index={idxKey + 1}
                        question={q.question_text}
                        value={typeof currentValue === "number" ? currentValue : undefined}
                        onChange={(value) =>
                          update({
                            answers: {
                              ...assessment.answers,
                              [questionKey]: value,
                              [`1-${idxKey}`]: value,
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
            disabled={
              step === 1 &&
              (selectedDimension === "R" || selectedDimension === "ALL")
            }
            onClick={() => {
              if (step === 1 && selectedDimension !== "ALL") {
                const currIdx = RIASEC_ORDER.indexOf(
                  selectedDimension as (typeof RIASEC_ORDER)[number],
                )
                if (currIdx > 0) {
                  setSelectedDimension(RIASEC_ORDER[currIdx - 1])
                  window.scrollTo({ top: 0, behavior: "smooth" })
                  return
                }
              }
              setStep(step - 1)
            }}
          >
            Quay lại
          </Button>
          <div className="flex items-center gap-3">
            {step === 1 && !allRiasecGroupsCovered && (
              <span className="text-[11px] font-medium text-slate-500 hidden sm:inline">
                (Đã trả lời {answeredCount}/30 câu · Cần tối thiểu 18 câu & đủ 6 nhóm để sang Bước 2)
              </span>
            )}
            {step === 2 && answeredCount < cognitiveQuestions.length && (
              <span className="text-[11px] font-medium text-slate-500 hidden sm:inline">
                (Đã chọn {answeredCount}/{cognitiveQuestions.length} câu nhận thức)
              </span>
            )}
            {step === 1 && allRiasecGroupsCovered && selectedDimension !== "C" && selectedDimension !== "ALL" && (
              <Button
                variant="secondary"
                onClick={() => {
                  setStep(2)
                  update({ step: 2 })
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Sang Bước 2 ngay ({answeredCount}/30)
              </Button>
            )}
            <Button
              icon={step === 3 ? Check : ArrowRight}
              disabled={!canContinue}
              onClick={next}
            >
              {step === 3
                ? "Hoàn thành & Xem kết quả"
                : step === 1 &&
                    selectedDimension !== "ALL" &&
                    selectedDimension !== "C"
                  ? `Nhóm tiếp theo (${nextRiasecDim})`
                  : "Tiếp tục sang bước kế"}
            </Button>
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
