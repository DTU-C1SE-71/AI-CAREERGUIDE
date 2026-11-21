import { useState } from "react"
import { Check, CircleDot, Info, Orbit, SunMedium, X } from "lucide-react"
import { AI_MODEL_CHOICES, type AIModelChoice } from "../../constants/aiModels"

interface ModelQuickSelectProps {
  value: string
  activeModel?: string
  availableModels?: string[]
  disabled: boolean
  onSelect: (model: string) => void
}

const KNOWN_MODELS = new Map<string, AIModelChoice>(
  AI_MODEL_CHOICES.map(model => [model.id, model])
)

export function ModelQuickSelect({ value, activeModel, availableModels, disabled, onSelect }: ModelQuickSelectProps) {
  const [inspectedId, setInspectedId] = useState<string | null>(null)

  const models: AIModelChoice[] = availableModels && availableModels.length > 0
    ? availableModels.map((id, index) => {
        const known = KNOWN_MODELS.get(id)
        return known ?? {
          id,
          label: id,
          symbol: index % 2 === 0 ? "sol" : "astra",
          badges: ["ENV"],
          description: "Model tùy chỉnh được khai báo từ biến môi trường LLM_AVAILABLE_MODELS.",
        }
      })
    : [...AI_MODEL_CHOICES.slice(0, 8)]

  const inspectedModel = inspectedId ? models.find(model => model.id === inspectedId) ?? null : null

  const handleSelect = (modelId: string) => {
    onSelect(modelId)
    setInspectedId(modelId)
  }

  return (
    <fieldset className="admin-model-picker" disabled={disabled}>
      <legend>Chọn nhanh model</legend>
      <p id="model-choice-help">Bấm vào model để cập nhật bản nháp và xem giải thích chi tiết. Cấu hình đang chạy chỉ đổi khi bạn lưu và áp dụng.</p>
      <div className="admin-model-options" role="group" aria-label="Model có sẵn" aria-describedby="model-choice-help">
        {models.map(model => {
          const selected = value === model.id
          const active = activeModel === model.id
          const Icon = model.symbol === "sol" ? SunMedium : Orbit
          return <button key={model.id} type="button" className={`admin-model-choice ${selected ? "selected" : ""}`}
            aria-label={`Chọn ${model.label}`} aria-pressed={selected} onClick={() => handleSelect(model.id)}>
            <span className={`admin-model-symbol ${model.symbol}`}><Icon size={24} aria-hidden="true" /></span>
            <span className="admin-model-name"><strong>{model.label}</strong><code>{model.id}</code></span>
            <span className="admin-model-state">{selected ? <span className="draft-selected"><Check size={14} aria-hidden="true" />Đã chọn</span> : <span>Chọn bản nháp</span>}{active && <span className="runtime-active"><CircleDot size={13} aria-hidden="true" />Đang áp dụng</span>}</span>
          </button>
        })}
      </div>
      {inspectedModel && (
        <div className="mt-3 rounded-xl border border-sky-200 bg-sky-50/70 p-4 text-sm text-slate-700" role="region" aria-label={`Thông tin model ${inspectedModel.label}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2 font-semibold text-sky-900">
              <Info size={16} className="shrink-0 text-sky-600" aria-hidden="true" />
              <span>{inspectedModel.label}</span>
              <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs font-normal text-slate-600 border border-sky-100">{inspectedModel.id}</code>
            </div>
            <button
              type="button"
              onClick={() => setInspectedId(null)}
              className="rounded-md p-1 text-slate-500 hover:bg-sky-100 hover:text-slate-700 transition-colors"
              aria-label="Ẩn giải thích model"
            >
              <X size={15} aria-hidden="true" />
            </button>
          </div>
          {inspectedModel.badges.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {inspectedModel.badges.map(badge => (
                <span key={badge} className="rounded-full bg-white px-2.5 py-0.5 text-xs font-medium text-sky-800 border border-sky-200">
                  {badge}
                </span>
              ))}
            </div>
          )}
          <p className="mt-2 leading-relaxed text-slate-700">{inspectedModel.description}</p>
        </div>
      )}
      <p className="admin-model-custom">Bạn vẫn có thể nhập model khác trong ô bên dưới hoặc thêm vào biến môi trường <code>LLM_AVAILABLE_MODELS</code>.</p>
    </fieldset>
  )
}
