import { completeTranscriptBlocks } from "../utils/assessmentEvidence"
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Compass,
  Download,
  Eye,
  GraduationCap,
  History,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  Zap,
} from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useNavigate } from "react-router"
import { Badge } from "../components/common/Badge"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { HollandInterestSummary } from "../components/assessment/HollandInterestSummary"
import { RiasecRadarChart } from "../components/visualization/RiasecRadarChart"
import { AspirationAlignmentCard } from "../components/xai/AspirationAlignmentCard"
import { SkillAnalysisCard } from "../components/xai/SkillAnalysisCard"
import { TwoTierFunnelRecommendation } from "../components/xai/TwoTierFunnelRecommendation"
import { useAuth } from "../context/AuthContext"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest, requestJSON } from "../services/api"
import {
  riasecData as fallbackRiasec,
  type RiasecRadarPoint,
} from "../services/mockData"
import type {
  InterestEvidence,
  AspirationAnalysisPayload,
  AssessmentState,
  CareerAspirationInput,
} from "../types/assessment"
import type { StudentSkillAnalysis } from "../types/insight"
import type { FunnelRecommendationData, Major } from "../types/major"
import { formatBlockWithSubjects } from "../utils"
import { buildEvaluateProfilePayload, getValidRiasecAnswer } from "../utils/assessmentPayload"

interface BestBlockStatsPayload {
  block: string
  raw_sum?: number | null
  z_score?: string
  percentile?: string
  failing_subjects?: string[]
}

interface DashboardOverviewPayload {
  has_assessment?: boolean
  user_name?: string
  gender?: string
  grade_level?: string
  horizon_label?: string
  horizon_tau?: number
  weights_applied?: {
    w_riasec?: number
    w_academic?: number
    w_preference?: number
  }
  riasecData?: RiasecRadarPoint[]
  bestBlockStats?: BestBlockStatsPayload | null
  scoreBarData?: Array<{ name: string; value: number }>
  majors?: Major[]
  funnel?: FunnelRecommendationData
  interest_evidence?: InterestEvidence
  aspirationAnalysis?: AspirationAnalysisPayload | null
}

const ARCHETYPES: Record<string, string> = {
  I: "Nhà nghiên cứu Khoa học",
  R: "Kỹ sư Thực hành & Công nghệ",
  A: "Nhà sáng tạo Nghệ thuật",
  S: "Chuyên gia Phát triển Con người",
  E: "Nhà lãnh đạo Kinh doanh",
  C: "Chuyên gia Quản trị Dữ liệu",
}

function formatDateTimeVi(iso?: string): string {
  if (!iso) return "Vừa xong"
  try {
    const d = new Date(iso)
    return d.toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
  } catch {
    return iso
  }
}

function hasUsableAssessmentData(state: Pick<AssessmentState, "answers" | "scores">): boolean {
  const hasAnswers = Object.keys(state.answers || {}).length >= 3
  const hasScores = (state.scores || []).length >= 2
  return hasAnswers || hasScores
}

export function Dashboard() {
  const { user } = useAuth()
  const {
    assessment,
    history,
    activeHistoryId,
    hydrating,
    update,
    reset,
    selectHistoryAttempt,
    deleteHistoryAttempt,
  } = useAssessment()

  // The saved profile is the only source of demographic context here.
  const profileGradeLevel = user?.grade_level?.trim() || undefined
  const profileGender = user?.gender?.trim() || undefined

  const activeAttemptIndex = useMemo(() => {
    if (!activeHistoryId) return 0
    const idx = history.findIndex((h) => h.id === activeHistoryId)
    return idx >= 0 ? idx : 0
  }, [history, activeHistoryId])
  const activeAttempt = history[activeAttemptIndex] || null

  const effectiveAssessment = useMemo<AssessmentState>(() => {
    if (activeAttemptIndex > 0 && activeAttempt) {
      return {
        step: 4,
        answers: activeAttempt.answers || {},
        cognitive: activeAttempt.cognitive || {},
        scores: activeAttempt.scores || [],
        aspiration: activeAttempt.aspiration,
        completed: true,
        completedAt: activeAttempt.createdAt,
      }
    }
    if (assessment.completed && hasUsableAssessmentData(assessment)) {
      return assessment
    }
    if (history[0] && hasUsableAssessmentData(history[0])) {
      return {
        step: 4,
        answers: history[0].answers || {},
        cognitive: history[0].cognitive || {},
        scores: history[0].scores || [],
        aspiration: history[0].aspiration,
        completed: true,
        completedAt: history[0].createdAt,
      }
    }
    return assessment
  }, [assessment, history, activeAttempt, activeAttemptIndex])

  const navigate = useNavigate()
  const [data, setData] = useState<DashboardOverviewPayload | null>(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [isAnalyzingAspiration, setIsAnalyzingAspiration] = useState(false)
  const [evaluateError, setEvaluateError] = useState<string | null>(null)
  const [reloadNonce, setReloadNonce] = useState(0)
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false)
  const [recommendationMode, setRecommendationMode] = useState<"algorithm" | "ai">("algorithm")
  const [aiAnalysisTriggered, setAiAnalysisTriggered] = useState(false)
  const [skillAnalysis, setSkillAnalysis] =
    useState<StudentSkillAnalysis | null>(null)
  const [skillLoading, setSkillLoading] = useState(false)
  const skillCacheRef = useRef<Record<string, StudentSkillAnalysis>>({})
  const inFlightAiFingerprintRef = useRef<string | null>(null)
  const aspirationRequest = useRef(0)
  const profileRef = useRef(effectiveAssessment)
  useEffect(() => { profileRef.current = effectiveAssessment }, [effectiveAssessment])
  const reportTopRef = useRef<HTMLDivElement>(null)

  const hasUsableData = useMemo(
    () => hasUsableAssessmentData(effectiveAssessment),
    [effectiveAssessment],
  )
  const hasCompletedAssessment = Boolean(hasUsableData)
  const isDraftPreview = Boolean(hasUsableData && !effectiveAssessment.completed)

  useEffect(() => {
    let mounted = true
    const controller = new AbortController()
    const request = ++aspirationRequest.current
    setData(null)
    setEvaluateError(null)
    if (hasCompletedAssessment) {
      setIsEvaluating(true)
      setIsAnalyzingAspiration(true)
      const payload = buildEvaluateProfilePayload(effectiveAssessment, 435, {
        gender: profileGender,
        grade_level: profileGradeLevel,
      })
      requestJSON<DashboardOverviewPayload | null>(
        "/recommender/evaluate",
        {
          method: "POST",
          signal: controller.signal,
          body: JSON.stringify(payload),
        },
      )
        .then((res) => {
          if (mounted && request === aspirationRequest.current && res && res.funnel) {
            setData(res)
            setEvaluateError(null)
          }
        })
        .catch((err) => {
          if (mounted && request === aspirationRequest.current && !(err instanceof DOMException && err.name === "AbortError")) {
            setEvaluateError(
              err instanceof Error && err.message
                ? err.message
                : "Không tải được kết quả đề xuất ngành từ máy chủ. Vui lòng thử lại.",
            )
          }
        })
        .finally(() => {
          if (mounted && request === aspirationRequest.current) {
            setIsEvaluating(false)
            setIsAnalyzingAspiration(false)
          }
        })
    } else {
      setData(null)
      setEvaluateError(null)
      setIsEvaluating(false)
      setIsAnalyzingAspiration(false)
    }

    return () => {
      mounted = false
      controller.abort()
    }
  }, [
    hasCompletedAssessment,
    effectiveAssessment,
    profileGender,
    profileGradeLevel,
    activeHistoryId,
    reloadNonce,
  ])

  // Khóa vân tay theo toàn bộ yếu tố ảnh hưởng thuật toán đề xuất (điểm, lớp, giới tính, RIASEC, nhận thức, nguyện vọng, top ngành).
  // Chỉ khi vân tay này đổi thì mới cho phép gọi lại AI; ngược lại luôn lấy từ cache/CSDL.
  const topRecommendedMajorCode = data?.majors?.[0]?.code ?? ""
  const aiProfileFingerprint = useMemo(
    () =>
      JSON.stringify({
        answers: effectiveAssessment.answers || {},
        cognitive: effectiveAssessment.cognitive || {},
        scores: effectiveAssessment.scores || [],
        aspiration: effectiveAssessment.aspiration || null,
        grade: profileGradeLevel || "",
        gender: profileGender || "",
        topMajor: topRecommendedMajorCode,
      }),
    [
      effectiveAssessment,
      profileGradeLevel,
      profileGender,
      topRecommendedMajorCode,
    ],
  )

  // Khi hồ sơ / điểm / lớp / giới tính thay đổi -> hiển thị cache tương ứng nếu đã có, chưa có thì chờ người dùng mở chế độ AI.
  useEffect(() => {
    const cached = skillCacheRef.current[aiProfileFingerprint] ?? null
    setSkillAnalysis(cached)
    if (cached) {
      setSkillLoading(false)
    }
  }, [aiProfileFingerprint])

  // Agent "Phân tích kỹ năng": chỉ gọi AI khi người dùng chủ động mở chế độ "Đề xuất ngành có AI"
  // + chống bấm đúp (inFlightAiFingerprintRef) + chỉ gọi lại khi aiProfileFingerprint đổi.
  useEffect(() => {
    if (!hasCompletedAssessment || recommendationMode !== "ai" || !aiAnalysisTriggered) {
      return
    }
    const cached = skillCacheRef.current[aiProfileFingerprint]
    if (cached) {
      setSkillAnalysis(cached)
      setSkillLoading(false)
      return
    }
    if (inFlightAiFingerprintRef.current === aiProfileFingerprint) {
      return
    }

    let mounted = true
    const fingerprintAtStart = aiProfileFingerprint
    inFlightAiFingerprintRef.current = fingerprintAtStart
    const skillPayload = buildEvaluateProfilePayload(effectiveAssessment, undefined, {
      gender: profileGender,
      grade_level: profileGradeLevel,
    })

    setSkillLoading(true)
    apiRequest<StudentSkillAnalysis | null>(
      "/major-insights/student-skills",
      null,
      {
        method: "POST",
        body: JSON.stringify({
          ...skillPayload,
          major_code: topRecommendedMajorCode || undefined,
        }),
      },
    )
      .then((res) => {
        if (res) {
          skillCacheRef.current[fingerprintAtStart] = res
          if (mounted && aiProfileFingerprint === fingerprintAtStart) {
            setSkillAnalysis(res)
          }
        }
      })
      .catch(() => {})
      .finally(() => {
        if (inFlightAiFingerprintRef.current === fingerprintAtStart) {
          inFlightAiFingerprintRef.current = null
        }
        if (mounted) setSkillLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [
    hasCompletedAssessment,
    recommendationMode,
    aiAnalysisTriggered,
    aiProfileFingerprint,
    effectiveAssessment,
    profileGender,
    profileGradeLevel,
    topRecommendedMajorCode,
  ])

  const handleOpenAiMode = () => {
    if (skillLoading && recommendationMode === "ai") return
    setRecommendationMode("ai")
    setAiAnalysisTriggered(true)
    reportTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const handleOpenAlgorithmMode = () => {
    setRecommendationMode("algorithm")
    reportTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const handleUpdateAspiration = async (nextAspiration: CareerAspirationInput) => {
    if (activeAttemptIndex > 0) throw new Error("Không sửa bản xem lại")
    const snapshot = effectiveAssessment
    const request = ++aspirationRequest.current
    setIsAnalyzingAspiration(true)
    try {
      const response = await apiRequest<DashboardOverviewPayload | null>("/recommender/evaluate", null, {
        method: "POST",
        body: JSON.stringify(buildEvaluateProfilePayload({ ...snapshot, aspiration: nextAspiration }, 435, { gender: profileGender, grade_level: profileGradeLevel })),
      })
      if (request !== aspirationRequest.current || profileRef.current !== snapshot) throw new Error("Hồ sơ đã đổi")
      if (!response?.aspirationAnalysis) throw new Error("Chưa có phân tích")
      update({ aspiration: nextAspiration })
      setData(response)
    } finally {
      if (request === aspirationRequest.current) { setIsAnalyzingAspiration(false); setIsEvaluating(false) }
    }
  }

  // Merge user's live/selected assessment answers & scores into RIASEC radar data (prioritizing Backend result)
  const displayedRiasec: RiasecRadarPoint[] = useMemo(() => {
    if (data?.riasecData && data.riasecData.length > 0) {
      return data.riasecData
    }
    const groups = "RIASEC".split("")
    return fallbackRiasec.flatMap(point => {
      const index = groups.indexOf(point.key)
      const values = Array.from({ length: 5 }, (_, i) => getValidRiasecAnswer(effectiveAssessment.answers, `${point.key}${i + 1}`, index * 5 + i)).filter((v): v is number => v !== undefined)
      if (!values.length) return []
      return [{ ...point, value: Math.round((values.reduce((a, b) => a + b, 0) / values.length - 1) / 4 * 100), academicValue: null }]
    })
  }, [data?.riasecData, effectiveAssessment.answers])

  const interestEvidence: InterestEvidence = useMemo(() => {
    if (data?.interest_evidence) return data.interest_evidence
    const groups = (["R", "I", "A", "S", "E", "C"] as const).map((code, index) => {
      const values = Array.from({ length: 5 }, (_, i) => getValidRiasecAnswer(effectiveAssessment.answers, `${code}${i + 1}`, index * 5 + i)).filter((v): v is number => v !== undefined)
      return { code, percent: values.length ? Math.round((values.reduce((a, b) => a + b, 0) / values.length - 1) / 4 * 100) : null, answered: values.length, total: 5 }
    })
    const total = groups.reduce((sum, g) => sum + g.answered, 0)
    return { status: total === 30 ? "COMPLETE" : total ? "PARTIAL" : "MISSING", groups }
  }, [data, effectiveAssessment.answers])

  const top3Dimensions = useMemo(() => {
    if (interestEvidence.status !== "COMPLETE") return []
    const sorted = [...displayedRiasec].filter(point => Number.isFinite(point.value)).sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    const threshold = sorted[2]?.value ?? 0
    return sorted.filter(point => (point.value ?? 0) >= threshold)
  }, [displayedRiasec, interestEvidence.status])

  const hollandCodeBadge = useMemo(
    () => top3Dimensions.map((d) => d.key).join(" · "),
    [top3Dimensions],
  )

  const archetypeTitle = useMemo(() => {
    if (interestEvidence.status === "NON_DISCRIMINATING") return "Sở thích chưa phân biệt giữa các nhóm"
    const primaryKey = top3Dimensions[0]?.key
    if (top3Dimensions.length > 1 && top3Dimensions[0].value === top3Dimensions[1].value) return "Nhiều nhóm sở thích đồng điểm cao nhất"
    return primaryKey ? ARCHETYPES[primaryKey] : "Chưa đủ dữ liệu sở thích"
  }, [top3Dimensions, interestEvidence.status])

  const bestBlockStats = useMemo(() => {
    if (data?.bestBlockStats && data.bestBlockStats.block) {
      return {
        block: data.bestBlockStats.block,
        rawSum: data.bestBlockStats.raw_sum ?? 0,
        zScore: data.bestBlockStats.z_score ?? "Chưa xác minh",
        percentile: data.bestBlockStats.percentile ?? "Chưa có nguồn phân phối điểm",
        failingSubjects: data.bestBlockStats.failing_subjects ?? [],
      }
    }

    const best = completeTranscriptBlocks(effectiveAssessment.scores || [])[0]
    return {
      block: best ? `Khối ${best.code} (${best.subjects.join(", ")})` : "Chưa đủ tổ hợp môn",
      rawSum: best?.sum ?? null,
      zScore: "Chưa xác minh",
      percentile: "Điểm học bạ tự khai; chưa đối chiếu phân phối thi",
      failingSubjects: (effectiveAssessment.scores || []).filter(item => Number.isFinite(item.score) && item.score <= 1).map(item => `${item.subject} (${item.score}đ)`),
    }

  }, [data, effectiveAssessment.scores])

  const activeFunnel: FunnelRecommendationData = data?.funnel ?? { tier1_fields: [], all_majors: [] }

  const handleExportPdf = () => {
    window.print()
  }

  const handleRetakeAssessment = () => {
    reset()
    navigate("/assessment")
  }

  const handleSelectHistory = (attemptId: string) => {
    selectHistoryAttempt(attemptId)
    setShowHistoryDrawer(false)
    setData(null)
    reportTopRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const displayName = user?.name || data?.user_name || "Học sinh"

  return (
    <section className="py-6 sm:py-9 lg:py-11" ref={reportTopRef}>
      <PageContainer>
        {/* Header */}
        <div className="mb-6 flex flex-col justify-between gap-4 sm:mb-8 lg:flex-row lg:items-end">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-sky-600">
              <Sparkles size={14} />
              AI CareerGuide · 435 Ngành
            </div>
            <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-900 sm:text-3xl xl:text-4xl">
              Đề xuất ngành học
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {hasCompletedAssessment
                ? `Chào ${displayName}, xem các ngành phù hợp với hồ sơ của bạn.`
                : `Chào ${displayName}, làm bài đánh giá để nhận đề xuất phù hợp.`}
            </p>
          </div>

          {hasCompletedAssessment && (
            <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
              {history.length > 0 && (
                <Button
                  variant="secondary"
                  icon={History}
                  onClick={() => setShowHistoryDrawer((v) => !v)}
                >
                  Lịch sử ({history.length})
                </Button>
              )}
              <Button
                variant="secondary"
                icon={RotateCcw}
                onClick={handleRetakeAssessment}
              >
                Làm lại
              </Button>
              <Button
                variant="secondary"
                icon={Download}
                onClick={handleExportPdf}
              >
                Xuất PDF
              </Button>
            </div>
          )}
        </div>

        {activeAttemptIndex === 0 && assessment.syncStatus === "LOCAL_ONLY" && <p role="status" className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Đã lưu trên thiết bị, chưa đồng bộ máy chủ. Bài làm vẫn được giữ trên trình duyệt này; hãy mở lại bài đánh giá và gửi lại khi kết nối hoạt động.</p>}
        {activeAttemptIndex === 0 && assessment.syncStatus === "SYNCED" && assessment.submissionId && <p role="status" className="mb-5 text-xs text-slate-600">Đã đồng bộ bài đánh giá với máy chủ.</p>}

        {/* Liquid Glass Hydrating / Empty State when Student has NOT completed the Assessment */}
        {!hasCompletedAssessment && hydrating ? (
          <div className="mb-10 rounded-[32px] border border-white/80 bg-white/60 p-10 text-center shadow-[0_18px_50px_rgba(14,165,233,0.1)] backdrop-blur-2xl sm:p-14">
            <div className="mx-auto mb-3 size-10 animate-spin rounded-full border-4 border-sky-200 border-t-sky-600" />
            <h2 className="text-lg font-extrabold text-slate-800">
              Đang đồng bộ hồ sơ đánh giá của bạn...
            </h2>
            <p className="mt-1.5 text-sm text-slate-500">
              Hệ thống đang kiểm tra bài trắc nghiệm đã lưu trên tài khoản của bạn.
            </p>
          </div>
        ) : !hasCompletedAssessment ? (
          <div className="relative mb-10 overflow-hidden rounded-[36px] border border-white/80 bg-white/40 p-8 shadow-[0_24px_80px_rgba(14,165,233,0.14)] backdrop-blur-2xl sm:p-14">
            <div className="pointer-events-none absolute -left-16 -top-16 size-72 rounded-full bg-sky-300/35 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 -right-16 size-80 rounded-full bg-cyan-200/40 blur-3xl" />

            <div className="relative mx-auto max-w-2xl text-center">
              <span className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/60 px-4 py-1.5 text-xs font-extrabold tracking-wide text-sky-700 shadow-2xs backdrop-blur-md">
                <ClipboardCheck size={14} />
                Chưa có dữ liệu trắc nghiệm
              </span>

              <h2 className="mt-5 text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
                Làm bài đánh giá để mở khóa đề xuất từ 435 ngành
              </h2>

              <div className="mt-8 grid gap-3.5 sm:grid-cols-3 sm:gap-4">
                {[
                  { title: "Sở thích RIASEC", desc: "Thiên hướng 6 nhóm nghề nghiệp" },
                  { title: "Học lực & Tổ hợp", desc: "Đối chiếu chuẩn tuyển sinh" },
                  { title: "Phong cách nhận thức", desc: "Thói quen học tập & tư duy" },
                ].map((pillar) => (
                  <div
                    key={pillar.title}
                    className="rounded-3xl border border-white/80 bg-white/50 p-4 text-center shadow-[0_8px_30px_rgba(14,165,233,0.07)] backdrop-blur-xl sm:p-5"
                  >
                    <h3 className="text-sm font-extrabold text-sky-700 sm:text-base">
                      {pillar.title}
                    </h3>
                    <p className="mt-1.5 text-xs font-medium leading-relaxed text-slate-600">
                      {pillar.desc}
                    </p>
                  </div>
                ))}
              </div>

              <p className="mt-4 text-xs font-medium text-slate-500">
                Hệ số trọng số tự động điều chỉnh linh hoạt theo khối lớp và dữ liệu hồ sơ của bạn.
              </p>

              <div className="mt-9 flex justify-center">
                <Link to="/assessment">
                  <Button
                    icon={ArrowRight}
                    className="rounded-2xl px-8 py-3.5 text-sm shadow-lg shadow-sky-500/20"
                  >
                    Bắt đầu đánh giá ngay
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <>
            {isDraftPreview && (
              <div
                role="status"
                className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-xs sm:text-sm text-amber-900"
              >
                <span>
                  Bạn đang xem đề xuất tạm từ bài làm chưa bấm hoàn tất. Hãy mở mục{" "}
                  <strong>Trắc nghiệm</strong> và bấm <strong>Hoàn tất</strong> ở bước cuối để lưu chính thức lên máy chủ.
                </span>
                <Link
                  to="/assessment"
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-amber-600 px-3.5 py-1.5 text-xs font-extrabold text-white transition hover:bg-amber-700"
                >
                  Hoàn tất trắc nghiệm
                  <ArrowRight size={13} />
                </Link>
              </div>
            )}

            {/* Collapsible History Drawer (only visible when user clicks "Lịch sử" or has multiple attempts) */}
            {(showHistoryDrawer || history.length > 1) && (
              <div className="mb-6 min-w-0 rounded-2xl border border-white/80 bg-white/50 p-3.5 shadow-[0_10px_35px_rgba(14,165,233,0.08)] backdrop-blur-xl sm:rounded-3xl sm:p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 text-xs font-bold text-slate-800">
                    <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-sky-500/15 text-sky-600">
                      <Clock size={15} />
                    </span>
                    <span>
                      Lần #{history.length - activeAttemptIndex}
                      <span className="ml-2 font-medium text-slate-400">
                        {formatDateTimeVi(
                          activeAttempt?.createdAt || assessment.completedAt,
                        )}
                      </span>
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {history.map((item, idx) => {
                      const isCurrent =
                        item.id === (activeAttempt?.id || history[0]?.id)
                      const attemptNumber = history.length - idx
                      return (
                        <div key={item.id} className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => handleSelectHistory(item.id)}
                            className={`inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs font-bold transition sm:px-3 ${
                              isCurrent
                                ? "bg-sky-600 text-white shadow-xs"
                                : "border border-white/80 bg-white/60 text-slate-600 hover:bg-white hover:text-sky-700"
                            }`}
                          >
                            {isCurrent ? <CheckCircle2 size={12} /> : <Eye size={12} />}
                            Lần #{attemptNumber} · Hồ sơ đã lưu
                          </button>
                          {history.length > 1 && (
                            <button
                              type="button"
                              onClick={() => deleteHistoryAttempt(item.id)}
                              className="rounded-lg p-1.5 text-slate-400 hover:bg-white/70 hover:text-slate-700"
                              title="Xóa"
                            >
                              <Trash2 size={12} />
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Bộ chuyển chế độ: Thuật toán đề xuất (tức thì) vs Đề xuất ngành có AI (phân tích sâu) */}
            <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-white/80 bg-white/60 p-2 shadow-[0_10px_35px_rgba(14,165,233,0.08)] backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between sm:rounded-3xl sm:p-2.5">
              <div className="grid w-full grid-cols-1 gap-2 sm:flex sm:w-auto">
                <button
                  type="button"
                  onClick={handleOpenAlgorithmMode}
                  className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs font-extrabold transition sm:rounded-2xl sm:text-sm ${
                    recommendationMode === "algorithm"
                      ? "bg-sky-600 text-white shadow-md shadow-sky-500/20"
                      : "text-slate-600 hover:bg-white hover:text-sky-700"
                  }`}
                >
                  <Zap size={15} className="shrink-0" />
                  <span>Thuật toán đề xuất</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      recommendationMode === "algorithm"
                        ? "bg-white/20 text-white"
                        : "bg-sky-100 text-sky-700"
                    }`}
                  >
                    Tức thì · Không AI
                  </span>
                </button>

                <button
                  type="button"
                  onClick={handleOpenAiMode}
                  disabled={skillLoading && recommendationMode === "ai"}
                  className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs font-extrabold transition disabled:cursor-wait disabled:opacity-80 sm:rounded-2xl sm:text-sm ${
                    recommendationMode === "ai"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/20"
                      : "text-slate-600 hover:bg-white hover:text-indigo-700"
                  }`}
                >
                  {skillLoading ? (
                    <Loader2 size={15} className="shrink-0 animate-spin" />
                  ) : (
                    <Sparkles size={15} className="shrink-0" />
                  )}
                  <span>{skillLoading ? "AI đang phân tích..." : "Đề xuất ngành có AI"}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      recommendationMode === "ai"
                        ? "bg-white/20 text-white"
                        : "bg-indigo-100 text-indigo-700"
                    }`}
                  >
                    {skillLoading ? "Đang tải" : "Phân tích sâu"}
                  </span>
                </button>
              </div>

              <p className="px-2 text-[11px] font-medium text-slate-500 sm:text-right sm:text-xs">
                {recommendationMode === "algorithm"
                  ? "Tính toán 100% bằng thuật toán 3 trụ cột (RIASEC · Học lực · Tự khai), hiển thị ngay lập tức."
                  : "Kết hợp thuật toán với AI đối chiếu nguyện vọng & phân tích điểm mạnh/yếu chuyên sâu."}
              </p>
            </div>

            {recommendationMode === "ai" && (
              <div className="mb-6">
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-indigo-200/80 bg-indigo-50/70 px-4 py-3 text-xs text-indigo-900 sm:rounded-3xl sm:px-5 sm:py-3.5 sm:text-sm">
                  <div className="flex items-center gap-2.5">
                    <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-indigo-600 text-white">
                      {skillLoading || isAnalyzingAspiration ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Sparkles size={16} />
                      )}
                    </span>
                    <div>
                      <p className="font-extrabold text-indigo-950">
                        {skillLoading || isAnalyzingAspiration
                          ? "AI đang phân tích chuyên sâu hồ sơ của bạn..."
                          : "Chế độ Đề xuất ngành có AI phân tích chuyên sâu"}
                      </p>
                      <p className="text-xs font-medium text-indigo-700">
                        {skillLoading || isAnalyzingAspiration
                          ? "Vui lòng chờ vài giây trong lúc AI xử lý; kết quả sẽ được lưu lại trong lịch sử CSDL."
                          : "AI đối chiếu nguyện vọng nghề nghiệp, đánh giá điểm mạnh/yếu kỹ năng dựa trên kết quả thuật toán."}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleOpenAlgorithmMode}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-white px-3.5 py-2 text-xs font-extrabold text-indigo-700 transition hover:bg-indigo-100"
                  >
                    <ArrowLeft size={14} />
                    Quay lại Thuật toán
                  </button>
                </div>
              </div>
            )}

            {/* Đối chiếu nguyện vọng nghề nghiệp & học lực (hiển thị tức thì ở cả 2 chế độ; nhận xét AI bổ sung khi bật chế độ Có AI) */}
            <div className="mb-6">
              <AspirationAlignmentCard
                analysis={data?.aspirationAnalysis ?? null}
                currentAspiration={effectiveAssessment.aspiration}
                onUpdateAspiration={handleUpdateAspiration}
                isAnalyzing={isAnalyzingAspiration}
                readOnly={activeAttemptIndex > 0}
                isAiMode={recommendationMode === "ai"}
                aiCoachingSummary={skillAnalysis?.summary ?? null}
              />
            </div>

            {recommendationMode === "ai" && (
              <div className="mb-6">
                {/* AI Phân tích kỹ năng & điểm mạnh/yếu (chỉ gọi khi mở chế độ AI) */}
                <SkillAnalysisCard data={skillAnalysis} loading={skillLoading} />
              </div>
            )}

            {/* 1. Hồ sơ RIASEC & Phễu Ngành đề xuất 2 tầng */}
            <div className="mb-8 grid min-w-0 gap-6 xl:grid-cols-12 xl:gap-8">
              {/* Left Column: Single Unified Profile Card */}
              <div className="min-w-0 xl:col-span-4">
                <Card className="rounded-2xl p-4 sm:rounded-3xl sm:p-6 xl:sticky xl:top-6">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs font-bold uppercase tracking-wider text-sky-700">
                        Hồ sơ Định hướng
                      </p>
                      <h2 className="mt-1 break-words text-lg font-bold text-slate-900 sm:text-xl xl:text-2xl">
                        {archetypeTitle}
                      </h2>
                    </div>
                    <Badge tone="indigo" className="shrink-0 whitespace-nowrap">{hollandCodeBadge}</Badge>
                  </div>

                  <div className="md:grid md:grid-cols-12 md:items-center md:gap-6 xl:block">
                    <div className="md:col-span-6 xl:col-span-12">
                      {interestEvidence.status === "COMPLETE" && displayedRiasec.length === 6 && displayedRiasec.every(point => Number.isFinite(point.value)) ? <RiasecRadarChart data={displayedRiasec} /> : <HollandInterestSummary evidence={interestEvidence} />}
                    </div>

                    <div className="md:col-span-6 xl:col-span-12">
                      <div className="mt-3 grid grid-cols-3 gap-2 sm:gap-2.5">
                        {top3Dimensions.map((item) => (
                          <div
                            className="min-w-0 rounded-xl border border-slate-200/80 bg-white/70 p-2 text-center sm:p-3"
                            key={item.key}
                          >
                            <p className="text-base font-bold text-sky-600 sm:text-lg">
                              {item.key}
                            </p>
                            <p className="truncate text-[11px] font-medium text-slate-500 sm:text-xs">
                              {item.label}
                            </p>
                            <p className="mt-1 text-xs font-bold tabular-nums text-slate-900 sm:text-sm">
                              {item.value}%
                            </p>
                          </div>
                        ))}
                      </div>

                      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200/80 bg-white/70 px-3.5 py-3 sm:px-4">
                        <div className="flex min-w-0 items-center gap-2">
                          <GraduationCap size={18} className="shrink-0 text-sky-600" />
                          <span className="min-w-0 break-words text-xs font-bold text-slate-800">
                            {formatBlockWithSubjects(bestBlockStats.block, { short: true })}
                            {bestBlockStats.rawSum ? ` · ${bestBlockStats.rawSum}đ` : ""}
                          </span>
                        </div>
                        <span className="break-words text-xs font-semibold tabular-nums text-sky-700">
                          Z-Score {bestBlockStats.zScore} · {bestBlockStats.percentile}
                        </span>
                      </div>
                      {bestBlockStats.failingSubjects.length > 0 && (
                        <div className="mt-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
                          Cảnh báo điểm liệt: {bestBlockStats.failingSubjects.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </div>

              {/* Right Column: 2-Tier Recommendation Funnel */}
              <div className="min-w-0 xl:col-span-8">
                {evaluateError && (
                  <div
                    role="alert"
                    className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
                  >
                    <span>{evaluateError}</span>
                    <button
                      type="button"
                      onClick={() => setReloadNonce((n) => n + 1)}
                      className="rounded-xl border border-rose-300 bg-white px-3.5 py-1.5 text-xs font-extrabold text-rose-700 transition hover:bg-rose-100"
                    >
                      Thử tải lại
                    </button>
                  </div>
                )}
                <TwoTierFunnelRecommendation
                  funnelData={activeFunnel}
                  isLoading={isEvaluating && (!activeFunnel.tier1_fields || activeFunnel.tier1_fields.length === 0)}
                  activeGradeLevel={profileGradeLevel}
                  activeGender={profileGender}
                  weightsApplied={data?.weights_applied}
                />
              </div>
            </div>

            {/* CTA mở chế độ Đề xuất ngành có AI khi đang ở chế độ Thuật toán */}
            {recommendationMode === "algorithm" && (
              <div className="mb-6 rounded-2xl border border-indigo-200/80 bg-gradient-to-r from-indigo-50/90 via-sky-50/80 to-white/90 p-5 shadow-[0_12px_35px_rgba(79,70,229,0.08)] sm:rounded-3xl sm:p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 space-y-1.5">
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-white/80 px-2.5 py-0.5 text-[11px] font-extrabold text-indigo-700">
                      <Sparkles size={12} />
                      Tùy chọn nâng cao · Phân tích AI
                    </div>
                    <h3 className="text-base font-extrabold text-slate-900 sm:text-lg">
                      Muốn AI phân tích chuyên sâu hơn để tăng độ chính xác?
                    </h3>
                    <p className="max-w-2xl text-xs leading-relaxed text-slate-600 sm:text-sm">
                      Kết quả phía trên được tính tức thời 100% bằng thuật toán (không mất thời gian chờ AI). Nếu bạn muốn AI đối chiếu sâu với nguyện vọng cá nhân và phân tích điểm mạnh/yếu kỹ năng, hãy chuyển sang chế độ <strong>Đề xuất ngành có AI</strong>.
                    </p>
                  </div>
                  <Button
                    type="button"
                    icon={skillLoading ? undefined : Sparkles}
                    onClick={handleOpenAiMode}
                    disabled={skillLoading}
                    className="shrink-0 rounded-2xl bg-indigo-600 px-5 py-3 text-xs font-extrabold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-80 sm:text-sm"
                  >
                    {skillLoading ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 size={15} className="animate-spin" />
                        AI đang phân tích...
                      </span>
                    ) : (
                      "Mở đề xuất ngành có AI"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Link to separate 435 MOET Majors Catalog Page */}
        <div className="mt-8">
          <Card className="flex flex-col items-start justify-between gap-4 rounded-[28px] p-5 sm:flex-row sm:items-center sm:p-6">
            <div>
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-sky-600">
                <Compass size={15} />
                Danh mục chuẩn Bộ GD&ĐT
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-700">
                Muốn tự tìm kiếm và tra cứu toàn bộ 435 ngành đào tạo theo mã ngành hoặc lĩnh vực?
              </p>
            </div>
            <Link
              to="/majors"
              className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-xs font-extrabold text-white shadow-sm transition hover:bg-sky-700"
            >
              Mở Danh mục ngành
              <ArrowRight size={15} />
            </Link>
          </Card>
        </div>

      </PageContainer>
    </section>
  )
}
