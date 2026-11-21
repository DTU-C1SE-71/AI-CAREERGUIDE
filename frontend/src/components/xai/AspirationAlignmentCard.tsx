import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Compass,
  Edit3,
  Loader2,
  Sparkles,
  Target,
  X,
} from "lucide-react"
import { useRef, useState } from "react"
import { Link } from "react-router"
import type {
  AspirationAnalysisPayload,
  AspirationMajorBrief,
  CareerAspirationInput,
} from "../../types/assessment"
import type { AspirationAIAnalysis, AspirationMajorSuggestion } from "../../types/insight"
import { formatBlockWithSubjects } from "../../utils"
import { QUICK_DREAM_JOBS } from "../assessment/aspirationOptions"
import { TrendBadge } from "./TrendBadge"

const FIT_BADGE_STYLE: Record<AspirationAIAnalysis["fit_level"], string> = {
  HIGH: "border-emerald-200 bg-emerald-50 text-emerald-700",
  MEDIUM: "border-sky-200 bg-sky-50 text-sky-700",
  LOW: "border-amber-200 bg-amber-50 text-amber-800",
  UNKNOWN: "border-slate-200 bg-slate-100 text-slate-700",
}

function MajorBriefTile({
  major,
  verified = true,
}: {
  major: AspirationMajorBrief
  verified?: boolean
}) {
  const readiness = verified ? major.readiness : undefined
  const status = readiness?.status ?? "UNKNOWN"
  const riasecColor =
    major.riasec_fit == null
      ? ""
      : major.riasec_fit >= 70
        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
        : major.riasec_fit >= 45
          ? "border-sky-200 bg-sky-50 text-sky-800"
          : "border-rose-200 bg-rose-50 text-rose-800"

  const statusTone =
    status === "READY_REFERENCE"
      ? "bg-emerald-50 text-emerald-700"
      : status === "NEEDS_IMPROVEMENT"
        ? "bg-amber-50 text-amber-800"
        : "bg-slate-100 text-slate-600"

  const statusLabel =
    status === "READY_REFERENCE"
      ? "Đạt mốc tham chiếu"
      : status === "NEEDS_IMPROVEMENT"
        ? "Cần cải thiện điểm"
        : "Chưa đủ dữ liệu"

  const warningText = verified ? major.subfacet_note || major.trait_warning : null

  return (
    <Link
      to={`/majors/${major.major_code}`}
      className="group flex min-w-0 flex-col justify-between rounded-2xl border border-slate-200 bg-white/85 p-4 transition hover:border-sky-300 hover:shadow-md"
    >
      <div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-sky-700">Mã {major.major_code}</span>
          <TrendBadge tier={major.trend_tier} isTrending={major.is_trending} />
          <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${statusTone}`}>
            {statusLabel}
          </span>
        </div>

        <h4 className="mt-2 font-bold text-slate-900">{major.major_name}</h4>

        {verified && (major.overall_match != null || major.riasec_fit != null) && (
          <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-semibold">
            {major.overall_match != null && (
              <span className="rounded-lg border border-sky-200 bg-sky-50 px-2 py-0.5 text-sky-800">
                Tổng hợp: {major.overall_match}%
              </span>
            )}
            {major.riasec_fit != null && (
              <span className={`rounded-lg border px-2 py-0.5 ${riasecColor}`}>
                Holland: {major.riasec_fit}%
              </span>
            )}
          </div>
        )}

        {warningText && (
          <div className="mt-2.5 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50/90 px-3 py-2 text-xs text-amber-900">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
            <span>{warningText}</span>
          </div>
        )}

        {readiness?.block && (
          <p className="mt-2.5 text-xs font-medium text-slate-600">
            {formatBlockWithSubjects(readiness.block, { short: true })} · Điểm{" "}
            <span className="font-bold text-slate-800">{readiness.block_score ?? "—"}</span>
            {readiness.benchmark_cutoff != null && (
              <>
                {" "}
                / Mốc <span className="font-bold text-slate-800">{readiness.benchmark_cutoff}</span>
              </>
            )}
          </p>
        )}

        {!readiness?.block && readiness?.missing_subjects?.length ? (
          <p className="mt-2 text-xs text-amber-800">
            Cần bổ sung điểm: {readiness.missing_subjects.join(", ")}
          </p>
        ) : null}
      </div>

      <span className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs font-semibold text-sky-700 group-hover:text-sky-800">
        Xem chi tiết ngành <ArrowUpRight className="size-4" />
      </span>
    </Link>
  )
}

function SuggestionMajorCard({ suggestion }: { suggestion: AspirationMajorSuggestion }) {
  return (
    <Link
      to={`/majors/${suggestion.major_code}`}
      className="group flex min-w-0 flex-col justify-between rounded-2xl border border-slate-200 bg-white/85 p-4 transition hover:border-sky-300 hover:shadow-md"
    >
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="font-semibold text-sky-700">Mã {suggestion.major_code}</span>
          {suggestion.match_score != null && (
            <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-bold text-sky-700">
              Khớp {suggestion.match_score}%
            </span>
          )}
        </div>
        <h4 className="mt-2 font-bold text-slate-900">{suggestion.major_name}</h4>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{suggestion.reason}</p>
      </div>
      <span className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs font-semibold text-sky-700 group-hover:text-sky-800">
        Xem chi tiết ngành <ArrowUpRight className="size-4" />
      </span>
    </Link>
  )
}

interface AspirationAlignmentCardProps {
  analysis: AspirationAnalysisPayload | null
  aiAnalysis?: AspirationAIAnalysis | null
  aiLoading?: boolean
  aiError?: string
  currentAspiration?: CareerAspirationInput
  onUpdateAspiration: (next: CareerAspirationInput) => Promise<void>
  isAnalyzing?: boolean
  readOnly?: boolean
}

export function AspirationAlignmentCard({
  analysis,
  aiAnalysis = null,
  aiLoading = false,
  aiError = "",
  currentAspiration,
  onUpdateAspiration,
  isAnalyzing = false,
  readOnly = false,
}: AspirationAlignmentCardProps) {
  const [editing, setEditing] = useState(false)
  const [draftJob, setDraftJob] = useState(
    currentAspiration?.dreamJob || aiAnalysis?.dream_job || analysis?.dream_job || "",
  )
  const [saveError, setSaveError] = useState("")
  const [saving, setSaving] = useState(false)
  const editVersion = useRef(0)

  const setDraft = (value: string) => {
    editVersion.current += 1
    setDraftJob(value)
    setSaveError("")
  }

  const apply = async (job: string) => {
    if (saving || readOnly) return
    const version = editVersion.current
    setSaving(true)
    setSaveError("")
    try {
      await onUpdateAspiration({ ...currentAspiration, dreamJob: job.trim(), desiredField: "" })
      if (version === editVersion.current) setEditing(false)
    } catch {
      setSaveError("Chưa lưu được nguyện vọng. Nội dung nháp vẫn được giữ; hãy thử lại.")
    } finally {
      setSaving(false)
    }
  }

  const modern = Boolean(analysis?.match_status)
  const goals = isAnalyzing ? [] : (analysis?.dream_majors ?? [])
  const current =
    modern && !isAnalyzing
      ? (analysis?.current_options ?? []).filter((m) => m.readiness?.status === "READY_REFERENCE")
      : []
  const goalCodes = new Set(goals.map((m) => m.major_code))
  const fallbackAlternatives = current.filter((m) => !goalCodes.has(m.major_code)).slice(0, 3)
  const betterMajors = aiAnalysis?.better_majors ?? []
  const activeDreamJob =
    currentAspiration?.dreamJob || aiAnalysis?.dream_job || analysis?.dream_job || ""

  return (
    <section className="glass-card min-w-0 overflow-hidden rounded-2xl p-4 sm:rounded-3xl sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Compass className="size-5 text-sky-600" />
            Phân tích nguyện vọng với AI
          </h2>
          <p className="mt-1 break-words text-sm text-slate-600">
            Nghề mơ ước:{" "}
            <span className="font-bold text-slate-900">
              {activeDreamJob || "Chưa chọn nghề mong muốn"}
            </span>
          </p>
        </div>

        {!readOnly && (
          <button
            type="button"
            disabled={saving}
            onClick={() => {
              if (!editing) setDraft(activeDreamJob)
              setEditing(!editing)
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-white px-3.5 py-2 text-xs font-bold text-sky-700 transition hover:bg-sky-50"
          >
            {editing ? <X className="size-4" /> : <Edit3 className="size-4" />}
            {editing ? "Đóng" : "Đổi nghề mơ ước"}
          </button>
        )}
      </div>

      {editing && (
        <form
          className="mt-4 rounded-2xl border border-sky-200 bg-sky-50/50 p-4"
          onSubmit={(event) => {
            event.preventDefault()
            void apply(draftJob)
          }}
        >
          <label htmlFor="aspiration-edit" className="text-sm font-semibold text-slate-800">
            Nghề mong muốn
          </label>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              id="aspiration-edit"
              name="dreamJob"
              disabled={saving}
              value={draftJob}
              onChange={(e) => setDraft(e.target.value)}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-sky-500"
              placeholder="Ví dụ: Bác sĩ Y khoa, Kỹ sư phần mềm..."
            />
            <button
              type="submit"
              disabled={saving || isAnalyzing || aiLoading}
              className="flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:opacity-50"
            >
              {saving && <Loader2 className="size-4 animate-spin" />}
              {saveError ? "Thử lại" : "Lưu & phân tích lại"}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {QUICK_DREAM_JOBS.map((chip) => (
              <button
                key={chip.label}
                type="button"
                disabled={saving}
                onClick={() => setDraft(chip.dreamJob)}
                className="rounded-lg border border-sky-200 bg-white px-2.5 py-1 text-xs font-medium text-sky-700 hover:bg-sky-50"
              >
                {chip.label}
              </button>
            ))}
          </div>
          {saveError && (
            <p role="alert" className="mt-3 text-sm text-rose-700">
              {saveError}
            </p>
          )}
        </form>
      )}

      <div className="mt-4 space-y-5">
        {(isAnalyzing || aiLoading) && (
          <div
            role="status"
            className="flex items-center gap-3 rounded-2xl border border-sky-200 bg-sky-50/70 px-4 py-4 text-sm font-semibold text-sky-900"
          >
            <Loader2 className="size-5 shrink-0 animate-spin text-sky-600" />
            <span>AI đang đối chiếu nghề mơ ước với sở thích Holland và điểm học tập...</span>
          </div>
        )}

        {aiError && !aiLoading && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-800">
            {aiError}
          </p>
        )}

        {!aiLoading && aiAnalysis && (
          <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${
                    FIT_BADGE_STYLE[aiAnalysis.fit_level] || FIT_BADGE_STYLE.UNKNOWN
                  }`}
                >
                  <Sparkles className="size-3.5" />
                  {aiAnalysis.fit_label}
                </span>
              </div>

              {aiAnalysis.cached ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
                  <CheckCircle2 className="size-3" />
                  Đã lưu · 0 token
                </span>
              ) : aiAnalysis.is_ai_generated ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-bold text-sky-700">
                  <Sparkles className="size-3" />
                  AI vừa phân tích
                </span>
              ) : null}
            </div>

            <p className="mt-3 text-sm leading-relaxed text-slate-700">{aiAnalysis.summary}</p>

            {(aiAnalysis.reasons_fit.length > 0 || aiAnalysis.reasons_gap.length > 0) && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/40 p-3.5">
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-700">
                    <CheckCircle2 className="size-3.5" /> Điểm phù hợp
                  </p>
                  {aiAnalysis.reasons_fit.length > 0 ? (
                    <ul className="space-y-2">
                      {aiAnalysis.reasons_fit.map((item) => (
                        <li key={item.title} className="text-xs leading-relaxed text-slate-700">
                          <span className="block font-bold text-slate-900">{item.title}</span>
                          {item.detail}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">Chưa ghi nhận điểm khớp nổi bật.</p>
                  )}
                </div>

                <div className="rounded-xl border border-amber-200/80 bg-amber-50/40 p-3.5">
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-800">
                    <AlertTriangle className="size-3.5" /> Điểm cần cân nhắc
                  </p>
                  {aiAnalysis.reasons_gap.length > 0 ? (
                    <ul className="space-y-2">
                      {aiAnalysis.reasons_gap.map((item) => (
                        <li key={item.title} className="text-xs leading-relaxed text-slate-700">
                          <span className="block font-bold text-slate-900">{item.title}</span>
                          {item.detail}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">Không phát hiện trở ngại lớn.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {!isAnalyzing && modern && analysis?.match_status === "AMBIGUOUS" && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900">
              Nguyện vọng khớp nhiều hướng nghề. Chọn một nghề để đối chiếu:
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {analysis.intent_candidates?.map((candidate) => (
                <button
                  key={candidate.id}
                  type="button"
                  disabled={readOnly || saving || isAnalyzing}
                  onClick={() => {
                    setDraft(candidate.canonicalDreamJob)
                    setEditing(true)
                    void apply(candidate.canonicalDreamJob)
                  }}
                  className="rounded-lg border border-amber-200 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100/60 disabled:opacity-50"
                >
                  {candidate.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {goals.length > 0 && (
          <section>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
              Ngành gắn với nghề mơ ước
            </h3>
            <div className="mt-2.5 grid gap-3 sm:grid-cols-2">
              {goals.slice(0, 2).map((major) => (
                <MajorBriefTile key={major.major_code} major={major} verified={modern} />
              ))}
            </div>
          </section>
        )}

        <section>
          <div className="flex items-center gap-2">
            <Target className="size-4 text-sky-600" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-700">
              Gợi ý các ngành phù hợp hơn với hồ sơ của bạn
            </h3>
          </div>
          {betterMajors.length > 0 ? (
            <div className="mt-2.5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {betterMajors.map((item) => (
                <SuggestionMajorCard key={item.major_code} suggestion={item} />
              ))}
            </div>
          ) : fallbackAlternatives.length > 0 ? (
            <div className="mt-2.5 grid gap-3 sm:grid-cols-2">
              {fallbackAlternatives.map((major) => (
                <MajorBriefTile key={major.major_code} major={major} verified={modern} />
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">
              {aiLoading || isAnalyzing
                ? "Đang tìm các ngành thay thế phù hợp nhất..."
                : "Nhập nghề mơ ước và hoàn thành trắc nghiệm để AI đề xuất các ngành phù hợp hơn."}
            </p>
          )}
        </section>
      </div>
    </section>
  )
}
