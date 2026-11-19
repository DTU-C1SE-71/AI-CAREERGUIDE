import { ChevronRight, Compass, Search } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useLocation, useSearchParams } from "react-router"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { TrendBadge } from "../components/xai/TrendBadge"
import { requestJSON } from "../services/api"

interface TaxonomyCatalogItem {
  major_code: string
  name_vi?: string
  name?: string
  category?: string
  subject_blocks?: string[]
  blocks?: string[]
  is_trending?: boolean
  trend_tier?: "TIER_1" | "TIER_2" | "TIER_3" | null
  trend_priority?: number
  trend_reason?: string | null
}

export function MajorsCatalog() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const searchRef = useRef<HTMLInputElement>(null)
  const [catalog, setCatalog] = useState<TaxonomyCatalogItem[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("ALL")
  const [showAllCatalog, setShowAllCatalog] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [loadAttempt, setLoadAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    requestJSON<TaxonomyCatalogItem[]>("/taxonomy/majors?limit=1000", {
      signal: controller.signal,
    })
      .then((list) => {
        if (!Array.isArray(list)) throw new Error("Phản hồi danh mục ngành không hợp lệ.")
        if (!controller.signal.aborted) setCatalog(list)
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("Không tải được danh mục ngành. Vui lòng thử lại.")
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [loadAttempt])

  useEffect(() => {
    if (searchParams.get("search") === "1") searchRef.current?.focus()
  }, [searchParams, location.key])

  const categories = useMemo(
    () => ["ALL", ...new Set(catalog.flatMap((item) => item.category ? [item.category] : []))],
    [catalog],
  )

  const filteredCatalog = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return catalog
      .filter((item) => {
        const matchesCategory = selectedCategory === "ALL" || item.category === selectedCategory
        const matchesQuery = !query || [item.major_code, item.name_vi, item.name, item.category]
          .some((value) => value?.toLowerCase().includes(query))
        return matchesCategory && matchesQuery
      })
      .sort((a, b) => (b.trend_priority || 0) - (a.trend_priority || 0))
  }, [catalog, searchQuery, selectedCategory])

  const visibleCatalog = showAllCatalog ? filteredCatalog : filteredCatalog.slice(0, 9)
  const hasFilters = searchQuery.trim() !== "" || selectedCategory !== "ALL"
  const clearFilters = () => {
    setSearchQuery("")
    setSelectedCategory("ALL")
    setShowAllCatalog(false)
  }

  return (
    <section className="py-9 sm:py-12">
      <PageContainer>
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
              Danh mục ngành
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Tra cứu mã ngành, lĩnh vực và tổ hợp xét tuyển.
            </p>
          </div>
          <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-sky-700 hover:text-sky-800">
            Khám phá ngành phù hợp <ChevronRight size={16} aria-hidden="true" />
          </Link>
        </div>

        <Card className="rounded-[32px] p-5 sm:p-8">
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-sky-600">
            <Compass size={15} aria-hidden="true" />
            Danh mục chuẩn Bộ GD&ĐT
          </div>
          <h2 className="mt-1 text-xl font-black text-slate-900">
            {loading ? "Đang tải danh mục ngành…" : error ? "Danh mục ngành đào tạo" : `Khám phá ${catalog.length} ngành đào tạo`}
          </h2>

          <div className="mt-6 grid min-w-0 gap-3 md:grid-cols-2">
            <div className="min-w-0">
              <label htmlFor="major-search" className="mb-2 block text-xs font-bold text-slate-700">
                Tìm mã hoặc tên ngành
              </label>
              <div className="flex min-w-0 items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 shadow-xs transition focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-100">
                <Search size={18} className="pointer-events-none shrink-0 text-slate-500" aria-hidden="true" />
                <input
                  ref={searchRef}
                  id="major-search"
                  type="search"
                  value={searchQuery}
                  onChange={(event) => { setSearchQuery(event.target.value); setShowAllCatalog(false) }}
                  placeholder="Tìm mã hoặc tên ngành..."
                  className="h-11 min-w-0 w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-500 focus-visible:outline-none"
                />
              </div>
            </div>
            <div className="min-w-0">
              <label htmlFor="major-category" className="mb-2 block text-xs font-bold text-slate-700">
                Lĩnh vực đào tạo
              </label>
              <select
                id="major-category"
                value={selectedCategory}
                onChange={(event) => { setSelectedCategory(event.target.value); setShowAllCatalog(false) }}
                className="h-11 w-full min-w-0 max-w-full truncate rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 shadow-xs outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category === "ALL" ? "Tất cả lĩnh vực" : category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {loading ? (
            <p role="status" className="mt-6 text-sm text-slate-600">Đang tải danh mục ngành…</p>
          ) : error ? (
            <div role="alert" className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
              <p>{error}</p>
              <button type="button" onClick={() => { setLoading(true); setError(null); setLoadAttempt((attempt) => attempt + 1) }} className="mt-3 rounded-xl border border-rose-300 bg-white px-4 py-2 font-bold hover:bg-rose-100">
                Thử lại
              </button>
            </div>
          ) : (
            <>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
                <p role="status" className="text-xs font-medium text-slate-600">
                  Hiển thị {visibleCatalog.length} / {filteredCatalog.length} ngành
                </p>
                {hasFilters && (
                  <button type="button" onClick={clearFilters} className="text-xs font-bold text-sky-700 underline-offset-4 hover:underline">
                    Xóa bộ lọc
                  </button>
                )}
              </div>
              {filteredCatalog.length === 0 ? (
                <p className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-600">
                  {catalog.length ? "Không tìm thấy ngành phù hợp." : "Chưa có ngành đào tạo trong danh mục."}
                </p>
              ) : (
                <div className="mt-5 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {visibleCatalog.map((item) => {
                    const blocks = item.subject_blocks || item.blocks || []
                    return (
                      <Link
                        key={item.major_code}
                        to={`/majors/${item.major_code}`}
                        state={{ from: "/majors" }}
                        className="group flex min-w-0 flex-col justify-between rounded-2xl border border-slate-200/80 bg-white/75 p-4 transition hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white hover:shadow-md"
                      >
                        <div>
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="rounded-md bg-sky-50 px-2 py-0.5 text-xs font-semibold text-sky-700">Mã {item.major_code}</span>
                            <TrendBadge tier={item.trend_tier} isTrending={item.is_trending} reason={item.trend_reason} />
                          </div>
                          {blocks.length > 0 && <p className="mt-1.5 text-xs font-medium text-slate-500">{blocks.slice(0, 3).join(", ")}</p>}
                          <h3 className="mt-2.5 text-sm font-bold leading-snug text-slate-900 group-hover:text-sky-700">
                            {item.name_vi || item.name || item.major_code}
                          </h3>
                          <p className="mt-1 text-xs text-slate-500">{item.category || "Danh mục ngành"}</p>
                        </div>
                        <div className="mt-3.5 flex items-center justify-between border-t border-slate-100 pt-2.5 text-xs font-bold text-sky-600">
                          <span>Xem chi tiết</span>
                          <ChevronRight size={15} className="transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                        </div>
                      </Link>
                    )
                  })}
                </div>
              )}
              {filteredCatalog.length > 9 && (
                <div className="mt-5 text-center">
                  <button type="button" onClick={() => setShowAllCatalog((value) => !value)} className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-2 text-xs font-extrabold text-sky-700 transition hover:bg-sky-100">
                    {showAllCatalog ? "Thu gọn danh sách" : `Xem tất cả ${filteredCatalog.length} ngành`}
                  </button>
                </div>
              )}
            </>
          )}
        </Card>
      </PageContainer>
    </section>
  )
}
