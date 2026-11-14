import { AnimatePresence, motion } from "framer-motion"
import {
  AlertCircle,
  BookOpen,
  Briefcase,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ExternalLink,
  GraduationCap,
  Loader2,
  RefreshCw,
  Search,
  TrendingUp,
  X,
} from "lucide-react"
import { Fragment, useCallback, useEffect, useMemo, useState } from "react"
import { readStorage } from "../../services/storage"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { TrendBadge } from "../xai/TrendBadge"

/** Bản ghi ngành trả về từ `GET /api/v1/taxonomy/majors` (chỉ ngành đang hoạt động). */
interface CatalogMajor {
  major_code: string
  name: string
  category?: string
  degree_level?: string
  blocks?: string[]
  careers?: string[]
  riasec?: Record<string, number>
  outlook?: string
  description?: string | null
  cutoff_score?: number | string | null
  benchmark_score?: number | string | null
  min_score?: number | string | null
  is_trending?: boolean
  trend_tier?: string | null
  trend_label?: string | null
  trend_reason?: string | null
  trend_sources?: Array<{ title?: string; url?: string; source?: string }>
}

interface MajorsCatalogPanelProps {
  /** Tăng giá trị này để buộc panel tải lại (ví dụ sau khi import Excel xong). */
  refreshKey?: number
  onNotify?: (msg: string, error?: boolean) => void
}

type TrendFilter = "ALL" | "TRENDING" | "NORMAL"

const PAGE_SIZE = 50
const RIASEC_DIMENSIONS = ["R", "I", "A", "S", "E", "C"] as const
const CAREERS_PREVIEW_LIMIT = 14
const INLINE_BLOCKS_LIMIT = 4
const SMOOTH_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

function hollandTop3(riasec?: Record<string, number>): string {
  if (!riasec) return "—"
  const ranked = RIASEC_DIMENSIONS.map((dim) => [dim, Number(riasec[dim] ?? 0)] as const)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
  if (!ranked.length) return "—"
  return ranked.map(([dim, value]) => `${dim}·${value.toFixed(2)}`).join("  ")
}

function formatCutoffScore(major: CatalogMajor): string {
  const raw = major.cutoff_score ?? major.benchmark_score ?? major.min_score
  if (raw === null || raw === undefined || raw === "") return "—"
  const numeric = typeof raw === "number" ? raw : Number(String(raw).replace(",", "."))
  if (Number.isFinite(numeric) && numeric > 0) return numeric.toFixed(2)
  const text = String(raw).trim()
  return text || "—"
}

export function MajorsCatalogPanel({
  refreshKey = 0,
  onNotify,
}: MajorsCatalogPanelProps) {
  const [majors, setMajors] = useState<CatalogMajor[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("ALL")
  const [trendFilter, setTrendFilter] = useState<TrendFilter>("ALL")
  const [page, setPage] = useState(1)
  const [expandedCode, setExpandedCode] = useState<string | null>(null)
  const [insightBusy, setInsightBusy] = useState<string | null>(null)

  const loadCatalog = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const token = readStorage<string | null>("career-guide:token", null)
      const res = await fetch("/api/v1/taxonomy/majors?limit=1000", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error(`Không tải được danh mục (HTTP ${res.status}).`)
      const data: unknown = await res.json()
      if (!Array.isArray(data)) throw new Error("Phản hồi danh mục ngành không hợp lệ.")
      setMajors(data as CatalogMajor[])
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Không tải được danh mục ngành từ CSDL."
      setLoadError(message)
      onNotify?.(message, true)
    } finally {
      setLoading(false)
    }
  }, [onNotify])

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog, refreshKey])

  const categories = useMemo(() => {
    const unique = new Set<string>()
    for (const major of majors) unique.add(major.category || "Khác")
    return Array.from(unique).sort((a, b) => a.localeCompare(b, "vi"))
  }, [majors])

  const stats = useMemo(() => {
    const tiers = { TIER_1: 0, TIER_2: 0, TIER_3: 0 }
    let withCareers = 0
    for (const major of majors) {
      const tier = major.trend_tier
      if (major.is_trending && tier && tier in tiers) {
        tiers[tier as keyof typeof tiers] += 1
      }
      if (major.careers?.length) withCareers += 1
    }
    return {
      total: majors.length,
      groups: categories.length,
      trending: tiers.TIER_1 + tiers.TIER_2 + tiers.TIER_3,
      tiers,
      withCareers,
    }
  }, [majors, categories.length])

  const filteredMajors = useMemo(() => {
    const q = search.trim().toLowerCase()
    return majors.filter((major) => {
      if (category !== "ALL" && (major.category || "Khác") !== category) return false
      if (trendFilter === "TRENDING" && !major.is_trending) return false
      if (trendFilter === "NORMAL" && major.is_trending) return false
      if (!q) return true
      return [
        major.major_code,
        major.name,
        major.category,
        major.degree_level,
        ...(major.blocks ?? []),
      ]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(q))
    })
  }, [majors, search, category, trendFilter])

  const totalPages = Math.max(1, Math.ceil(filteredMajors.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageRows = filteredMajors.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  )

  const resetPage = () => {
    setPage(1)
    setExpandedCode(null)
  }

  /** Admin: sinh lại / xoá cache nội dung đào tạo của một ngành. */
  const handleInsightCache = async (
    majorCode: string,
    action: "regenerate" | "delete",
  ) => {
    const token = readStorage<string | null>("career-guide:token", null)
    if (!token) {
      onNotify?.("Vui lòng đăng nhập bằng tài khoản ADMIN để thực hiện.", true)
      return
    }

    setInsightBusy(`${action}:${majorCode}`)
    try {
      const res = await fetch(
        `/api/v1/major-insights/${majorCode}${action === "regenerate" ? "/regenerate" : ""}`,
        {
          method: action === "regenerate" ? "POST" : "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        },
      )
      const body: unknown = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = (body as { detail?: string } | null)?.detail
        throw new Error(detail || `Thao tác thất bại (HTTP ${res.status}).`)
      }
      if (action === "regenerate") {
        const isAi = Boolean((body as { is_ai_generated?: boolean } | null)?.is_ai_generated)
        onNotify?.(
          `Đã sinh lại nội dung đào tạo ngành ${majorCode} ${isAi ? "bằng AI" : "từ dữ liệu dựng sẵn"}.`,
        )
      } else {
        const message = (body as { message?: string } | null)?.message
        onNotify?.(message || `Đã xoá cache nội dung đào tạo ngành ${majorCode}.`)
      }
    } catch (err) {
      onNotify?.(
        err instanceof Error ? err.message : "Không thực hiện được thao tác.",
        true,
      )
    } finally {
      setInsightBusy(null)
    }
  }

  const hasActiveFilter =
    search.trim().length > 0 || category !== "ALL" || trendFilter !== "ALL"

  return (
    <div className="glass-card overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 shadow-sm sm:rounded-3xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/70 px-4 py-3.5 sm:px-5 sm:py-4">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          aria-controls="majors-catalog-body"
          className="flex min-w-0 items-center gap-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40 rounded-xl"
        >
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-sky-600 text-white shadow-xs">
            <BookOpen size={18} />
          </span>
          <span className="min-w-0">
            <span className="flex items-center gap-2 text-base font-bold text-slate-900 sm:text-lg">
              Danh mục Ngành Đào tạo
              <span className="text-slate-400">
                {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </span>
            </span>
            <span className="block truncate text-xs text-slate-500 tabular-nums">
              {loading
                ? "Đang đồng bộ danh mục..."
                : `${stats.total} ngành hoạt động · ${stats.groups} nhóm lĩnh vực · ${stats.trending} xu hướng`}
            </span>
          </span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700 tabular-nums">
            {stats.total} ngành
          </span>
          <Badge tone="slate">{stats.groups} nhóm</Badge>
          {stats.trending > 0 && (
            <Badge tone="emerald">{stats.trending} xu hướng</Badge>
          )}
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => void loadCatalog()}
            loading={loading}
            className="!min-h-9 !px-3.5 !py-1.5 !text-sm"
          >
            Làm mới
          </Button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id="majors-catalog-body"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: SMOOTH_EASE }}
            className="overflow-hidden"
          >
            {/* Filter Toolbar */}
            <div className="flex flex-col gap-3 border-b border-slate-200/70 bg-slate-50/70 px-4 py-3.5 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="relative w-full sm:w-64">
                  <label htmlFor="catalog-search" className="sr-only">
                    Tìm ngành theo mã, tên hoặc khối thi
                  </label>
                  <Search
                    size={15}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />
                  <input
                    id="catalog-search"
                    value={search}
                    onChange={(event) => {
                      setSearch(event.target.value)
                      resetPage()
                    }}
                    placeholder="Tìm mã, tên ngành, khối..."
                    className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-800 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-500/20"
                  />
                </div>

                <label htmlFor="catalog-category" className="sr-only">
                  Lọc theo nhóm lĩnh vực
                </label>
                <select
                  id="catalog-category"
                  value={category}
                  onChange={(event) => {
                    setCategory(event.target.value)
                    resetPage()
                  }}
                  className="h-9 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none transition focus:border-sky-400 focus:ring-2 focus:ring-sky-500/20 sm:w-auto sm:max-w-[260px]"
                >
                  <option value="ALL">Tất cả nhóm lĩnh vực ({stats.groups})</option>
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>

                <div
                  role="group"
                  aria-label="Lọc theo trạng thái xu hướng"
                  className="inline-flex rounded-xl border border-slate-200 bg-white p-1"
                >
                  {(
                    [
                      ["ALL", "Tất cả"],
                      ["TRENDING", "Xu hướng"],
                      ["NORMAL", "Tiêu chuẩn"],
                    ] as Array<[TrendFilter, string]>
                  ).map(([value, label]) => {
                    const active = trendFilter === value
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => {
                          setTrendFilter(value)
                          resetPage()
                        }}
                        aria-pressed={active}
                        className={`relative rounded-lg px-3 py-1 text-xs font-semibold transition cursor-pointer ${
                          active ? "text-white" : "text-slate-600 hover:text-sky-700"
                        }`}
                      >
                        {active && (
                          <motion.span
                            layoutId="catalog-trend-filter-pill"
                            transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                            className="absolute inset-0 rounded-lg bg-sky-600 shadow-2xs"
                          />
                        )}
                        <span className="relative z-10">{label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="flex items-center justify-between gap-2.5 text-xs text-slate-600 tabular-nums sm:text-sm lg:justify-end">
                <span>
                  <strong className="font-semibold text-slate-900">
                    {filteredMajors.length}
                  </strong>{" "}
                  kết quả
                  {hasActiveFilter ? ` / ${stats.total}` : ""}
                </span>
                {hasActiveFilter && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearch("")
                      setCategory("ALL")
                      setTrendFilter("ALL")
                      resetPage()
                    }}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-600 transition hover:border-sky-200 hover:text-sky-700 cursor-pointer"
                  >
                    <X size={13} />
                    Xóa lọc
                  </button>
                )}
              </div>
            </div>

            {/* Loading / Error / Empty / Table */}
            {loading && majors.length === 0 ? (
              <div className="flex items-center justify-center gap-2.5 p-12 text-sm font-medium text-slate-500">
                <Loader2 size={18} className="animate-spin text-sky-600" />
                Đang tải danh mục ngành đào tạo...
              </div>
            ) : loadError ? (
              <div className="flex flex-col items-center justify-center gap-3 p-12 text-center">
                <AlertCircle size={22} className="text-rose-500" />
                <p className="text-sm font-semibold text-rose-700">{loadError}</p>
                <Button
                  variant="secondary"
                  icon={RefreshCw}
                  onClick={() => void loadCatalog()}
                  className="!min-h-9 !px-4 !text-sm"
                >
                  Thử lại
                </Button>
              </div>
            ) : pageRows.length === 0 ? (
              <div className="p-12 text-center text-sm font-medium text-slate-500">
                Không có ngành nào khớp bộ lọc hiện tại.
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[960px] border-collapse text-left">
                    <caption className="sr-only">
                      Danh mục ngành đào tạo đang hoạt động trong CSDL
                    </caption>
                    <thead className="border-b border-slate-200 bg-slate-50/95 text-xs font-bold uppercase tracking-wider text-slate-600">
                      <tr>
                        <th className="w-12 px-3 py-3 text-center">STT</th>
                        <th className="w-32 px-3 py-3">Mã ngành</th>
                        <th className="min-w-[220px] px-3 py-3">Tên ngành</th>
                        <th className="min-w-[170px] px-3 py-3">Nhóm lĩnh vực</th>
                        <th className="min-w-[165px] px-3 py-3">Tổ hợp xét tuyển</th>
                        <th className="w-28 px-3 py-3 text-right">Điểm chuẩn</th>
                        <th className="min-w-[140px] px-3 py-3">Xu hướng</th>
                        <th className="w-16 px-3 py-3 text-center">Chi tiết</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {pageRows.map((major, index) => {
                        const isOpen = expandedCode === major.major_code
                        const detailId = `catalog-detail-${major.major_code}`
                        const blocks = major.blocks ?? []
                        const cutoffDisplay = formatCutoffScore(major)

                        return (
                          <Fragment key={major.major_code}>
                            <tr
                              onClick={() =>
                                setExpandedCode(isOpen ? null : major.major_code)
                              }
                              className={`cursor-pointer transition-colors ${
                                isOpen ? "bg-sky-50/70" : "hover:bg-slate-50/90"
                              }`}
                            >
                              <td className="px-3 py-2.5 text-center text-xs font-bold text-slate-400 tabular-nums">
                                {(currentPage - 1) * PAGE_SIZE + index + 1}
                              </td>
                              <td className="px-3 py-2.5 whitespace-nowrap">
                                <span className="rounded-md bg-sky-50 px-2 py-0.5 font-mono text-xs font-bold text-sky-700 ring-1 ring-inset ring-sky-200/80">
                                  {major.major_code}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-sm font-semibold text-slate-900">
                                {major.name}
                              </td>
                              <td className="px-3 py-2.5 text-sm text-slate-600">
                                {major.category || "Khác"}
                              </td>
                              <td className="px-3 py-2.5">
                                {blocks.length > 0 ? (
                                  <div className="flex flex-wrap items-center gap-1">
                                    {blocks.slice(0, INLINE_BLOCKS_LIMIT).map((block) => (
                                      <span
                                        key={block}
                                        className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 font-mono text-xs font-medium text-slate-700"
                                      >
                                        {block}
                                      </span>
                                    ))}
                                    {blocks.length > INLINE_BLOCKS_LIMIT && (
                                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-semibold text-slate-500 tabular-nums">
                                        +{blocks.length - INLINE_BLOCKS_LIMIT}
                                      </span>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-xs text-slate-400">—</span>
                                )}
                              </td>
                              <td className="px-3 py-2.5 text-right text-sm font-bold text-slate-900 tabular-nums whitespace-nowrap">
                                {cutoffDisplay === "—" ? (
                                  <span className="font-normal text-slate-400">—</span>
                                ) : (
                                  cutoffDisplay
                                )}
                              </td>
                              <td className="px-3 py-2.5">
                                {major.is_trending && major.trend_tier ? (
                                  <TrendBadge
                                    tier={major.trend_tier}
                                    isTrending
                                    reason={major.trend_reason}
                                  />
                                ) : (
                                  <span className="text-xs text-slate-400">—</span>
                                )}
                              </td>
                              <td
                                className="px-3 py-2.5 text-center"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <button
                                  type="button"
                                  onClick={() =>
                                    setExpandedCode(isOpen ? null : major.major_code)
                                  }
                                  aria-expanded={isOpen}
                                  aria-controls={detailId}
                                  aria-label={`Xem chi tiết ngành ${major.name}`}
                                  className={`inline-grid size-8 place-items-center rounded-lg border transition cursor-pointer ${
                                    isOpen
                                      ? "border-sky-300 bg-sky-600 text-white"
                                      : "border-slate-200 bg-white text-slate-500 hover:border-sky-300 hover:text-sky-700"
                                  }`}
                                >
                                  {isOpen ? (
                                    <ChevronUp size={15} />
                                  ) : (
                                    <ChevronDown size={15} />
                                  )}
                                </button>
                              </td>
                            </tr>

                            <AnimatePresence initial={false}>
                              {isOpen && (
                                <tr id={detailId}>
                                  <td
                                    colSpan={8}
                                    className="bg-sky-50/40 p-0 border-b border-sky-100"
                                  >
                                    <motion.div
                                      initial={{ opacity: 0, height: 0 }}
                                      animate={{ opacity: 1, height: "auto" }}
                                      exit={{ opacity: 0, height: 0 }}
                                      transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                                      className="overflow-hidden"
                                    >
                                      <div className="space-y-4 px-4 py-4 sm:px-6 sm:py-5">
                                        {/* Compact Secondary Metadata Strip */}
                                        <div className="flex flex-wrap items-center gap-2 text-xs">
                                          <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white px-2.5 py-1 font-medium text-slate-700">
                                            <GraduationCap
                                              size={14}
                                              className="text-sky-600"
                                            />
                                            Bậc đào tạo:{" "}
                                            <strong className="font-semibold text-slate-900">
                                              {major.degree_level || "Đại học"}
                                            </strong>
                                          </span>
                                          <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white px-2.5 py-1 font-medium text-slate-700">
                                            Holland ưu thế:{" "}
                                            <strong className="font-mono font-semibold text-sky-700 tabular-nums">
                                              {hollandTop3(major.riasec)}
                                            </strong>
                                          </span>
                                          {major.riasec && (
                                            <div className="flex flex-wrap items-center gap-1 tabular-nums">
                                              {RIASEC_DIMENSIONS.map((dim) => {
                                                const val = Number(
                                                  major.riasec?.[dim] ?? 0,
                                                )
                                                return (
                                                  <span
                                                    key={dim}
                                                    className={`rounded-md px-2 py-0.5 font-mono text-xs tabular-nums ${
                                                      val >= 0.7
                                                        ? "bg-sky-600 font-bold text-white shadow-2xs"
                                                        : "bg-white text-slate-600 ring-1 ring-inset ring-slate-200/80"
                                                    }`}
                                                  >
                                                    {dim}:{val.toFixed(2)}
                                                  </span>
                                                )
                                              })}
                                            </div>
                                          )}
                                        </div>

                                        <div className="grid gap-4 lg:grid-cols-12">
                                          <div className="space-y-3 lg:col-span-7">
                                            <div>
                                              <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">
                                                Mô tả ngành
                                              </h4>
                                              <p className="text-sm leading-relaxed text-slate-700">
                                                {(major.description || "").trim() ||
                                                  "Chưa có mô tả chi tiết cho ngành này trong CSDL."}
                                              </p>
                                            </div>

                                            <div>
                                              <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500 tabular-nums">
                                                <Briefcase
                                                  size={13}
                                                  className="text-sky-600"
                                                />
                                                Vị trí việc làm ({major.careers?.length ?? 0})
                                              </h4>
                                              {major.careers?.length ? (
                                                <div className="flex flex-wrap gap-1.5">
                                                  {major.careers
                                                    .slice(0, CAREERS_PREVIEW_LIMIT)
                                                    .map((career) => (
                                                      <span
                                                        key={career}
                                                        className="rounded-lg border border-slate-200/80 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"
                                                      >
                                                        {career}
                                                      </span>
                                                    ))}
                                                  {major.careers.length >
                                                    CAREERS_PREVIEW_LIMIT && (
                                                    <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 tabular-nums">
                                                      +
                                                      {major.careers.length -
                                                        CAREERS_PREVIEW_LIMIT}
                                                    </span>
                                                  )}
                                                </div>
                                              ) : (
                                                <p className="text-sm text-slate-500">
                                                  Chưa cập nhật danh sách vị trí việc làm.
                                                </p>
                                              )}
                                            </div>
                                          </div>

                                          <div className="space-y-3 lg:col-span-5">
                                            <div>
                                              <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500">
                                                Triển vọng nghề nghiệp
                                              </h4>
                                              <p className="text-sm leading-relaxed text-slate-700">
                                                {(major.outlook || "").trim() ||
                                                  "Chưa có dữ liệu triển vọng ngành."}
                                              </p>
                                            </div>

                                            {major.is_trending && major.trend_tier && (
                                              <div className="rounded-xl border border-sky-200/80 bg-sky-50/50 p-3.5">
                                                <p className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-700">
                                                  <TrendingUp size={14} />
                                                  {major.trend_label || "Ngành xu hướng"}
                                                </p>
                                                <p className="text-sm leading-relaxed text-slate-700">
                                                  {(major.trend_reason || "").trim() ||
                                                    "Đang được đánh dấu xu hướng trên thị trường lao động."}
                                                </p>
                                                {!!major.trend_sources?.length && (
                                                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                                                    {major.trend_sources
                                                      .filter((source) => source.url)
                                                      .slice(0, 4)
                                                      .map((source) => (
                                                        <a
                                                          key={source.url}
                                                          href={source.url}
                                                          target="_blank"
                                                          rel="noreferrer"
                                                          className="inline-flex items-center gap-1 rounded-lg border border-sky-200 bg-white px-2.5 py-1 text-xs font-semibold text-sky-700 transition hover:bg-sky-50"
                                                        >
                                                          <span>
                                                            {source.source ||
                                                              source.title ||
                                                              "Nguồn tin"}
                                                          </span>
                                                          <ExternalLink size={12} />
                                                        </a>
                                                      ))}
                                                  </div>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        </div>

                                        {/* AI Content Cache Actions */}
                                        <div className="flex flex-wrap items-center justify-between gap-2.5 border-t border-sky-200/70 pt-3">
                                          <span className="text-xs font-medium text-slate-500">
                                            Bộ nhớ đệm nội dung đào tạo (AI Insights)
                                          </span>
                                          <div className="flex flex-wrap items-center gap-2">
                                            <Button
                                              variant="secondary"
                                              icon={RefreshCw}
                                              onClick={() =>
                                                void handleInsightCache(
                                                  major.major_code,
                                                  "regenerate",
                                                )
                                              }
                                              loading={
                                                insightBusy ===
                                                `regenerate:${major.major_code}`
                                              }
                                              className="!min-h-8 !px-3 !py-1 !text-xs"
                                            >
                                              Sinh lại nội dung
                                            </Button>
                                            <Button
                                              variant="secondary"
                                              icon={X}
                                              onClick={() =>
                                                void handleInsightCache(
                                                  major.major_code,
                                                  "delete",
                                                )
                                              }
                                              loading={
                                                insightBusy ===
                                                `delete:${major.major_code}`
                                              }
                                              className="!min-h-8 !px-3 !py-1 !text-xs !text-rose-700 hover:!bg-rose-50"
                                            >
                                              Xoá cache
                                            </Button>
                                          </div>
                                        </div>
                                      </div>
                                    </motion.div>
                                  </td>
                                </tr>
                              )}
                            </AnimatePresence>
                          </Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination + Summary */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/70 bg-slate-50/70 px-4 py-3 text-xs text-slate-600 tabular-nums sm:px-5 sm:text-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <span>
                      Hiển thị{" "}
                      <strong className="font-semibold text-slate-900">
                        {(currentPage - 1) * PAGE_SIZE + 1}–
                        {Math.min(currentPage * PAGE_SIZE, filteredMajors.length)}
                      </strong>{" "}
                      / {filteredMajors.length} ngành
                    </span>
                    {stats.trending > 0 && (
                      <span className="hidden items-center gap-2.5 border-l border-slate-200 pl-3 text-xs md:inline-flex">
                        <span className="font-semibold text-emerald-700">
                          Bậc 1: {stats.tiers.TIER_1}
                        </span>
                        <span className="font-semibold text-sky-700">
                          Bậc 2: {stats.tiers.TIER_2}
                        </span>
                        <span className="font-semibold text-cyan-700">
                          Bậc 3: {stats.tiers.TIER_3}
                        </span>
                      </span>
                    )}
                  </div>

                  {totalPages > 1 && (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        disabled={currentPage <= 1}
                        onClick={() => {
                          setPage(Math.max(1, currentPage - 1))
                          setExpandedCode(null)
                        }}
                        aria-label="Trang trước"
                        className="grid size-8 place-items-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:border-sky-300 hover:text-sky-700 disabled:opacity-40 cursor-pointer"
                      >
                        <ChevronLeft size={15} />
                      </button>
                      <span className="px-2 text-xs font-semibold text-slate-800 sm:text-sm">
                        {currentPage} / {totalPages}
                      </span>
                      <button
                        type="button"
                        disabled={currentPage >= totalPages}
                        onClick={() => {
                          setPage(Math.min(totalPages, currentPage + 1))
                          setExpandedCode(null)
                        }}
                        aria-label="Trang sau"
                        className="grid size-8 place-items-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:border-sky-300 hover:text-sky-700 disabled:opacity-40 cursor-pointer"
                      >
                        <ChevronRight size={15} />
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
