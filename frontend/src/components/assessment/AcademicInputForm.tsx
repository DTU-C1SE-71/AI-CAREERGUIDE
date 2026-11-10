import { Calculator, Sparkles, Zap } from "lucide-react"

const subjects = [
  { name: "Toán", group: "Tự nhiên & Tư duy" },
  { name: "Ngữ văn", group: "Ngôn ngữ & Xã hội" },
  { name: "Tiếng Anh", group: "Hội nhập Quốc tế" },
  { name: "Vật lý", group: "Kỹ thuật & Công nghệ" },
  { name: "Hóa học", group: "Y Sinh & Vật liệu" },
  { name: "Sinh học", group: "Khoa học Sự sống" },
]

const QUICK_SCORES = [6.5, 7.5, 8.0, 8.5, 9.2]

export function AcademicInputForm({
  scores,
  onChange,
}: {
  scores: Record<string, number>
  onChange: (subject: string, value: number) => void
}) {
  const values = Object.values(scores).filter((v) => typeof v === "number" && v > 0)
  const average = values.length
    ? values.reduce((a, b) => a + b, 0) / values.length
    : 0
  const zScore = (average - 7.1) / 1.2

  const applyPresetAll = (val: number) => {
    subjects.forEach((s) => onChange(s.name, val))
  }

  return (
    <div className="space-y-5">
      {/* Quick Preset Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sky-200/70 bg-sky-50/60 px-4 py-3 backdrop-blur-md">
        <div className="flex items-center gap-2 text-xs font-extrabold text-sky-900">
          <Zap className="size-4 text-sky-600" />
          <span>Điền nhanh mức điểm trung bình:</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {QUICK_SCORES.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => applyPresetAll(preset)}
              className="rounded-xl border border-sky-200 bg-white/90 px-3 py-1.5 text-xs font-black text-sky-700 shadow-sm transition hover:border-sky-400 hover:bg-sky-500 hover:text-white"
            >
              {preset.toFixed(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Subject Cards */}
      <div className="grid gap-3.5 sm:grid-cols-2">
        {subjects.map(({ name, group }) => {
          const val = scores[name] ?? 8.0
          return (
            <div
              key={name}
              className="rounded-2xl border border-white/80 bg-white/75 p-4 shadow-[0_8px_24px_rgba(14,165,233,0.06)] backdrop-blur-md transition hover:border-sky-300"
            >
              <div className="mb-2.5 flex items-center justify-between">
                <div>
                  <span className="block text-sm font-black text-slate-900">
                    {name}
                  </span>
                  <span className="text-[11px] font-semibold text-slate-500">
                    {group}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
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
                    className="h-9 w-16 rounded-xl border border-sky-200 bg-sky-50/70 text-center text-sm font-black text-sky-800 outline-none transition focus:border-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              <input
                type="range"
                min="4.0"
                max="10.0"
                step="0.1"
                value={val}
                onChange={(e) => onChange(name, Number(e.target.value))}
                className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-sky-100 accent-sky-600"
              />

              <div className="mt-2 flex items-center justify-between gap-1">
                {QUICK_SCORES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => onChange(name, q)}
                    className={`rounded-lg px-2 py-0.5 text-[10px] font-bold transition ${
                      Math.abs(val - q) < 0.05
                        ? "bg-sky-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-sky-100 hover:text-sky-700"
                    }`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Unified Sky/Cyan Liquid Glass Power Summary */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-sky-300/40 bg-gradient-to-r from-sky-600 to-cyan-600 p-5 text-white shadow-[0_12px_30px_rgba(14,165,233,0.24)]">
        <div className="flex items-center gap-3.5">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 backdrop-blur-md">
            <Calculator size={20} />
          </span>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-sky-100">
              Chỉ số Z-Score Học Lực Chuẩn Hóa
            </p>
            <div className="flex items-baseline gap-2.5">
              <p className="text-2xl font-black">
                {Number.isFinite(zScore) ? (zScore >= 0 ? `+${zScore.toFixed(2)}` : zScore.toFixed(2)) : "0.00"}
              </p>
              <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] font-extrabold text-white">
                TB: {average.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 rounded-xl bg-white/15 px-3.5 py-2 text-xs font-bold text-sky-50 backdrop-blur-md">
          <Sparkles className="size-4 text-cyan-200" />
          <span>Sẵn sàng mở khóa Bản đồ 435 Ngành</span>
        </div>
      </div>
    </div>
  )
}
