import { AnimatePresence, motion } from "framer-motion"
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  Flame,
  Globe,
  Info,
  Layers,
  Loader2,
  Radar,
  RotateCcw,
  Sparkles,
  Trash2,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState, useRef } from "react"
import { readStorage } from "../../services/storage"
import { apiFetch } from "../../services/api"
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

const DEFAULT_TREND_QUERY_2026 =
  "dự báo nhu cầu nhân lực thị trường lao động Việt Nam 2026 ngành mũi nhọn AI bán dẫn y tế kinh tế xanh"

const TREND_QUERY_PRESETS: Array<{ label: string; query: string }> = [
  {
    label: "Toàn cảnh Nhân lực 2026",
    query: DEFAULT_TREND_QUERY_2026,
  },
  {
    label: "AI, Bán dẫn & An ninh mạng 2026",
    query:
      "xu hướng tuyển dụng Việt Nam 2026 trí tuệ nhân tạo AI thiết kế vi mạch bán dẫn an ninh mạng khoa học dữ liệu",
  },
  {
    label: "Fintech, Thương mại & Logistics 2026",
    query:
      "nhu cầu nhân lực 2026 Fintech tài chính số thương mại điện tử logistics chuỗi cung ứng kinh tế số Việt Nam",
  },
  {
    label: "Y tế, Kỹ thuật Xanh & Giáo dục 2026",
    query:
      "thiếu hụt nhân lực 2026 y khoa điều dưỡng robot tự động hóa năng lượng tái tạo ESG giáo dục STEM Việt Nam",
  },
]

const SMOOTH_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

export function TrendAgentPanel({ onNotify }: TrendAgentPanelProps) {
  const [statusData, setStatusData] = useState<TrendAgentStatusPayload | null>(null)
  const [focusQuery, setFocusQuery] = useState(DEFAULT_TREND_QUERY_2026)
  const [running, setRunning] = useState(false)
  const [savingToDb, setSavingToDb] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [updatingCode, setUpdatingCode] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [tierFilter, setTierFilter] = useState<"ALL" | "TIER_1" | "TIER_2" | "TIER_3">("ALL")
  const [showMethodology, setShowMethodology] = useState(false)
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({})
  const [showAllSources, setShowAllSources] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const mounted = useRef(true)
  const operation = useRef(false)


  const loadSavedStatus = useCallback(async () => {
    setLoading(true); setLoadError(null)
    try {
      const r = await apiFetch("/api/v1/taxonomy/trend-agent/status")
      if (!r.ok) throw new Error(`Không tải được trạng thái xu hướng (HTTP ${r.status}).`)
      const res: TrendAgentStatusPayload = await r.json()
      if (!mounted.current) return
      setStatusData(res)
      if (res.focus_query && /202[6-9]/.test(res.focus_query)) {
        setFocusQuery(res.focus_query)
      }
      if ((res.total_trending_marked || 0) > 0) setExpanded(true)
    } catch (error) {
      if (mounted.current) setLoadError(error instanceof Error ? error.message : "Không tải được trạng thái xu hướng.")
      throw error
    } finally { if (mounted.current) setLoading(false) }
  }, [])

  useEffect(() => {
    mounted.current = true
    void loadSavedStatus().catch(() => {})
    return () => { mounted.current = false }
  }, [loadSavedStatus])

  const getAdminAuthHeader = (): Record<string, string> => {
    const token = readStorage<string | null>("career-guide:token", null)
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const handleRunAgent = async () => {
    if (operation.current) return
    operation.current = true
    setRunning(true)
    try {
      const res = await apiFetch("/api/v1/taxonomy/trend-agent/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAdminAuthHeader(),
        },
        body: JSON.stringify({
          focus_query: focusQuery.trim() || DEFAULT_TREND_QUERY_2026,
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
      if (!mounted.current) return
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
      operation.current = false
      if (mounted.current) setRunning(false)
    }
  }

  const handleSaveToDb = async () => {
    const list = statusData?.trending_majors || []
    if (list.length === 0) {
      onNotify("Không có ngành xu hướng nào trong bản nháp để lưu.", true)
      return
    }
    if (operation.current) return
    operation.current = true
    setSavingToDb(true)
    try {
      const res = await apiFetch("/api/v1/taxonomy/trend-agent/save", {
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
      if (!mounted.current) return
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
      operation.current = false
      if (mounted.current) setSavingToDb(false)
    }
  }

  const handleDiscardDraft = async () => {
    try { await loadSavedStatus(); onNotify("Đã tải lại dữ liệu xu hướng đang lưu trong CSDL.") }
    catch { onNotify("Chưa tải được dữ liệu đang lưu. Bản nháp chưa bị thay đổi.", true) }
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

    if (operation.current) return
    operation.current = true
    setUpdatingCode(majorCode)
    try {
      const res = await apiFetch(`/api/v1/taxonomy/trend-agent/majors/${majorCode}`, {
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
      if (!mounted.current) return
      setStatusData(updated)
      onNotify(`Đã cập nhật bậc xu hướng cho mã ${majorCode} trong CSDL.`)
    } catch {
      onNotify("Không cập nhật được bậc ưu tiên ngành.", true)
    } finally {
      operation.current = false
      if (mounted.current) setUpdatingCode(null)
    }
  }

  const handleClearTrends = async () => {
    if (operation.current || !window.confirm("Xóa các đánh dấu xu hướng đang lưu?")) return
    operation.current = true
    setClearing(true)
    try {
      const res = await apiFetch("/api/v1/taxonomy/trend-agent/clear", {
        method: "DELETE",
        headers: { ...getAdminAuthHeader() },
      })
      if (res.status === 401 || res.status === 403) {
        onNotify("Cần quyền Admin để xóa đánh dấu xu hướng.", true)
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const cleared: TrendAgentStatusPayload = await res.json()
      if (!mounted.current) return
      setStatusData(cleared)
      setExpanded(false)
      onNotify("Đã xóa toàn bộ đánh dấu ngành xu hướng.")
    } catch {
      onNotify("Không thể xóa đánh dấu xu hướng.", true)
    } finally {
      operation.current = false
      if (mounted.current) setClearing(false)
    }
  }

  const trendingList = useMemo(() => statusData?.trending_majors || [], [statusData])
  const filteredMajors = useMemo(() => trendingList.filter(item => (tierFilter === "ALL" || item.trend_tier === tierFilter) && `${item.major_name} ${item.major_code} ${item.category || ""}`.toLocaleLowerCase("vi").includes(search.trim().toLocaleLowerCase("vi"))), [trendingList, tierFilter, search])
  const totalPages = Math.max(1, Math.ceil(filteredMajors.length / 25))
  const currentPage = Math.min(page, totalPages)
  const pageRows = filteredMajors.slice((currentPage - 1) * 25, currentPage * 25)

  const counts = statusData?.tier_counts || {}
  const totalMarked = statusData?.total_trending_marked || 0
  const isDraft = Boolean(statusData?.pending_save)
  const isSavedInDb = Boolean(statusData?.saved_to_db) || (!isDraft && totalMarked > 0)
  const totalCategories = statusData?.total_categories || 23
  const coveredCategories =
    statusData?.categories_covered ??
    new Set(trendingList.map((m) => m.category).filter(Boolean)).size

  const toggleCitation = (code: string) => {
    setExpandedCitations((prev) => ({ ...prev, [code]: !prev[code] }))
  }

  return (
    <div className="glass-card mb-5 rounded-3xl p-4 sm:p-5">
      {loading && <p role="status" className="mb-4 text-sm text-slate-600">Đang tải dữ liệu xu hướng…</p>}
      {loadError && <div role="alert" className="admin-notice is-error"><span>{loadError}</span><button type="button" className="admin-button" onClick={() => void loadSavedStatus().catch(() => {})}>Thử lại</button></div>}
      {!loading && !loadError && totalMarked === 0 && <p className="mb-4 text-sm text-slate-600">Chưa có danh sách xu hướng được lưu. Chạy tìm kiếm để tạo bản nháp và rà soát nguồn.</p>}
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
        <div className="flex items-start gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-xs">
            {running ? <Loader2 size={20} className="animate-spin" /> : <Radar size={20} />}
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                Trợ lý Navi - Tìm Ngành Xu Hướng Thị Trường Lao Động 2026
              </h2>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">
                Chạy thủ công theo nhu cầu Admin
              </span>
              {isDraft && (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-800">
                  Bản nháp chờ lưu CSDL
                </span>
              )}
              {isSavedInDb && (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-700">
                  <Database size={13} />
                  Đã lưu CSDL · Đề xuất đọc trực tiếp
                </span>
              )}
              {totalMarked > 0 && (
                <>
                  <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2.5 py-0.5 text-xs font-bold text-white tabular-nums">
                    <Flame size={12} />
                    {totalMarked} ngành đại diện
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-cyan-200 bg-cyan-50 px-2.5 py-0.5 text-xs font-bold text-cyan-800 tabular-nums">
                    <Layers size={12} />
                    Phủ {coveredCategories}/{totalCategories} nhóm ngành
                  </span>
                </>
              )}
            </div>

            {totalMarked > 0 ? (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50/70 px-2 py-0.5 font-bold text-emerald-800 tabular-nums">
                  Bậc 1: {counts.TIER_1 || 0}
                </span>
                <span className="inline-flex items-center gap-1 rounded-md border border-sky-200 bg-sky-50/70 px-2 py-0.5 font-bold text-sky-800 tabular-nums">
                  Bậc 2: {counts.TIER_2 || 0}
                </span>
                <span className="inline-flex items-center gap-1 rounded-md border border-cyan-200 bg-cyan-50/70 px-2 py-0.5 font-bold text-cyan-800 tabular-nums">
                  Bậc 3: {counts.TIER_3 || 0}
                </span>
                <span className="text-slate-500 font-medium tabular-nums">
                  · {statusData?.articles_scanned || 0} bài báo thị trường
                </span>
                <span className="text-slate-400 font-medium tabular-nums">
                  · {statusData?.saved_at && !isDraft
                    ? `Lưu CSDL: ${formatRunTime(statusData.saved_at)}`
                    : `Quét lúc: ${formatRunTime(statusData?.last_run_at)}`}
                </span>
                <button
                  type="button"
                  onClick={() => setShowMethodology((v) => !v)}
                  className="ml-auto inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900 cursor-pointer"
                >
                  <Info size={13} className="text-sky-600" />
                  <span>Tiêu chí vĩ mô</span>
                  {showMethodology ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
              </div>
            ) : (
              <p className="mt-1 text-xs text-slate-500 font-medium">
                Agent tự động quét dữ liệu tuyển dụng 2026, đánh giá bao phủ 23 nhóm ngành MOET theo thang đo vĩ mô toàn thị trường.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Collapsible Methodology Panel */}
      <AnimatePresence initial={false}>
        {showMethodology && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: SMOOTH_EASE }}
            className="overflow-hidden"
          >
            <div className="mt-3 rounded-2xl border border-sky-200/80 bg-sky-50/50 p-4 text-xs text-slate-700 space-y-2">
              <div className="flex items-center gap-2 font-bold text-sky-950">
                <Sparkles size={15} className="text-sky-600" />
                <span>Quy trình Đánh giá Xu hướng Vĩ mô (Macro Level Trend 2026)</span>
              </div>
              <p className="leading-relaxed text-slate-600">
                Thuật toán phân tích tin tức thị trường lao động từ 65 nguồn tin báo chí chính thống và dữ liệu O*NET/CIP. Phân bổ đại diện tối thiểu 3 ngành/nhóm và 4–6 ngành cho các nhóm xu hướng cao (Công nghệ thông tin, Bán dẫn, Y tế, Kinh tế số).
              </p>
              <div className="grid gap-2 sm:grid-cols-3 pt-1">
                <div className="rounded-xl border border-emerald-200 bg-white p-2.5">
                  <span className="font-bold text-emerald-800">Bậc 1 (Mũi nhọn quốc gia):</span>
                  <p className="mt-0.5 text-slate-600">Điểm vĩ mô ≥ 90. Nhu cầu cấp thiết, tăng trưởng đột biến.</p>
                </div>
                <div className="rounded-xl border border-sky-200 bg-white p-2.5">
                  <span className="font-bold text-sky-800">Bậc 2 (Tăng trưởng cao):</span>
                  <p className="mt-0.5 text-slate-600">Điểm vĩ mô 75–89. Thị trường mở rộng mạnh, tuyển dụng liên tục.</p>
                </div>
                <div className="rounded-xl border border-cyan-200 bg-white p-2.5">
                  <span className="font-bold text-cyan-800">Bậc 3 (Ổn định cơ bản):</span>
                  <p className="mt-0.5 text-slate-600">Điểm vĩ mô 60–74. Nhu cầu bền vững, cơ cấu nhân lực dài hạn.</p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Wide Search Prompt Bar + Preset 2026 Chips */}
      <div className="mt-3.5 space-y-2.5 rounded-2xl border border-sky-100 bg-sky-50/50 p-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-0 flex-1">
            <Globe size={15} className="absolute left-3 top-2.5 text-sky-500" />
            <input
              aria-label="Chủ đề tìm xu hướng"
              value={focusQuery}
              onChange={(e) => setFocusQuery(e.target.value)}
              placeholder="Nhập từ khóa xu hướng thị trường lao động 2026..."
              title={focusQuery}
              className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-xs font-semibold text-slate-800 outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
            />
          </div>

          <Button
            onClick={handleRunAgent}
            loading={running}
            disabled={running || savingToDb || clearing || Boolean(updatingCode)}
            icon={Radar}
            className="!min-h-9 !px-4 !text-xs !bg-sky-600 hover:!bg-sky-700 shrink-0"
          >
            {running ? "Đang quét 6 truy vấn 2026..." : "Chạy Agent Tìm Xu Hướng 2026"}
          </Button>

          {isDraft && totalMarked > 0 && (
            <>
              <button
                type="button"
                disabled={savingToDb}
                onClick={handleSaveToDb}
                className="inline-flex h-9 items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50 cursor-pointer shrink-0"
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
                className="inline-flex h-9 items-center gap-1 rounded-xl border border-amber-300 bg-amber-50 px-3 text-xs font-bold text-amber-800 hover:bg-amber-100 disabled:opacity-50 cursor-pointer shrink-0"
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
                className="inline-flex h-9 items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 hover:bg-slate-50 cursor-pointer shrink-0"
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {expanded ? "Thu gọn bảng" : `Xem bảng (${totalMarked} ngành)`}
              </button>
              {!isDraft && (
                <button
                  type="button"
                  disabled={clearing}
                  onClick={handleClearTrends}
                  title="Xóa toàn bộ đánh dấu xu hướng trong CSDL"
                  aria-label="Xóa toàn bộ đánh dấu xu hướng"
                  className="inline-flex h-9 items-center gap-1 rounded-xl border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-500 hover:border-rose-200 hover:text-rose-600 disabled:opacity-50 cursor-pointer shrink-0"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="font-bold text-slate-500">Mẫu tìm kiếm 2026:</span>
          {TREND_QUERY_PRESETS.map((preset) => {
            const active = focusQuery.trim() === preset.query.trim()
            return (
              <button
                key={preset.label}
                type="button"
                onClick={() => setFocusQuery(preset.query)}
                className={`rounded-lg border px-2.5 py-1 font-semibold transition cursor-pointer ${
                  active
                    ? "border-sky-500 bg-sky-600 text-white shadow-2xs"
                    : "border-sky-200 bg-white text-sky-700 hover:bg-sky-50"
                }`}
              >
                {preset.label}
              </button>
            )
          })}
          <span className="ml-auto font-medium text-slate-400 hidden sm:inline">
            Tự mở rộng 6 truy vấn báo chí + Tavily
          </span>
        </div>
      </div>

      {/* Draft Confirmation Banner */}
      {isDraft && totalMarked > 0 && (
        <div className="mt-3 flex flex-col justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-xs text-amber-900 sm:flex-row sm:items-center">
          <div className="leading-relaxed">
            <span className="font-bold">⚠️ Bản nháp phân hạng vĩ mô chưa lưu CSDL: </span>
            <span>
              Đã quét phủ {coveredCategories}/{totalCategories} nhóm ngành. Hãy rà soát danh sách và bấm{" "}
              <strong>&ldquo;Lưu vào CSDL&rdquo;</strong> để tính năng gợi ý ngành cho học sinh áp dụng dữ liệu mới.
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              disabled={savingToDb}
              onClick={handleSaveToDb}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <Database size={13} />
              Lưu vào CSDL ({totalMarked} ngành)
            </button>
            <button
              type="button"
              disabled={savingToDb}
              onClick={handleDiscardDraft}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-amber-300 bg-white px-2.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 cursor-pointer"
            >
              Hủy nháp
            </button>
          </div>
        </div>
      )}

      {/* Expanded Results Table */}
      {expanded && totalMarked > 0 && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-sky-200/80 bg-white/90">
          <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-100 bg-sky-50/70 px-4 py-3">
            <div className="flex flex-wrap items-center gap-1.5">
              {(
                [
                  { id: "ALL", label: `Tất cả (${totalMarked})` },
                  { id: "TIER_1", label: `Bậc 1 · Cao nhất (${counts.TIER_1 || 0})` },
                  { id: "TIER_2", label: `Bậc 2 · Tăng trưởng (${counts.TIER_2 || 0})` },
                  { id: "TIER_3", label: `Bậc 3 · Ổn định (${counts.TIER_3 || 0})` },
                ] as const
              ).map((tab) => {
                const isActive = tierFilter === tab.id
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => { setTierFilter(tab.id); setPage(1) }}
                    className={`relative rounded-lg px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                      isActive ? "text-white shadow-xs" : "bg-white text-slate-600 hover:bg-sky-50"
                    }`}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="trend-tier-filter-tab-pill"
                        transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                        className="absolute inset-0 rounded-lg bg-sky-600"
                      />
                    )}
                    <span className="relative z-10 tabular-nums">{tab.label}</span>
                  </button>
                )
              })}
            </div>

            {statusData?.search_sources && statusData.search_sources.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowAllSources((v) => !v)}
                  className="inline-flex items-center gap-1 rounded-lg border border-sky-200 bg-white px-2.5 py-1 text-xs font-semibold text-sky-700 hover:bg-sky-50 cursor-pointer"
                >
                  <BookOpen size={13} />
                  <span>Nguồn tin đã quét ({statusData.search_sources.length})</span>
                  {showAllSources ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </button>
              </div>
            )}
          </div>

          {/* Scanned Sources Accordion Drawer */}
          <AnimatePresence initial={false}>
            {showAllSources && statusData?.search_sources && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                className="overflow-hidden border-b border-sky-100 bg-sky-50/30 p-3"
              >
                <p className="text-xs font-bold text-slate-700 mb-2">Các bài báo và nguồn tham chiếu thị trường 2026:</p>
                <div className="flex flex-wrap gap-2">
                  {statusData.search_sources.map((src, idx) => (
                    <a
                      key={idx}
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-sky-300 hover:text-sky-700"
                    >
                      <span className="max-w-[240px] truncate">{src.title || src.source}</span>
                      <ExternalLink size={12} className="shrink-0 text-slate-400" />
                    </a>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <label className="admin-field m-4">Tìm ngành xu hướng<input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} /></label>
          <div className="max-h-[460px] overflow-x-auto overflow-y-auto">
            <table className="w-full min-w-[960px] border-collapse text-left text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-600 shadow-2xs border-b border-slate-200">
                <tr>
                  <th className="w-12 px-3 py-3 text-center">STT</th>
                  <th className="px-3 py-3 min-w-[170px]">Nhóm ngành</th>
                  <th className="px-3 py-3 min-w-[220px]">Ngành xu hướng đại diện</th>
                  <th className="px-3 py-3 min-w-[170px]">Cấp độ xu hướng vĩ mô</th>
                  <th className="px-3 py-3">Phân tích xu hướng & Nguồn</th>
                  <th className="px-3 py-3 text-right w-44">Điều chỉnh</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pageRows.map((item, idx) => {
                  const isCitationOpen = Boolean(expandedCitations[item.major_code])
                  const sources = item.trend_sources || []

                  return (
                    <tr key={item.major_code} className="hover:bg-sky-50/40">
                      <td className="px-3 py-3 text-center text-xs font-bold text-slate-400 tabular-nums">
                        {(currentPage - 1) * 25 + idx + 1}
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-block rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
                          {item.category || "Chưa phân nhóm"}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <p className="font-bold text-slate-900">{item.major_name}</p>
                        <p className="font-mono text-xs font-bold text-sky-700 mt-0.5">
                          {item.major_code}
                        </p>
                      </td>
                      <td className="px-3 py-3">
                        <TrendBadge
                          tier={item.trend_tier}
                          isTrending={true}
                          reason={item.trend_reason}
                        />
                        <p className="mt-1 text-xs font-semibold text-slate-400 tabular-nums">
                          Điểm vĩ mô: {item.trend_score}/100
                        </p>
                      </td>
                      <td className="px-3 py-3 text-sm text-slate-700">
                        <p className="leading-relaxed">{item.trend_reason}</p>

                        {/* Collapsible Citations Accordion */}
                        {sources.length > 0 && (
                          <div className="mt-2">
                            <button
                              type="button"
                              onClick={() => toggleCitation(item.major_code)}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-sky-200/80 bg-sky-50/80 px-2.5 py-1 text-xs font-semibold text-sky-700 hover:bg-sky-100 transition cursor-pointer"
                            >
                              <span>Nguồn tham khảo ({sources.length})</span>
                              <ChevronDown
                                size={13}
                                className={`transition-transform duration-200 ${
                                  isCitationOpen ? "rotate-180" : ""
                                }`}
                              />
                            </button>

                            <AnimatePresence initial={false}>
                              {isCitationOpen && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: "auto" }}
                                  exit={{ opacity: 0, height: 0 }}
                                  transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                                  className="overflow-hidden"
                                >
                                  <div className="mt-2 flex flex-wrap gap-1.5 rounded-xl border border-sky-100 bg-white p-2.5 shadow-2xs">
                                    {sources.map((s, si) => (
                                      <a
                                        key={si}
                                        href={s.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-sky-700 hover:border-sky-300 hover:bg-sky-50 transition"
                                      >
                                        <span>{s.source || s.title || "Nguồn tin"}</span>
                                        <ExternalLink size={11} className="shrink-0 text-slate-400" />
                                      </a>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <select
                          aria-label={`Bậc xu hướng ngành ${item.major_name}`}
                          disabled={Boolean(updatingCode) || savingToDb || running || clearing}
                          value={item.trend_tier}
                          onChange={(e) => handleTierChange(item.major_code, e.target.value)}
                          className="h-8 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-700 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-100 cursor-pointer"
                        >
                          <option value="TIER_1">Bậc 1 (Cao nhất)</option>
                          <option value="TIER_2">Bậc 2 (Mạnh)</option>
                          <option value="TIER_3">Bậc 3 (Ổn định)</option>
                          <option value="NONE">Bỏ đánh dấu</option>
                        </select>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {pageRows.length === 0 && <p className="p-5 text-sm text-slate-600">Không có ngành khớp bộ lọc.</p>}
          </div>
          <div className="admin-pagination px-4"><span>{filteredMajors.length} ngành · Trang {currentPage}/{totalPages}</span><button className="admin-button" type="button" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>Trước</button><button className="admin-button" type="button" disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>Sau</button></div>
        </div>
      )}
    </div>
  )
}
