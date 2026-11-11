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
  // Chuyển đổi cú pháp **bold** và `code` đơn giản từ Agent sang JSX sạch sẽ
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return tokens.map((tok, i) => {
    if (tok.startsWith("**") && tok.endsWith("**")) {
      return (
        <strong key={i} className="font-extrabold text-slate-900">
          {tok.slice(2, -2)}
        </strong>
      )
    }
    if (tok.startsWith("`") && tok.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded-md bg-sky-500/12 px-1.5 py-0.5 font-mono text-[11px] font-bold text-sky-800"
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
      className="group flex flex-col justify-between rounded-2xl border border-white/85 bg-white/70 p-3.5 shadow-[0_6px_20px_rgba(14,165,233,0.06)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white"
    >
      <div>
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <div className="flex flex-wrap items-center gap-1">
            <span className="inline-flex items-center gap-1 rounded-lg bg-sky-500/12 px-2 py-0.5 text-[10px] font-extrabold text-sky-700">
              {tagLabel} · {major.major_code}
            </span>
            <TrendBadge tier={major.trend_tier} isTrending={major.is_trending} />
          </div>
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
              isTarget
                ? "bg-sky-600 text-white"
                : isUnknown
                  ? "border border-amber-300 bg-amber-50 text-amber-800"
                  : "border border-slate-300 bg-slate-100 text-slate-700"
            }`}
          >
            {isTarget ? (
              <CheckCircle2 className="size-3" />
            ) : isUnknown ? (
              <Compass className="size-3 text-amber-600" />
            ) : (
              <ShieldAlert className="size-3" />
            )}
            {isTarget ? "Đủ điểm (TARGET)" : isUnknown ? "Chưa có điểm" : "Thử thách (REACH)"}
          </span>
        </div>

        <h4 className="mt-2 text-sm font-black text-slate-900 group-hover:text-sky-700">
          {major.major_name}
        </h4>

        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] font-bold text-slate-600">
          <span className="rounded-md bg-slate-100/90 px-2 py-0.5 text-sky-700">
            Hợp {major.overall_match}%
          </span>
          <span className="rounded-md bg-slate-100/90 px-2 py-0.5">
            Sở thích {major.riasec_fit}%
          </span>
          {major.benchmark_cutoff != null && (
            <span className="rounded-md bg-slate-100/90 px-2 py-0.5">
              {major.best_matching_block
                ? `Khối ${major.best_matching_block} (${major.best_block_score ?? "—"}đ)`
                : "Tổ hợp"}{" "}
              · Chuẩn ~{major.benchmark_cutoff}đ
            </span>
          )}
        </div>

        {!isTarget && major.constraint_violations?.length > 0 && (
          <p className="mt-1.5 text-[11px] font-semibold text-slate-500">
            {major.constraint_violations[0]}
          </p>
        )}
      </div>

      <div className="mt-2.5 flex items-center justify-between border-t border-slate-200/60 pt-2 text-[11px] font-extrabold text-sky-600">
        <span>Xem lộ trình & chi tiết</span>
        <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
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

    const dreams = analysis.dream_majors || []
    const subs = analysis.recommended_substitutes || []
    const bridges = analysis.bridge_majors || []

    pushUnique(dreams[0], dreams[0]?.role_tag === "TOP_TEST" ? "Hợp nhất" : "Ước mơ")
    if (subs.length > 0) {
      pushUnique(subs[0], "Thay thế vừa sức")
    }
    if (analysis.alignment_status === "TRAIT_DIVERGENCE" && bridges.length > 0) {
      pushUnique(bridges[0], "Cầu nối")
    }
    dreams.slice(1).forEach((m) =>
      pushUnique(m, m.role_tag === "TOP_TEST" ? "Hợp nhất" : "Ước mơ"),
    )
    subs.slice(1).forEach((m) => pushUnique(m, "Thay thế vừa sức"))
    bridges.forEach((m) => {
      if (combinedTiles.length < 3) {
        pushUnique(m, "Cầu nối")
      }
    })
  }

  const statusTone =
    analysis?.alignment_status === "ALIGNED_AND_ELIGIBLE"
      ? "border-sky-300/80 bg-sky-500 text-white"
      : analysis?.alignment_status === "PASSION_MATCH_SCORE_GAP"
        ? "border-sky-300/80 bg-sky-100 text-sky-900"
        : analysis?.alignment_status === "TRAIT_DIVERGENCE"
          ? "border-cyan-300/80 bg-cyan-50 text-cyan-900"
          : analysis?.alignment_status === "NEED_ACADEMIC_DATA"
            ? "border-amber-300/80 bg-amber-50 text-amber-900"
            : "border-slate-200 bg-slate-100 text-slate-700"

  return (
    <div className="mb-6 rounded-[28px] border border-white/85 bg-white/55 p-5 sm:p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_16px_44px_rgba(14,165,233,0.1)] backdrop-blur-2xl">
      {/* Header Row */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-sm">
            {isAnalyzing ? (
              <Loader2 className="size-5 animate-spin" />
            ) : (
              <Bot className="size-5" />
            )}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-extrabold uppercase tracking-wider text-sky-700">
                <Sparkles className="size-3.5" />
                AI Agent Đối chiếu Nguyện vọng
              </span>
              {analysis && (
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] font-extrabold ${statusTone}`}
                >
                  {analysis.alignment_label}
                </span>
              )}
              {analysis?.is_llm_enriched && (
                <span className="rounded-full border border-sky-200 bg-white/80 px-2 py-0.5 text-[10px] font-bold text-sky-700">
                  AI Agent Tổng hợp
                </span>
              )}
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold text-slate-600">
              <span>
                Nguyện vọng:{" "}
                <strong className="text-slate-900">
                  {analysis?.dream_job ||
                    currentAspiration?.dreamJob ||
                    "Chưa nhập nghề mơ ước"}
                </strong>
              </span>
              {analysis && (
                <span>
                  · Trắc nghiệm:{" "}
                  <strong className="text-sky-700">
                    {analysis.holland_code}
                  </strong>{" "}
                  ({analysis.best_block_summary})
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center">
          {analysis && (
            <div className="rounded-xl border border-sky-200/80 bg-white/80 px-3 py-1.5 text-center backdrop-blur-md">
              <span className="text-[10px] font-bold uppercase text-slate-400">
                Đối chiếu
              </span>
              <p className="text-sm font-black text-sky-700">
                {analysis.alignment_score}%
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-sky-200/90 bg-white/80 px-3 py-2 text-xs font-extrabold text-sky-700 transition hover:border-sky-400 hover:bg-white cursor-pointer"
          >
            {editing ? <X className="size-3.5" /> : <Edit3 className="size-3.5" />}
            {editing ? "Đóng" : "Đổi nghề mơ ước"}
          </button>
        </div>
      </div>

      {/* Inline Aspiration Editor */}
      {editing && (
        <div className="mt-4 rounded-2xl border border-sky-200/80 bg-white/80 p-3.5 backdrop-blur-xl">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Compass className="absolute left-3 top-3 size-4 text-sky-500" />
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
                placeholder="Nhập nghề nghiệp bạn mong muốn (VD: Kỹ sư AI, Bác sĩ, Marketing, Kế toán...)"
                className="h-10 w-full rounded-xl border border-sky-200 bg-white pl-9 pr-3 text-xs sm:text-sm font-semibold text-slate-900 outline-none focus:border-sky-500"
              />
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => handleApplyDreamJob(draftJob)}
              className="inline-flex h-10 items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-sky-500 to-cyan-500 px-4 text-xs font-extrabold text-white shadow-sm transition hover:opacity-95 disabled:opacity-50 cursor-pointer"
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
                className="rounded-lg border border-sky-100 bg-sky-50/80 px-2.5 py-1 text-[11px] font-bold text-sky-800 transition hover:bg-sky-500 hover:text-white cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Agent Verdict + Key Takeaways */}
      {analysis ? (
        <div className="mt-4 space-y-4">
          <div className="rounded-2xl border border-white/90 bg-white/70 p-4 backdrop-blur-xl">
            <p className="text-xs sm:text-sm leading-relaxed text-slate-700">
              {renderFormattedInline(analysis.agent_verdict)}
            </p>
            {analysis.key_takeaways?.length > 0 && (
              <ul className="mt-2.5 space-y-1.5 border-t border-slate-200/60 pt-2.5">
                {analysis.key_takeaways.map((tk, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs leading-snug text-slate-600"
                  >
                    <GitBranch className="mt-0.5 size-3.5 shrink-0 text-sky-600" />
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
        <div className="mt-3 flex items-center justify-between rounded-2xl border border-white/80 bg-white/60 px-4 py-3 text-xs font-semibold text-slate-600">
          <span>
            {isAnalyzing
              ? "AI Agent đang đối chiếu nguyện vọng nghề nghiệp với kết quả bài test 435 ngành..."
              : "Bấm \"Đổi nghề mơ ước\" để AI Agent đối chiếu nguyện vọng nghề nghiệp với điểm chuẩn & hồ sơ RIASEC của bạn."}
          </span>
        </div>
      )}
    </div>
  )
}
