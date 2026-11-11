import {
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  Flame,
  Globe,
  Layers,
  Loader2,
  Radar,
  RotateCcw,
  Trash2,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
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
  pending_save?: boolean
  saved_to_db?: boolean
  saved_at?: string | null
  last_run_at?: string | null
  triggered_by?: string | null
  focus_query?: string
  articles_scanned?: number
  total_trending_marked?: number
  categories_covered?: number
  total_categories?: number
  llm_refined?: boolean
  tier_counts?: { TIER_1?: number; TIER_2?: number; TIER_3?: number }
  trending_majors?: MarkedTrendingMajor[]
  search_sources?: TrendSourceLink[]
  elapsed_ms?: number
}

interface TrendAgentPanelProps {
  onNotify: (msg: string, error?: boolean) => void
}

const DRAFT_TIER_META: Record<
  "TIER_1" | "TIER_2" | "TIER_3",
  { priority: number; label: string; score: number }
> = {
  TIER_1: {
    priority: 1,
    label: "Xu hướng Bậc 1 (Ưu tiên cao nhất)",
    score: 95,
  },
  TIER_2: {
    priority: 2,
    label: "Xu hướng Bậc 2 (Tăng trưởng mạnh)",
    score: 80,
  },
  TIER_3: {
    priority: 3,
    label: "Xu hướng Bậc 3 (Triển vọng ổn định)",
    score: 65,
  },
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
    "ngành nghề xu hướng khát nhân lực Việt Nam 2026",
  )
  const [running, setRunning] = useState(false)
  const [savingToDb, setSavingToDb] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [updatingCode, setUpdatingCode] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [tierFilter, setTierFilter] = useState<"ALL" | "TIER_1" | "TIER_2" | "TIER_3">("ALL")

  const loadSavedStatus = useCallback(async () => {
    try {
      const r = await fetch("/api/v1/taxonomy/trend-agent/status")
      if (!r.ok) return
      const res: TrendAgentStatusPayload = await r.json()
      setStatusData(res)
      if (res.focus_query) setFocusQuery(res.focus_query)
      if ((res.total_trending_marked || 0) > 0) setExpanded(true)
    } catch {
      // ignore initial load error
    }
  }, [])

  useEffect(() => {
    void loadSavedStatus()
  }, [loadSavedStatus])

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
          focus_query: focusQuery.trim() || "ngành nghề xu hướng khát nhân lực Việt Nam 2026",
          auto_save: false,
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
      setStatusData({
        ...data,
        has_run: true,
        pending_save: data.pending_save ?? true,
        saved_to_db: data.saved_to_db ?? false,
      })
      setExpanded(true)
      onNotify(
        data.message ||
          `Đã tạo bản nháp ${data.total_trending_marked ?? 0} ngành xu hướng phủ ${data.categories_covered ?? 0}/${data.total_categories ?? 23} nhóm ngành. Hãy rà soát và bấm "Lưu vào CSDL".`,
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

  const handleSaveToDb = async () => {
    const list = statusData?.trending_majors || []
    if (list.length === 0) {
      onNotify("Không có ngành xu hướng nào trong bản nháp để lưu.", true)
      return
    }
    setSavingToDb(true)
    try {
      const res = await fetch("/api/v1/taxonomy/trend-agent/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAdminAuthHeader(),
        },
        body: JSON.stringify({
          focus_query: statusData?.focus_query || focusQuery.trim(),
          articles_scanned: statusData?.articles_scanned || 0,
          search_sources: statusData?.search_sources || [],
          majors: list.map((m) => ({
            major_code: m.major_code,
            major_name: m.major_name,
            category: m.category,
            trend_tier: m.trend_tier,
            trend_score: m.trend_score,
            trend_reason: m.trend_reason,
            trend_sources: m.trend_sources || [],
          })),
        }),
      })
      if (res.status === 401 || res.status === 403) {
        onNotify(
          "Cần đăng nhập lại bằng tài khoản Admin (JWT hợp lệ) để lưu dữ liệu vào CSDL.",
          true,
        )
        return
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.detail || `Lỗi HTTP ${res.status}`)
      }
      const saved: TrendAgentStatusPayload = await res.json()
      setStatusData({
        ...saved,
        has_run: true,
        pending_save: false,
        saved_to_db: true,
      })
      onNotify(
        saved.message ||
          `Đã lưu ${saved.total_trending_marked ?? list.length} ngành xu hướng vào CSDL cho hệ thống Đề xuất ngành.`,
      )
    } catch (err) {
      onNotify(
        err instanceof Error ? err.message : "Không thể lưu danh sách xu hướng vào CSDL.",
        true,
      )
    } finally {
      setSavingToDb(false)
    }
  }

  const handleDiscardDraft = async () => {
    await loadSavedStatus()
    onNotify("Đã hủy bản nháp và khôi phục dữ liệu xu hướng đang lưu trong CSDL.")
  }

  const handleTierChange = async (majorCode: string, nextTier: string) => {
    if (statusData?.pending_save) {
      const currentList = statusData.trending_majors || []
      const nextList: MarkedTrendingMajor[] =
        nextTier === "NONE"
          ? currentList.filter((m) => m.major_code !== majorCode)
          : currentList
              .map((m) => {
                if (m.major_code !== majorCode) return m
                const tierKey = nextTier as "TIER_1" | "TIER_2" | "TIER_3"
                const meta = DRAFT_TIER_META[tierKey]
                return {
                  ...m,
                  trend_tier: tierKey,
                  trend_priority: meta.priority,
                  trend_label: meta.label,
                  trend_score: meta.score,
                }
              })
              .sort(
                (a, b) =>
                  (a.trend_priority || 9) - (b.trend_priority || 9) ||
                  (b.trend_score || 0) - (a.trend_score || 0),
              )

      const nextCounts = {
        TIER_1: nextList.filter((m) => m.trend_tier === "TIER_1").length,
        TIER_2: nextList.filter((m) => m.trend_tier === "TIER_2").length,
        TIER_3: nextList.filter((m) => m.trend_tier === "TIER_3").length,
      }
      const coveredCats = new Set(nextList.map((m) => m.category).filter(Boolean)).size
      setStatusData({
        ...statusData,
        trending_majors: nextList,
        total_trending_marked: nextList.length,
        tier_counts: nextCounts,
        categories_covered: coveredCats,
      })
      onNotify(
        nextTier === "NONE"
          ? `Đã loại mã ${majorCode} khỏi bản nháp. Bấm "Lưu vào CSDL" để xác nhận.`
          : `Đã điều chỉnh bậc nháp cho mã ${majorCode}. Bấm "Lưu vào CSDL" để áp dụng.`,
      )
      return
    }

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
      onNotify(`Đã cập nhật bậc xu hướng cho mã ${majorCode} trong CSDL.`)
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
  const isDraft = Boolean(statusData?.pending_save)
  const isSavedInDb = Boolean(statusData?.saved_to_db) || (!isDraft && totalMarked > 0)
  const totalCategories = statusData?.total_categories || 23
  const coveredCategories =
    statusData?.categories_covered ??
    new Set(trendingList.map((m) => m.category).filter(Boolean)).size

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
                AI Agent Tìm Ngành Xu Hướng Trên Mạng (Macro Level Trend)
              </h2>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[10px] font-extrabold text-sky-700">
                Chỉ chạy khi Admin bấm nút
              </span>
              {isDraft && (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-[10px] font-extrabold text-amber-800">
                  Bản nháp chờ lưu CSDL
                </span>
              )}
              {isSavedInDb && (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-700">
                  <Database size={11} />
                  Đã lưu CSDL · Đề xuất đọc trực tiếp
                </span>
              )}
              {totalMarked > 0 && (
                <>
                  <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2.5 py-0.5 text-[10px] font-extrabold text-white">
                    <Flame size={11} />
                    {totalMarked} ngành đại diện
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[10px] font-extrabold text-indigo-700">
                    <Layers size={11} />
                    Phủ {coveredCategories}/{totalCategories} nhóm ngành
                  </span>
                </>
              )}
            </div>
            <p className="mt-0.5 text-[11px] font-medium text-slate-500">
              {totalMarked > 0
                ? `Bậc 1: ${counts.TIER_1 || 0} · Bậc 2: ${counts.TIER_2 || 0} · Bậc 3: ${counts.TIER_3 || 0} · ${
                    statusData?.saved_at && !isDraft
                      ? `Lưu CSDL: ${formatRunTime(statusData.saved_at)}`
                      : `Quét lúc: ${formatRunTime(statusData?.last_run_at)}`
                  } (${statusData?.articles_scanned || 0} tin) · Nguồn đề xuất: CSDL`
                : "Agent tìm tin tức thị trường lao động năm 2026, phân hạng theo thang đo vĩ mô toàn thị trường phủ 100% nhóm ngành (tối thiểu 3 ngành/nhóm; nhóm xu hướng cao 4–6 ngành). Admin bấm Lưu vào CSDL để lưu cố định."}
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

          {isDraft && totalMarked > 0 && (
            <>
              <button
                type="button"
                disabled={savingToDb}
                onClick={handleSaveToDb}
                className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 text-xs font-extrabold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50 cursor-pointer"
              >
                {savingToDb ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Database size={14} />
                )}
                {savingToDb ? "Đang lưu CSDL..." : `Lưu vào CSDL (${totalMarked} ngành)`}
              </button>
              <button
                type="button"
                disabled={savingToDb}
                onClick={handleDiscardDraft}
                title="Hủy bản nháp và khôi phục dữ liệu CSDL hiện tại"
                className="inline-flex h-9 items-center gap-1 rounded-xl border border-amber-300 bg-amber-50 px-3 text-xs font-bold text-amber-800 hover:bg-amber-100 disabled:opacity-50 cursor-pointer"
              >
                <RotateCcw size={13} />
                Hủy nháp
              </button>
            </>
          )}

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
              {!isDraft && (
                <button
                  type="button"
                  disabled={clearing}
                  onClick={handleClearTrends}
                  title="Xóa toàn bộ đánh dấu xu hướng trong CSDL"
                  className="inline-flex h-9 items-center gap-1 rounded-xl border border-slate-200 bg-white/85 px-2.5 text-xs font-bold text-slate-500 hover:border-rose-200 hover:text-rose-600 disabled:opacity-50 cursor-pointer"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Draft Confirmation Banner */}
      {isDraft && totalMarked > 0 && (
        <div className="mt-3 flex flex-col justify-between gap-2 rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-2.5 text-xs text-amber-900 sm:flex-row sm:items-center">
          <div>
            <span className="font-extrabold">Bản nháp phân hạng vĩ mô chưa lưu vào CSDL: </span>
            <span>
              Đã quét phủ {coveredCategories}/{totalCategories} nhóm ngành theo thang đo vĩ mô toàn thị trường (không đôn ép nhóm ít nhu cầu lên Bậc 1). Hãy rà soát lại các bậc và bấm{" "}
              <strong>&ldquo;Lưu vào CSDL&rdquo;</strong> để hệ thống đề xuất ngành cho học sinh đọc trực tiếp từ DB.
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              disabled={savingToDb}
              onClick={handleSaveToDb}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-emerald-600 px-3 text-[11px] font-extrabold text-white hover:bg-emerald-700 disabled:opacity-50 cursor-pointer"
            >
              <Database size={13} />
              Lưu vào CSDL ({totalMarked} ngành)
            </button>
            <button
              type="button"
              disabled={savingToDb}
              onClick={handleDiscardDraft}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-amber-300 bg-white px-2.5 text-[11px] font-bold text-amber-800 hover:bg-amber-100 cursor-pointer"
            >
              Hủy bản nháp
            </button>
          </div>
        </div>
      )}

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

          <div className="max-h-[380px] overflow-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] font-extrabold uppercase text-slate-500 shadow-2xs">
                <tr>
                  <th className="w-10 border-b border-slate-200 px-3 py-2 text-center">STT</th>
                  <th className="border-b border-slate-200 px-3 py-2 min-w-[160px]">Nhóm ngành</th>
                  <th className="border-b border-slate-200 px-3 py-2 min-w-[200px]">
                    Ngành xu hướng đại diện
                  </th>
                  <th className="border-b border-slate-200 px-3 py-2 min-w-[155px]">
                    Cấp độ xu hướng vĩ mô
                  </th>
                  <th className="border-b border-slate-200 px-3 py-2">Phân tích xu hướng & Nguồn</th>
                  <th className="border-b border-slate-200 px-3 py-2 text-right">Điều chỉnh</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredMajors.map((item, idx) => (
                  <tr key={item.major_code} className="hover:bg-sky-50/40">
                    <td className="px-3 py-2 text-center font-bold text-slate-500">{idx + 1}</td>
                    <td className="px-3 py-2">
                      <span className="inline-block rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                        {item.category || "Chưa phân nhóm"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <p className="font-bold text-slate-900">{item.major_name}</p>
                      <p className="font-mono text-[10px] font-bold text-sky-700">
                        Mã ngành: {item.major_code}
                      </p>
                    </td>
                    <td className="px-3 py-2">
                      <TrendBadge
                        tier={item.trend_tier}
                        isTrending={true}
                        reason={item.trend_reason}
                      />
                      <p className="mt-1 text-[10px] font-semibold text-slate-400">
                        Thang vĩ mô: {item.trend_score}/100
                      </p>
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
                        disabled={updatingCode === item.major_code || savingToDb}
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
