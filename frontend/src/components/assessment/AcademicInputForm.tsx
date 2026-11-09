import { Calculator } from "lucide-react"

const subjects = [
  "Toán",
  "Ngữ văn",
  "Tiếng Anh",
  "Vật lý",
  "Hóa học",
  "Sinh học",
]

export function AcademicInputForm({
  scores,
  onChange,
}: {
  scores: Record<string, number>
  onChange: (subject: string, value: number) => void
}) {
  const average = Object.values(scores).length
    ? Object.values(scores).reduce((a, b) => a + b, 0) /
      Object.values(scores).length
    : 0
  const zScore = (average - 7.1) / 1.2
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        {subjects.map((subject) => (
          <label key={subject} className="block">
            <span className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">
              {subject}
            </span>
            <input
              type="number"
              min="0"
              max="10"
              step="0.1"
              value={scores[subject] ?? ""}
              onChange={(event) =>
                onChange(subject, Number(event.target.value))
              }
              placeholder="0.0 — 10.0"
              className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-bold outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-100"
            />
          </label>
        ))}
      </div>
      <div className="flex items-center gap-4 rounded-2xl bg-gradient-to-r from-sky-500 to-blue-600 p-5 text-white shadow-lg shadow-sky-200/70">
        <span className="grid size-11 place-items-center rounded-xl bg-white/10">
          <Calculator size={21} />
        </span>
        <div>
          <p className="text-xs font-semibold text-sky-200">
            Z-Score học lực ước tính
          </p>
          <p className="text-2xl font-extrabold">
            {Number.isFinite(zScore) ? zScore.toFixed(2) : "0.00"}
          </p>
        </div>
        <p className="ml-auto max-w-xs text-right text-xs leading-5 text-sky-200">
          So sánh tương đối với dữ liệu tham chiếu, không phải điểm xét tuyển
          chính thức.
        </p>
      </div>
    </div>
  )
}
