import { Compass, Sparkles, Target } from "lucide-react"
import type { CareerAspirationInput } from "../../types/assessment"

const QUICK_DREAM_JOBS: Array<{
  label: string
  dreamJob: string
  field: string
}> = [
  {
    label: "💻 Kỹ sư AI & Phần mềm",
    dreamJob: "Kỹ sư Trí tuệ nhân tạo & Kỹ thuật phần mềm",
    field: "Máy tính và công nghệ thông tin",
  },
  {
    label: "⚙️ Vi mạch & Tự động hóa",
    dreamJob: "Kỹ sư Thiết kế vi mạch & Tự động hóa",
    field: "Công nghệ kỹ thuật",
  },
  {
    label: "🩺 Bác sĩ & Dược sĩ",
    dreamJob: "Bác sĩ Y khoa & Dược học",
    field: "Sức khỏe",
  },
  {
    label: "📊 Marketing & Kinh doanh",
    dreamJob: "Chuyên gia Marketing số & Kinh doanh quốc tế",
    field: "Kinh doanh và quản lý",
  },
  {
    label: "🏛️ Tài chính & Fintech",
    dreamJob: "Chuyên gia Tài chính - Ngân hàng & Fintech",
    field: "Kinh doanh và quản lý",
  },
  {
    label: "🎨 Thiết kế & Truyền thông",
    dreamJob: "Nhà Thiết kế Đồ họa UI/UX & Truyền thông đa phương tiện",
    field: "Nghệ thuật",
  },
  {
    label: "📚 Giáo viên & Tâm lý học",
    dreamJob: "Giáo viên Sư phạm & Chuyên gia Tâm lý học",
    field: "Khoa học giáo dục và đào tạo giáo viên",
  },
  {
    label: "⚖️ Luật sư & Ngoại giao",
    dreamJob: "Luật sư Pháp chế & Quan hệ quốc tế",
    field: "Pháp luật",
  },
]

const WORK_VALUE_OPTIONS: Array<{ id: string; label: string }> = [
  { id: "HIGH_INCOME_GROWTH", label: "Thu nhập & thăng tiến nhanh" },
  { id: "TECH_INNOVATION", label: "Sáng tạo công nghệ mới" },
  { id: "SOCIAL_IMPACT", label: "Giúp đỡ cộng đồng & con người" },
  { id: "STABILITY_EXPERTISE", label: "Chuyên sâu học thuật & ổn định" },
]

const STRATEGY_OPTIONS: Array<{
  id: NonNullable<CareerAspirationInput["scoreStrategy"]>
  title: string
  desc: string
}> = [
  {
    id: "FLEXIBLE_PATHWAY",
    title: "Linh hoạt ngành liên thông vừa sức",
    desc: "Nếu ngành mơ ước vượt điểm chuẩn, AI tự động gợi ý ngành cùng nhóm vừa sức.",
  },
  {
    id: "REALISTIC_SAFE",
    title: "Ưu tiên an toàn đậu Đại học",
    desc: "Chỉ tập trung các ngành đạt chuẩn điểm tổ hợp hiện tại (TARGET).",
  },
  {
    id: "CHALLENGE_TOP",
    title: "Quyết tâm bứt phá ngành Top",
    desc: "Giữ mục tiêu ngành điểm chuẩn cao kèm lộ trình bù đắp môn thiếu.",
  },
]

interface CareerAspirationStepProps {
  value: CareerAspirationInput
  onChange: (next: CareerAspirationInput) => void
  topHollandPreview: string
}

export function CareerAspirationStep({
  value,
  onChange,
  topHollandPreview,
}: CareerAspirationStepProps) {
  const selectedValues = value.workValues || []
  const activeStrategy = value.scoreStrategy || "FLEXIBLE_PATHWAY"

  const toggleWorkValue = (id: string) => {
    const exists = selectedValues.includes(id)
    const next = exists
      ? selectedValues.filter((v) => v !== id)
      : [...selectedValues.slice(-1), id]
    onChange({ ...value, workValues: next })
  }

  return (
    <div className="space-y-5">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-sky-200/80 bg-sky-50/70 px-4 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-sky-500 text-white shadow-xs">
            <Sparkles className="size-4" />
          </span>
          <div>
            <h2 className="text-sm sm:text-base font-black text-slate-900">
              AI Agent Phân tích Nguyện vọng & Đối chiếu Bài test
            </h2>
            <p className="text-xs text-slate-600">
              Đối chiếu ước muốn nghề nghiệp với mã Holland{" "}
              <strong className="text-sky-700">{topHollandPreview}</strong> & điểm chuẩn 435 ngành
            </p>
          </div>
        </div>
      </div>

      {/* Question 1: Dream Job Input + Quick Chips */}
      <div className="space-y-2.5">
        <label className="flex items-center gap-1.5 text-xs sm:text-sm font-extrabold text-slate-800">
          <Compass className="size-4 text-sky-600" />
          1. Sau này bạn ước muốn làm nghề gì hoặc theo đuổi ngành nào?
        </label>
        <input
          type="text"
          value={value.dreamJob || ""}
          onChange={(e) =>
            onChange({
              ...value,
              dreamJob: e.target.value,
            })
          }
          placeholder="Nhập nghề mơ ước (VD: Kỹ sư AI, Bác sĩ, Marketing, Thiết kế đồ họa, Luật sư...)"
          className="h-11 w-full rounded-2xl border border-sky-200/90 bg-white/90 px-4 text-sm font-semibold text-slate-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
        />

        <div className="flex flex-wrap gap-1.5 pt-1">
          {QUICK_DREAM_JOBS.map((chip) => {
            const isSelected =
              (value.dreamJob || "").toLowerCase() ===
              chip.dreamJob.toLowerCase()
            return (
              <button
                key={chip.label}
                type="button"
                onClick={() =>
                  onChange({
                    ...value,
                    dreamJob: chip.dreamJob,
                    desiredField: chip.field,
                  })
                }
                className={`rounded-xl border px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                  isSelected
                    ? "border-sky-500 bg-sky-500 text-white shadow-xs"
                    : "border-white/85 bg-white/75 text-slate-700 hover:border-sky-300 hover:bg-sky-50/70"
                }`}
              >
                {chip.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Question 2: Work Values */}
      <div className="space-y-2">
        <label className="block text-xs sm:text-sm font-extrabold text-slate-800">
          2. Giá trị công việc bạn coi trọng nhất (chọn tối đa 2):
        </label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {WORK_VALUE_OPTIONS.map((opt) => {
            const active = selectedValues.includes(opt.id)
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => toggleWorkValue(opt.id)}
                className={`flex items-center justify-between rounded-2xl border px-3.5 py-2.5 text-left text-xs font-bold transition cursor-pointer ${
                  active
                    ? "border-sky-500 bg-sky-50/90 text-sky-900 ring-1 ring-sky-500/25"
                    : "border-white/85 bg-white/75 text-slate-700 hover:border-sky-200 hover:bg-white"
                }`}
              >
                <span>{opt.label}</span>
                <span
                  className={`size-2.5 rounded-full ${
                    active ? "bg-sky-500" : "bg-slate-300"
                  }`}
                />
              </button>
            )
          })}
        </div>
      </div>

      {/* Question 3: Score Strategy */}
      <div className="space-y-2">
        <label className="flex items-center gap-1.5 text-xs sm:text-sm font-extrabold text-slate-800">
          <Target className="size-4 text-sky-600" />
          3. Định hướng khi AI đối chiếu nguyện vọng với điểm chuẩn:
        </label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {STRATEGY_OPTIONS.map((st) => {
            const active = activeStrategy === st.id
            return (
              <button
                key={st.id}
                type="button"
                onClick={() => onChange({ ...value, scoreStrategy: st.id })}
                className={`flex flex-col justify-between rounded-2xl border p-3 text-left transition cursor-pointer ${
                  active
                    ? "border-sky-500 bg-sky-50/90 ring-1 ring-sky-500/25"
                    : "border-white/85 bg-white/75 hover:border-sky-200 hover:bg-white"
                }`}
              >
                <p className="text-xs font-extrabold text-slate-900">
                  {st.title}
                </p>
                <p className="mt-1 text-[11px] leading-snug text-slate-500">
                  {st.desc}
                </p>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
