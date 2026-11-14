import { motion } from "framer-motion"
import { Sparkles, Target } from "lucide-react"

interface GapAnalysisCardProps {
  gaps?: string[]
  className?: string
}

export function GapAnalysisCard({ gaps = [], className = "" }: GapAnalysisCardProps) {
  if (!gaps || gaps.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`glass-card rounded-2xl p-5 sm:rounded-3xl sm:p-6 border border-slate-200/80 bg-white/70 shadow-xs ${className}`}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="grid size-9 place-items-center rounded-xl bg-amber-50 text-amber-600">
            <Target size={16} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">
              Kỹ năng cần bổ sung
            </h3>
            <p className="text-xs text-slate-500">
              Các kỹ năng cốt lõi được hệ thống gợi ý rèn luyện thêm
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 border border-amber-200">
          <Sparkles size={12} />
          {gaps.length} kỹ năng
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {gaps.map((gap, index) => (
          <motion.span
            key={`${gap}-${index}`}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: index * 0.04 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 transition hover:border-amber-300 hover:bg-amber-100"
          >
            <span className="size-1.5 rounded-full bg-amber-500 shrink-0" />
            {gap}
          </motion.span>
        ))}
      </div>
    </motion.div>
  )
}
