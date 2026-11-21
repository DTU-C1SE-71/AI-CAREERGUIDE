import { Check, CircleDot, Orbit, SunMedium } from "lucide-react"
import { AI_MODEL_CHOICES } from "../../constants/aiModels"

interface ModelQuickSelectProps {
  value: string
  activeModel?: string
  availableModels?: string[]
  disabled: boolean
  onSelect: (model: string) => void
}

const KNOWN_MODELS = new Map<string, (typeof AI_MODEL_CHOICES)[number]>(
  AI_MODEL_CHOICES.map(model => [model.id, model])
)

export function ModelQuickSelect({ value, activeModel, availableModels, disabled, onSelect }: ModelQuickSelectProps) {
  const models = availableModels && availableModels.length > 0
    ? availableModels.map((id, index) => {
        const known = KNOWN_MODELS.get(id)
        return known ?? { id, label: id, symbol: index % 2 === 0 ? "sol" : "astra" as const }
      })
    : AI_MODEL_CHOICES

  return (
    <fieldset className="admin-model-picker" disabled={disabled}>
      <legend>Chọn nhanh model</legend>
      <p id="model-choice-help">Chọn model để cập nhật bản nháp. Cấu hình đang chạy chỉ đổi khi bạn lưu và áp dụng.</p>
      <div className="admin-model-options" role="group" aria-label="Model có sẵn" aria-describedby="model-choice-help">
        {models.map(model => {
          const selected = value === model.id
          const active = activeModel === model.id
          const Icon = model.symbol === "sol" ? SunMedium : Orbit
          return <button key={model.id} type="button" className={`admin-model-choice ${selected ? "selected" : ""}`}
            aria-label={`Chọn ${model.label}`} aria-pressed={selected} onClick={() => onSelect(model.id)}>
            <span className={`admin-model-symbol ${model.symbol}`}><Icon size={24} aria-hidden="true" /></span>
            <span className="admin-model-name"><strong>{model.label}</strong><code>{model.id}</code></span>
            <span className="admin-model-state">{selected ? <span className="draft-selected"><Check size={14} aria-hidden="true" />Đã chọn</span> : <span>Chọn bản nháp</span>}{active && <span className="runtime-active"><CircleDot size={13} aria-hidden="true" />Đang áp dụng</span>}</span>
          </button>
        })}
      </div>
      <p className="admin-model-custom">Bạn vẫn có thể nhập model khác trong ô bên dưới hoặc thêm vào biến môi trường <code>LLM_AVAILABLE_MODELS</code>.</p>
    </fieldset>
  )
}
