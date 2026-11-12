import {
  CircleAlert,
  CircleCheck,
  Lightbulb,
  Loader2,
  Sparkles,
  Target,
} from "lucide-react"
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

export function SkillAnalysisCard({
  data,
  loading = false,
}: {
  data: StudentSkillAnalysis | null
  loading?: boolean
}) {
  if (!loading && !data) return null

  return (
    <div className="glass-card rounded-3xl p-6">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-extrabold text-slate-800">
          <Sparkles size={16} className="text-sky-600" />
          Phân tích kỹ năng của bạn
        </div>
        {loading && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/75 px-2.5 py-1 text-[10px] font-bold text-sky-700 ring-1 ring-white/90">
            <Loader2 size={12} className="animate-spin text-sky-600" />
            Đang chấm...
          </span>
        )}
      </div>

      {data ? (
        <>
          <p className="rounded-2xl bg-sky-500/8 px-4 py-3 text-xs font-semibold leading-5 text-slate-700">
            {data.summary}
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wide text-emerald-700">
                <CircleCheck size={13} /> Ưu điểm
              </p>
              <ul className="space-y-1.5">
                {data.strengths.map((item) => (
                  <li
                    key={item.title}
                    className="rounded-xl border border-white/85 bg-white/65 px-3 py-2"
                  >
                    <span className="block text-xs font-bold text-slate-800">
                      {item.title}
                    </span>
                    {item.detail && (
                      <span className="block text-[11px] leading-4 text-slate-600">
                        {item.detail}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wide text-amber-700">
                <CircleAlert size={13} /> Cần cải thiện
              </p>
              <ul className="space-y-1.5">
                {data.weaknesses.map((item) => (
                  <li
                    key={item.title}
                    className="rounded-xl border border-white/85 bg-white/65 px-3 py-2"
                  >
                    <span className="block text-xs font-bold text-slate-800">
                      {item.title}
                    </span>
                    {item.detail && (
                      <span className="block text-[11px] leading-4 text-slate-600">
                        {item.detail}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {data.skill_gaps.length > 0 && (
            <div className="mt-4">
              <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wide text-sky-700">
                <Target size={13} /> Kỹ năng cần bổ sung
              </p>
              <div className="space-y-2">
                {data.skill_gaps.map((gap) => (
                  <div
                    key={gap.skill}
                    className="rounded-xl border border-white/85 bg-white/65 px-3 py-2"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        {gap.skill}
                      </span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                          PRIORITY_STYLE[gap.priority] || PRIORITY_STYLE.MEDIUM
                        }`}
                      >
                        {PRIORITY_LABEL[gap.priority] || "Nên làm"}
                      </span>
                    </div>
                    {gap.why && (
                      <p className="mt-0.5 text-[11px] leading-4 text-slate-600">
                        {gap.why}
                      </p>
                    )}
                    {gap.how_to_improve.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {gap.how_to_improve.map((step) => (
                          <li
                            key={step}
                            className="flex gap-1.5 text-[11px] leading-4 text-slate-700"
                          >
                            <Lightbulb
                              size={11}
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
      ) : (
        <p className="text-xs text-slate-500">
          Hoàn thành bài test để nhận phân tích ưu điểm, điểm cần cải thiện và kỹ
          năng nên bổ sung.
        </p>
      )}
    </div>
  )
}
