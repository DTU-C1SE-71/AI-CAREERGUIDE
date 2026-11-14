import { Badge } from "../common/Badge"
import { CheckCircle2, Target } from "lucide-react"

export function FeasibilityBadge({
  value = "TARGET",
  label,
}: {
  value?: "TARGET" | "REACH" | string
  label?: string
}) {
  const isTarget = (value || "").toUpperCase().includes("TARGET")
  const text = label || (isTarget ? "Khả thi cao" : "Thử thách")
  return (
    <Badge tone={isTarget ? "emerald" : "amber"}>
      {isTarget ? (
        <CheckCircle2 size={13} className="shrink-0 text-emerald-600" />
      ) : (
        <Target size={13} className="shrink-0 text-amber-600" />
      )}
      <span>{text}</span>
    </Badge>
  )
}
