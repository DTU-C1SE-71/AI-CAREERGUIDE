import { CheckCircle2 } from "lucide-react"
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
  return (
    <Card className={`p-5 transition-all ${value ? "border-sky-200" : ""}`}>
      <div className="mb-4 flex items-start gap-3">
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-lg text-xs font-bold ${
            value
              ? "bg-emerald-50 text-emerald-600"
              : "bg-slate-100 text-slate-500"
          }`}
        >
          {value ? <CheckCircle2 size={17} /> : index}
        </span>
        <p className="pt-1 text-sm font-semibold leading-6 text-slate-800">
          {question}
        </p>
      </div>
      <LikertScale value={value} onChange={onChange} />
    </Card>
  )
}
