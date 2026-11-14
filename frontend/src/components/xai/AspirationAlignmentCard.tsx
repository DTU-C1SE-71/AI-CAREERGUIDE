import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Compass,
  Edit3,
  GitBranch,
  Loader2,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react"
import { useEffect, useState, type ReactNode } from "react"
import { Link } from "react-router"
import type {
  AspirationAnalysisPayload,
  AspirationMajorBrief,
  CareerAspirationInput,
} from "../../types/assessment"
import { formatBlockWithSubjects } from "../../utils"
import { TrendBadge } from "./TrendBadge"

const QUICK_ASPIRATION_CHIPS = [
  "Kỹ sư AI & Phần mềm",
  "Bác sĩ Y khoa",
  "Marketing số",
  "Tài chính & Fintech",
  "Thiết kế đồ họa UI/UX",
  "Vi mạch & Tự động hóa",
  "Sư phạm & Tâm lý học",
  "Luật sư & Ngoại giao",
]

function renderFormattedInline(text: string): ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return tokens.map((tok, i) => {
    if (tok.startsWith("**") && tok.endsWith("**")) {
      return (
        <strong key={i} className="font-bold text-slate-900">
          {tok.slice(2, -2)}
        </strong>
      )
    }
    if (tok.startsWith("`") && tok.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded-md bg-sky-50 px-1.5 py-0.5 font-mono text-xs font-semibold text-sky-800"
        >
          {tok.slice(1, -1)}
        </code>
      )
    }
    return <span key={i}>{tok}</span>
  })
}

function MajorBriefTile({
  major,
  tagLabel,
}: {
  major: AspirationMajorBrief
  tagLabel: string
}) {
  const isTarget = major.feasibility_tier === "TARGET"
  const isUnknown = major.feasibility_tier === "UNKNOWN"
  return (
    <Link
      to={`/majors/${major.major_code}`}
      className="group flex flex-col justify-between rounded-2xl border border-slate-200/85 bg-white/80 p-4 transition hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white hover:shadow-md"
    >
      <div>
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">
              {tagLabel} · Mã {major.major_code}
            </span>
            <TrendBadge tier={major.trend_tier} isTrending={major.is_trending} />
          </div>
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              isTarget
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : isUnknown
                  ? "border border-amber-200 bg-amber-50 text-amber-800"
                  : "border border-slate-200 bg-slate-50 text-slate-700"
            }`}
          >
            {isTarget ? (
              <CheckCircle2 className="size-3.5 text-emerald-600" />
            ) : isUnknown ? (
              <Compass className="size-3.5 text-amber-600" />
            ) : (
              <ShieldAlert className="size-3.5 text-slate-500" />
            )}
            {isTarget ? "Khả thi cao" : isUnknown ? "Chưa có điểm" : "Thử thách"}
          </span>
        </div>

        <h4 className="mt-2.5 text-base font-bold text-slate-900 group-hover:text-sky-700">
          {major.major_name}
        </h4>

        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs font-medium text-slate-600">
          <span className="rounded-md bg-slate-100 px-2 py-0.5 font-bold tabular-nums text-sky-700">
            Hợp {major.overall_match}%
          </span>
          <span className="rounded-md bg-slate-100 px-2 py-0.5 font-medium tabular-nums">
            Sở thích {major.riasec_fit}%
          </span>
          {major.benchmark_cutoff != null && (
            <span className="rounded-md bg-slate-100 px-2 py-0.5">
              {major.best_matching_block
                ? `${formatBlockWithSubjects(major.best_matching_block, { short: true })} (${major.best_block_score ?? "—"}đ)`
                : "Tổ hợp"}{" "}
              · Chuẩn ~{major.benchmark_cutoff}đ
            </span>
          )}
        </div>

        {!isTarget && major.constraint_violations?.length > 0 && (
          <p className="mt-2 text-xs font-medium text-slate-500">
            {major.constraint_violations[0]}
          </p>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 text-xs font-bold text-sky-600">
        <span>Xem lộ trình & chi tiết</span>
        <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </div>
    </Link>
  )
}

interface AspirationAlignmentCardProps {
  analysis: AspirationAnalysisPayload | null
  currentAspiration?: CareerAspirationInput
  onUpdateAspiration: (next: CareerAspirationInput) => Promise<void> | void
  isAnalyzing?: boolean
}

export function AspirationAlignmentCard({
  analysis,
  currentAspiration,
  onUpdateAspiration,
  isAnalyzing = false,
}: AspirationAlignmentCardProps) {
  const [editing, setEditing] = useState(false)
  const [draftJob, setDraftJob] = useState(
    currentAspiration?.dreamJob || analysis?.dream_job || "",
  )

  useEffect(() => {
    setDraftJob(currentAspiration?.dreamJob || "")
  }, [currentAspiration?.dreamJob])

  const handleApplyDreamJob = async (jobText: string) => {
    const trimmed = jobText.trim()
    await onUpdateAspiration({
      ...(currentAspiration || {}),
      dreamJob: trimmed,
    })
    setEditing(false)
  }

  const combinedTiles: Array<{
    major: AspirationMajorBrief
    tagLabel: string
  }> = []

  if (analysis) {
    const pushUnique = (m: AspirationMajorBrief | undefined, tagLabel: string) => {
      if (!m) return
      if (!combinedTiles.some((t) => t.major.major_code === m.major_code)) {
        combinedTiles.push({ major: m, tagLabel })
      }
    }

    ;(analysis.dream_majors || []).forEach((m) => pushUnique(m, "Nguyện vọng 1"))
    ;(analysis.recommended_substitutes || []).forEach((m) =>
      pushUnique(m, "Dự phòng vừa sức"),
    )
    ;(analysis.bridge_majors || []).forEach((m) =>
      pushUnique(m, "Ngành bắc cầu"),
    )
  }

  const statusTone =
    analysis?.alignment_status === "ALIGNED_AND_ELIGIBLE"
      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
      : analysis?.alignment_status === "PASSION_MATCH_SCORE_GAP"
        ? "bg-amber-50 text-amber-800 border-amber-200"
        : "bg-sky-50 text-sky-800 border-sky-200"

  return (
    <div className="glass-card rounded-2xl p-5 sm:rounded-3xl sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3.5">
          <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-50 text-sky-600">
            {isAnalyzing ? (
              <Loader2 className="size-5 animate-spin" />
            ) : (
              <Bot className="size-5" />
            )}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-700">
                <Sparkles className="size-3.5" />
                Đối chiếu Nguyện vọng Cá nhân
              </span>
              {analysis && (
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusTone}`}
                >
                  {analysis.alignment_label}
                </span>
              )}
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
              <span>
                Nghề mơ ước:{" "}
                <strong className="font-bold text-slate-900">
                  {analysis?.dream_job ||
                    currentAspiration?.dreamJob ||
                    "Chưa nhập nghề mơ ước"}
                </strong>
              </span>
              {analysis && (
                <span>
                  · RIASEC:{" "}
                  <strong className="font-bold text-sky-700">
                    {analysis.holland_code}
                  </strong>{" "}
                  · Tổ hợp:{" "}
                  <span className="font-semibold text-slate-800">
                    {formatBlockWithSubjects(analysis.best_block_summary, { short: true })}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-center">
          {analysis && (
            <div className="rounded-xl border border-sky-200/80 bg-white px-3.5 py-1.5 text-center">
              <span className="block text-[11px] font-semibold uppercase text-slate-400">
                Độ phù hợp
              </span>
              <p className="text-base font-black tabular-nums text-sky-700">
                {analysis.alignment_score}%
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-sky-200 bg-white px-3.5 py-2 text-xs font-bold text-sky-700 transition hover:border-sky-300 hover:bg-sky-50"
          >
            {editing ? <X className="size-3.5" /> : <Edit3 className="size-3.5" />}
            {editing ? "Đóng" : "Đổi nghề mơ ước"}
          </button>
        </div>
      </div>

      {/* Inline Aspiration Editor */}
      {editing && (
        <div className="mt-4 rounded-2xl border border-sky-200/80 bg-sky-50/50 p-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Compass className="absolute left-3.5 top-3 size-4 text-sky-500" />
              <input
                type="text"
                value={draftJob}
                onChange={(e) => setDraftJob(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleApplyDreamJob(draftJob)
                  }
                }}
                placeholder="Nhập nghề nghiệp bạn mong muốn (VD: Kỹ sư AI, Bác sĩ, Marketing...)"
                className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm font-medium text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
              />
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => handleApplyDreamJob(draftJob)}
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl bg-sky-600 px-4 text-xs font-bold text-white transition hover:bg-sky-700 disabled:opacity-50"
            >
              {isAnalyzing ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              Phân tích lại
            </button>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {QUICK_ASPIRATION_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => {
                  setDraftJob(chip)
                  handleApplyDreamJob(chip)
                }}
                className="rounded-lg border border-sky-200/70 bg-white px-2.5 py-1 text-xs font-medium text-sky-800 transition hover:bg-sky-600 hover:text-white"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Agent Verdict & Key Takeaways */}
      {analysis ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-4 sm:p-5">
            <p className="text-sm leading-relaxed text-slate-700">
              {renderFormattedInline(analysis.agent_verdict)}
            </p>
            {analysis.key_takeaways?.length > 0 && (
              <ul className="mt-3 space-y-2 border-t border-slate-100 pt-3">
                {analysis.key_takeaways.map((tk, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 text-xs text-slate-600 sm:text-sm"
                  >
                    <GitBranch className="mt-0.5 size-4 shrink-0 text-sky-600" />
                    <span>{renderFormattedInline(tk)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Recommended Dream / Substitute / Bridge Majors Grid */}
          {combinedTiles.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {combinedTiles.slice(0, 3).map(({ major, tagLabel }) => (
                <MajorBriefTile
                  key={`${tagLabel}-${major.major_code}`}
                  major={major}
                  tagLabel={tagLabel}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-4 flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white/60 px-4 py-3 text-xs text-slate-600">
          <span>
            {isAnalyzing
              ? "Hệ thống đang đối chiếu nguyện vọng nghề nghiệp với 435 ngành..."
              : 'Bấm "Đổi nghề mơ ước" để hệ thống đối chiếu nguyện vọng nghề nghiệp với điểm số và hồ sơ RIASEC của bạn.'}
          </span>
        </div>
      )}
    </div>
  )
}
