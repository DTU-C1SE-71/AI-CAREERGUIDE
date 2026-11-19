import {
  ChevronDown,
  ChevronUp,
  CircleAlert,
  CircleCheck,
  Lightbulb,
  Loader2,
  Sparkles,
  Target,
} from "lucide-react"
import { useState } from "react"
import type { StudentSkillAnalysis } from "../../types/insight"

const PRIORITY_STYLE: Record<string, string> = {
  HIGH: "bg-rose-50 text-rose-700 border-rose-200",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
  LOW: "bg-sky-50 text-sky-700 border-sky-200",
}

const PRIORITY_LABEL: Record<string, string> = {
  HIGH: "Ưu tiên cao",
  MEDIUM: "Nên làm",
  LOW: "Bổ trợ",
}

function formatSkillSummary(summary: unknown): string {
  if (!summary) return ""
  if (Array.isArray(summary)) {
    return summary.filter(Boolean).map((s) => String(s).trim()).join(" ")
  }
  if (typeof summary === "string") {
    const trimmed = summary.trim()
    if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
      try {
        const parsed = JSON.parse(trimmed.replace(/'/g, '"'))
        if (Array.isArray(parsed)) {
          return parsed.filter(Boolean).map((s) => String(s).trim()).join(" ")
        }
      } catch {
        return trimmed.slice(1, -1).replace(/['"]/g, "").trim()
      }
    }
    return trimmed
  }
  return String(summary)
}

export function SkillAnalysisCard({
  data,
  loading = false,
}: {
  data: StudentSkillAnalysis | null
  loading?: boolean
}) {
  const [showAllGaps, setShowAllGaps] = useState(false)
  if (!loading && !data) return null

  const allGaps = data?.skill_gaps ?? []
  const visibleGaps = showAllGaps ? allGaps : allGaps.slice(0, 2)

  return (
    <div className="glass-card min-w-0 overflow-hidden rounded-2xl p-4 sm:rounded-3xl sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
          <Sparkles size={16} className="text-sky-600" />
          <span>Phân tích kỹ năng theo hồ sơ</span>
        </div>
        {loading ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">
            <Loader2 size={13} className="animate-spin text-sky-600" />
            AI đang phân tích...
          </span>
        ) : data?.cached ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-700">
            <CircleCheck size={12} />
            Đã tải từ CSDL · 0 token
          </span>
        ) : data?.is_ai_generated ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-bold text-sky-700">
            <Sparkles size={12} />
            AI vừa phân tích &amp; đã lưu
          </span>
        ) : null}
      </div>

      {data ? (
        <>
          <p className="rounded-2xl border border-sky-100 bg-sky-50/50 px-4 py-3 text-sm leading-relaxed text-slate-700">
            {formatSkillSummary(data.summary)}
          </p>

          {!data.strengths.length && !data.weaknesses.length && <p className="mt-3 text-sm text-slate-600">Chưa có đủ bằng chứng để xác định điểm mạnh hoặc điểm cần cải thiện. Điểm học tập và phong cách tự khai không chứng minh mức thành thạo kỹ năng.</p>}
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <div>
              <p className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-700">
                <CircleCheck size={14} /> Dữ liệu cho thấy điểm mạnh
              </p>
              <ul className="space-y-2">
                {data.strengths.map((item) => (
                  <li
                    key={item.title}
                    className="min-w-0 rounded-xl border border-slate-200/80 bg-white/70 p-3"
                  >
                    <span className="block text-sm font-bold text-slate-800">
                      {item.title}
                    </span>
                    {item.detail && (
                      <span className="mt-1 block text-xs leading-relaxed text-slate-600">
                        {item.detail}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-700">
                <CircleAlert size={14} /> Điểm cần bồi dưỡng
              </p>
              <ul className="space-y-2">
                {data.weaknesses.map((item) => (
                  <li
                    key={item.title}
                    className="min-w-0 rounded-xl border border-slate-200/80 bg-white/70 p-3"
                  >
                    <span className="block text-sm font-bold text-slate-800">
                      {item.title}
                    </span>
                    {item.detail && (
                      <span className="mt-1 block text-xs leading-relaxed text-slate-600">
                        {item.detail}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {allGaps.length > 0 && (
            <div className="mt-5 border-t border-slate-100 pt-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-700">
                  <Target size={14} /> Kỹ năng cần bổ sung ({allGaps.length})
                </p>
                {allGaps.length > 2 && (
                  <button
                    type="button"
                    onClick={() => setShowAllGaps((prev) => !prev)}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-sky-700 transition hover:border-sky-300 hover:bg-sky-50"
                  >
                    {showAllGaps ? (
                      <>
                        Thu gọn <ChevronUp size={13} />
                      </>
                    ) : (
                      <>
                        Xem thêm {allGaps.length - 2} kỹ năng <ChevronDown size={13} />
                      </>
                    )}
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {visibleGaps.map((gap) => (
                  <div
                    key={gap.skill}
                    className="rounded-xl border border-slate-200/80 bg-white/80 p-3.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-bold text-slate-800">
                        {gap.skill}
                      </span>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                          PRIORITY_STYLE[gap.priority] || PRIORITY_STYLE.MEDIUM
                        }`}
                      >
                        {PRIORITY_LABEL[gap.priority] || "Nên làm"}
                      </span>
                    </div>
                    {gap.why && (
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                        {gap.why}
                      </p>
                    )}
                    {gap.how_to_improve && gap.how_to_improve.length > 0 && (
                      <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
                        {gap.how_to_improve.slice(0, 2).map((step) => (
                          <li
                            key={step}
                            className="flex items-start gap-1.5 text-xs text-slate-700"
                          >
                            <Lightbulb
                              size={12}
                              className="mt-0.5 shrink-0 text-sky-500"
                            />
                            <span>{step}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : loading ? (
        <div
          role="status"
          className="flex flex-col items-center justify-center gap-2.5 rounded-2xl border border-sky-200/80 bg-sky-50/50 px-4 py-8 text-center"
        >
          <span className="grid size-10 place-items-center rounded-2xl bg-sky-600 text-white shadow-sm">
            <Loader2 size={20} className="animate-spin" />
          </span>
          <p className="text-sm font-extrabold text-slate-900">
            AI đang phân tích hồ sơ &amp; kỹ năng của bạn...
          </p>
          <p className="max-w-md text-xs leading-relaxed text-slate-600">
            Kết quả được lưu cache theo hồ sơ để những lần truy cập sau mở ngay lập tức.
          </p>
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          Hoàn thành bài đánh giá để nhận phân tích chi tiết kỹ năng của bạn.
        </p>
      )}
    </div>
  )
}
