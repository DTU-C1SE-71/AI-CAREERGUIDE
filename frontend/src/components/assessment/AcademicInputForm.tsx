import { Calculator } from "lucide-react"
import { completeTranscriptBlocks } from "../../utils/assessmentEvidence"

export interface SubjectGrade {
  subject: string
  score: number
  zScore?: number | null
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

export function AcademicInputForm({
  scores,
  onChange,
}: {
  scores: Record<string, number>
  onChange: (subject: string, value: number | undefined) => void
}) {
  const validScoreItems = HIGH_SCHOOL_SUBJECTS
    .map((s) => ({ subject: s.name, score: scores[s.name], zScore: null }))
    .filter(
      (item): item is { subject: string; score: number; zScore: null } =>
        typeof item.score === "number" && Number.isFinite(item.score) && item.score >= 0 && item.score <= 10,
    )
  const completeBlocks = completeTranscriptBlocks(validScoreItems)
  const hasInvalid = HIGH_SCHOOL_SUBJECTS.some((s) => {
    const v = scores[s.name]
    return v !== undefined && (!Number.isFinite(v) || v < 0 || v > 10)
  })
  const topBlock = completeBlocks[0]
  const values = validScoreItems.map((item) => item.score)
  const average = values.length
    ? values.reduce((a, b) => a + b, 0) / values.length
    : 0

  const handleNumberInputChange = (subjectName: string, rawValue: string) => {
    if (rawValue.trim() === "") { onChange(subjectName, undefined); return }
    const value = Number(rawValue)
    if (Number.isFinite(value)) onChange(subjectName, value)

  }

  return (
    <div className="relative flex flex-col gap-4">
      {/* Scrollable Responsive Bento Grid for All 10 High School Subjects (Multi-Column on Desktop) */}
      <div className="custom-scrollbar grid max-h-[62vh] grid-cols-1 gap-3.5 overflow-y-auto pr-1.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {HIGH_SCHOOL_SUBJECTS.map((subj) => {
          const val = scores[subj.name]
          const invalid = val !== undefined && (!Number.isFinite(val) || val < 0 || val > 10)
          const fillPct = Math.min(100, Math.max(0, ((val ?? 0) / 10) * 100))

          const groupBadgeClass = "bg-sky-50 text-sky-800 border-sky-200/80"

          return (
            <div
              key={subj.name}
              className="group flex flex-col justify-between rounded-2xl border border-white/90 bg-white/80 p-4 shadow-[0_6px_20px_rgba(14,165,233,0.06)] backdrop-blur-xl transition-all duration-150 hover:border-sky-300 hover:bg-white hover:shadow-md"
            >
              <div>
                <div className="mb-1.5 flex items-center justify-between gap-1.5">
                  <span className={`inline-block rounded-md border px-1.5 py-0.5 text-[10px] font-bold ${groupBadgeClass}`}>
                    {subj.group === "Khoa học xã hội & Công nghệ" ? "Xã hội & CN" : subj.group}
                  </span>
                  <span className="truncate text-[10px] font-semibold text-slate-400">
                    {subj.blocks}
                  </span>
                </div>

                <div className="mb-3 flex items-center justify-between gap-2">
                  <span className="truncate text-base font-black text-slate-900">
                    {subj.name}
                  </span>

                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={10}
                    step="any"
                    value={val ?? ""}
                    placeholder="Chưa nhập"
                    aria-invalid={invalid}
                    onKeyDown={(e) => {
                      if (["-", "+", "e", "E"].includes(e.key)) {
                        e.preventDefault()
                      }
                    }}
                    onChange={(e) =>
                      handleNumberInputChange(subj.name, e.target.value)
                    }
                    aria-label={`Điểm môn ${subj.name}`}
                    className="h-10 w-20 shrink-0 rounded-xl border border-sky-200 bg-white text-center font-mono text-base font-black tabular-nums text-sky-900 shadow-inner outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-400/25"
                  />
                </div>
              </div>

              {invalid && <p role="alert" className="mb-2 text-sm text-rose-700">Điểm cần nằm trong khoảng 0 đến 10.</p>}
              {/* Thanh trượt chỉ cập nhật điểm khi người dùng thao tác. */}
              <div className="space-y-1 pt-1">
                <input
                  type="range"
                  min={0}
                  max={10}
                  step={0.1}
                  value={val ?? 0}
                  onChange={(e) =>
                    onChange(subj.name, Number(e.target.value))
                  }
                  aria-label={`Thanh trượt điểm môn ${subj.name}`}
                  style={{
                    background: `linear-gradient(to right, #0284c7 0%, #0284c7 ${fillPct}%, #e0f2fe ${fillPct}%, #e0f2fe 100%)`,
                  }}
                  className="h-2.5 w-full cursor-pointer appearance-none rounded-lg accent-sky-600 focus:outline-none"
                />
                <div className="flex justify-between font-mono text-[10px] font-bold tabular-nums text-slate-400">
                  <span>0.0</span>
                  <span>5.0</span>
                  <span>10.0</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Sticky Bottom Summary Bar */}
      <div className="sticky bottom-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-5 py-3.5 text-sky-900">
        <div className="flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-white/20 backdrop-blur-md">
            <Calculator className="size-5" />
          </span>
          <div>
            <p className="text-xs font-semibold text-sky-800">
              Điểm học bạ tự khai ({values.length}/{HIGH_SCHOOL_SUBJECTS.length} môn)
            </p>
            <p className="font-mono text-2xl font-black leading-tight tabular-nums sm:text-3xl">
              {values.length ? average.toFixed(2) : "Chưa nhập"}
            </p>
          </div>
        </div>
        {hasInvalid ? (
          <span className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-bold text-rose-700 sm:text-sm">
            Vui lòng kiểm tra lại điểm trong khoảng 0 – 10
          </span>
        ) : topBlock ? (
          <span className="rounded-xl border border-sky-200/90 bg-white/90 px-4 py-2 text-xs font-bold tabular-nums text-sky-900 shadow-2xs sm:text-sm">
            Tổ hợp cao nhất: {topBlock.code} ({topBlock.sum.toFixed(1)}đ) · Đủ {completeBlocks.length} tổ hợp
          </span>
        ) : (
          <span className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs font-bold tabular-nums text-amber-800 sm:text-sm">
            Cần nhập đủ ít nhất 1 tổ hợp 3 môn (VD: A00, A01, D01, C00)
          </span>
        )}
      </div>
    </div>
  )
}
