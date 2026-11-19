import { Badge } from "../common/Badge"
import { AlertCircle, CheckCircle2, Target } from "lucide-react"
import type { AspirationReadiness } from "../../types/assessment"

export function FeasibilityBadge({
  value,
  label,
  readiness,
}: {
  value?: string
  label?: string
  readiness?: AspirationReadiness
}) {
  const normVal = (value || "").toUpperCase()
  const isTarget =
    normVal.includes("TARGET") ||
    normVal.includes("SAFE") ||
    normVal.includes("MATCH") ||
    readiness?.status === "READY_REFERENCE"
  const isReach =
    normVal.includes("REACH") ||
    readiness?.status === "NEEDS_IMPROVEMENT"

  const customLabel =
    label &&
    !label.includes("Chưa đủ cơ sở đối chiếu") &&
    !label.includes("Chưa đủ bằng chứng")
      ? label
      : null

  const text = customLabel
    ? customLabel
    : isTarget
      ? "Đạt mốc tham chiếu"
      : isReach
        ? "Cần cải thiện theo mốc"
        : "Chưa đủ bằng chứng đối chiếu"

  return (
    <Badge tone={isTarget ? "emerald" : isReach ? "amber" : "amber"}>
      {isTarget ? (
        <CheckCircle2 size={13} className="shrink-0 text-emerald-600" />
      ) : isReach ? (
        <Target size={13} className="shrink-0 text-amber-600" />
      ) : (
        <AlertCircle size={13} className="shrink-0 text-amber-600" />
      )}
      <span>{text}</span>
    </Badge>
  )
}
