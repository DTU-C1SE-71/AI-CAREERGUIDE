import { ArrowUpRight, Layers } from "lucide-react"

export function GapAnalysisCard({ gaps }: { gaps: string[] }) {
  return (
    <div className="glass-card rounded-3xl p-6">
      <div className="mb-3 flex items-center gap-2 text-sm font-extrabold text-slate-800">
        <Layers size={16} className="text-sky-600" />
        Kỹ năng cần bổ sung
      </div>
      <div className="flex flex-wrap gap-2">
        {gaps.map((gap) => (
          <span
            key={gap}
            className="inline-flex items-center gap-1 rounded-xl border border-white/85 bg-white/65 px-3 py-1.5 text-xs font-bold text-slate-700 shadow-2xs backdrop-blur-md"
          >
            {gap}
            <ArrowUpRight size={13} className="text-sky-600" />
          </span>
        ))}
      </div>
    </div>
  )
}
