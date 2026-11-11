import {
  ArrowRight,
  ChevronDown,
  Compass,
  Search,
  SlidersHorizontal,
  Sparkles,
  Target,
  X,
} from "lucide-react"
import { useState } from "react"
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
    label: "📚 Sư phạm & Tâm lý học",
    dreamJob: "Giáo viên Sư phạm & Chuyên gia Tâm lý học",
    field: "Khoa học giáo dục và đào tạo giáo viên",
  },
  {
    label: "⚖️ Luật sư & Ngoại giao",
    dreamJob: "Luật sư Pháp chế & Quan hệ quốc tế",
    field: "Pháp luật",
  },
]

const WORK_VALUE_OPTIONS: Array<{ id: string; label: string; icon: string }> = [
  { id: "HIGH_INCOME_GROWTH", label: "Thu nhập & thăng tiến nhanh", icon: "💰" },
  { id: "TECH_INNOVATION", label: "Sáng tạo công nghệ mới", icon: "💡" },
  { id: "SOCIAL_IMPACT", label: "Giúp đỡ cộng đồng & con người", icon: "🤝" },
  { id: "STABILITY_EXPERTISE", label: "Chuyên sâu học thuật & ổn định", icon: "🎓" },
]

const STRATEGY_OPTIONS: Array<{
  id: NonNullable<CareerAspirationInput["scoreStrategy"]>
  title: string
  desc: string
  icon: string
}> = [
  {
    id: "FLEXIBLE_PATHWAY",
    title: "Linh hoạt ngành liên thông vừa sức",
    desc: "Nếu nghề mơ ước vượt điểm, AI tự gợi ý ngành cùng nhóm vừa sức (Mặc định).",
    icon: "🎯",
  },
  {
    id: "REALISTIC_SAFE",
    title: "Ưu tiên an toàn đậu Đại học",
    desc: "Chỉ tập trung các ngành đạt chuẩn điểm tổ hợp môn hiện tại (TARGET).",
    icon: "🛡️",
  },
  {
    id: "CHALLENGE_TOP",
    title: "Quyết tâm bứt phá ngành Top",
    desc: "Giữ mục tiêu ngành điểm chuẩn cao kèm lộ trình bù đắp môn thiếu hụt.",
    icon: "🚀",
  },
]

interface CareerAspirationStepProps {
  value: CareerAspirationInput
  onChange: (next: CareerAspirationInput) => void
  topHollandPreview: string
  onSkip?: () => void
}

export function CareerAspirationStep({
  value,
  onChange,
  topHollandPreview,
  onSkip,
}: CareerAspirationStepProps) {
  const selectedValues = value.workValues || []
  const activeStrategy = value.scoreStrategy || "FLEXIBLE_PATHWAY"

  // Kiểm tra xem người dùng đã từng tùy chỉnh giá trị công việc hoặc chiến lược điểm chưa
  const hasCustomOptions =
    selectedValues.length > 0 ||
    (Boolean(value.scoreStrategy) && value.scoreStrategy !== "FLEXIBLE_PATHWAY")

  const [showAdvanced, setShowAdvanced] = useState(hasCustomOptions)

  const toggleWorkValue = (id: string) => {
    const exists = selectedValues.includes(id)
    const next = exists
      ? selectedValues.filter((v) => v !== id)
      : [...selectedValues.slice(-1), id]
    onChange({ ...value, workValues: next })
  }

  const handleClearJob = () => {
    onChange({
      ...value,
      dreamJob: "",
      desiredField: "",
    })
  }

  const handleSelectChip = (chip: (typeof QUICK_DREAM_JOBS)[number]) => {
    const isAlreadySelected =
      (value.dreamJob || "").trim().toLowerCase() ===
      chip.dreamJob.trim().toLowerCase()

    if (isAlreadySelected) {
      handleClearJob()
    } else {
      onChange({
        ...value,
        dreamJob: chip.dreamJob,
        desiredField: chip.field,
      })
    }
  }

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Header Banner tinh gọn, có nút Bỏ qua */}
      <div className="flex flex-col gap-3 rounded-2xl border border-sky-200/80 bg-gradient-to-r from-sky-50/90 via-sky-50/50 to-white/70 p-3.5 sm:flex-row sm:items-center sm:justify-between sm:p-4 backdrop-blur-xl">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-sky-500 text-white shadow-xs">
            <Sparkles className="size-4" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-1.5">
              <h2 className="text-sm sm:text-base font-black text-slate-900">
                Nguyện vọng nghề nghiệp mong muốn
              </h2>
              <span className="rounded-full border border-sky-300/80 bg-sky-100/80 px-2 py-0.5 text-[10px] font-extrabold text-sky-800">
                Tùy chọn · Không bắt buộc
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-600">
              Đối chiếu nghề mơ ước với mã Holland{" "}
              <strong className="text-sky-700">{topHollandPreview}</strong> & 435 ngành TT74.
            </p>
          </div>
        </div>

        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="self-end sm:self-center inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white/90 px-3 py-1.5 text-xs font-bold text-slate-600 shadow-2xs transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 cursor-pointer"
          >
            <span>Bỏ qua bước này</span>
            <ArrowRight className="size-3" />
          </button>
        )}
      </div>

      {/* Mục cốt lõi duy nhất cần thiết: Ô nhập nghề mơ ước + Gợi ý nhanh */}
      <div className="space-y-2.5 rounded-2xl border border-white/85 bg-white/60 p-3.5 sm:p-4 shadow-xs backdrop-blur-md">
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-1.5 text-xs sm:text-sm font-extrabold text-slate-800">
            <Compass className="size-4 text-sky-600" />
            Bạn ước muốn làm nghề gì hoặc theo đuổi ngành nào sau này?
          </label>
          {Boolean(value.dreamJob?.trim()) && (
            <button
              type="button"
              onClick={handleClearJob}
              className="text-[11px] font-bold text-slate-400 hover:text-rose-500 transition cursor-pointer"
            >
              Xóa chọn
            </button>
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={value.dreamJob || ""}
            onChange={(e) =>
              onChange({
                ...value,
                dreamJob: e.target.value,
              })
            }
            placeholder="VD: Kỹ sư AI, Bác sĩ, Marketing, Thiết kế đồ họa, Phi công, Luật sư..."
            className="h-11 w-full rounded-2xl border border-sky-200/90 bg-white/95 pl-10 pr-9 text-xs sm:text-sm font-semibold text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
          />
          {Boolean(value.dreamJob?.trim()) && (
            <button
              type="button"
              onClick={handleClearJob}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* 8 gợi ý nhanh 1 chạm */}
        <div className="pt-0.5">
          <span className="block text-[11px] font-bold text-slate-500 mb-1.5">
            Gợi ý phổ biến (bấm để chọn nhanh):
          </span>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_DREAM_JOBS.map((chip) => {
              const isSelected =
                (value.dreamJob || "").trim().toLowerCase() ===
                chip.dreamJob.trim().toLowerCase()
              return (
                <button
                  key={chip.label}
                  type="button"
                  onClick={() => handleSelectChip(chip)}
                  className={`rounded-xl border px-2.5 py-1 text-xs font-bold transition cursor-pointer ${
                    isSelected
                      ? "border-sky-500 bg-sky-500 text-white shadow-xs"
                      : "border-slate-200/80 bg-white/80 text-slate-700 hover:border-sky-300 hover:bg-sky-50/70"
                  }`}
                >
                  {chip.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Accordion tùy chọn mở rộng: Thu gọn các mục phụ để không làm rối giao diện */}
      <div className="rounded-2xl border border-slate-200/70 bg-white/40 p-2.5 sm:p-3 transition">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex w-full items-center justify-between text-left text-xs font-bold text-slate-600 hover:text-sky-700 cursor-pointer"
        >
          <div className="flex items-center gap-1.5">
            <SlidersHorizontal className="size-3.5 text-sky-600" />
            <span>Tùy chỉnh thêm giá trị & chiến lược điểm số (Không bắt buộc)</span>
            {hasCustomOptions && (
              <span className="inline-flex items-center rounded-full bg-sky-500/15 px-1.5 py-0.2 font-mono text-[10px] font-extrabold text-sky-800">
                Đã tùy chỉnh
              </span>
            )}
          </div>
          <ChevronDown
            className={`size-4 text-slate-400 transition-transform duration-200 ${
              showAdvanced ? "rotate-180" : ""
            }`}
          />
        </button>

        {showAdvanced && (
          <div className="mt-3.5 space-y-4 border-t border-slate-200/60 pt-3">
            {/* Giá trị công việc */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-700">
                Giá trị công việc coi trọng (chọn tối đa 2):
              </label>
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {WORK_VALUE_OPTIONS.map((opt) => {
                  const active = selectedValues.includes(opt.id)
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => toggleWorkValue(opt.id)}
                      className={`flex items-center justify-between rounded-xl border px-3 py-2 text-left text-xs font-semibold transition cursor-pointer ${
                        active
                          ? "border-sky-500 bg-sky-50 text-sky-900 ring-1 ring-sky-500/20"
                          : "border-slate-200 bg-white/70 text-slate-700 hover:border-sky-200 hover:bg-white"
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        <span>{opt.icon}</span>
                        <span>{opt.label}</span>
                      </span>
                      <span
                        className={`size-2 rounded-full ${
                          active ? "bg-sky-500" : "bg-slate-300"
                        }`}
                      />
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Chiến lược đối chiếu điểm chuẩn */}
            <div className="space-y-1.5">
              <label className="flex items-center gap-1 text-xs font-bold text-slate-700">
                <Target className="size-3.5 text-sky-600" />
                Định hướng khi AI đối chiếu với điểm chuẩn:
              </label>
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
                {STRATEGY_OPTIONS.map((st) => {
                  const active = activeStrategy === st.id
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => onChange({ ...value, scoreStrategy: st.id })}
                      className={`flex flex-col justify-between rounded-xl border p-2.5 text-left transition cursor-pointer ${
                        active
                          ? "border-sky-500 bg-sky-50/90 ring-1 ring-sky-500/20"
                          : "border-slate-200 bg-white/70 hover:border-sky-200 hover:bg-white"
                      }`}
                    >
                      <div className="flex items-center gap-1 text-xs font-bold text-slate-900">
                        <span>{st.icon}</span>
                        <span>{st.title}</span>
                      </div>
                      <p className="mt-1 text-[11px] leading-snug text-slate-500">
                        {st.desc}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
