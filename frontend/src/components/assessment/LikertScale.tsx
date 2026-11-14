interface LikertOption {
  score: number
  label: string
  shortLabel: string
}

const LIKERT_OPTIONS: readonly LikertOption[] = [
  { score: 1, label: "Không thích", shortLabel: "Ghét" },
  { score: 2, label: "Ít thích", shortLabel: "Ít" },
  { score: 3, label: "Phân vân", shortLabel: "Vừa" },
  { score: 4, label: "Khá thích", shortLabel: "Thích" },
  { score: 5, label: "Rất thích", shortLabel: "Mê" },
] as const

export function LikertScale({
  value,
  onChange,
}: {
  value?: number
  onChange: (value: number) => void
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Thang đo mức độ yêu thích"
      className="grid grid-cols-5 gap-1.5 sm:gap-2.5"
    >
      {LIKERT_OPTIONS.map(({ score, label, shortLabel }) => {
        const isSelected = value === score
        return (
          <button
            key={score}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={`${score} điểm - ${label}`}
            onClick={() => onChange(score)}
            className={`group relative flex min-h-[48px] sm:min-h-[52px] flex-col items-center justify-center rounded-2xl border px-1.5 py-2 text-center transition-all duration-150 cursor-pointer active:scale-[0.94] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 ${
              isSelected
                ? "border-sky-500 bg-gradient-to-b from-sky-500 to-cyan-600 text-white shadow-[0_6px_18px_rgba(14,165,233,0.32)] ring-2 ring-sky-400/25 scale-[1.02]"
                : "border-slate-200/80 bg-white/90 text-slate-700 shadow-2xs hover:border-sky-300 hover:bg-sky-50/50 hover:text-sky-900"
            }`}
          >
            <span
              className={`text-base sm:text-lg font-black leading-tight tabular-nums transition-transform group-hover:scale-105 ${
                isSelected ? "text-white" : "text-slate-800"
              }`}
            >
              {score}
            </span>
            <span
              className={`mt-0.5 text-[10px] sm:text-xs font-bold leading-none tracking-tight ${
                isSelected ? "text-sky-100" : "text-slate-500 group-hover:text-sky-700"
              }`}
            >
              <span className="inline sm:hidden">{shortLabel}</span>
              <span className="hidden sm:inline">{label}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
