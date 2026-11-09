import { Badge } from "../common/Badge"

export function FeasibilityBadge({
  value = "TARGET",
}: {
  value?: "TARGET" | "REACH" | string
}) {
  const isTarget = (value || "").toUpperCase().includes("TARGET")
  return (
    <Badge tone={isTarget ? "emerald" : "slate"}>
      {isTarget ? "Khả thi cao" : "Thử thách"}
    </Badge>
  )
}
