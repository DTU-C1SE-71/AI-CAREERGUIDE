import { Calculator, Zap } from "lucide-react"

const subjects = ["Toán", "Ngữ văn", "Tiếng Anh", "Vật lý", "Hóa học", "Sinh học"]
const QUICK_SCORES = [6.5, 7.5, 8.0, 8.5, 9.2]

export function AcademicInputForm({
  scores,
  onChange,
}: {
  scores: Record<string, number>
  onChange: (subject: string, value: number) => void
}) {
  const values = Object.values(scores).filter(
    (v) => typeof v === "number" && v > 0
  )
  const average = values.length
    ? values.reduce((a, b) => a + b, 0) / values.length
    : 0
  const zScore = (average - 7.1) / 1.2

  const applyPresetAll = (val: number) => {
    subjects.forEach((name) => onChange(name, val))
  }

  return (
    <div className="space-y-5">
      {/* Quick Preset Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/85 bg-white/60 px-4 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-2 text-sm font-extrabold text-sky-900">
          <Zap className="size-4 text-sky-600" />
          <span>Điền nhanh</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {QUICK_SCORES.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => applyPresetAll(preset)}
              className="rounded-xl border border-white/85 bg-white/80 px-3.5 py-1.5 text-sm font-black text-sky-700 shadow-sm transition hover:bg-sky-600 hover:text-white"
            >
              {preset.toFixed(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Subject Cards */}
      <div className="grid gap-3.5 sm:grid-cols-2">
        {subjects.map((name) => {
          const val = scores[name] ?? 8.0
          return (
            <div
              key={name}
              className="rounded-2xl border border-white/90 bg-white/70 p-4 shadow-[0_8px_24px_rgba(14,165,233,0.06)] backdrop-blur-xl transition hover:border-sky-300"
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="text-base font-black text-slate-900">
                  {name}
                </span>
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.1"
                  value={scores[name] ?? ""}
                  onChange={(event) =>
                    onChange(
                      name,
                      Math.min(10, Math.max(0, Number(event.target.value)))
                    )
                  }
                  className="h-10 w-20 rounded-xl border border-sky-200 bg-white/90 text-center text-base font-black text-sky-800 outline-none transition focus:border-sky-500"
                />
              </div>

              <input
                type="range"
                min="4.0"
                max="10.0"
                step="0.1"
                value={val}
                onChange={(e) => onChange(name, Number(e.target.value))}
                className="h-2.5 w-full cursor-pointer appearance-none rounded-lg bg-sky-100 accent-sky-600"
              />
            </div>
          )
        })}
      </div>

      {/* Summary Glass Pill */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-sky-300/50 bg-gradient-to-r from-sky-500 to-cyan-500 p-5 text-white shadow-[0_14px_32px_rgba(14,165,233,0.24)]">
        <div className="flex items-center gap-3.5">
          <span className="grid size-11 place-items-center rounded-xl bg-white/20 backdrop-blur-md">
            <Calculator size={20} />
          </span>
          <div>
            <p className="text-xs font-bold text-sky-100">Z-Score Học lực</p>
            <p className="text-2xl font-black">
              {Number.isFinite(zScore)
                ? zScore >= 0
                  ? `+${zScore.toFixed(2)}`
                  : zScore.toFixed(2)
                : "0.00"}
            </p>
          </div>
        </div>
        <span className="rounded-xl bg-white/20 px-4 py-2 text-sm font-black text-white backdrop-blur-md">
          Trung bình: {average.toFixed(2)}
        </span>
      </div>
    </div>
  )
}
