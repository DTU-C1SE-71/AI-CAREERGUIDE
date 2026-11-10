import { motion } from "framer-motion"
import {
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Copy,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  Layers3,
  RefreshCw,
  Search,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react"
import { type ChangeEvent, type DragEvent, useEffect, useMemo, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import * as XLSX from "xlsx"
import { Badge } from "../components/common/Badge"
import { Button } from "../components/common/Button"
import { PageContainer } from "../components/layout/PageContainer"
import { apiRequest } from "../services/api"

type Status = "PENDING" | "APPROVED" | "REJECTED"

interface StagingRecord {
  id: number | string
  title: string
  majorCode: string
  source: string
  type: string
  status: Status
  updated: string
  markdown: string
}

interface PreviewMajorItem {
  major_code: string
  raw_code?: string
  name: string
  category?: string
  field_code?: string
  group_code?: string
  group_name?: string
  cip_code?: string
  holland_code?: string
  legacy_tt09_codes?: string
  blocks?: string[]
  riasec?: Record<string, number>
  cognitive?: Record<string, string>
}

const initialRecords: StagingRecord[] = [
  {
    id: 1,
    title: "Lộ trình Khoa học dữ liệu",
    majorCode: "7460108",
    source: "daa.uit.edu.vn",
    type: "Tavily Discovery",
    status: "PENDING",
    updated: "2 phút trước",
    markdown: `## Tuần 1\n- Xác suất thống kê\n- Python cơ bản`,
  },
  {
    id: 2,
    title: "Danh mục ngành TT09",
    majorCode: "7480101",
    source: "moet.gov.vn",
    type: "Excel Auto-Map",
    status: "PENDING",
    updated: "18 phút trước",
    markdown: `**Mã:** 7480101 · **Ngành:** Khoa học máy tính · **CIP:** 11.0701 · **Holland:** IRC`,
  },
  {
    id: 3,
    title: "Lộ trình Kỹ thuật phần mềm",
    majorCode: "7480103",
    source: "hust.edu.vn",
    type: "Tavily Discovery",
    status: "APPROVED",
    updated: "1 giờ trước",
    markdown: `Đã lưu 12 nhiệm vụ vào **pgvector**.`,
  },
]

interface DbHealthPayload {
  status?: string
  majors_count?: number
}

interface ParsedSheetOption {
  sheet_name: string
  count: number
  majors: PreviewMajorItem[]
}

const ITEMS_PER_PAGE = 50

function parseExcelClientFallback(buffer: ArrayBuffer): {
  activeSheet: string
  majors: PreviewMajorItem[]
  sheets: ParsedSheetOption[]
} {
  const wb = XLSX.read(buffer, { type: "array" })
  const allSheets: ParsedSheetOption[] = []

  const headerMapLookup: Record<string, string> = {
    field_code: "field_code",
    group_code: "group_code",
    group_name: "group_name",
    major_code: "major_code",
    "mã ngành": "major_code",
    ma_nganh: "major_code",
    major_name: "major_name",
    "tên ngành đào tạo": "major_name",
    ten_nganh: "major_name",
    legacy_tt09_codes: "legacy_tt09_codes",
    cip_code: "cip_code",
    holland_code: "holland_code",
    riasec_r: "riasec_r",
    riasec_i: "riasec_i",
    riasec_a: "riasec_a",
    riasec_s: "riasec_s",
    riasec_e: "riasec_e",
    riasec_c: "riasec_c",
    subject_blocks: "subject_blocks",
  }

  for (const sheetName of wb.SheetNames) {
    const ws = wb.Sheets[sheetName]
    const rows = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1, defval: "" })
    if (!rows.length) continue

    let headerIdx = -1
    const colIdxMap: Record<number, string> = {}

    for (let i = 0; i < Math.min(20, rows.length); i++) {
      const rowLow = rows[i].map((c) => String(c ?? "").trim().toLowerCase())
      if (rowLow.some((c) => c === "major_code" || c === "mã ngành" || c === "ma_nganh")) {
        headerIdx = i
        rowLow.forEach((col, cIdx) => {
          if (headerMapLookup[col]) colIdxMap[cIdx] = headerMapLookup[col]
        })
        break
      }
    }

    if (headerIdx === -1) continue

    const parsed: PreviewMajorItem[] = []
    const seen = new Set<string>()

    for (let r = headerIdx + 1; r < rows.length; r++) {
      const row = rows[r]
      const rec: Record<string, string> = {}
      Object.entries(colIdxMap).forEach(([idxStr, key]) => {
        rec[key] = String(row[Number(idxStr)] ?? "").trim()
      })

      const digits = (rec.major_code || "").replace(/\D/g, "")
      if (digits.length !== 6 && digits.length !== 7) continue
      if (seen.has(digits)) continue
      seen.add(digits)

      const full7 = digits.length === 6 ? `7${digits}` : digits
      const raw6 = digits.length === 7 && digits.startsWith("7") ? digits.slice(1) : digits
      const numOr = (v: string, fb: number) => {
        const n = parseFloat(v)
        return Number.isFinite(n) ? Number(n.toFixed(2)) : fb
      }
      const riasec = {
        R: numOr(rec.riasec_r, 0.5),
        I: numOr(rec.riasec_i, 0.6),
        A: numOr(rec.riasec_a, 0.3),
        S: numOr(rec.riasec_s, 0.4),
        E: numOr(rec.riasec_e, 0.4),
        C: numOr(rec.riasec_c, 0.5),
      }
      const blocks = rec.subject_blocks
        ? rec.subject_blocks.split(/[,;/]/).map((b) => b.trim().toUpperCase()).filter(Boolean)
        : ["A00", "A01", "D01"]

      parsed.push({
        major_code: full7,
        raw_code: raw6,
        name: rec.major_name || `Ngành ${raw6}`,
        field_code: rec.field_code || raw6.slice(0, 2),
        group_code: rec.group_code || raw6.slice(0, 4),
        group_name: rec.group_name,
        cip_code: rec.cip_code || "-",
        holland_code: rec.holland_code || "IRS",
        legacy_tt09_codes: rec.legacy_tt09_codes || full7,
        blocks,
        riasec,
        cognitive: {
          abstract_thinking: riasec.I >= 0.75 ? "high" : "medium",
          analytical_reasoning: Math.max(riasec.I, riasec.C) >= 0.75 ? "high" : "medium",
        },
      })
    }

    if (parsed.length > 0) {
      allSheets.push({ sheet_name: sheetName, count: parsed.length, majors: parsed })
    }
  }

  if (allSheets.length === 0) {
    return { activeSheet: "", majors: [], sheets: [] }
  }
  const activeTabIdx = Number((wb.Workbook?.Views?.[0] as { activeTab?: number } | undefined)?.activeTab ?? 0)
  const activeTabName = wb.SheetNames[activeTabIdx]
  const activeMatch = activeTabName ? allSheets.find((s) => s.sheet_name === activeTabName) : undefined
  const best = activeMatch ?? allSheets[0]
  return { activeSheet: best.sheet_name, majors: best.majors, sheets: allSheets }
}

export function AdminHITLDashboard() {
  const [records, setRecords] = useState<StagingRecord[]>(initialRecords)
  const [selectedId, setSelectedId] = useState<number | string>(initialRecords[0].id)
  const [statusFilter, setStatusFilter] = useState<Status | "ALL">("ALL")
  const [searchTerm, setSearchTerm] = useState("")
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">("markdown")
  const [dbHealth, setDbHealth] = useState<DbHealthPayload | null>(null)
  const [toast, setToast] = useState<{ msg: string; error?: boolean } | null>(null)
  const [copiedPrompt, setCopiedPrompt] = useState(false)

  // Drag & Drop + Preview state
  const [isDragging, setIsDragging] = useState(false)
  const [parsingFile, setParsingFile] = useState(false)
  const [committingImport, setCommittingImport] = useState(false)
  const [previewFile, setPreviewFile] = useState<File | null>(null)
  const [previewMajors, setPreviewMajors] = useState<PreviewMajorItem[]>([])
  const [parsedSheets, setParsedSheets] = useState<ParsedSheetOption[]>([])
  const [activeSheetName, setActiveSheetName] = useState("")
  const [parseTimeMs, setParseTimeMs] = useState<number | null>(null)
  const [previewSearch, setPreviewSearch] = useState("")
  const [previewPage, setPreviewPage] = useState(1)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const showToast = (msg: string, error = false) => {
    setToast({ msg, error })
    window.setTimeout(() => setToast(null), 4500)
  }

  // Prevent browser from navigating away if user drops file slightly outside dropzone
  useEffect(() => {
    const preventNav = (e: globalThis.DragEvent) => {
      e.preventDefault()
    }
    window.addEventListener("dragover", preventNav)
    window.addEventListener("drop", preventNav)
    return () => {
      window.removeEventListener("dragover", preventNav)
      window.removeEventListener("drop", preventNav)
    }
  }, [])

  useEffect(() => {
    let mounted = true
    apiRequest<DbHealthPayload | null>("/health/db", null).then((res) => {
      if (mounted && res) setDbHealth(res)
    })

    apiRequest<
      Array<{
        id: string
        stream_type: string
        major_code?: string
        source_title?: string
        source_url?: string
        status: Status
        raw_markdown?: string
      }> | null
    >("/rag-governance/staging", null).then((apiRecords) => {
      if (mounted && apiRecords && Array.isArray(apiRecords) && apiRecords.length > 0) {
        const mapped: StagingRecord[] = apiRecords.map((r) => ({
          id: r.id,
          title: r.source_title || `Bản ghi ${r.major_code || "MOET"}`,
          majorCode: r.major_code || "MOET",
          source: r.source_url || "moet.gov.vn",
          type: r.stream_type?.includes("STREAM_A") ? "Excel Ingest" : "Tavily Discovery",
          status: r.status || "PENDING",
          updated: "Đồng bộ",
          markdown: r.raw_markdown || `**Mã:** ${r.major_code}`,
        }))
        setRecords((prev) => [...mapped, ...prev])
      }
    })

    return () => {
      mounted = false
    }
  }, [])

  const filteredRecords = useMemo(() => {
    const q = searchTerm.trim().toLowerCase()
    return records.filter((rec) => {
      const matchStatus = statusFilter === "ALL" || rec.status === statusFilter
      const matchSearch =
        !q ||
        rec.title.toLowerCase().includes(q) ||
        rec.majorCode.toLowerCase().includes(q)
      return matchStatus && matchSearch
    })
  }, [records, statusFilter, searchTerm])

  const selected =
    filteredRecords.find((record) => record.id === selectedId) ??
    records.find((record) => record.id === selectedId) ??
    records[0]

  const pendingCount = useMemo(
    () => records.filter((r) => r.status === "PENDING").length,
    [records],
  )

  const indexedPreviewMajors = useMemo(() => {
    const withStt = previewMajors.map((item, idx) => ({ stt: idx + 1, item }))
    const q = previewSearch.trim().toLowerCase()
    if (!q) return withStt
    return withStt.filter(
      ({ item }) =>
        item.name?.toLowerCase().includes(q) ||
        item.major_code?.toLowerCase().includes(q) ||
        item.raw_code?.toLowerCase().includes(q) ||
        item.cip_code?.toLowerCase().includes(q) ||
        item.holland_code?.toLowerCase().includes(q) ||
        item.group_code?.toLowerCase().includes(q) ||
        item.legacy_tt09_codes?.toLowerCase().includes(q),
    )
  }, [previewMajors, previewSearch])

  const totalPreviewPages = Math.max(1, Math.ceil(indexedPreviewMajors.length / ITEMS_PER_PAGE))
  const paginatedPreviewMajors = useMemo(() => {
    const start = (previewPage - 1) * ITEMS_PER_PAGE
    return indexedPreviewMajors.slice(start, start + ITEMS_PER_PAGE)
  }, [indexedPreviewMajors, previewPage])

  const updateStatus = async (status: Status) => {
    setRecords((current) =>
      current.map((record) =>
        record.id === selected.id ? { ...record, status, updated: "Vừa cập nhật" } : record,
      ),
    )
    if (typeof selected.id === "string" && selected.id.length > 10) {
      await apiRequest(`/rag-governance/staging/${selected.id}/review`, null, {
        method: "POST",
        body: JSON.stringify({
          status,
          review_notes: status === "APPROVED" ? "Approved" : "Rejected",
        }),
      })
    }
    showToast(status === "APPROVED" ? `Đã duyệt "${selected.title}"` : `Đã từ chối "${selected.title}"`)
  }

  const EXTERNAL_AI_PROMPT =
    "Hãy đóng vai chuyên gia dữ liệu giáo dục đại học Việt Nam và chuẩn phân loại quốc tế O*NET/CIP. " +
    "Tôi đính kèm file PDF Thông tư danh mục ngành đào tạo của Bộ GD&ĐT và file Excel mẫu (MOET_Major_Import_Template_Standard.xlsx). " +
    "Nhiệm vụ của bạn:\n" +
    "1. Đọc TOÀN BỘ danh mục ngành trong Phụ lục I và bảng chuyển đổi mã ngành cũ (nếu có) ở Phụ lục II trong file PDF — trích xuất đầy đủ mọi ngành có trong văn bản (số lượng ngành linh hoạt theo từng Thông tư).\n" +
    "2. Xuất ra file Excel (.xlsx) tuân thủ CHÍNH XÁC 19 cột như Sheet 'MAU_NHAP_NGANH_CHUAN' của file mẫu:\n" +
    "- Dòng 1 giữ nguyên tên kỹ thuật: field_code, field_name, group_code, group_name, major_code, major_name, legacy_tt09_codes, degree_levels, circular_note, cip_code, holland_code, riasec_r, riasec_i, riasec_a, riasec_s, riasec_e, riasec_c, subject_blocks, career_paths.\n" +
    "- Xóa các dòng ví dụ mẫu và điền toàn bộ dữ liệu thực tế từ Dòng 2 hoặc Dòng 3.\n" +
    "3. Tham chiếu Sheet 'BANG_TRA_CUU_CIP_RIASEC' kết hợp đặc thù từng ngành để điền mã CIP (cip_code), mã Holland 3 ký tự (holland_code), 6 trọng số RIASEC (0.0 -> 1.0), tổ hợp xét tuyển (subject_blocks) và nghề nghiệp (career_paths).\n" +
    "4. Xuất kết quả thành file .xlsx hoàn chỉnh để tôi tải về và import vào hệ thống."

  const copyExternalAiPrompt = async () => {
    try {
      await navigator.clipboard.writeText(EXTERNAL_AI_PROMPT)
      setCopiedPrompt(true)
      showToast("Đã copy Prompt AI!")
      window.setTimeout(() => setCopiedPrompt(false), 2500)
    } catch {
      showToast("Hãy copy Prompt tại Sheet 3 trong File Excel mẫu.", true)
    }
  }

  const downloadExcelTemplate = () => {
    const link = document.createElement("a")
    link.href = "/MOET_Major_Import_Template_Standard.xlsx"
    link.download = "MOET_Major_Import_Template_Standard.xlsx"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    showToast("Đang tải xuống file Excel mẫu...")
  }

  const processSelectedFile = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase()
    if (!ext || !["xlsx", "xls", "csv"].includes(ext)) {
      showToast("Chỉ hỗ trợ file .xlsx, .xls hoặc .csv!", true)
      return
    }

    setParsingFile(true)
    setPreviewFile(file)
    setPreviewSearch("")
    setPreviewPage(1)

    const t0 = performance.now()
    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch("/api/v1/taxonomy/import-excel?preview_only=true", {
        method: "POST",
        body: formData,
      })
      if (res.ok) {
        const data = await res.json()
        const majors: PreviewMajorItem[] = data.majors || data.preview || []
        const sheets: ParsedSheetOption[] = data.sheets || []
        if (majors.length > 0) {
          setPreviewMajors(majors)
          setParsedSheets(sheets)
          setActiveSheetName(data.sheet_name || sheets[0]?.sheet_name || "Sheet 1")
          setParseTimeMs(data.parse_ms ?? Math.round(performance.now() - t0))
          showToast(`Đã đọc ${majors.length} ngành từ "${file.name}".`)
          return
        }
      }
      // Fallback: Parse directly in browser if backend is offline or unreachable
      const buf = await file.arrayBuffer()
      const localRes = parseExcelClientFallback(buf)
      if (localRes.majors.length === 0) {
        throw new Error("Không tìm thấy mã ngành hợp lệ (6 hoặc 7 số) trong file.")
      }
      setPreviewMajors(localRes.majors)
      setParsedSheets(localRes.sheets)
      setActiveSheetName(localRes.activeSheet)
      setParseTimeMs(Math.round(performance.now() - t0))
      showToast(`Đã đọc ${localRes.majors.length} ngành từ Sheet "${localRes.activeSheet}".`)
    } catch (err) {
      setPreviewFile(null)
      setPreviewMajors([])
      setParsedSheets([])
      setActiveSheetName("")
      setParseTimeMs(null)
      showToast(err instanceof Error ? err.message : "Lỗi đọc file Excel.", true)
    } finally {
      setParsingFile(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleSheetChange = (sheetName: string) => {
    const found = parsedSheets.find((s) => s.sheet_name === sheetName)
    if (found) {
      setActiveSheetName(found.sheet_name)
      setPreviewMajors(found.majors)
      setPreviewPage(1)
      showToast(`Đã chuyển sang Sheet "${found.sheet_name}" (${found.majors.length} ngành).`)
    }
  }

  const confirmImportToDb = async () => {
    if (!previewFile || previewMajors.length === 0) return
    setCommittingImport(true)
    try {
      const formData = new FormData()
      formData.append("file", previewFile)
      const qs = new URLSearchParams({
        preview_only: "false",
        ...(activeSheetName ? { sheet_name: activeSheetName } : {}),
      }).toString()
      const res = await fetch(`/api/v1/taxonomy/import-excel?${qs}`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        throw new Error("Backend chưa phản hồi (cần chạy Backend cổng 8000 để lưu vào CSDL).")
      }
      const data = await res.json()
      const totalImported = data.total ?? previewMajors.length

      const newRecord: StagingRecord = {
        id: Date.now(),
        title: `Import · ${previewFile.name}`,
        majorCode: `${totalImported} ngành`,
        source: `${previewFile.name} (${activeSheetName})`,
        type: "Excel Auto-Map",
        status: "APPROVED",
        updated: "Vừa đồng bộ",
        markdown: `Đã nạp **${totalImported} ngành** từ Sheet \`${activeSheetName}\` (Mới: ${data.inserted ?? 0}, Cập nhật: ${data.updated ?? totalImported}).`,
      }
      setRecords((prev) => [newRecord, ...prev])
      setSelectedId(newRecord.id)
      setDbHealth((prev) => ({ ...prev, majors_count: totalImported }))
      showToast(`Đã lưu ${totalImported} ngành vào CSDL!`)
      setPreviewFile(null)
      setPreviewMajors([])
      setParsedSheets([])
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Lỗi kết nối Backend.", true)
    } finally {
      setCommittingImport(false)
    }
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) processSelectedFile(file)
  }

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    e.dataTransfer.dropEffect = "copy"
    if (!isDragging) setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) processSelectedFile(file)
  }

  return (
    <section className="min-h-screen py-5">
      <PageContainer className="max-w-[1450px]">
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mb-4 flex items-center justify-between gap-3 rounded-2xl border px-4 py-2.5 text-xs font-bold shadow-sm ${
              toast.error
                ? "border-rose-200 bg-rose-50 text-rose-800"
                : "border-emerald-200 bg-emerald-50 text-emerald-800"
            }`}
          >
            <span className="flex items-center gap-2">
              <CheckCircle2
                size={15}
                className={toast.error ? "text-rose-600" : "text-emerald-600"}
              />
              {toast.msg}
            </span>
            <button onClick={() => setToast(null)} className="opacity-70 hover:opacity-100">
              <X size={14} />
            </button>
          </motion.div>
        )}

        {/* Minimal Header */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-black tracking-tight text-slate-900 sm:text-2xl">
            Quản trị Danh mục Ngành
          </h1>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 rounded-xl border border-white/80 bg-white/75 px-3 py-1.5 shadow-sm">
              <Database size={14} className="text-sky-600" />
              <span className="text-[11px] text-slate-500">CSDL:</span>
              <span className="text-xs font-black text-slate-900">
                {dbHealth?.majors_count !== undefined ? `${dbHealth.majors_count} ngành` : "--"}
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/80 bg-white/75 px-3 py-1.5 shadow-sm">
              <Clock3 size={14} className="text-amber-600" />
              <span className="text-[11px] text-slate-500">Chờ duyệt:</span>
              <span className="text-xs font-black text-amber-600">{pendingCount}</span>
            </div>
          </div>
        </div>

        {/* 2 Compact Cards: Excel Template | AI Prompt */}
        <div className="mb-4 grid gap-3 md:grid-cols-2">
          <div className="glass-card flex items-center justify-between gap-3 rounded-2xl p-3.5">
            <div className="flex items-center gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-emerald-500 text-white">
                <FileSpreadsheet size={18} />
              </span>
              <div>
                <h2 className="text-xs font-black text-slate-900">File Excel Mẫu (.xlsx)</h2>
                <p className="text-[10px] text-slate-500">19 cột chuẩn · Kèm mô tả cách nhập từng cột</p>
              </div>
            </div>
            <Button
              onClick={downloadExcelTemplate}
              icon={Download}
              className="!min-h-8 !px-3.5 !py-1.5 !text-xs !bg-emerald-600 hover:!bg-emerald-700 shrink-0"
            >
              Tải mẫu
            </Button>
          </div>

          <div className="glass-card flex items-center justify-between gap-3 rounded-2xl p-3.5">
            <div className="flex items-center gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-sky-500 text-white">
                <Sparkles size={18} />
              </span>
              <div>
                <h2 className="text-xs font-black text-slate-900">Prompt cho AI</h2>
                <p className="text-[10px] text-slate-500">Chuyển PDF Thông tư → Excel</p>
              </div>
            </div>
            <Button
              variant={copiedPrompt ? "primary" : "secondary"}
              onClick={copyExternalAiPrompt}
              icon={copiedPrompt ? Check : Copy}
              className="!min-h-8 !px-3.5 !py-1.5 !text-xs shrink-0"
            >
              {copiedPrompt ? "Đã Copy" : "Copy Prompt"}
            </Button>
          </div>
        </div>

        {/* Drag & Drop Excel Upload + Preview Table */}
        <div className="glass-card mb-5 rounded-3xl p-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={handleFileChange}
          />

          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click()
            }}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`flex min-h-24 w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed p-4 text-center transition cursor-pointer select-none ${
              isDragging
                ? "border-sky-500 bg-sky-100/80 ring-4 ring-sky-200"
                : "border-sky-200 bg-sky-50/40 hover:border-sky-400 hover:bg-sky-50/70"
            }`}
          >
            <UploadCloud
              size={22}
              className={`pointer-events-none mb-1.5 transition ${
                isDragging ? "text-sky-600 animate-bounce" : "text-sky-500"
              }`}
            />
            <p className="pointer-events-none text-xs font-extrabold text-slate-700">
              {parsingFile
                ? "Đang phân tích file Excel..."
                : isDragging
                  ? "Thả file vào đây"
                  : "Kéo thả file Excel (.xlsx, .csv) vào đây hoặc bấm chọn file"}
            </p>
          </div>

          {/* Preview Table */}
          {previewMajors.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-2xl border border-sky-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-100 bg-sky-50/80 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="emerald">Tổng: {previewMajors.length} ngành</Badge>
                  <span className="max-w-[200px] truncate text-xs font-bold text-slate-700">
                    {previewFile?.name}
                  </span>
                  {parsedSheets.length > 1 ? (
                    <div className="flex flex-wrap items-center gap-1 rounded-xl bg-white p-1 border border-sky-200 shadow-2xs">
                      {parsedSheets.map((s) => {
                        const isActive = s.sheet_name === activeSheetName
                        return (
                          <button
                            key={s.sheet_name}
                            type="button"
                            onClick={() => handleSheetChange(s.sheet_name)}
                            className={`rounded-lg px-2.5 py-1 text-[11px] font-bold transition ${
                              isActive
                                ? "bg-sky-600 text-white shadow-xs"
                                : "text-slate-600 hover:bg-sky-50 hover:text-sky-700"
                            }`}
                          >
                            {s.sheet_name} ({s.count} ngành)
                          </button>
                        )
                      })}
                    </div>
                  ) : (
                    activeSheetName && (
                      <span className="rounded-md bg-white px-2 py-0.5 text-[10px] font-bold text-slate-500 border border-slate-200">
                        Sheet: {activeSheetName} ({previewMajors.length} ngành)
                      </span>
                    )
                  )}
                  {parseTimeMs !== null && (
                    <span className="text-[10px] font-semibold text-slate-400">
                      ({parseTimeMs}ms)
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
                    <input
                      value={previewSearch}
                      onChange={(e) => {
                        setPreviewSearch(e.target.value)
                        setPreviewPage(1)
                      }}
                      placeholder="Tìm mã / tên / CIP..."
                      className="h-8 w-44 rounded-lg border border-slate-200 bg-white pl-8 pr-2.5 text-xs outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </div>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setPreviewMajors([])
                      setPreviewFile(null)
                    }}
                    className="!min-h-8 !px-3 !py-1 !text-xs"
                  >
                    Hủy
                  </Button>
                  <Button
                    onClick={confirmImportToDb}
                    loading={committingImport}
                    icon={Check}
                    className="!min-h-8 !px-4 !py-1 !text-xs"
                  >
                    Import {previewMajors.length} ngành vào CSDL
                  </Button>
                </div>
              </div>

              <div className="max-h-[420px] overflow-auto">
                <table className="w-full border-collapse text-left text-[11px]">
                  <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] font-extrabold uppercase text-slate-500 shadow-sm">
                    <tr>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center w-10">STT</th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Mã TT74</th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Mã TT09</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[170px]">Tên ngành</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center">Nhóm</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center">CIP</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 text-center">Holland</th>
                      <th className="border-b border-slate-200 px-2.5 py-2 min-w-[235px]">
                        Vector RIASEC (R·I·A·S·E·C)
                      </th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Khối thi</th>
                      <th className="border-b border-slate-200 px-2.5 py-2">Nhận thức</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {paginatedPreviewMajors.map(({ stt, item }) => {
                      const rv = item.riasec || {}
                      const cog = item.cognitive || {}
                      return (
                        <tr key={`${stt}-${item.major_code}`} className="hover:bg-sky-50/40">
                          <td className="px-2.5 py-1.5 text-center font-bold text-slate-500">{stt}</td>
                          <td className="px-2.5 py-1.5 font-mono font-bold text-sky-700">
                            {item.major_code}
                          </td>
                          <td
                            className="max-w-[110px] truncate px-2.5 py-1.5 font-mono text-[10px] text-slate-500"
                            title={item.legacy_tt09_codes}
                          >
                            {item.legacy_tt09_codes || "-"}
                          </td>
                          <td className="px-2.5 py-1.5 font-semibold text-slate-800">{item.name}</td>
                          <td className="px-2.5 py-1.5 text-center font-mono text-slate-600">
                            {item.group_code || "-"}
                          </td>
                          <td className="px-2.5 py-1.5 text-center font-mono font-bold text-emerald-700">
                            {item.cip_code || "-"}
                          </td>
                          <td className="px-2.5 py-1.5 text-center">
                            <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[10px] font-extrabold text-indigo-700">
                              {item.holland_code || "-"}
                            </span>
                          </td>
                          <td className="px-2.5 py-1.5 font-mono text-[10px]">
                            <div className="flex gap-1">
                              {(["R", "I", "A", "S", "E", "C"] as const).map((dim) => (
                                <span
                                  key={dim}
                                  className={`rounded px-1 py-0.5 ${
                                    (rv[dim] ?? 0) >= 0.7
                                      ? "bg-sky-100 font-bold text-sky-800"
                                      : "bg-slate-100 text-slate-500"
                                  }`}
                                >
                                  {dim}:{Number(rv[dim] ?? 0).toFixed(2)}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-2.5 py-1.5 font-mono text-[10px] font-semibold text-slate-700">
                            {(item.blocks || []).join(", ")}
                          </td>
                          <td className="px-2.5 py-1.5 text-[10px] text-slate-500">
                            {cog.abstract_thinking || "med"}/{cog.analytical_reasoning || "med"}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-3 py-2 text-[11px] text-slate-600">
                <span>
                  {paginatedPreviewMajors.length} / {indexedPreviewMajors.length} ngành
                </span>
                {totalPreviewPages > 1 && (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={previewPage <= 1}
                      onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                      className="grid size-6 place-items-center rounded border border-slate-200 bg-white disabled:opacity-40"
                    >
                      <ChevronLeft size={13} />
                    </button>
                    <span className="px-1.5 font-bold">
                      {previewPage}/{totalPreviewPages}
                    </span>
                    <button
                      type="button"
                      disabled={previewPage >= totalPreviewPages}
                      onClick={() => setPreviewPage((p) => Math.min(totalPreviewPages, p + 1))}
                      className="grid size-6 place-items-center rounded border border-slate-200 bg-white disabled:opacity-40"
                    >
                      <ChevronRight size={13} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Minimal HITL Review */}
        <div className="glass-card overflow-hidden rounded-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/70 p-3.5">
            <div className="flex items-center gap-2">
              <Layers3 size={16} className="text-sky-600" />
              <h2 className="text-sm font-black text-slate-900">Kiểm duyệt HITL</h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-xl bg-white/60 p-0.5 ring-1 ring-slate-200">
                {(["ALL", "PENDING", "APPROVED", "REJECTED"] as (Status | "ALL")[]).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setStatusFilter(st)}
                    className={`rounded-lg px-2 py-1 text-[10px] font-extrabold transition ${
                      statusFilter === st ? "bg-sky-600 text-white" : "text-slate-500"
                    }`}
                  >
                    {st === "ALL" ? "Tất cả" : st}
                  </button>
                ))}
              </div>
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Tìm..."
                  className="h-8 w-36 rounded-xl border border-slate-200 bg-white/80 pl-8 pr-2 text-xs outline-none"
                />
              </div>
            </div>
          </div>

          <div className="grid min-h-[340px] lg:grid-cols-[310px_1fr]">
            <div className="max-h-[360px] divide-y divide-slate-100 overflow-y-auto border-b border-white/70 lg:border-b-0 lg:border-r">
              {filteredRecords.map((record) => (
                <button
                  key={record.id}
                  type="button"
                  onClick={() => setSelectedId(record.id)}
                  className={`flex w-full items-center gap-2.5 p-3 text-left transition ${
                    selected?.id === record.id ? "bg-sky-50/90" : "hover:bg-white/50"
                  }`}
                >
                  <FileText size={15} className="shrink-0 text-sky-600" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-bold text-slate-800">{record.title}</p>
                    <div className="mt-1 flex items-center gap-1.5">
                      <Badge
                        tone={
                          record.status === "APPROVED"
                            ? "emerald"
                            : record.status === "REJECTED"
                              ? "rose"
                              : "amber"
                        }
                      >
                        {record.status}
                      </Badge>
                      <span className="text-[10px] text-slate-400">{record.majorCode}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {selected && (
              <div className="flex min-w-0 flex-col justify-between">
                <div className="p-4">
                  <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2.5">
                    <div>
                      <h3 className="text-sm font-black text-slate-900">{selected.title}</h3>
                      <p className="text-[10px] text-slate-400">
                        {selected.majorCode} · {selected.source}
                      </p>
                    </div>
                    <div className="flex rounded-lg bg-white/70 p-0.5 ring-1 ring-slate-200">
                      <button
                        type="button"
                        onClick={() => setPreviewMode("markdown")}
                        className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                          previewMode === "markdown" ? "bg-sky-600 text-white" : "text-slate-500"
                        }`}
                      >
                        Text
                      </button>
                      <button
                        type="button"
                        onClick={() => setPreviewMode("json")}
                        className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                          previewMode === "json" ? "bg-sky-600 text-white" : "text-slate-500"
                        }`}
                      >
                        JSON
                      </button>
                    </div>
                  </div>

                  <div className="max-h-[220px] overflow-auto rounded-2xl border border-sky-100 bg-sky-50/40 p-3.5 text-xs leading-5 text-slate-700">
                    {previewMode === "markdown" ? (
                      <Markdown remarkPlugins={[remarkGfm]}>{selected.markdown}</Markdown>
                    ) : (
                      <pre className="font-mono text-[11px] text-sky-900">
                        {JSON.stringify(selected, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 border-t border-white/70 bg-white/40 p-3">
                  <Button
                    variant="secondary"
                    icon={RefreshCw}
                    onClick={() => updateStatus("REJECTED")}
                    className="!min-h-8 !px-3.5 !text-xs"
                  >
                    Từ chối
                  </Button>
                  <Button
                    icon={Check}
                    onClick={() => updateStatus("APPROVED")}
                    className="!min-h-8 !px-3.5 !text-xs"
                  >
                    Phê duyệt
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
