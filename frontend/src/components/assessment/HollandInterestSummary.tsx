import type { InterestEvidence, RiasecKey } from "../../types/assessment"

const GROUPS: Array<[RiasecKey, string]> = [
  ["R", "Thực tế"], ["I", "Nghiên cứu"], ["A", "Nghệ thuật"],
  ["S", "Xã hội"], ["E", "Quản lý"], ["C", "Nghiệp vụ"],
]

export function HollandInterestSummary({ evidence }: { evidence: InterestEvidence }) {
  const complete = evidence.status === "COMPLETE" || evidence.status === "NON_DISCRIMINATING"
  const known = evidence.groups.filter(g => g.percent !== null)
  const highest = Math.max(...known.map(g => g.percent ?? 0))
  const leaders = known.filter(g => g.percent === highest).map(g => g.code)
  return (
    <section aria-label="Sáu nhóm sở thích Holland" className="rounded-2xl border border-sky-100 bg-white/80 p-4 sm:p-5">
      <h3 className="text-sm font-bold text-slate-900">Sáu nhóm sở thích Holland</h3>
      <p className="mt-1 text-xs leading-relaxed text-slate-600">
        {complete ? "Đã trả lời đủ 30 câu." : evidence.status === "LEGACY_UNVERIFIED" ? "Kết quả cũ chưa có số câu để xác minh. Hãy làm lại bài sở thích." : "Kết quả tạm thời theo số câu đã trả lời; nhóm chưa trả lời chưa có điểm."}
        {complete && leaders.length > 0 && leaders.length < 6 && ` Nhóm cao nhất${leaders.length > 1 ? " đồng điểm" : ""}: ${leaders.join(" · ")}.`}
        {complete && leaders.length === 6 && " Sáu nhóm đồng điểm; chưa có nhóm sở thích nổi trội."}
        {" Thang 0–100 quy đổi từ mức trả lời 1–5. Đây là sở thích, không phải kết luận năng lực hay điều kiện tuyển sinh."}
      </p>
      <div className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {GROUPS.map(([code, label]) => {
          const group = evidence.groups.find(g => g.code === code)
          const percent = group?.percent ?? null
          return <div key={code}>
            <div className="mb-1 flex justify-between gap-2 text-xs">
              <span className="font-semibold text-slate-800">{code} · {label}</span>
              <span className="text-slate-600">{percent === null ? "Chưa có điểm" : `${Number(percent.toFixed(1))}%`}{group?.answered != null && ` · ${group.answered}/${group.total} câu`}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
              {percent !== null && <div className="h-full rounded-full bg-sky-500" style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />}
            </div>
          </div>
        })}
      </div>
    </section>
  )
}
