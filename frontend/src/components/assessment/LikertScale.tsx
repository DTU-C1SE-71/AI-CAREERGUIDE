const options = [
  [1, "Không thích"],
  [2, "Ít thích"],
  [3, "Phân vân"],
  [4, "Khá thích"],
  [5, "Rất thích"],
] as const

export function LikertScale({
  value,
  onChange,
}: {
  value?: number
  onChange: (value: number) => void
}) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {options.map(([score, label]) => (
        <button
          key={score}
          type="button"
          onClick={() => onChange(score)}
          className={`group flex min-h-17 flex-col items-center justify-center rounded-xl border px-1 transition-all ${
            value === score
              ? "border-sky-600 bg-sky-600 text-white shadow-lg shadow-sky-100"
              : "border-slate-200 bg-white text-slate-500 hover:border-sky-300 hover:bg-sky-50"
          }`}
        >
          <span className="text-base font-extrabold">{score}</span>
          <span className="mt-0.5 hidden text-[10px] font-medium sm:block">
            {label}
          </span>
        </button>
      ))}
    </div>
  )
}
