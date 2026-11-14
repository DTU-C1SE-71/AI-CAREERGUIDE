import { Check, CheckCircle2 } from "lucide-react"
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
      className={`rounded-3xl p-5 sm:p-7 transition-all duration-200 backdrop-blur-xl ${
        isAnswered
          ? "border-sky-300/80 bg-white/95 shadow-[0_10px_30px_rgba(14,165,233,0.1)]"
          : "border-slate-200/90 bg-white/80 hover:border-sky-200 hover:bg-white/90"
      }`}
    >
      {/* Header without redundant kicker */}
      <div className="mb-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`grid size-8 shrink-0 place-items-center rounded-xl text-xs sm:text-sm font-black tabular-nums transition-colors ${
                isAnswered
                  ? "bg-emerald-500 text-white shadow-xs"
                  : "border border-sky-200 bg-sky-50 text-sky-800"
              }`}
            >
              {isAnswered ? <Check className="size-4 stroke-[2.5]" /> : index}
            </span>
            {dimensionBadge && (
              <span className="rounded-full border border-sky-200/80 bg-sky-50/90 px-3 py-1 text-xs font-extrabold text-sky-800">
                {dimensionBadge}
              </span>
            )}
          </div>
          {isAnswered && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-black text-emerald-700">
              <CheckCircle2 className="size-3.5" />
              <span>Đã chọn ({selectedKey})</span>
            </span>
          )}
        </div>

        {/* Large readable question text */}
        <h3 className="text-base sm:text-lg lg:text-xl font-bold text-slate-900 leading-snug">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-2 text-sm sm:text-base font-medium leading-relaxed text-slate-600">
            {subtitle}
          </p>
        )}
      </div>

      {/* 4 Multiple-Choice Options with Comfortable 52px+ Tap Targets */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-1">
        {options.map((opt) => {
          const isSelected = selectedKey === opt.option_key

          return (
            <button
              key={opt.option_key}
              type="button"
              onClick={() => onSelect(opt.option_key)}
              className={`group flex min-h-[52px] items-start gap-3.5 rounded-2xl border p-4 sm:p-4.5 text-left transition-all duration-150 cursor-pointer active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 ${
                isSelected
                  ? "border-sky-500 bg-sky-50/90 ring-2 ring-sky-400/25 shadow-sm"
                  : "border-slate-200/90 bg-white/90 hover:border-sky-300 hover:bg-sky-50/40"
              }`}
            >
              {/* Option Letter Badge */}
              <span
                className={`grid size-9 shrink-0 place-items-center rounded-xl text-xs sm:text-sm font-black transition-all ${
                  isSelected
                    ? "bg-sky-600 text-white shadow-xs"
                    : "bg-slate-100 text-slate-700 group-hover:bg-sky-100 group-hover:text-sky-800"
                }`}
              >
                {opt.option_key}
              </span>

              {/* Text content */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1.5">
                  <h4
                    className={`text-sm sm:text-base font-bold leading-snug transition-colors ${
                      isSelected
                        ? "text-sky-950 font-extrabold"
                        : "text-slate-800 group-hover:text-sky-950"
                    }`}
                  >
                    {opt.title}
                  </h4>
                  {isSelected && (
                    <span className="grid size-5 shrink-0 place-items-center rounded-full bg-sky-600 text-white">
                      <Check className="size-3 stroke-[2.5]" />
                    </span>
                  )}
                </div>
                <p
                  className={`mt-1.5 text-xs sm:text-sm leading-relaxed transition-colors ${
                    isSelected
                      ? "text-sky-900/90 font-medium"
                      : "text-slate-600 group-hover:text-slate-700"
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
