import { motion } from "framer-motion"
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  CircleCheck,
  Compass,
  Loader2,
} from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useLocation, useParams } from "react-router"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { ExplanationBox } from "../components/xai/ExplanationBox"
import { FeasibilityBadge } from "../components/xai/FeasibilityBadge"
import { GapAnalysisCard } from "../components/xai/GapAnalysisCard"
import { MajorInfoCards } from "../components/xai/MajorInfoCards"
import { SkillAnalysisCard } from "../components/xai/SkillAnalysisCard"
import { TrendBadge } from "../components/xai/TrendBadge"
import { useAuth } from "../context/AuthContext"
import { MOET_435_MAJORS } from "../data/moetMajors435"
import { useSelectedAssessment } from "../hooks/useSelectedAssessment"
import { apiRequest } from "../services/api"
import { readStorage, writeStorage } from "../services/storage"
import type { MajorInsight, StudentSkillAnalysis } from "../types/insight"
import type { Major } from "../types/major"
import { formatBlockWithSubjects } from "../utils"
import { buildEvaluateProfilePayload } from "../utils/assessmentPayload"

interface TaxonomyMajorDetail {
  major_code: string
  name_vi?: string
  name?: string
  category?: string
  description?: string
  subject_blocks?: string[]
  careers?: Array<{ title_vi: string; description?: string } | string>
  is_trending?: boolean
  trend_tier?: "TIER_1" | "TIER_2" | "TIER_3" | null
  trend_priority?: number
  trend_label?: string | null
  trend_reason?: string | null
  trend_sources?: Array<{ title: string; url: string; source?: string }>
}

interface AIExplanationApiPayload {
  major_code: string
  major_name: string
  detailed_explanation: string
  riasec_alignment?: string
  academic_alignment?: string
  diagnostic_readiness?: string
  strengths?: string[]
  recommended_focus_areas?: string[]
  is_ai_generated?: boolean
}

interface SavedRoadmapItem {
  code: string
  label: string
  status: "TARGET" | "REACH" | "UNKNOWN"
}

function catalogMajor(id?: string): Major {
  const catalog = MOET_435_MAJORS.find(item => item.major_code === id)
  return {
    id: id || "", code: id || "", name: catalog?.name_vi || "Chưa xác định ngành",
    category: catalog?.category, university: catalog?.category || "Chưa có thông tin ngành",
    match: null, feasibility: "UNKNOWN", feasibility_label: "Chưa đủ bằng chứng đối chiếu",
    fit: { interest: null, academic: null, cognitive: null }, explanation: "Chưa có phân tích hồ sơ.", gaps: [],
  }
}

export function MajorDetail() {
  const { id } = useParams()
  const location = useLocation()
  const fromCatalog = location.state?.from === "/majors"
  const assessment = useSelectedAssessment()
  const { user } = useAuth()
  const [major, setMajor] = useState<Major>(() => catalogMajor(id))
  const [hasEvaluation, setHasEvaluation] = useState(false)
  const [taxDetail, setTaxDetail] = useState<TaxonomyMajorDetail | null>(null)
  const [majorInsight, setMajorInsight] = useState<MajorInsight | null>(null)
  const [skillAnalysis, setSkillAnalysis] =
    useState<StudentSkillAnalysis | null>(null)
  const [insightLoading, setInsightLoading] = useState(false)
  const [skillLoading, setSkillLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [aiExplaining, setAiExplaining] = useState(false)
  const [aiExplanationText, setAiExplanationText] = useState<string | null>(
    null,
  )
  const [savedList, setSavedList] = useState<SavedRoadmapItem[]>(() =>
    readStorage<SavedRoadmapItem[]>("career-guide:saved-roadmaps", []),
  )

  useEffect(() => {
    if (!id) return
    let mounted = true
    setLoading(true)
    setAiExplaining(true)
    setAiExplanationText(null)
    setMajorInsight(null)
    setSkillAnalysis(null)
    setInsightLoading(true)
    setSkillLoading(false)

    setMajor(catalogMajor(id))
    setHasEvaluation(false)
    setTaxDetail(null)
    const codeToLookup = id

    const evalPayload = buildEvaluateProfilePayload(assessment, 435, {
      gender: user?.gender,
      grade_level: user?.grade_level,
    })
    const hasUserAssessment =
      Object.keys(evalPayload.riasec_answers).length > 0 ||
      Object.keys(evalPayload.grades_by_subject).length > 0 ||
      Object.keys(evalPayload.cognitive_answers).length > 0

    // 1. Fetch Major Taxonomy & Deterministic 435-major Constraint Evaluation
    Promise.all([
      apiRequest<{ majors?: Major[]; blocked_goals?: Major[] } | null>("/recommender/evaluate", null, {
        method: "POST", body: JSON.stringify(evalPayload),
      }),
      apiRequest<TaxonomyMajorDetail | null>(
        `/taxonomy/majors/${codeToLookup}`,
        null,
      ),
    ])
      .then(([evalOrList, taxonomyInfo]) => {
        if (!mounted) return
        const recList = Array.isArray(evalOrList)
          ? evalOrList
          : [...(evalOrList?.majors || []), ...(evalOrList?.blocked_goals || [])]
        if (recList && Array.isArray(recList)) {
          const found = recList.find(
            (m) => m.id === id || m.code === id || m.code === codeToLookup,
          )
          if (found) {
            setMajor(found)
            setHasEvaluation(true)
          }
        }
        if (taxonomyInfo && taxonomyInfo.major_code) {
          setTaxDetail(taxonomyInfo)
          setMajor((prev) => ({
            ...prev,
            id: taxonomyInfo.major_code,
            code: taxonomyInfo.major_code,
            name: taxonomyInfo.name_vi || taxonomyInfo.name || prev.name,
            category: taxonomyInfo.category || prev.category,
            is_trending: taxonomyInfo.is_trending ?? prev.is_trending,
            trend_tier: taxonomyInfo.trend_tier ?? prev.trend_tier,
            trend_priority: taxonomyInfo.trend_priority ?? prev.trend_priority,
            trend_label: taxonomyInfo.trend_label ?? prev.trend_label,
            trend_reason: taxonomyInfo.trend_reason ?? prev.trend_reason,
            trend_sources: taxonomyInfo.trend_sources ?? prev.trend_sources,
            university:
              prev.university ||
              `${taxonomyInfo.category || "Khối ngành chuẩn Bộ GD&ĐT"} · Khối ${(taxonomyInfo.subject_blocks || []).join(", ")}`,
          }))
        }
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setLoading(false)
      })

    // 2. Agent "Phân tích ngành": nội dung đào tạo + vị trí nghề nghiệp (cache-first)
    const insightCacheKey = `careerguide:insight:${codeToLookup}`
    const cachedInsightRaw = sessionStorage.getItem(insightCacheKey)
    if (cachedInsightRaw) {
      try {
        const parsed = JSON.parse(cachedInsightRaw)
        if (parsed) {
          setMajorInsight(parsed)
          setInsightLoading(false)
        }
      } catch {
        sessionStorage.removeItem(insightCacheKey)
      }
    } else {
      apiRequest<MajorInsight | null>(`/major-insights/${codeToLookup}`, null)
        .then((insight) => {
          if (mounted && insight) {
            setMajorInsight(insight)
            try {
              sessionStorage.setItem(insightCacheKey, JSON.stringify(insight))
            } catch {}
          }
        })
        .catch(() => {})
        .finally(() => {
          if (mounted) setInsightLoading(false)
        })
    }

    // 3. Agent "Phân tích kỹ năng": ưu/nhược điểm học tập + kỹ năng cần bổ sung
    if (hasUserAssessment) {
      setSkillLoading(true)
      apiRequest<StudentSkillAnalysis | null>(
        "/major-insights/student-skills",
        null,
        {
          method: "POST",
          body: JSON.stringify({ ...evalPayload, major_code: codeToLookup }),
        },
      )
        .then((analysis) => {
          if (mounted && analysis) setSkillAnalysis(analysis)
        })
        .catch(() => {})
        .finally(() => {
          if (mounted) setSkillLoading(false)
        })
    }

    // 4. Automatically call AI Explanation API on page entry (session-cached for instant 0-token navigation)
    const explanationCacheKey = `careerguide:ai_explanation:${codeToLookup}:${user?.id || "guest"}:${JSON.stringify(evalPayload.riasec_answers || {})}:${JSON.stringify(evalPayload.grades_by_subject || {})}`
    const cachedExplanation = sessionStorage.getItem(explanationCacheKey)
    if (cachedExplanation) {
      setAiExplanationText(cachedExplanation)
      setAiExplaining(false)
    } else {
      apiRequest<AIExplanationApiPayload | null>(
        "/rag-governance/explain-recommendation",
        null,
        {
          method: "POST",
          body: JSON.stringify({ ...evalPayload, major_code: codeToLookup }),
        },
      )
        .then((aiRes) => {
          if (!mounted || !aiRes) return
          let cleanDetail = (aiRes.detailed_explanation || "").trim()
          if (cleanDetail.startsWith("{")) {
            try {
              const parsed = JSON.parse(cleanDetail)
              if (parsed.detailed_explanation) {
                cleanDetail = String(parsed.detailed_explanation)
              }
            } catch {
              const match = cleanDetail.match(
                /"detailed_explanation"\s*:\s*"((?:\\"|[^"])*)"/,
              )
              if (match?.[1]) {
                cleanDetail = match[1].replace(/\\n/g, "\n").replace(/\\"/g, '"')
              }
            }
          }

          const lines: string[] = []
          if (cleanDetail) {
            lines.push(cleanDetail)
          }
          if (!aiRes.is_ai_generated) {
            if (!cleanDetail.includes("###") && !cleanDetail.includes("##")) {
              lines.unshift("### Đối chiếu hồ sơ và ngành học", "")
            }
            if (aiRes.riasec_alignment) {
              lines.push(`- **Sở thích nghề nghiệp:** ${aiRes.riasec_alignment}`)
            }
            if (aiRes.academic_alignment) {
              lines.push(`- **Năng lực học tập:** ${aiRes.academic_alignment}`)
            }
            if (aiRes.strengths && aiRes.strengths.length > 0) {
              lines.push(
                `- **Điểm mạnh nổi bật:** ${aiRes.strengths.join(" · ")}`,
              )
            }
          }
          const formattedText = lines.join("\n\n")
          setAiExplanationText(formattedText)
          try {
            sessionStorage.setItem(explanationCacheKey, formattedText)
          } catch {}

          if (
            aiRes.recommended_focus_areas &&
            aiRes.recommended_focus_areas.length > 0
          ) {
            setMajor((prev) => ({
              ...prev,
              gaps:
                prev.gaps && prev.gaps.length > 0
                  ? prev.gaps
                  : aiRes.recommended_focus_areas!,
            }))
          }
        })
        .catch(() => {})
        .finally(() => {
          if (mounted) setAiExplaining(false)
        })
    }

    return () => {
      mounted = false
    }
  }, [
    id,
    assessment,
    assessment.answers,
    assessment.scores,
    assessment.cognitive,
    user?.gender,
    user?.grade_level,
  ])

  const isSaved = savedList.some((item) => item.code === major.code)

  const toggleSaveMajor = () => {
    const next: SavedRoadmapItem[] = isSaved
      ? savedList.filter((item) => item.code !== major.code)
      : [
          ...savedList,
          {
            code: major.code,
            label: major.name,
            status: "UNKNOWN",
          },
        ]
    setSavedList(next)
    writeStorage("career-guide:saved-roadmaps", next)
    window.dispatchEvent(new Event("saved-roadmaps-updated"))
  }

  const rawBlocks =
    majorInsight?.subject_blocks && majorInsight.subject_blocks.length > 0
      ? majorInsight.subject_blocks
      : taxDetail?.subject_blocks && taxDetail.subject_blocks.length > 0
        ? taxDetail.subject_blocks
        : []

  const blockText = rawBlocks
    .map((b) => formatBlockWithSubjects(b, { short: true }))
    .join(" · ")

  const skillCardVisible = skillLoading || Boolean(skillAnalysis)

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className="py-8 sm:py-10"
    >
      <PageContainer className="max-w-7xl">
        {/* Navigation & Actions Top Bar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link
            to={fromCatalog ? "/majors" : "/dashboard"}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white/80 px-3.5 py-2 text-xs font-bold text-slate-600 shadow-2xs backdrop-blur-md transition-colors hover:border-sky-300 hover:text-sky-700"
          >
            <ArrowLeft size={14} />
            {fromCatalog ? "Quay lại danh mục ngành" : "Quay lại đề xuất ngành học"}
          </Link>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={toggleSaveMajor}
              className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-bold backdrop-blur-md transition-all ${
                isSaved
                  ? "border-sky-300 bg-sky-50 text-sky-800 shadow-xs"
                  : "border-slate-200/85 bg-white/80 text-slate-700 hover:border-sky-200 hover:bg-white hover:text-sky-700"
              }`}
            >
              {isSaved ? (
                <BookmarkCheck size={15} className="text-sky-600" />
              ) : (
                <Bookmark size={15} />
              )}
              {isSaved ? "Đã lưu vào danh mục" : "Lưu ngành học"}
            </button>

            <Link
              to={`/roadmap?major=${major.code}&name=${encodeURIComponent(major.name)}`}
              className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-2 text-xs font-bold text-sky-700 transition hover:bg-sky-100"
            >
              <Compass size={14} />
              <span>Lộ trình 4 tuần · Coming Soon</span>
            </Link>
          </div>
        </div>

        {/* Major Overview Hero Card */}
        <Card className="rounded-3xl p-6 sm:p-8 border border-white/80 bg-white/80 shadow-sm backdrop-blur-xl">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div className="flex-1">
              {/* Badges strip - clean, uncluttered, legible */}
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded-lg bg-sky-500/12 px-2.5 py-1 text-xs font-extrabold text-sky-700">
                  Mã {major.code}
                </span>

                {major.category && (
                  <span className="rounded-full border border-slate-200/80 bg-slate-100/80 px-3 py-1 text-xs font-semibold text-slate-700">
                    {major.category}
                  </span>
                )}

                <FeasibilityBadge
                  readiness={major.readiness}
                  value={major.feasibility}
                  label={major.feasibility_label}
                />

                <TrendBadge
                  tier={major.trend_tier}
                  isTrending={major.is_trending}
                  reason={major.trend_reason}
                />

                {major.best_matching_block && major.best_block_score != null && (
                  <span className="rounded-full border border-sky-200 bg-sky-50/90 px-3 py-1 text-xs font-bold text-sky-800">
                    Khối {formatBlockWithSubjects(major.best_matching_block, { short: true, includePrefix: false })}: {major.best_block_score}đ
                    {major.benchmark_cutoff ? ` / ~${major.benchmark_cutoff}đ` : ""}
                  </span>
                )}

                {loading && (
                  <Loader2 size={15} className="animate-spin text-sky-600" />
                )}
              </div>

              {/* Constraint violations notice */}
              {major.constraint_violations && major.constraint_violations.length > 0 && (
                <div className="mt-3.5 flex items-center gap-2 rounded-2xl border border-amber-200/80 bg-amber-50/80 px-4 py-2.5 text-xs font-medium text-amber-900">
                  <AlertTriangle size={15} className="text-amber-600 shrink-0" />
                  <span>{major.constraint_violations.join(" · ")}</span>
                </div>
              )}

              {/* Title & University */}
              <h1 className="mt-4 text-2xl font-black text-slate-900 sm:text-3xl lg:text-4xl">
                {major.name}
              </h1>
              <p className="mt-2 text-xs font-medium text-slate-500 sm:text-sm">
                {major.university}
              </p>

              {/* Fit dimensions breakdown */}
              {hasEvaluation && major.fit && (
                <div className="mt-4 inline-flex flex-wrap items-center gap-3.5 rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-2 text-xs font-semibold text-slate-700 shadow-2xs">
                  <span>
                    Sở thích: <strong className="text-sky-600 font-extrabold">{major.fit.interest == null ? "Chưa có dữ liệu" : `${major.fit.interest}/100`}</strong>
                  </span>
                  <span className="text-slate-300">·</span>
                  <span>
                    Học lực: <strong className="text-sky-600 font-extrabold">{major.fit.academic == null ? "Chưa có dữ liệu" : `${major.fit.academic}/100`}</strong>
                  </span>
                  <span className="text-slate-300">·</span>
                  <span>
                    Thiên hướng tự khai: <strong className="text-cyan-600 font-extrabold">{major.fit.cognitive == null ? "Chưa có dữ liệu" : `${major.fit.cognitive}/100`}</strong>
                  </span>
                </div>
              )}
            </div>

            {/* Match score prominent badge */}
            <div className="flex flex-col items-start lg:items-end rounded-2xl bg-sky-50/60 p-4 border border-sky-100 sm:bg-transparent sm:border-0 sm:p-0">
              <span className="text-4xl sm:text-5xl font-black text-sky-600 tracking-tight">
                {hasEvaluation && major.match != null ? `${major.match}/100` : "—"}
              </span>
              <span className="mt-0.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                Điểm gợi ý tham khảo
              </span>
              <span className="mt-1 max-w-56 text-xs text-slate-500">Không phải xác suất trúng tuyển hay kết quả đo kỹ năng.</span>
            </div>
          </div>
        </Card>

        {/* Balanced 12-Column Responsive Layout */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-6 xl:gap-8 items-start">
          {/* Main Column: Explanation, Competency Gaps & Skill Analysis (8 cols on xl, 7 cols on lg) */}
          <div className="lg:col-span-7 xl:col-span-8 space-y-6">
            <ExplanationBox
              content={aiExplanationText || (hasEvaluation ? major.explanation : "Chưa có kết quả đối chiếu hồ sơ. Hãy thử lại khi dịch vụ hoạt động.")}
              loading={aiExplaining}
            />

            {major.gaps && major.gaps.length > 0 && (
              <GapAnalysisCard gaps={major.gaps} />
            )}

            {skillCardVisible && (
              <SkillAnalysisCard data={skillAnalysis} loading={skillLoading} />
            )}
          </div>

          {/* Sticky Career/Curriculum Info Cards + Roadmap Launcher (4 cols on xl, 5 cols on lg) */}
          <div className="lg:col-span-5 xl:col-span-4 space-y-6 lg:sticky lg:top-20">
            <MajorInfoCards
              training={majorInsight?.training_content || null}
              careers={majorInsight?.career_positions || []}
              subjectBlocks={blockText}
              loading={insightLoading}
            />

            {/* Quick 4-Week Roadmap Coming Soon Card */}
            <Card className="rounded-3xl border border-sky-100 bg-gradient-to-br from-white/95 to-sky-50/50 p-6 shadow-xs">
              <div className="flex items-start gap-3.5">
                <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-sky-600 text-white shadow-sm">
                  <CircleCheck size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-extrabold text-slate-900">
                      Lộ trình 4 tuần
                    </h3>
                    <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-sky-700">
                      Coming Soon
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                    Tính năng lộ trình hành động 4 tuần theo ngành {major.name} đang được phát triển và sẽ sớm ra mắt.
                  </p>
                </div>
              </div>
              <Link
                to={`/roadmap?major=${major.code}&name=${encodeURIComponent(major.name)}`}
                className="mt-4 block"
              >
                <Button variant="secondary" icon={ArrowRight} className="w-full justify-center text-xs">
                  Lộ trình 4 tuần · Coming Soon
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </PageContainer>
    </motion.section>
  )
}
