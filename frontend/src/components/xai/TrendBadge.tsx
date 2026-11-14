import { Flame, Sparkles, TrendingUp } from "lucide-react"

interface TrendBadgeProps {
  tier?: "TIER_1" | "TIER_2" | "TIER_3" | string | null
  isTrending?: boolean
  reason?: string | null
}

/**
 * Huy hiệu hiển thị Bậc Ưu tiên Ngành Xu Hướng đồng bộ theo Design System
 */
export function TrendBadge({ tier, isTrending, reason }: TrendBadgeProps) {
  if (!isTrending || !tier || tier === "NONE") return null

  const normalized = String(tier).toUpperCase()

  if (normalized === "TIER_1") {
    return (
      <span
        title={reason || "Xu hướng Bậc 1 · Ưu tiên cao nhất"}
        className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs"
      >
        <Flame size={13} className="shrink-0" />
        <span>Xu hướng Bậc 1</span>
      </span>
    )
  }

  if (normalized === "TIER_2") {
    return (
      <span
        title={reason || "Xu hướng Bậc 2 · Tăng trưởng mạnh"}
        className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-800"
      >
        <TrendingUp size={13} className="shrink-0 text-sky-600" />
        <span>Xu hướng Bậc 2</span>
      </span>
    )
  }

  return (
    <span
      title={reason || "Xu hướng Bậc 3 · Triển vọng ổn định"}
      className="inline-flex items-center gap-1 rounded-full border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-800"
    >
      <Sparkles size={13} className="shrink-0 text-cyan-600" />
      <span>Xu hướng Bậc 3</span>
    </span>
  )
}
