import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Check, ChevronLeft, ChevronRight, RefreshCw, X } from "lucide-react"
import { useAdmin } from "../components/admin/AdminLayout"
import { LLMConnectionPanel } from "../components/admin/LLMConnectionPanel"
import { TrendAgentPanel } from "../components/admin/TrendAgentPanel"
import { requestJSON } from "../services/api"

type Status = "PENDING" | "APPROVED" | "REJECTED"
interface StagingRecord {
  id: string; stream_type: string; major_code?: string; source_title?: string
  source_url?: string; status: Status; raw_content?: string; markdown?: string; created_at?: string
}
const labels: Record<Status, string> = { PENDING: "Chờ duyệt", APPROVED: "Đã duyệt", REJECTED: "Đã từ chối" }
const PAGE_SIZE = 25

export function AdminHITLDashboard() {
  const { notify } = useAdmin()
  const [records, setRecords] = useState<StagingRecord[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<Status | "ALL">("ALL")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const busy = useRef(false)
  const mounted = useRef(true)
  const pending = useRef<AbortController | null>(null)
  const load = useCallback(async () => {
    pending.current?.abort()
    const controller = new AbortController(); pending.current = controller
    setLoading(true); setError(null)
    try {
      const rows = await requestJSON<StagingRecord[]>("/rag-governance/staging", { signal: controller.signal })
      if (!controller.signal.aborted) { setRecords(rows); setSelectedId(current => rows.some(row => row.id === current) ? current : rows[0]?.id || null) }
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không tải được danh sách kiểm duyệt.")
    } finally { if (!controller.signal.aborted) setLoading(false) }
  }, [])
  useEffect(() => { mounted.current = true; void load(); return () => { mounted.current = false; pending.current?.abort() } }, [load])
  const filtered = useMemo(() => records.filter(row => (statusFilter === "ALL" || row.status === statusFilter) &&
    `${row.source_title || ""} ${row.major_code || ""}`.toLocaleLowerCase("vi").includes(search.trim().toLocaleLowerCase("vi"))), [records, search, statusFilter])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pages)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const selected = filtered.find(row => row.id === selectedId)
  const review = async (status: Status) => {
    if (!selected || busy.current) return
    busy.current = true; setSaving(true); setError(null)
    try {
      const updated = await requestJSON<StagingRecord>(`/rag-governance/staging/${selected.id}/review`, {
        method: "POST", body: JSON.stringify({ status, review_notes: labels[status] }),
      }, 30000)
      if (!mounted.current) return
      setRecords(rows => rows.map(row => row.id === updated.id ? updated : row))
      notify(`${labels[status]}: ${selected.source_title || selected.major_code || "Bản ghi"}.`)
    } catch (err) { if (mounted.current) setError(err instanceof Error ? err.message : "Không lưu được quyết định. Dữ liệu chưa thay đổi.") }
    finally { busy.current = false; if (mounted.current) setSaving(false) }
  }
  return <section>
    <div className="admin-page-heading"><div><h1>Kiểm duyệt dữ liệu</h1><p>Rà soát nguồn và nội dung trước khi xuất bản vào kho tư vấn.</p></div><button type="button" className="admin-button" disabled={loading} onClick={() => void load()}><RefreshCw size={17} aria-hidden="true" />Tải lại</button></div>
    <div className="admin-toolbar"><label>Tìm bản ghi<input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} placeholder="Tiêu đề hoặc mã ngành" /></label><label>Trạng thái<select value={statusFilter} onChange={event => { setStatusFilter(event.target.value as Status | "ALL"); setPage(1) }}><option value="ALL">Tất cả trạng thái</option>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
    {error && <p role="alert" className="admin-notice is-error">{error}</p>}
    {loading ? <div role="status" className="admin-panel p-8">Đang tải dữ liệu kiểm duyệt…</div> : <div className="admin-review-grid admin-panel">
      <div className="admin-record-list" aria-label="Danh sách bản ghi">
        {visible.length === 0 && <p className="p-6 text-slate-600">{records.length === 0 ? "Chưa có dữ liệu chờ kiểm duyệt. Bản ghi từ quy trình nạp và khám phá sẽ xuất hiện tại đây." : "Không có bản ghi khớp bộ lọc."}</p>}
        {visible.map(row => <button type="button" key={row.id} className={selectedId === row.id ? "selected" : ""} onClick={() => setSelectedId(row.id)} aria-pressed={selectedId === row.id}><strong>{row.source_title || "Bản ghi chưa đặt tiêu đề"}</strong><span>{row.major_code || "Chưa gắn ngành"} · {labels[row.status]}</span></button>)}
      </div>
      <div className="min-w-0 p-5 sm:p-7">{selected ? <>
        <div className="flex flex-wrap justify-between gap-3 border-b border-slate-200 pb-4"><h2 className="text-lg font-semibold">{selected.source_title || "Chi tiết bản ghi"}</h2><span className="text-sm text-slate-600">{labels[selected.status]}</span></div>
        <dl className="my-4 grid gap-2 text-sm"><div><dt className="inline font-semibold">Mã ngành: </dt><dd className="inline">{selected.major_code || "Chưa gắn"}</dd></div><div><dt className="inline font-semibold">Nguồn: </dt><dd className="inline break-all">{selected.source_url || "Chưa cung cấp"}</dd></div></dl>
        <div className="admin-markdown min-h-40 overflow-auto break-words"><Markdown remarkPlugins={[remarkGfm]}>{selected.raw_content || selected.markdown || "Bản ghi chưa có nội dung văn bản."}</Markdown></div>
        <div className="mt-6 flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-4"><button type="button" className="admin-button" disabled={saving || selected.status !== "PENDING"} onClick={() => void review("REJECTED")}><X size={17} aria-hidden="true" />Từ chối</button><button type="button" className="admin-button primary" disabled={saving || selected.status !== "PENDING"} onClick={() => void review("APPROVED")}><Check size={17} aria-hidden="true" />{saving ? "Đang lưu…" : "Phê duyệt"}</button></div>
      </> : <p className="py-12 text-slate-600">Chọn bản ghi trong danh sách để xem nội dung.</p>}</div>
    </div>}
    <div className="admin-pagination"><span>{filtered.length} bản ghi · Trang {currentPage}/{pages}</span><button type="button" className="admin-button" aria-label="Trang trước" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={18} /></button><button type="button" className="admin-button" aria-label="Trang sau" disabled={currentPage >= pages} onClick={() => setPage(currentPage + 1)}><ChevronRight size={18} /></button></div>
  </section>
}

export function AdminTrendsPage() {
  const { notify } = useAdmin()
  return <section><div className="admin-page-heading"><div><h1>Xu hướng nghề nghiệp</h1><p>Rà soát các nguồn tham khảo và duyệt bản nháp trước khi cập nhật danh mục.</p></div></div><TrendAgentPanel onNotify={notify} /></section>
}
export function AdminAISettingsPage() {
  const { notify } = useAdmin()
  return <section><div className="admin-page-heading"><div><h1>Cấu hình AI & API</h1><p>Kiểm tra bản nháp, áp dụng cấu hình và quản lý credential của dịch vụ AI.</p></div></div><LLMConnectionPanel onNotify={notify} /></section>
}
