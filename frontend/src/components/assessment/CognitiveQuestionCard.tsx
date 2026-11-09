import { CheckCircle2, Sparkles } from "lucide-react"
import { Card } from "../common/Card"

export interface CognitiveOption {
  option_key: string
  trait_code?: string
  title: string
  description: string
}

export interface CognitiveQuestionProps {
  index: number
  code: string
  title: string
  subtitle?: string
  dimensionBadge?: string
  options: CognitiveOption[]
  selectedKey?: string
  onSelect: (optionKey: string) => void
}

export function CognitiveQuestionCard({
  index,
  title,
  subtitle,
  dimensionBadge,
  options,
  selectedKey,
  onSelect,
}: CognitiveQuestionProps) {
  const isAnswered = Boolean(selectedKey)

  return (
    <Card
      className={`p-6 transition-all duration-200 ${
        isAnswered ? "border-sky-200 shadow-md shadow-sky-100/50" : "border-slate-200 hover:border-slate-300"
      }`}
    >
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2.5">
            <span
              className={`grid size-7 shrink-0 place-items-center rounded-lg text-xs font-black transition-colors ${
                isAnswered ? "bg-emerald-500 text-white shadow-xs" : "bg-sky-100 text-sky-700"
              }`}
            >
              {isAnswered ? <CheckCircle2 size={16} /> : index}
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-sky-600">
              Câu hỏi nhận thức 0{index}
            </span>
          </div>
          {dimensionBadge && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-bold text-slate-600 border border-slate-200">
              {dimensionBadge}
            </span>
          )}
        </div>

        <h3 className="text-base font-extrabold text-slate-900 sm:text-lg">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-1 text-xs sm:text-sm text-slate-500 font-medium">
            {subtitle}
          </p>
        )}
      </div>

      {/* 4 Multiple-Choice Options */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
        {options.map((opt) => {
          const isSelected = selectedKey === opt.option_key

          return (
            <button
              key={opt.option_key}
              type="button"
              onClick={() => onSelect(opt.option_key)}
              className={`group flex items-start gap-3.5 p-4 rounded-2xl text-left border transition-all duration-150 cursor-pointer ${
                isSelected
                  ? "border-sky-500 bg-sky-50/80 ring-2 ring-sky-400/20 shadow-sm"
                  : "border-slate-200/90 bg-white hover:border-sky-300 hover:bg-slate-50/80"
              }`}
            >
              {/* Option Letter Badge */}
              <span
                className={`grid size-8 shrink-0 place-items-center rounded-xl text-xs font-black transition-all ${
                  isSelected
                    ? "bg-sky-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 group-hover:bg-sky-100 group-hover:text-sky-700"
                }`}
              >
                {opt.option_key}
              </span>

              {/* Text content */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <h4
                    className={`text-xs sm:text-sm font-bold transition-colors ${
                      isSelected ? "text-sky-950 font-extrabold" : "text-slate-800 group-hover:text-sky-900"
                    }`}
                  >
                    {opt.title}
                  </h4>
                  {isSelected && (
                    <CheckCircle2 size={16} className="text-sky-600 shrink-0 ml-1" />
                  )}
                </div>
                <p
                  className={`mt-1 text-xs leading-relaxed transition-colors line-clamp-3 ${
                    isSelected ? "text-sky-800/90 font-medium" : "text-slate-500 group-hover:text-slate-600"
                  }`}
                >
                  {opt.description}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
