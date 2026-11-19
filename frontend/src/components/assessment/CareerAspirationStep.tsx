import {
  ArrowRight,
  Check,
  ChevronDown,
  Compass,
  Search,
  SlidersHorizontal,
  Sparkles,
  Target,
  X,
} from "lucide-react"
import { useState } from "react"
import type { CareerAspirationInput, InterestEvidence } from "../../types/assessment"

import { QUICK_DREAM_JOBS } from "./aspirationOptions"
import { HollandInterestSummary } from "./HollandInterestSummary"

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
    title: "Khám phá hướng liên quan",
    desc: "Xem ngành liên quan; chỉ đánh dấu đạt mốc khi có đủ bằng chứng.",
    icon: "🎯",
  },
  {
    id: "REALISTIC_SAFE",
    title: "Ưu tiên mốc hiện tại",
    desc: "Ưu tiên ngành đạt mốc tham chiếu; không bảo đảm trúng tuyển.",
    icon: "🛡️",
  },
  {
    id: "CHALLENGE_TOP",
    title: "Giữ mục tiêu dài hạn",
    desc: "Giữ nguyện vọng và xem phần dữ liệu hoặc học lực cần bổ sung.",
    icon: "🚀",
  },
]

interface CareerAspirationStepProps {
  value: CareerAspirationInput
  onChange: (next: CareerAspirationInput) => void
  interestEvidence: InterestEvidence
  readOnly?: boolean
  onSkip?: () => void
}

export function CareerAspirationStep({
  value,
  onChange,
  interestEvidence,
  readOnly = false,
  onSkip,
}: CareerAspirationStepProps) {
  const selectedValues = value.workValues || []
  const activeStrategy = value.scoreStrategy || "FLEXIBLE_PATHWAY"

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

  const hasDreamJob = Boolean(value.dreamJob?.trim())

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Header Banner tinh gọn */}
      <div className="flex flex-col gap-3 rounded-2xl border border-sky-200/80 bg-gradient-to-r from-sky-50/90 via-sky-50/50 to-white/70 p-4 sm:flex-row sm:items-center sm:justify-between backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-sm">
            <Sparkles className="size-5" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base sm:text-lg font-black text-slate-900">
                Nguyện vọng nghề nghiệp mong muốn
              </h2>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-extrabold text-sky-800">
                Tùy chọn
              </span>
            </div>
            <p className="mt-0.5 text-xs sm:text-sm text-slate-600">
              Đối chiếu nguyện vọng với sở thích và dữ liệu học tập của bạn.
            </p>
          </div>
        </div>

        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="self-end sm:self-center inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white/90 px-3.5 py-2 text-xs font-bold text-slate-600 shadow-2xs transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 cursor-pointer active:scale-95"
          >
            <span>Bỏ qua bước này</span>
            <ArrowRight className="size-3.5" />
          </button>
        )}
      </div>

      <HollandInterestSummary evidence={interestEvidence} />
      <fieldset disabled={readOnly} className="space-y-4 min-w-0">
      <legend className="sr-only">Nguyện vọng nghề nghiệp</legend>
      {/* Input Nghề mơ ước + Gợi ý nhanh */}
      <div className="space-y-3 rounded-3xl border border-white/90 bg-white/75 p-4 sm:p-6 shadow-sm backdrop-blur-md">
        <div className="flex items-center justify-between">
          <label htmlFor="dream-job" className="flex items-center gap-2 text-sm sm:text-base font-extrabold text-slate-900">
            <Compass className="size-4.5 text-sky-600" />
            Nghề nghiệp hoặc lĩnh vực bạn muốn theo đuổi
          </label>
          {hasDreamJob && (
            <button
              type="button"
              onClick={handleClearJob}
              className="text-xs font-bold text-rose-500 hover:text-rose-700 hover:underline transition cursor-pointer"
            >
              Xóa chọn
            </button>
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-4 top-1/2 size-4.5 -translate-y-1/2 text-slate-400" />
          <input
            id="dream-job"
            name="dreamJob"
            type="text"
            value={value.dreamJob || ""}
            onChange={(e) =>
              onChange({
                ...value,
                dreamJob: e.target.value,
                desiredField: "",
              })
            }
            placeholder="VD: Kỹ sư AI, Bác sĩ, Marketing, Thiết kế UI/UX, Phi công, Luật sư..."
            className="h-12 w-full rounded-2xl border border-sky-200/90 bg-white pl-11 pr-10 text-sm sm:text-base font-semibold text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
          />
          {hasDreamJob && (
            <button
              type="button"
              onClick={handleClearJob}
              aria-label="Xóa nội dung đã nhập"
              className="absolute right-3.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition cursor-pointer"
            >
              <X className="size-4" />
            </button>
          )}
        </div>

        {/* Status Pill: Emerald when filled, Amber when empty */}
        {hasDreamJob ? (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50/80 px-3 py-1.5 text-xs font-bold text-emerald-800">
            <Check className="size-4 text-emerald-600 stroke-[2.5]" />
            <span>Mục tiêu đang chọn: <strong>{value.dreamJob}</strong></span>
          </div>
        ) : (
          <div className="flex items-center gap-2 rounded-xl border border-amber-200/70 bg-amber-50/60 px-3 py-1.5 text-xs font-medium text-amber-800">
            <span>💡 Nhập tên nghề hoặc chọn từ danh sách phổ biến bên dưới.</span>
          </div>
        )}

        {/* 8 Gợi ý nhanh - Unified Sky/Cyan Chips */}
        <div className="pt-2">
          <span className="block text-xs font-bold text-slate-600 mb-2">
            Gợi ý phổ biến (bấm để chọn nhanh):
          </span>
          <div className="flex flex-wrap gap-2">
            {QUICK_DREAM_JOBS.map((chip) => {
              const isSelected =
                (value.dreamJob || "").trim().toLowerCase() ===
                chip.dreamJob.trim().toLowerCase()
              return (
                <button
                  key={chip.label}
                  type="button"
                  onClick={() => handleSelectChip(chip)}
                  aria-pressed={isSelected}
                  className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs sm:text-sm font-bold transition-all duration-150 cursor-pointer active:scale-95 ${
                    isSelected
                      ? "border-sky-500 bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-[0_4px_12px_rgba(14,165,233,0.25)] ring-1 ring-sky-400"
                      : "border-slate-200/90 bg-white/90 text-slate-700 hover:border-sky-300 hover:bg-sky-50/60 hover:text-sky-900 shadow-2xs"
                  }`}
                >
                  {isSelected && <Check className="size-3.5 stroke-[2.5]" />}
                  <span>{chip.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Accordion tùy chọn mở rộng */}
      <div className="rounded-3xl border border-slate-200/80 bg-white/60 p-4 transition">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          aria-expanded={showAdvanced}
          className="flex w-full items-center justify-between text-left text-xs sm:text-sm font-bold text-slate-700 hover:text-sky-700 cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="size-4 text-sky-600" />
            <span>Tùy chỉnh thêm giá trị làm việc & chiến lược điểm số</span>
            {hasCustomOptions && (
              <span className="inline-flex items-center rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11px] font-black text-emerald-800">
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
          <div className="mt-4 space-y-4 border-t border-slate-200/70 pt-4">
            <fieldset className="space-y-2">
              <legend className="text-sm font-bold text-slate-800">Giá trị công việc coi trọng (chọn tối đa 2 mục)</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {WORK_VALUE_OPTIONS.map(opt => <label key={opt.id} className="flex min-h-12 cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
                  <input type="checkbox" name="workValues" value={opt.id} checked={selectedValues.includes(opt.id)} onChange={() => toggleWorkValue(opt.id)} className="size-4 accent-sky-600" />
                  <span>{opt.icon} {opt.label}</span>
                </label>)}
              </div>
            </fieldset>
            <fieldset className="space-y-2">
              <legend className="flex items-center gap-2 text-sm font-bold text-slate-800"><Target className="size-4 text-sky-600" />Định hướng khi đối chiếu học lực</legend>
              <div className="grid gap-2.5 sm:grid-cols-3">
                {STRATEGY_OPTIONS.map(st => <label key={st.id} className={`cursor-pointer rounded-2xl border p-3.5 ${activeStrategy === st.id ? "border-sky-500 bg-sky-50" : "border-slate-200 bg-white"}`}>
                  <span className="flex items-center gap-2 text-sm font-bold text-slate-900"><input type="radio" name="scoreStrategy" value={st.id} checked={activeStrategy === st.id} onChange={() => onChange({ ...value, scoreStrategy: st.id })} className="size-4 accent-sky-600" />{st.icon} {st.title}</span>
                  <span className="mt-2 block text-xs leading-relaxed text-slate-600">{st.desc}</span>
                </label>)}
              </div>
            </fieldset>
          </div>
        )}
      </div>
      </fieldset>
    </div>
  )
}
