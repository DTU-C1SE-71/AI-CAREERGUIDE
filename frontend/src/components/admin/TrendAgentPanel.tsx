import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Flame,
  Globe,
  Loader2,
  Radar,
  Trash2,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { readStorage } from "../../services/storage"
import { Button } from "../common/Button"
import { TrendBadge } from "../xai/TrendBadge"

interface TrendSourceLink {
  title: string
  url: string
  source?: string
  published_at?: string
}

interface MarkedTrendingMajor {
  major_code: string
  major_name: string
  category?: string
  trend_tier: "TIER_1" | "TIER_2" | "TIER_3"
  trend_priority: number
  trend_label: string
  trend_score: number
  trend_reason: string
  trend_sources?: TrendSourceLink[]
}

interface TrendAgentStatusPayload {
  status?: string
  message?: string
  has_run?: boolean
  last_run_at?: string | null
  triggered_by?: string | null
  focus_query?: string
  articles_scanned?: number
  total_trending_marked?: number
  tier_counts?: { TIER_1?: number; TIER_2?: number; TIER_3?: number }
  trending_majors?: MarkedTrendingMajor[]
  search_sources?: TrendSourceLink[]
  elapsed_ms?: number
}

interface TrendAgentPanelProps {
  onNotify: (msg: string, error?: boolean) => void
}

function formatRunTime(iso?: string | null): string {
  if (!iso) return "Chưa chạy"
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
  } catch {
    return iso
  }
}

export function TrendAgentPanel({ onNotify }: TrendAgentPanelProps) {
  const [statusData, setStatusData] = useState<TrendAgentStatusPayload | null>(null)
  const [focusQuery, setFocusQuery] = useState(
    "ngành nghề xu hướng khát nhân lực Việt Nam",
  )
  const [running, setRunning] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [updatingCode, setUpdatingCode] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [tierFilter, setTierFilter] = useState<"ALL" | "TIER_1" | "TIER_2" | "TIER_3">("ALL")

  useEffect(() => {
    let mounted = true
    fetch("/api/v1/taxonomy/trend-agent/status")
      .then((r) => (r.ok ? r.json() : null))
      .then((res: TrendAgentStatusPayload | null) => {
        if (mounted && res) {
          setStatusData(res)
          if (res.focus_query) setFocusQuery(res.focus_query)
          if ((res.total_trending_marked || 0) > 0) setExpanded(true)
        }
      })
      .catch(() => {})
    return () => {
      mounted = false
    }
  }, [])

  const getAdminAuthHeader = (): Record<string, string> => {
    const token = readStorage<string | null>("career-guide:token", null)
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const handleRunAgent = async () => {
    setRunning(true)
    try {
      const res = await fetch("/api/v1/taxonomy/trend-agent/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAdminAuthHeader(),
        },
        body: JSON.stringify({
          focus_query: focusQuery.trim() || "ngành nghề xu hướng khát nhân lực Việt Nam",
        }),
      })
      if (res.status === 401 || res.status === 403) {
        onNotify(
          "Cần đăng nhập lại bằng tài khoản Admin (JWT hợp lệ) để chạy Agent tìm kiếm.",
          true,
        )
        return
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.detail || `Lỗi HTTP ${res.status}`)
      }
      const data: TrendAgentStatusPayload = await res.json()
      setStatusData({ ...data, has_run: true })
      setExpanded(true)
      onNotify(
        data.message ||
          `Đã đánh dấu ${data.total_trending_marked ?? 0} ngành xu hướng từ Internet!`,
      )
    } catch (err) {
      onNotify(
        err instanceof Error ? err.message : "Không thể chạy Agent tìm xu hướng.",
        true,
      )
    } finally {
      setRunning(false)
    }
  }

  const handleTierChange = async (majorCode: string, nextTier: string) => {
    setUpdatingCode(majorCode)
    try {
      const res = await fetch(`/api/v1/taxonomy/trend-agent/majors/${majorCode}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...getAdminAuthHeader(),
        },
        body: JSON.stringify({ trend_tier: nextTier }),
      })
      if (res.status === 401 || res.status === 403) {
        onNotify("Phiên quản trị không hợp lệ. Vui lòng đăng nhập lại tài khoản Admin.", true)
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const updated: TrendAgentStatusPayload = await res.json()
      setStatusData(updated)
      onNotify(`Đã cập nhật bậc xu hướng cho mã ${majorCode}.`)
    } catch {
      onNotify("Không cập nhật được bậc ưu tiên ngành.", true)
    } finally {
      setUpdatingCode(null)
    }
  }

  const handleClearTrends = async () => {
    setClearing(true)
    try {
      const res = await fetch("/api/v1/taxonomy/trend-agent/clear", {
        method: "DELETE",
        headers: { ...getAdminAuthHeader() },
      })
      if (res.status === 401 || res.status === 403) {
        onNotify("Cần quyền Admin để xóa đánh dấu xu hướng.", true)
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const cleared: TrendAgentStatusPayload = await res.json()
      setStatusData(cleared)
      setExpanded(false)
      onNotify("Đã xóa toàn bộ đánh dấu ngành xu hướng.")
    } catch {
      onNotify("Không thể xóa đánh dấu xu hướng.", true)
    } finally {
      setClearing(false)
    }
  }

  const trendingList = statusData?.trending_majors || []
  const filteredMajors = useMemo(() => {
    if (tierFilter === "ALL") return trendingList
    return trendingList.filter((m) => m.trend_tier === tierFilter)
  }, [trendingList, tierFilter])

  const counts = statusData?.tier_counts || {}
  const totalMarked = statusData?.total_trending_marked || 0

  return (
    <div className="glass-card mb-5 rounded-3xl p-4">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-xs">
            {running ? <Loader2 size={19} className="animate-spin" /> : <Radar size={19} />}
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-black text-slate-900">
                AI Agent Tìm Ngành Xu Hướng Trên Mạng
              </h2>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[10px] font-extrabold text-sky-700">
                Chỉ chạy khi Admin bấm nút
              </span>
              {totalMarked > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2.5 py-0.5 text-[10px] font-extrabold text-white">
                  <Flame size={11} />
                  {totalMarked} ngành đang ưu tiên
                </span>
              )}
            </div>
            <p className="mt-0.5 text-[11px] font-medium text-slate-500">
              {totalMarked > 0
                ? `Bậc 1: ${counts.TIER_1 || 0} · Bậc 2: ${counts.TIER_2 || 0} · Bậc 3: ${counts.TIER_3 || 0} · Cập nhật: ${formatRunTime(statusData?.last_run_at)} (${statusData?.articles_scanned || 0} tin)`
                : "Agent sẽ tìm tin tức thị trường lao động trực tuyến, phân 3 bậc ưu tiên và đánh dấu vào dữ liệu ngành để đẩy các ngành xu hướng lên đầu khi đề xuất."}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Globe size={14} className="absolute left-3 top-2.5 text-sky-500" />
            <input
              value={focusQuery}
              onChange={(e) => setFocusQuery(e.target.value)}
              placeholder="Từ khóa xu hướng..."
              className="h-9 w-64 rounded-xl border border-slate-200 bg-white/90 pl-8 pr-3 text-xs font-semibold text-slate-800 outline-none focus:border-sky-400"
            />
          </div>

          <Button
            onClick={handleRunAgent}
            loading={running}
            icon={Radar}
            className="!min-h-9 !px-4 !text-xs"
          >
            {running ? "Đang tìm trên mạng..." : "Chạy Agent Tìm Xu Hướng"}
          </Button>

          {totalMarked > 0 && (
            <>
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="inline-flex h-9 items-center gap-1 rounded-xl border border-slate-200 bg-white/85 px-3 text-xs font-bold text-slate-700 hover:bg-white cursor-pointer"
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {expanded ? "Thu gọn" : `Xem ${totalMarked} ngành`}
              </button>
              <button
                type="button"
                disabled={clearing}
                onClick={handleClearTrends}
                title="Xóa toàn bộ đánh dấu xu hướng"
                className="inline-flex h-9 items-center gap-1 rounded-xl border border-slate-200 bg-white/85 px-2.5 text-xs font-bold text-slate-500 hover:border-rose-200 hover:text-rose-600 disabled:opacity-50 cursor-pointer"
              >
                <Trash2 size={13} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Expanded Results Table */}
      {expanded && totalMarked > 0 && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-sky-200/80 bg-white/90">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-sky-50/70 px-3.5 py-2.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {(
                [
                  { id: "ALL", label: `Tất cả (${totalMarked})` },
                  { id: "TIER_1", label: `Bậc 1 · Cao nhất (${counts.TIER_1 || 0})` },
                  { id: "TIER_2", label: `Bậc 2 · Tăng trưởng (${counts.TIER_2 || 0})` },
                  { id: "TIER_3", label: `Bậc 3 · Ổn định (${counts.TIER_3 || 0})` },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setTierFilter(tab.id)}
                  className={`rounded-lg px-2.5 py-1 text-[11px] font-extrabold transition cursor-pointer ${
                    tierFilter === tab.id
                      ? "bg-sky-600 text-white shadow-2xs"
                      : "bg-white text-slate-600 hover:bg-sky-50"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {statusData?.search_sources && statusData.search_sources.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                <span className="font-bold text-slate-500">Nguồn tin:</span>
                {statusData.search_sources.slice(0, 3).map((src, i) => (
                  <a
                    key={i}
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex max-w-[160px] items-center gap-1 truncate rounded-md border border-sky-200 bg-white px-2 py-0.5 font-semibold text-sky-700 hover:underline"
                    title={src.title}
                  >
                    <span className="truncate">{src.source || src.title}</span>
                    <ExternalLink size={10} className="shrink-0" />
                  </a>
                ))}
              </div>
            )}
          </div>

          <div className="max-h-[340px] overflow-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] font-extrabold uppercase text-slate-500 shadow-2xs">
                <tr>
                  <th className="w-10 border-b border-slate-200 px-3 py-2 text-center">STT</th>
                  <th className="border-b border-slate-200 px-3 py-2">Mã</th>
                  <th className="border-b border-slate-200 px-3 py-2 min-w-[190px]">Ngành đào tạo</th>
                  <th className="border-b border-slate-200 px-3 py-2 min-w-[140px]">Bậc ưu tiên</th>
                  <th className="border-b border-slate-200 px-3 py-2">Phân tích xu hướng & Nguồn</th>
                  <th className="border-b border-slate-200 px-3 py-2 text-right">Điều chỉnh</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredMajors.map((item, idx) => (
                  <tr key={item.major_code} className="hover:bg-sky-50/40">
                    <td className="px-3 py-2 text-center font-bold text-slate-500">{idx + 1}</td>
                    <td className="px-3 py-2 font-mono font-bold text-sky-700">
                      {item.major_code}
                    </td>
                    <td className="px-3 py-2">
                      <p className="font-bold text-slate-900">{item.major_name}</p>
                      <p className="text-[10px] text-slate-400">{item.category}</p>
                    </td>
                    <td className="px-3 py-2">
                      <TrendBadge
                        tier={item.trend_tier}
                        isTrending={true}
                        reason={item.trend_reason}
                      />
                    </td>
                    <td className="px-3 py-2 text-[11px] text-slate-600">
                      <p>{item.trend_reason}</p>
                      {item.trend_sources && item.trend_sources.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {item.trend_sources.slice(0, 2).map((s, si) => (
                            <a
                              key={si}
                              href={s.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-0.5 text-[10px] font-bold text-sky-600 hover:underline"
                            >
                              [{s.source || "Nguồn"}] <ExternalLink size={9} />
                            </a>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <select
                        disabled={updatingCode === item.major_code}
                        value={item.trend_tier}
                        onChange={(e) => handleTierChange(item.major_code, e.target.value)}
                        className="h-7 rounded-lg border border-slate-200 bg-white px-2 text-[11px] font-bold text-slate-700 outline-none focus:border-sky-400"
                      >
                        <option value="TIER_1">Bậc 1 (Cao nhất)</option>
                        <option value="TIER_2">Bậc 2 (Mạnh)</option>
                        <option value="TIER_3">Bậc 3 (Ổn định)</option>
                        <option value="NONE">Bỏ đánh dấu</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
