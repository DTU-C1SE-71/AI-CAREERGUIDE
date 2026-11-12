import {
  AlertCircle,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  GraduationCap,
  Layers3,
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
const CAREERS_PREVIEW_LIMIT = 12

function hollandTop3(riasec?: Record<string, number>): string {
  if (!riasec) return "-"
  const ranked = RIASEC_DIMENSIONS.map((dim) => [dim, Number(riasec[dim] ?? 0)] as const)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
  if (!ranked.length) return "-"
  return ranked.map(([dim, value]) => `${dim}·${value.toFixed(2)}`).join("  ")
}

export function MajorsCatalogPanel({
  refreshKey = 0,
  onNotify,
}: MajorsCatalogPanelProps) {
  const [majors, setMajors] = useState<CatalogMajor[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
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
    let withBlocks = 0
    let withCareers = 0
    for (const major of majors) {
      const tier = major.trend_tier
      if (major.is_trending && tier && tier in tiers) {
        tiers[tier as keyof typeof tiers] += 1
      }
      if (major.blocks?.length) withBlocks += 1
      if (major.careers?.length) withCareers += 1
    }
    return {
      total: majors.length,
      groups: categories.length,
      trending: tiers.TIER_1 + tiers.TIER_2 + tiers.TIER_3,
      tiers,
      withBlocks,
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
      return [major.major_code, major.name, major.category, major.degree_level]
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
    <div className="glass-card mb-5 overflow-hidden rounded-3xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/70 p-3.5">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          aria-controls="majors-catalog-body"
          className="flex min-w-0 items-center gap-2 text-left"
        >
          <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-indigo-500 text-white">
            <BookOpen size={16} />
          </span>
          <span className="min-w-0">
            <span className="flex items-center gap-1.5 text-sm font-black text-slate-900">
              Danh mục ngành đào tạo trong hệ thống
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </span>
            <span className="block truncate text-[10px] text-slate-500">
              {loading
                ? "Đang tải dữ liệu..."
                : `${stats.total} ngành đang hoạt động · ${stats.groups} nhóm ngành · ${stats.trending} ngành xu hướng`}
            </span>
          </span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="indigo">{stats.total} ngành</Badge>
          <Badge tone="slate">{stats.groups} nhóm</Badge>
          <Badge tone="amber">{stats.withBlocks} có khối xét tuyển</Badge>
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => void loadCatalog()}
            loading={loading}
            className="!min-h-8 !px-3 !py-1 !text-xs"
          >
            Làm mới
          </Button>
        </div>
      </div>

      {expanded && (
        <div id="majors-catalog-body">
          {/* Filters */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-100 bg-sky-50/50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <label htmlFor="catalog-search" className="sr-only">
                  Tìm ngành theo mã hoặc tên
                </label>
                <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  id="catalog-search"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value)
                    resetPage()
                  }}
                  placeholder="Tìm mã ngành / tên ngành..."
                  className="h-8 w-52 rounded-lg border border-slate-200 bg-white pl-8 pr-2.5 text-xs outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>

              <label htmlFor="catalog-category" className="sr-only">
                Lọc theo nhóm ngành
              </label>
              <select
                id="catalog-category"
                value={category}
                onChange={(event) => {
                  setCategory(event.target.value)
                  resetPage()
                }}
                className="h-8 max-w-[240px] rounded-lg border border-slate-200 bg-white px-2 text-xs font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-sky-200"
              >
                <option value="ALL">Tất cả nhóm ngành ({stats.groups})</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>

              <div className="flex rounded-xl border border-slate-200 bg-white p-0.5">
                {(
                  [
                    ["ALL", "Tất cả"],
                    ["TRENDING", "Có xu hướng"],
                    ["NORMAL", "Không xu hướng"],
                  ] as Array<[TrendFilter, string]>
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      setTrendFilter(value)
                      resetPage()
                    }}
                    aria-pressed={trendFilter === value}
                    className={`rounded-lg px-2 py-1 text-[10px] font-extrabold transition ${
                      trendFilter === value
                        ? "bg-sky-600 text-white"
                        : "text-slate-500 hover:text-sky-700"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-slate-600">
              <span>
                <strong className="text-slate-900">{filteredMajors.length}</strong> kết quả
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
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-bold text-slate-600 hover:text-sky-700"
                >
                  <X size={11} />
                  Xóa lọc
                </button>
              )}
            </div>
          </div>

          {/* Loading / Error / Empty */}
          {loading && majors.length === 0 ? (
            <div className="flex items-center justify-center gap-2 p-10 text-xs font-bold text-slate-500">
              <Loader2 size={16} className="animate-spin text-sky-600" />
              Đang tải danh mục ngành đào tạo...
            </div>
          ) : loadError ? (
            <div className="flex flex-col items-center justify-center gap-2 p-10 text-center">
              <AlertCircle size={20} className="text-rose-500" />
              <p className="text-xs font-bold text-rose-700">{loadError}</p>
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => void loadCatalog()}
                className="!min-h-8 !px-3 !py-1 !text-xs"
              >
                Thử lại
              </Button>
            </div>
          ) : pageRows.length === 0 ? (
            <div className="p-10 text-center text-xs font-semibold text-slate-500">
              Không có ngành nào khớp bộ lọc hiện tại.
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-[11px]">
                  <caption className="sr-only">
                    Danh mục ngành đào tạo đang hoạt động trong CSDL, có tìm kiếm và lọc
                  </caption>
                  <thead className="bg-slate-50 text-[10px] font-extrabold uppercase text-slate-500">
                    <tr>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center w-10">STT</th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Mã ngành</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[190px]">
                        Tên ngành
                      </th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[150px]">Nhóm ngành</th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Bậc</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[130px]">
                        Khối xét tuyển
                      </th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[130px]">
                        Holland (top 3)
                      </th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Xu hướng</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center w-12">
                        Chi tiết
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pageRows.map((major, index) => {
                      const isOpen = expandedCode === major.major_code
                      const detailId = `catalog-detail-${major.major_code}`
                      return (
                        <Fragment key={major.major_code}>
                          <tr
                            className={`transition ${
                              isOpen ? "bg-sky-50/70" : "hover:bg-sky-50/40"
                            }`}
                          >
                            <td className="px-2.5 py-1.5 text-center font-bold text-slate-500">
                              {(currentPage - 1) * PAGE_SIZE + index + 1}
                            </td>
                            <td className="px-2.5 py-1.5 font-mono font-bold text-sky-700">
                              {major.major_code}
                            </td>
                            <td className="px-2.5 py-1.5 font-semibold text-slate-800">
                              {major.name}
                            </td>
                            <td className="px-2.5 py-1.5 text-[10px] font-bold text-slate-600">
                              {major.category || "Khác"}
                            </td>
                            <td className="px-2.5 py-1.5 text-[10px] text-slate-600">
                              {major.degree_level || "Đại học"}
                            </td>
                            <td className="px-2.5 py-1.5 font-mono text-[10px] font-semibold text-slate-700">
                              {major.blocks?.length ? major.blocks.join(", ") : "-"}
                            </td>
                            <td className="px-2.5 py-1.5 font-mono text-[10px] text-slate-700">
                              {hollandTop3(major.riasec)}
                            </td>
                            <td className="px-2.5 py-1.5">
                              {major.is_trending && major.trend_tier ? (
                                <TrendBadge
                                  tier={major.trend_tier}
                                  isTrending
                                  reason={major.trend_reason}
                                />
                              ) : (
                                <span className="text-[10px] text-slate-400">-</span>
                              )}
                            </td>
                            <td className="px-2.5 py-1.5 text-center">
                              <button
                                type="button"
                                onClick={() => setExpandedCode(isOpen ? null : major.major_code)}
                                aria-expanded={isOpen}
                                aria-controls={detailId}
                                aria-label={`Xem chi tiết ngành ${major.name}`}
                                className="grid size-6 place-items-center rounded border border-slate-200 bg-white text-slate-500 transition hover:text-sky-700"
                              >
                                {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                              </button>
                            </td>
                          </tr>

                          {isOpen && (
                            <tr id={detailId}>
                              <td colSpan={9} className="bg-sky-50/60 px-4 py-3">
                                <div className="grid gap-3 lg:grid-cols-[1.15fr_1fr]">
                                  <div className="space-y-2">
                                    <div>
                                      <p className="mb-1 flex items-center gap-1.5 text-[10px] font-extrabold uppercase text-slate-500">
                                        <GraduationCap size={12} className="text-sky-600" />
                                        Mô tả ngành
                                      </p>
                                      <p className="text-[11px] leading-5 text-slate-700">
                                        {(major.description || "").trim() ||
                                          "Chưa có mô tả cho ngành này trong CSDL."}
                                      </p>
                                    </div>
                                    <div>
                                      <p className="mb-1 flex items-center gap-1.5 text-[10px] font-extrabold uppercase text-slate-500">
                                        <Layers3 size={12} className="text-sky-600" />
                                        Vị trí việc làm ({major.careers?.length ?? 0})
                                      </p>
                                      {major.careers?.length ? (
                                        <div className="flex flex-wrap gap-1">
                                          {major.careers
                                            .slice(0, CAREERS_PREVIEW_LIMIT)
                                            .map((career) => (
                                              <span
                                                key={career}
                                                className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold text-slate-700"
                                              >
                                                {career}
                                              </span>
                                            ))}
                                          {major.careers.length > CAREERS_PREVIEW_LIMIT && (
                                            <span className="rounded-md border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                                              +{major.careers.length - CAREERS_PREVIEW_LIMIT}
                                            </span>
                                          )}
                                        </div>
                                      ) : (
                                        <p className="text-[11px] text-slate-500">
                                          Chưa cập nhật vị trí việc làm.
                                        </p>
                                      )}
                                    </div>
                                  </div>

                                  <div className="space-y-2">
                                    <div>
                                      <p className="mb-1 text-[10px] font-extrabold uppercase text-slate-500">
                                        Triển vọng ngành
                                      </p>
                                      <p className="text-[11px] leading-5 text-slate-700">
                                        {(major.outlook || "").trim() ||
                                          "Chưa có dữ liệu triển vọng ngành."}
                                      </p>
                                    </div>
                                    {major.is_trending && major.trend_tier && (
                                      <div className="rounded-xl border border-sky-200 bg-white/80 p-2">
                                        <p className="mb-1 flex items-center gap-1.5 text-[10px] font-extrabold uppercase text-sky-700">
                                          <TrendingUp size={12} />
                                          {major.trend_label || "Ngành xu hướng"}
                                        </p>
                                        <p className="text-[11px] leading-5 text-slate-700">
                                          {(major.trend_reason || "").trim() ||
                                            "Chưa có lý do xu hướng."}
                                        </p>
                                        {!!major.trend_sources?.length && (
                                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                                            {major.trend_sources
                                              .filter((source) => source.url)
                                              .slice(0, 4)
                                              .map((source) => (
                                                <a
                                                  key={source.url}
                                                  href={source.url}
                                                  target="_blank"
                                                  rel="noreferrer"
                                                  className="rounded-md border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-bold text-sky-700 hover:underline"
                                                >
                                                  {source.source || source.title || "Nguồn"}
                                                </a>
                                              ))}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </div>
                                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-sky-200/70 pt-2.5">
                                  <p className="mr-auto text-[10px] font-extrabold uppercase text-slate-500">
                                    Agent nội dung đào tạo (cache AI)
                                  </p>
                                  <Button
                                    variant="secondary"
                                    icon={RefreshCw}
                                    onClick={() =>
                                      void handleInsightCache(major.major_code, "regenerate")
                                    }
                                    loading={
                                      insightBusy === `regenerate:${major.major_code}`
                                    }
                                    className="!min-h-7 !px-2.5 !py-1 !text-[10px]"
                                  >
                                    Sinh lại nội dung
                                  </Button>
                                  <Button
                                    variant="secondary"
                                    icon={X}
                                    onClick={() =>
                                      void handleInsightCache(major.major_code, "delete")
                                    }
                                    loading={insightBusy === `delete:${major.major_code}`}
                                    className="!min-h-7 !px-2.5 !py-1 !text-[10px]"
                                  >
                                    Xoá cache
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 bg-slate-50/70 px-3 py-2 text-[11px] text-slate-600">
                <span>
                  {(currentPage - 1) * PAGE_SIZE + 1}–
                  {Math.min(currentPage * PAGE_SIZE, filteredMajors.length)} /{" "}
                  {filteredMajors.length} ngành
                </span>
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
                      className="grid size-6 place-items-center rounded border border-slate-200 bg-white disabled:opacity-40"
                    >
                      <ChevronLeft size={13} />
                    </button>
                    <span className="px-1.5 font-bold">
                      {currentPage}/{totalPages}
                    </span>
                    <button
                      type="button"
                      disabled={currentPage >= totalPages}
                      onClick={() => {
                        setPage(Math.min(totalPages, currentPage + 1))
                        setExpandedCode(null)
                      }}
                      aria-label="Trang sau"
                      className="grid size-6 place-items-center rounded border border-slate-200 bg-white disabled:opacity-40"
                    >
                      <ChevronRight size={13} />
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Tier summary */}
          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 bg-white/70 px-3 py-2 text-[10px] font-semibold text-slate-500">
            <span>Phân bố xu hướng:</span>
            <span className="text-sky-700">Bậc 1: {stats.tiers.TIER_1}</span>
            <span className="text-sky-600">Bậc 2: {stats.tiers.TIER_2}</span>
            <span className="text-cyan-700">Bậc 3: {stats.tiers.TIER_3}</span>
            <span className="ml-auto">{stats.withCareers} ngành có vị trí việc làm</span>
          </div>
        </div>
      )}
    </div>
  )
}
