import { Flame, Sparkles, TrendingUp } from "lucide-react"

interface TrendBadgeProps {
  tier?: "TIER_1" | "TIER_2" | "TIER_3" | string | null
  isTrending?: boolean
  reason?: string | null
}

/**
 * Huy hiệu hiển thị Bậc Ưu tiên Ngành Xu Hướng (tìm kiếm bởi Admin Trend Agent).
 */
export function TrendBadge({ tier, isTrending, reason }: TrendBadgeProps) {
  if (!isTrending || !tier || tier === "NONE") return null

  const normalized = String(tier).toUpperCase()

  if (normalized === "TIER_1") {
    return (
      <span
        title={reason || "Xu hướng Bậc 1 · Ưu tiên Cao nhất"}
        className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-r from-sky-500 to-cyan-500 px-2 py-0.5 text-[10px] font-extrabold text-white shadow-2xs"
      >
        <Flame className="size-3" />
        Xu hướng Bậc 1
      </span>
    )
  }

  if (normalized === "TIER_2") {
    return (
      <span
        title={reason || "Xu hướng Bậc 2 · Tăng trưởng Mạnh"}
        className="inline-flex items-center gap-1 rounded-lg border border-sky-300 bg-sky-50 px-2 py-0.5 text-[10px] font-extrabold text-sky-800"
      >
        <TrendingUp className="size-3 text-sky-600" />
        Xu hướng Bậc 2
      </span>
    )
  }

  return (
    <span
      title={reason || "Xu hướng Bậc 3 · Triển vọng Ổn định"}
      className="inline-flex items-center gap-1 rounded-lg border border-cyan-200 bg-cyan-50/90 px-2 py-0.5 text-[10px] font-bold text-cyan-800"
    >
      <Sparkles className="size-3 text-cyan-600" />
      Xu hướng Bậc 3
    </span>
  )
}
