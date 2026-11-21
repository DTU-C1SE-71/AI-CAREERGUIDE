import { useEffect, useRef, useState } from "react"
import { Link } from "react-router"
import { BookOpen, Check, Copy, Download, FileUp } from "lucide-react"
import { useAdmin } from "../components/admin/AdminLayout"
import { requestJSON } from "../services/api"

interface PreviewMajor {
  major_code: string
  name: string
  category?: string
}
interface ImportPreview {
  majors?: PreviewMajor[]
  preview?: PreviewMajor[]
  sheet_name?: string
  sheets?: Array<{ sheet_name: string; majors: PreviewMajor[]; count: number }>
  persisted_to_db?: boolean
  total?: number
}
const PAGE_SIZE = 25
const EXTRACTION_PROMPT = `Đọc tài liệu danh mục ngành được cung cấp và điền vào file Excel mẫu đính kèm.
Giữ nguyên tên và thứ tự các cột trong mẫu. Mỗi dòng là một ngành có trong tài liệu, ghi đúng mã ngành, tên ngành và nguồn.
Không tự tạo ngành, tổ hợp, điểm chuẩn hay điểm RIASEC. Trường không được nguồn xác nhận phải để trống và ghi chú dữ liệu còn thiếu.
Đối chiếu lại mã ngành, trạng thái hoạt động và các dòng trùng trước khi xuất file .xlsx. Kết quả cần được người quản trị rà soát trước khi nhập vào hệ thống.`

export function AdminImportPage() {
  const { notify } = useAdmin()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [sheet, setSheet] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [previewPage, setPreviewPage] = useState(1)
  const lock = useRef(false)
  const version = useRef(0)
  const controller = useRef<AbortController | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => () => { version.current += 1; controller.current?.abort() }, [])
  const rows = preview?.sheets?.find(item => item.sheet_name === sheet)?.majors || preview?.majors || preview?.preview || []
  const previewPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE))

  const upload = async (apply: boolean) => {
    if (!file || lock.current) return
    lock.current = true
    setBusy(true)
    setError(null)
    setSuccess(null)
    const expected = ++version.current
    const active = new AbortController()
    controller.current = active
    try {
      const data = new FormData()
      data.append("file", file)
      const query = new URLSearchParams({
        preview_only: String(!apply),
        replace_catalog: "true",
        ...(sheet ? { sheet_name: sheet } : {}),
      })
      const result = await requestJSON<ImportPreview>(`/v1/taxonomy/import-excel?${query}`, {
        method: "POST", body: data, signal: active.signal,
      }, 60000)
      if (expected !== version.current) return
      if (apply) {
        if (result.persisted_to_db !== true) throw new Error("Máy chủ chưa xác nhận ghi dữ liệu. Danh mục chưa được báo là đã lưu.")
        const message = `Đã lưu ${result.total ?? rows.length} ngành vào cơ sở dữ liệu.`
        setSuccess(message)
        notify(message)
        setFile(null)
        setPreview(null)
        setSheet("")
        if (fileInput.current) fileInput.current.value = ""
      } else {
        setPreview(result)
        setSheet(result.sheet_name || result.sheets?.[0]?.sheet_name || "")
        setPreviewPage(1)
      }
    } catch (err) {
      if (expected === version.current && !active.signal.aborted) {
        setError(err instanceof Error ? err.message : "Không xử lý được tệp. Kiểm tra tệp và thử lại.")
      }
    } finally {
      lock.current = false
      if (expected === version.current) setBusy(false)
    }
  }

  const copyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(EXTRACTION_PROMPT)
      setCopied(true)
      notify("Đã sao chép hướng dẫn trích xuất.")
    } catch {
      setError("Chưa sao chép được. Bạn có thể chọn và sao chép trực tiếp phần hướng dẫn bên dưới.")
    }
  }

  return (
    <section aria-labelledby="admin-import-title">
      <div className="admin-page-heading">
        <div>
          <h1 id="admin-import-title">Nhập danh mục</h1>
          <p>Chuẩn bị tệp, kiểm tra bản xem trước rồi lưu dữ liệu đã đối chiếu nguồn.</p>
        </div>
        <Link to="/admin/catalog" className="admin-button"><BookOpen size={17} aria-hidden="true" />Xem danh mục đã lưu</Link>
      </div>

      <section className="admin-panel mb-6 p-5 sm:p-6" aria-labelledby="import-template-title">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="import-template-title" className="text-lg font-semibold">Chuẩn bị tệp dữ liệu</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">Dùng đúng cấu trúc cột trong mẫu Excel. Hệ thống hỗ trợ .xlsx và .csv; dữ liệu thiếu cần được kiểm tra, không điền số ước lượng.</p>
          </div>
          <a className="admin-button" href="/MOET_Major_Import_Template_Standard.xlsx" download><Download size={17} aria-hidden="true" />Tải mẫu Excel</a>
        </div>
        <details className="mt-5 border-t border-slate-200 pt-4">
          <summary className="min-h-10 cursor-pointer font-semibold">Hướng dẫn trích xuất từ tài liệu bằng AI</summary>
          <p className="mt-3 text-sm text-slate-600">Nếu dùng AI hỗ trợ chuyển PDF sang Excel, hãy gửi kèm tài liệu nguồn và mẫu. Kiểm tra lại nội dung trước khi tải lên.</p>
          <pre className="my-4 whitespace-pre-wrap rounded-md bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-700">{EXTRACTION_PROMPT}</pre>
          <button type="button" className="admin-button" onClick={() => void copyPrompt()}>{copied ? <Check size={17} aria-hidden="true" /> : <Copy size={17} aria-hidden="true" />}{copied ? "Đã sao chép hướng dẫn" : "Sao chép hướng dẫn"}</button>
        </details>
      </section>

      <section className="admin-panel p-5 sm:p-6" aria-labelledby="import-upload-title" aria-busy={busy}>
        <h2 id="import-upload-title" className="text-lg font-semibold">Tải lên và xem trước</h2>
        <p className="mb-5 mt-2 text-sm text-slate-600">Xem trước chưa thay đổi cơ sở dữ liệu. Chọn đúng trang tính và rà soát mã, tên ngành trước khi lưu.</p>
        <label className="admin-field" htmlFor="catalog-import-file">Tệp dữ liệu</label>
        <input ref={fileInput} id="catalog-import-file" type="file" accept=".xlsx,.csv" disabled={busy}
          className="mt-2 w-full" onChange={event => {
            setFile(event.target.files?.[0] || null)
            setPreview(null)
            setSheet("")
            setPreviewPage(1)
            setError(null)
            setSuccess(null)
          }} />
        <div className="my-5 flex flex-wrap items-end gap-3">
          <button type="button" className="admin-button" disabled={!file || busy} onClick={() => void upload(false)}><FileUp size={17} aria-hidden="true" />{busy ? "Đang xử lý…" : "Xem trước tệp"}</button>
          {preview?.sheets && preview.sheets.length > 1 && <label className="admin-field">Trang tính<select value={sheet} disabled={busy} onChange={event => { setSheet(event.target.value); setPreviewPage(1) }}>{preview.sheets.map(item => <option key={item.sheet_name} value={item.sheet_name}>{item.sheet_name} ({item.count})</option>)}</select></label>}
        </div>
        {error && <p role="alert" className="admin-notice is-error">{error}</p>}
        {success && <div role="status" className="admin-notice is-success"><span>{success}</span><Link to="/admin/catalog" className="font-semibold underline underline-offset-4">Kiểm tra danh mục</Link></div>}
        {preview && <>
          <div className="border-t border-slate-200 pt-5"><h3 className="font-semibold">Bản xem trước</h3><p className="my-3 text-sm" role="status">{rows.length} ngành trong bản xem trước{sheet ? ` · ${sheet}` : ""}.</p></div>
          {rows.length ? <>
            <div className="overflow-x-auto"><table className="admin-table"><caption className="sr-only">Danh mục xem trước, trang {previewPage}</caption><thead><tr><th scope="col">Mã ngành</th><th scope="col">Tên ngành</th><th scope="col">Nhóm</th></tr></thead><tbody>{rows.slice((previewPage - 1) * PAGE_SIZE, previewPage * PAGE_SIZE).map(row => <tr key={row.major_code}><td>{row.major_code}</td><td>{row.name}</td><td>{row.category || "Chưa phân nhóm"}</td></tr>)}</tbody></table></div>
            <div className="admin-pagination"><span>Trang {previewPage}/{previewPages}</span><button className="admin-button" type="button" disabled={previewPage <= 1} onClick={() => setPreviewPage(value => value - 1)}>Trước</button><button className="admin-button" type="button" disabled={previewPage >= previewPages} onClick={() => setPreviewPage(value => value + 1)}>Sau</button></div>
          </> : <p className="rounded-md bg-slate-50 p-4 text-sm text-slate-600">Tệp chưa có ngành để nhập. Kiểm tra tên cột và các dòng dữ liệu rồi xem trước lại.</p>}
          <fieldset className="mt-5 border-t border-slate-200 pt-4" disabled={busy}><legend className="font-semibold">Cách lưu danh mục</legend>
            <p className="mt-2 mb-4 text-sm text-slate-600">Khi lưu danh mục mới, hệ thống sẽ tự động xóa toàn bộ danh mục ngành cũ và thay thế hoàn toàn bằng danh mục trong tệp này.</p>
            <button type="button" className="admin-button primary" disabled={!rows.length || busy} onClick={() => { if (window.confirm("Xóa toàn bộ danh mục ngành cũ và thay thế hoàn toàn bằng tệp đã chọn?")) void upload(true) }}>{busy ? "Đang lưu…" : "Lưu danh mục"}</button>
          </fieldset>
        </>}
      </section>
    </section>
  )
}
