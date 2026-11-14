import { Check, CheckCircle2 } from "lucide-react"
import { Card } from "../common/Card"
import { LikertScale } from "./LikertScale"

export function QuestionCard({
  index,
  question,
  value,
  onChange,
}: {
  index: number
  question: string
  value?: number
  onChange: (value: number) => void
}) {
  const isAnswered = typeof value === "number" && value > 0

  return (
    <Card
      className={`rounded-3xl p-5 sm:p-6 transition-all duration-200 backdrop-blur-xl ${
        isAnswered
          ? "border-sky-200/90 bg-white/90 shadow-[0_8px_24px_rgba(14,165,233,0.08)]"
          : "border-slate-200/80 bg-white/75 hover:border-sky-200 hover:bg-white/85"
      }`}
    >
      <div className="mb-4 sm:mb-5 flex items-start gap-3 sm:gap-4">
        <span
          className={`grid size-9 shrink-0 place-items-center rounded-2xl text-xs sm:text-sm font-black tabular-nums transition-all ${
            isAnswered
              ? "bg-emerald-500 text-white shadow-xs"
              : "border border-slate-200 bg-slate-100/90 text-slate-600"
          }`}
        >
          {isAnswered ? <Check className="size-4 stroke-[2.5]" /> : index}
        </span>
        <div className="min-w-0 flex-1 pt-0.5">
          <h3 className="text-base sm:text-lg lg:text-xl font-bold text-slate-900 leading-snug">
            {question}
          </h3>
          {isAnswered && (
            <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700">
              <CheckCircle2 className="size-3.5" />
              <span>Đã chọn: {value}/5 điểm</span>
            </span>
          )}
        </div>
      </div>
      <LikertScale value={value} onChange={onChange} />
    </Card>
  )
}
