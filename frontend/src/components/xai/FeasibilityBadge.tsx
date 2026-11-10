import { Badge } from "../common/Badge"

export function FeasibilityBadge({
  value = "TARGET",
  label,
}: {
  value?: "TARGET" | "REACH" | string
  label?: string
}) {
  const isTarget = (value || "").toUpperCase().includes("TARGET")
  const text = label || (isTarget ? "Khả thi cao" : "Thử thách")
  return <Badge tone={isTarget ? "emerald" : "slate"}>{text}</Badge>
}
