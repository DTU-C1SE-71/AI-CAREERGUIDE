import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  BookOpenCheck,
  BriefcaseBusiness,
  CircleCheck,
  GraduationCap,
  Loader2,
} from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { ExplanationBox } from "../components/xai/ExplanationBox"
import { FeasibilityBadge } from "../components/xai/FeasibilityBadge"
import { GapAnalysisCard } from "../components/xai/GapAnalysisCard"
import { MOET_435_MAJORS } from "../data/moetMajors435"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest } from "../services/api"
import { majors as fallbackMajors } from "../services/mockData"
import { readStorage, writeStorage } from "../services/storage"
import type { Major } from "../types/major"

interface TaxonomyMajorDetail {
  major_code: string
  name_vi: string
  category?: string
  description?: string
  subject_blocks?: string[]
  careers?: Array<{ title_vi: string; description?: string }>
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
  status: "TARGET" | "REACH"
}

export function MajorDetail() {
  const { id } = useParams()
  const { assessment } = useAssessment()
  const [major, setMajor] = useState<Major>(() => {
    return (
      fallbackMajors.find((item) => item.id === id || item.code === id) ??
      fallbackMajors[0]
    )
  })
  const [taxDetail, setTaxDetail] = useState<TaxonomyMajorDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [aiExplaining, setAiExplaining] = useState(false)
  const [aiExplanationText, setAiExplanationText] = useState<string | null>(
    null,
  )
  const [savedList, setSavedList] = useState<SavedRoadmapItem[]>(() =>
    readStorage<SavedRoadmapItem[]>("career-guide:saved-roadmaps", [
      { code: "7480101", label: "Khoa học máy tính", status: "TARGET" },
      { code: "7460108", label: "Khoa học dữ liệu", status: "REACH" },
    ]),
  )

  useEffect(() => {
    if (!id) return
    let mounted = true
    setLoading(true)
    setAiExplaining(true)
    setAiExplanationText(null)

    const localMatch = fallbackMajors.find(
      (item) => item.id === id || item.code === id,
    )
    if (localMatch) {
      setMajor(localMatch)
    } else {
      const catalogItem = MOET_435_MAJORS.find((item) => item.major_code === id)
      if (catalogItem) {
        setMajor({
          id: catalogItem.major_code,
          code: catalogItem.major_code,
          name: catalogItem.name_vi,
          category: catalogItem.category,
          university: `Khối ${(catalogItem.subject_blocks || ["A00", "A01", "D01"]).join(", ")} · Chuẩn Bộ GD&ĐT`,
          match: 88,
          feasibility: "TARGET",
          fit: { interest: 88, academic: 88, cognitive: 88 },
          explanation: `### Vì sao phù hợp?\nNgành **${catalogItem.name_vi}** (Mã ${catalogItem.major_code}) thuộc lĩnh vực **${catalogItem.category}** theo danh mục 435 ngành chuẩn Bộ GD&ĐT.`,
          gaps: [
            "Kiến thức nền tảng ngành",
            "Ngoại ngữ chuyên ngành",
            "Kỹ năng thực hành dự án",
          ],
        })
      }
    }

    const codeToLookup = localMatch?.code || id

    // Build student profile metrics from AssessmentContext for AI explanation
    const riasecScores: Record<string, number> = {}
    for (const dim of ["R", "I", "A", "S", "E", "C"]) {
      const vals: number[] = []
      for (let i = 1; i <= 5; i++) {
        const v = assessment.answers?.[`${dim}${i}`]
        if (typeof v === "number" && v > 0) vals.push(v)
      }
      if (vals.length > 0) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length
        riasecScores[dim] = Number((avg / 5).toFixed(2))
      }
    }

    const gradesBySubject: Record<string, number> = Object.fromEntries(
      (assessment.scores || []).map((s) => [s.subject, s.score]),
    )

    // 1. Fetch Major Taxonomy & Recommender data
    Promise.all([
      apiRequest<Major[] | null>("/recommender/majors?top_k=435", null),
      apiRequest<TaxonomyMajorDetail | null>(
        `/taxonomy/majors/${codeToLookup}`,
        null,
      ),
    ])
      .then(([recList, taxonomyInfo]) => {
        if (!mounted) return
        if (recList && Array.isArray(recList)) {
          const found = recList.find(
            (m) => m.id === id || m.code === id || m.code === codeToLookup,
          )
          if (found) {
            setMajor(found)
          }
        }
        if (taxonomyInfo && taxonomyInfo.major_code) {
          setTaxDetail(taxonomyInfo)
          setMajor((prev) => ({
            ...prev,
            id: taxonomyInfo.major_code,
            code: taxonomyInfo.major_code,
            name: taxonomyInfo.name_vi || prev.name,
            category: taxonomyInfo.category || prev.category,
            university:
              prev.university ||
              `${taxonomyInfo.category || "Khối ngành chuẩn Bộ GD&ĐT"} · Khối ${(taxonomyInfo.subject_blocks || ["A00", "A01", "D01"]).join(", ")}`,
          }))
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    // 2. Automatically call AI Explanation API on page entry
    apiRequest<AIExplanationApiPayload | null>(
      "/rag-governance/explain-recommendation",
      null,
      {
        method: "POST",
        body: JSON.stringify({
          major_code: codeToLookup,
          riasec_scores:
            Object.keys(riasecScores).length > 0 ? riasecScores : undefined,
          grades_by_subject:
            Object.keys(gradesBySubject).length > 0
              ? gradesBySubject
              : undefined,
          cognitive_preferences:
            Object.keys(assessment.cognitive || {}).length > 0
              ? assessment.cognitive
              : undefined,
        }),
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
        if (!cleanDetail.includes("###") && !cleanDetail.includes("##")) {
          lines.push("### Vì sao phù hợp?", "")
        }
        if (cleanDetail) {
          lines.push(cleanDetail, "")
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
        setAiExplanationText(lines.join("\n"))

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
      .finally(() => {
        if (mounted) setAiExplaining(false)
      })

    return () => {
      mounted = false
    }
  }, [id, assessment.answers, assessment.scores, assessment.cognitive])

  const isSaved = savedList.some((item) => item.code === major.code)

  const toggleSaveMajor = () => {
    const next: SavedRoadmapItem[] = isSaved
      ? savedList.filter((item) => item.code !== major.code)
      : [
          ...savedList,
          {
            code: major.code,
            label: major.name,
            status: major.feasibility === "REACH" ? "REACH" : "TARGET",
          },
        ]
    setSavedList(next)
    writeStorage("career-guide:saved-roadmaps", next)
    window.dispatchEvent(new Event("saved-roadmaps-updated"))
  }

  const careerText =
    taxDetail?.careers && taxDetail.careers.length > 0
      ? taxDetail.careers.map((c) => c.title_vi).join(", ")
      : "Kỹ sư chuyên môn, Chuyên viên phân tích, R&D, Quản lý dự án."

  const blockText =
    taxDetail?.subject_blocks && taxDetail.subject_blocks.length > 0
      ? taxDetail.subject_blocks.join(", ")
      : "A00, A01, D01, D07"

  const studyDescription =
    taxDetail?.description ||
    "Chương trình đào tạo kết hợp kiến thức nền tảng, kỹ năng thực hành và dự án thực tế."

  return (
    <section className="py-10">
      <PageContainer className="max-w-5xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-sky-600"
          >
            <ArrowLeft size={14} />
            Quay lại
          </Link>

          <button
            type="button"
            onClick={toggleSaveMajor}
            className={`inline-flex items-center gap-1.5 rounded-2xl border px-3.5 py-2 text-xs font-bold backdrop-blur-md transition ${
              isSaved
                ? "border-sky-300 bg-sky-500/15 text-sky-800"
                : "border-white/85 bg-white/60 text-slate-600 hover:bg-white hover:text-sky-700"
            }`}
          >
            {isSaved ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
            {isSaved ? "Đã lưu" : "Lưu ngành"}
          </button>
        </div>

        <Card className="rounded-[32px] p-7 sm:p-9">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-lg bg-sky-500/12 px-2.5 py-0.5 text-xs font-extrabold text-sky-700">
                  Mã {major.code}
                </span>
                {major.category && (
                  <span className="rounded-full border border-white/80 bg-white/70 px-2.5 py-0.5 text-[11px] font-bold text-slate-600">
                    {major.category}
                  </span>
                )}
                <FeasibilityBadge value={major.feasibility} />
                {loading && (
                  <Loader2 size={14} className="animate-spin text-sky-600" />
                )}
              </div>
              <h1 className="mt-3 text-3xl font-black text-slate-900 sm:text-4xl">
                {major.name}
              </h1>
              <p className="mt-1.5 text-xs font-medium text-slate-500">
                {major.university}
              </p>
              {major.fit && (
                <div className="mt-4 inline-flex flex-wrap items-center gap-3 rounded-2xl border border-white/85 bg-white/65 px-3.5 py-2 text-xs font-bold text-slate-700 backdrop-blur-md">
                  <span>
                    Sở thích: <b className="text-sky-600">{major.fit.interest}%</b>
                  </span>
                  <span className="text-slate-300">·</span>
                  <span>
                    Học lực: <b className="text-sky-600">{major.fit.academic}%</b>
                  </span>
                  <span className="text-slate-300">·</span>
                  <span>
                    Nhận thức: <b className="text-cyan-600">{major.fit.cognitive}%</b>
                  </span>
                </div>
              )}
            </div>
            <div className="text-left sm:text-right">
              <span className="text-5xl font-black text-sky-600">
                {major.match}%
              </span>
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Độ tương thích
              </span>
            </div>
          </div>
        </Card>

        <div className="mt-6 grid gap-5 lg:grid-cols-[1.2fr_.8fr]">
          <div className="space-y-5">
            <ExplanationBox
              content={aiExplanationText || major.explanation}
              loading={aiExplaining}
            />
            <GapAnalysisCard gaps={major.gaps} />
          </div>

          <div className="space-y-4">
            {[
              [GraduationCap, "Nội dung đào tạo", studyDescription],
              [BriefcaseBusiness, "Vị trí nghề nghiệp", careerText],
              [BookOpenCheck, "Tổ hợp xét tuyển", blockText],
            ].map(([Icon, title, text]) => (
              <Card key={String(title)} className="rounded-3xl p-5">
                <div className="flex gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-sky-500/12 text-sky-600">
                    <Icon size={19} />
                  </span>
                  <div>
                    <h3 className="text-sm font-extrabold text-slate-900">
                      {String(title)}
                    </h3>
                    <p className="mt-1 text-xs leading-5 text-slate-600">
                      {String(text)}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <Card className="mt-6 flex flex-col justify-between gap-4 rounded-3xl p-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <CircleCheck className="shrink-0 text-sky-600" />
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">
                Trải nghiệm lộ trình 4 tuần ngành {major.name}
              </h3>
            </div>
          </div>
          <Link
            to={`/roadmap?major=${major.code}&name=${encodeURIComponent(major.name)}`}
          >
            <Button icon={ArrowRight}>Mở lộ trình 4 tuần</Button>
          </Link>
        </Card>
      </PageContainer>
    </section>
  )
}
