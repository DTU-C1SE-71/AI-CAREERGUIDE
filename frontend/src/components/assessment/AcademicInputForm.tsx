import { Calculator } from "lucide-react"

export interface SubjectGrade {
  subject: string
  score: number
  zScore: number
  group?: "Bắt buộc" | "Khoa học tự nhiên" | "Khoa học xã hội & Công nghệ"
}

export const HIGH_SCHOOL_SUBJECTS: Array<{
  name: string
  code: string
  group: SubjectGrade["group"]
  blocks: string
}> = [
  { name: "Toán", code: "MATH", group: "Bắt buộc", blocks: "A00 · A01 · B00 · D01" },
  { name: "Ngữ văn", code: "LIT", group: "Bắt buộc", blocks: "C00 · D01 · C03 · C04" },
  { name: "Tiếng Anh", code: "ENG", group: "Bắt buộc", blocks: "A01 · D01 · D07 · D14" },
  { name: "Vật lý", code: "PHY", group: "Khoa học tự nhiên", blocks: "A00 · A01 · A02 · C01" },
  { name: "Hóa học", code: "CHEM", group: "Khoa học tự nhiên", blocks: "A00 · B00 · D07 · A02" },
  { name: "Sinh học", code: "BIO", group: "Khoa học tự nhiên", blocks: "B00 · B02 · B08 · D08" },
  { name: "Lịch sử", code: "HIST", group: "Khoa học xã hội & Công nghệ", blocks: "C00 · C03 · D14 · C19" },
  { name: "Địa lý", code: "GEO", group: "Khoa học xã hội & Công nghệ", blocks: "C00 · C04 · D10 · D15" },
  { name: "GDKT & Pháp luật", code: "ECON", group: "Khoa học xã hội & Công nghệ", blocks: "C19 · C20 · D66 · D84" },
  { name: "Tin học / Công nghệ", code: "TECH", group: "Khoa học xã hội & Công nghệ", blocks: "A00-IT · A01-IT · STEM" },
]

function clampGrade(raw: number): number {
  if (!Number.isFinite(raw)) return 0
  const clamped = Math.min(10, Math.max(0, raw))
  return Math.round(clamped * 100) / 100
}

export function AcademicInputForm({
  scores,
  onChange,
}: {
  scores: Record<string, number>
  onChange: (subject: string, value: number) => void
}) {
  const values = HIGH_SCHOOL_SUBJECTS.map((s) => scores[s.name]).filter(
    (v): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0
  )
  const average = values.length
    ? values.reduce((a, b) => a + b, 0) / values.length
    : 0
  const zScore = (average - 7.1) / 1.2

  const handleNumberInputChange = (subjectName: string, rawValue: string) => {
    // Strip invalid characters except digits and decimal point
    const cleaned = rawValue.replace(/[^0-9.]/g, "")
    if (cleaned === "") {
      onChange(subjectName, 0)
      return
    }
    const parsed = Number.parseFloat(cleaned)
    if (Number.isNaN(parsed)) return
    onChange(subjectName, clampGrade(parsed))
  }

  return (
    <div className="relative flex flex-col gap-4">
      {/* Scrollable Responsive Bento Grid for All 10 High School Subjects */}
      <div className="custom-scrollbar grid max-h-[58vh] grid-cols-1 gap-3.5 overflow-y-auto pr-1.5 sm:grid-cols-2">
        {HIGH_SCHOOL_SUBJECTS.map((subj) => {
          const val = clampGrade(scores[subj.name] ?? 0)
          const fillPct = Math.min(100, Math.max(0, (val / 10) * 100))

          return (
            <div
              key={subj.name}
              className="group rounded-2xl border border-white/90 bg-white/75 p-4 shadow-[0_6px_20px_rgba(14,165,233,0.06)] backdrop-blur-xl transition-all hover:border-sky-300 hover:bg-white/90"
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <span className="block truncate text-base font-black text-slate-900">
                    {subj.name}
                  </span>
                  <span className="block text-[11px] font-semibold text-slate-500">
                    {subj.blocks}
                  </span>
                </div>

                <input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  max={10}
                  step={0.1}
                  value={val}
                  onKeyDown={(e) => {
                    // Block negative signs, exponents, and plus signs
                    if (["-", "+", "e", "E"].includes(e.key)) {
                      e.preventDefault()
                    }
                  }}
                  onChange={(e) =>
                    handleNumberInputChange(subj.name, e.target.value)
                  }
                  onBlur={(e) =>
                    handleNumberInputChange(subj.name, e.target.value)
                  }
                  aria-label={`Điểm môn ${subj.name}`}
                  className="h-10 w-20 shrink-0 rounded-xl border border-sky-200 bg-white text-center text-base font-black text-sky-800 shadow-inner outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-400/25"
                />
              </div>

              {/* Synchronized Two-Way Range Slider (0.0 - 10.0) */}
              <div className="space-y-1">
                <input
                  type="range"
                  min={0}
                  max={10}
                  step={0.1}
                  value={val}
                  onChange={(e) =>
                    onChange(subj.name, clampGrade(Number(e.target.value)))
                  }
                  aria-label={`Thanh trượt điểm môn ${subj.name}`}
                  style={{
                    background: `linear-gradient(to right, #0284c7 0%, #06b6d4 ${fillPct}%, #e0f2fe ${fillPct}%, #e0f2fe 100%)`,
                  }}
                  className="h-2.5 w-full cursor-pointer appearance-none rounded-lg accent-sky-600"
                />
                <div className="flex justify-between text-[10px] font-bold text-slate-400">
                  <span>0.0</span>
                  <span>5.0</span>
                  <span>10.0</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Sticky Bottom Summary & Z-Score Bar */}
      <div className="sticky bottom-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sky-300/60 bg-gradient-to-r from-sky-500 to-cyan-500 px-5 py-3.5 text-white shadow-[0_12px_28px_rgba(14,165,233,0.26)] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-white/20 backdrop-blur-md">
            <Calculator className="size-5" />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-sky-100">
              Z-Score Học lực ({HIGH_SCHOOL_SUBJECTS.length} môn THPT)
            </p>
            <p className="text-2xl font-black leading-tight sm:text-3xl">
              {Number.isFinite(zScore)
                ? zScore >= 0
                  ? `+${zScore.toFixed(2)}`
                  : zScore.toFixed(2)
                : "0.00"}
            </p>
          </div>
        </div>
        <span className="rounded-xl border border-white/25 bg-white/20 px-4 py-2 text-sm font-black text-white backdrop-blur-md sm:text-base">
          Điểm trung bình: {average.toFixed(2)} / 10
        </span>
      </div>
    </div>
  )
}
