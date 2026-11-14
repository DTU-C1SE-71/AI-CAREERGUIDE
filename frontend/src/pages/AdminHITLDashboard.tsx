import { AnimatePresence, motion } from "framer-motion"
import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock3,
  Copy,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  HelpCircle,
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
import { MajorsCatalogPanel } from "../components/admin/MajorsCatalogPanel"
import { TrendAgentPanel } from "../components/admin/TrendAgentPanel"
import { LLMConnectionPanel } from "../components/admin/LLMConnectionPanel"
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
const SMOOTH_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

function parseExcelClientFallback(buffer: ArrayBuffer): {
  activeSheet: string
  majors: PreviewMajorItem[]
  sheets: ParsedSheetOption[]
} {
  const wb = XLSX.read(buffer, { type: "array" })
  const allSheets: ParsedSheetOption[] = []

  const headerMapLookup: Record<string, string> = {
    field_code: "field_code",
    field_name: "field_name",
    "lĩnh vực đào tạo": "field_name",
    "tên lĩnh vực": "field_name",
    category: "field_name",
    group_code: "group_code",
    group_name: "group_name",
    "nhóm ngành đào tạo": "group_name",
    "tên nhóm ngành": "group_name",
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
        category: rec.field_name || rec.group_name || "Khác",
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
  const [showHelpGuide, setShowHelpGuide] = useState(false)

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
  const [catalogRefreshKey, setCatalogRefreshKey] = useState(0)
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
        replace_catalog: "true",
        ...(activeSheetName ? { sheet_name: activeSheetName } : {}),
      }).toString()
      const res = await fetch(`/api/v1/taxonomy/import-excel?${qs}`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => null)
        throw new Error(
          errBody?.detail ||
            "Không thể lưu dữ liệu vào CSDL (cần kiểm tra Backend/PostgreSQL).",
        )
      }
      const data = await res.json()
      if (data.persisted_to_db === false) {
        throw new Error("Backend chưa ghi được dữ liệu vào CSDL PostgreSQL.")
      }
      const totalImported = data.total ?? previewMajors.length
      const deletedOld = data.deleted_old ?? 0

      const deletedNote =
        deletedOld > 0 ? `Đã xóa sạch ${deletedOld} ngành cũ, ` : ""
      const newRecord: StagingRecord = {
        id: Date.now(),
        title: `Import · ${previewFile.name}`,
        majorCode: `${totalImported} ngành`,
        source: `${previewFile.name} (${activeSheetName})`,
        type: "Excel Auto-Map",
        status: "APPROVED",
        updated: "Vừa đồng bộ",
        markdown: `${deletedNote}đã nạp mới **${totalImported} ngành** từ Sheet \`${activeSheetName}\`.`,
      }
      setRecords((prev) => [newRecord, ...prev])
      setSelectedId(newRecord.id)

      const liveHealth = await apiRequest<DbHealthPayload | null>("/health/db", null)
      if (liveHealth && liveHealth.majors_count !== undefined) {
        setDbHealth(liveHealth)
      } else {
        setDbHealth((prev) => ({ ...prev, majors_count: totalImported }))
      }

      // Danh mục ngành vừa thay đổi -> buộc bảng xem dữ liệu tải lại
      setCatalogRefreshKey((key) => key + 1)

      showToast(
        `${deletedNote}đã lưu mới ${totalImported} ngành vào CSDL!`,
      )
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
      <PageContainer size="wide">
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
                size={16}
                className={toast.error ? "text-rose-600" : "text-emerald-600"}
              />
              {toast.msg}
            </span>
            <button
              onClick={() => setToast(null)}
              className="rounded-lg p-1 opacity-70 hover:bg-black/5 hover:opacity-100 cursor-pointer"
            >
              <X size={14} />
            </button>
          </motion.div>
        )}

        {/* Minimal Header */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-black tracking-tight text-slate-900 sm:text-2xl">
              Quản trị Danh mục Ngành & Tuyển sinh
            </h1>
            <p className="mt-0.5 text-xs text-slate-500">
              Chuẩn hóa danh mục MOET TT74/TT09, phân loại RIASEC/CIP và điều phối dữ liệu đào tạo
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 rounded-xl border border-white/80 bg-white/75 px-3 py-1.5 shadow-sm">
              <Database size={15} className="text-sky-600" />
              <span className="text-xs text-slate-500 font-medium">CSDL:</span>
              <span className="text-xs font-bold text-slate-900 tabular-nums">
                {dbHealth?.majors_count !== undefined ? `${dbHealth.majors_count} ngành` : "--"}
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/80 bg-white/75 px-3 py-1.5 shadow-sm">
              <Clock3 size={15} className="text-amber-600" />
              <span className="text-xs text-slate-500 font-medium">Chờ duyệt HITL:</span>
              <span className="text-xs font-bold text-amber-600 tabular-nums">{pendingCount}</span>
            </div>
          </div>
        </div>

        {/* 2 Compact Guidance Cards: Excel Template | AI Prompt */}
        <div className="mb-3 grid gap-3 md:grid-cols-2">
          <div className="glass-card flex items-center justify-between gap-3 rounded-2xl p-4">
            <div className="flex items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-500 text-white shadow-xs">
                <FileSpreadsheet size={19} />
              </span>
              <div>
                <h2 className="text-sm font-bold text-slate-900">File Excel Mẫu (.xlsx)</h2>
                <p className="text-xs text-slate-500">
                  19 cột chuẩn TT74/TT09 · Bảng tra cứu CIP & RIASEC mẫu
                </p>
              </div>
            </div>
            <Button
              onClick={downloadExcelTemplate}
              icon={Download}
              className="!min-h-9 !px-3.5 !py-1.5 !text-xs !bg-emerald-600 hover:!bg-emerald-700 shrink-0"
            >
              Tải mẫu chuẩn
            </Button>
          </div>

          <div className="glass-card flex items-center justify-between gap-3 rounded-2xl p-4">
            <div className="flex items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-sky-500 text-white shadow-xs">
                <Sparkles size={19} />
              </span>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Prompt AI Trích Xuất</h2>
                <p className="text-xs text-slate-500">
                  Chuyển PDF Thông tư Bộ GD&ĐT sang bảng dữ liệu chuẩn hóa
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant={copiedPrompt ? "primary" : "secondary"}
                onClick={copyExternalAiPrompt}
                icon={copiedPrompt ? Check : Copy}
                className="!min-h-9 !px-3.5 !py-1.5 !text-xs shrink-0"
              >
                {copiedPrompt ? "Đã Copy" : "Copy Prompt"}
              </Button>
            </div>
          </div>
        </div>

        {/* Collapsible Format Guidance & Instructions */}
        <div className="mb-4">
          <button
            type="button"
            onClick={() => setShowHelpGuide((v) => !v)}
            aria-expanded={showHelpGuide}
            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-sky-700 cursor-pointer transition px-1"
          >
            <HelpCircle size={14} className="text-sky-600" />
            <span>Hướng dẫn định dạng 19 cột & quy trình Prompt AI</span>
            {showHelpGuide ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          <AnimatePresence initial={false}>
            {showHelpGuide && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                className="overflow-hidden"
              >
                <div className="mt-2.5 rounded-2xl border border-sky-200/80 bg-white/95 p-4 text-xs text-slate-700 shadow-xs space-y-3">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
                      <p className="font-bold text-slate-900 mb-1">1. Định danh ngành (7 cột)</p>
                      <p className="font-mono text-slate-600 leading-relaxed">
                        field_code, field_name, group_code, group_name, major_code, major_name, legacy_tt09_codes
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
                      <p className="font-bold text-slate-900 mb-1">2. CIP & RIASEC (8 cột)</p>
                      <p className="font-mono text-slate-600 leading-relaxed">
                        cip_code, holland_code, riasec_r, riasec_i, riasec_a, riasec_s, riasec_e, riasec_c (0.0 → 1.0)
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
                      <p className="font-bold text-slate-900 mb-1">3. Tuyển sinh & Nghề (4 cột)</p>
                      <p className="font-mono text-slate-600 leading-relaxed">
                        degree_levels, circular_note, subject_blocks (A00, A01...), career_paths
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-sky-100 bg-sky-50/60 p-3">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-bold text-sky-900">Prompt AI chuẩn bị sẵn cho ChatGPT / Claude / Gemini:</span>
                      <button
                        type="button"
                        onClick={copyExternalAiPrompt}
                        className="inline-flex items-center gap-1 text-xs font-bold text-sky-700 hover:text-sky-900 cursor-pointer"
                      >
                        {copiedPrompt ? <Check size={13} /> : <Copy size={13} />}
                        {copiedPrompt ? "Đã chép" : "Chép prompt"}
                      </button>
                    </div>
                    <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed">
                      {EXTERNAL_AI_PROMPT}
                    </pre>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Trạng thái kết nối AI & API Key */}
        <LLMConnectionPanel onNotify={showToast} />

        {/* AI Trend Hunter Agent Panel (Chạy thủ công khi Admin bấm nút) */}
        <TrendAgentPanel onNotify={showToast} />

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
              size={24}
              className={`pointer-events-none mb-1.5 transition ${
                isDragging ? "text-sky-600 animate-bounce" : "text-sky-500"
              }`}
            />
            <p className="pointer-events-none text-sm font-bold text-slate-800">
              {parsingFile
                ? "Đang phân tích file Excel và các sheet..."
                : isDragging
                  ? "Thả file vào đây để phân tích"
                  : "Kéo thả file Excel (.xlsx, .xls, .csv) vào đây hoặc bấm để chọn"}
            </p>
            <p className="pointer-events-none mt-0.5 text-xs text-slate-500">
              Hệ thống tự động đọc bảng dữ liệu, chuẩn hóa mã 7 số TT74 và liên kết mã TT09
            </p>
          </div>

          {/* Preview Table */}
          {previewMajors.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-2xl border border-sky-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-sky-50/80 p-3 sm:p-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="emerald">
                    <span className="tabular-nums">Tổng: {previewMajors.length} ngành</span>
                  </Badge>
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
                            className={`relative rounded-lg px-2.5 py-1 text-xs font-bold transition cursor-pointer ${
                              isActive
                                ? "text-white shadow-xs"
                                : "text-slate-600 hover:bg-sky-50 hover:text-sky-700"
                            }`}
                          >
                            {isActive && (
                              <motion.span
                                layoutId="preview-sheet-tab-pill"
                                transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                                className="absolute inset-0 rounded-lg bg-sky-600"
                              />
                            )}
                            <span className="relative z-10 tabular-nums">
                              {s.sheet_name} ({s.count} ngành)
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  ) : (
                    activeSheetName && (
                      <span className="rounded-md bg-white px-2 py-0.5 text-xs font-semibold text-slate-600 border border-slate-200 tabular-nums">
                        Sheet: {activeSheetName} ({previewMajors.length} ngành)
                      </span>
                    )
                  )}
                  {parseTimeMs !== null && (
                    <span className="text-xs font-medium text-slate-400 tabular-nums">
                      ({parseTimeMs}ms)
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
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
                    className="!min-h-8 !px-4 !py-1 !text-xs !bg-emerald-600 hover:!bg-emerald-700"
                  >
                    Import {previewMajors.length} ngành vào CSDL
                  </Button>
                </div>
              </div>

              <div className="max-h-[440px] overflow-x-auto overflow-y-auto">
                <table className="w-full min-w-[960px] border-collapse text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-600 shadow-sm border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2.5 text-center w-12">STT</th>
                      <th className="px-3 py-2.5 w-28">Mã TT74</th>
                      <th className="px-3 py-2.5 w-28">Mã TT09</th>
                      <th className="px-3 py-2.5 min-w-[200px]">Tên ngành</th>
                      <th className="px-3 py-2.5 text-center w-24">Nhóm</th>
                      <th className="px-3 py-2.5 text-center w-24">CIP</th>
                      <th className="px-3 py-2.5 text-center w-24">Holland</th>
                      <th className="px-3 py-2.5 min-w-[260px]">
                        Vector RIASEC (R·I·A·S·E·C)
                      </th>
                      <th className="px-3 py-2.5 min-w-[130px]">Khối thi</th>
                      <th className="px-3 py-2.5 w-28">Nhận thức</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {paginatedPreviewMajors.map(({ stt, item }) => {
                      const rv = item.riasec || {}
                      const cog = item.cognitive || {}
                      return (
                        <tr key={`${stt}-${item.major_code}`} className="hover:bg-sky-50/40">
                          <td className="px-3 py-2 text-center text-xs font-bold text-slate-400 tabular-nums">
                            {stt}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs font-bold text-sky-700">
                            {item.major_code}
                          </td>
                          <td
                            className="max-w-[120px] truncate px-3 py-2 font-mono text-xs text-slate-500"
                            title={item.legacy_tt09_codes}
                          >
                            {item.legacy_tt09_codes || "—"}
                          </td>
                          <td className="px-3 py-2 font-semibold text-slate-900">
                            {item.name}
                          </td>
                          <td className="px-3 py-2 text-center font-mono text-xs text-slate-600">
                            {item.group_code || "—"}
                          </td>
                          <td className="px-3 py-2 text-center font-mono text-xs font-bold text-emerald-700">
                            {item.cip_code || "—"}
                          </td>
                          <td className="px-3 py-2 text-center">
                            <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-xs font-bold text-indigo-700">
                              {item.holland_code || "—"}
                            </span>
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">
                            <div className="flex gap-1 tabular-nums">
                              {(["R", "I", "A", "S", "E", "C"] as const).map((dim) => (
                                <span
                                  key={dim}
                                  className={`rounded px-1.5 py-0.5 ${
                                    (rv[dim] ?? 0) >= 0.7
                                      ? "bg-sky-100 font-bold text-sky-800"
                                      : "bg-slate-100 text-slate-600"
                                  }`}
                                >
                                  {dim}:{Number(rv[dim] ?? 0).toFixed(2)}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-3 py-2 font-mono text-xs font-semibold text-slate-700">
                            {(item.blocks || []).join(", ") || "—"}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-600 capitalize">
                            {cog.abstract_thinking || "med"}/{cog.analytical_reasoning || "med"}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-4 py-2.5 text-xs text-slate-600 tabular-nums">
                <span>
                  Hiển thị {paginatedPreviewMajors.length} / {indexedPreviewMajors.length} ngành
                </span>
                {totalPreviewPages > 1 && (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={previewPage <= 1}
                      onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                      className="grid size-7 place-items-center rounded-lg border border-slate-200 bg-white transition hover:border-sky-300 disabled:opacity-40 cursor-pointer"
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <span className="px-2 font-bold text-slate-800">
                      {previewPage} / {totalPreviewPages}
                    </span>
                    <button
                      type="button"
                      disabled={previewPage >= totalPreviewPages}
                      onClick={() => setPreviewPage((p) => Math.min(totalPreviewPages, p + 1))}
                      className="grid size-7 place-items-center rounded-lg border border-slate-200 bg-white transition hover:border-sky-300 disabled:opacity-40 cursor-pointer"
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Danh mục ngành đào tạo đang hoạt động trong CSDL */}
        <div className="mb-5">
          <MajorsCatalogPanel refreshKey={catalogRefreshKey} onNotify={showToast} />
        </div>

        {/* Human-in-the-loop (HITL) Review Panel */}
        <div className="glass-card overflow-hidden rounded-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/70 p-4">
            <div className="flex items-center gap-2.5">
              <span className="grid size-9 place-items-center rounded-xl bg-sky-600 text-white shadow-xs">
                <Layers3 size={18} />
              </span>
              <div>
                <h2 className="text-base font-bold text-slate-900">Kiểm duyệt HITL (Staging Records)</h2>
                <p className="text-xs text-slate-500">Phê duyệt lộ trình học tập và bản ghi trích xuất RAG</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex rounded-xl bg-white/70 p-1 ring-1 ring-slate-200 shadow-2xs">
                {(["ALL", "PENDING", "APPROVED", "REJECTED"] as (Status | "ALL")[]).map((st) => {
                  const isActive = statusFilter === st
                  return (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setStatusFilter(st)}
                      className={`relative rounded-lg px-2.5 py-1 text-xs font-bold transition cursor-pointer ${
                        isActive ? "text-white shadow-xs" : "text-slate-600 hover:text-sky-700"
                      }`}
                    >
                      {isActive && (
                        <motion.span
                          layoutId="hitl-status-filter-pill"
                          transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                          className="absolute inset-0 rounded-lg bg-sky-600"
                        />
                      )}
                      <span className="relative z-10">
                        {st === "ALL" ? "Tất cả" : st}
                      </span>
                    </button>
                  )
                })}
              </div>

              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Tìm bản ghi..."
                  className="h-8 w-40 rounded-xl border border-slate-200 bg-white/90 pl-8 pr-2.5 text-xs outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
            </div>
          </div>

          <div className="grid min-h-[360px] lg:grid-cols-[330px_1fr]">
            {/* Records List (Left Pane) */}
            <div className="max-h-[380px] divide-y divide-slate-100 overflow-y-auto border-b border-white/70 lg:border-b-0 lg:border-r">
              {filteredRecords.length === 0 ? (
                <div className="p-8 text-center text-xs font-medium text-slate-400">
                  Không tìm thấy bản ghi nào phù hợp.
                </div>
              ) : (
                filteredRecords.map((record) => (
                  <button
                    key={record.id}
                    type="button"
                    onClick={() => setSelectedId(record.id)}
                    className={`flex w-full items-center gap-3 p-3.5 text-left transition cursor-pointer ${
                      selected?.id === record.id
                        ? "bg-sky-50/90 border-l-3 border-sky-600"
                        : "hover:bg-white/60"
                    }`}
                  >
                    <FileText
                      size={17}
                      className={`shrink-0 ${
                        selected?.id === record.id ? "text-sky-600" : "text-slate-400"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-slate-800">{record.title}</p>
                      <div className="mt-1 flex items-center gap-2">
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
                        <span className="font-mono text-xs text-slate-500">{record.majorCode}</span>
                        <span className="text-xs text-slate-400 ml-auto">{record.updated}</span>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Selected Record Detail (Right Pane) */}
            {selected ? (
              <div className="flex min-w-0 flex-col justify-between">
                <div className="p-4 sm:p-5">
                  <div className="mb-3.5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{selected.title}</h3>
                      <p className="text-xs text-slate-500 font-medium">
                        Mã: <span className="font-mono font-semibold text-sky-700">{selected.majorCode}</span> · Nguồn: {selected.source} · Loại: {selected.type}
                      </p>
                    </div>

                    <div className="flex rounded-lg bg-slate-100/90 p-0.5 ring-1 ring-slate-200">
                      <button
                        type="button"
                        onClick={() => setPreviewMode("markdown")}
                        className={`relative rounded-md px-3 py-1 text-xs font-bold transition cursor-pointer ${
                          previewMode === "markdown" ? "text-white" : "text-slate-600 hover:text-sky-700"
                        }`}
                      >
                        {previewMode === "markdown" && (
                          <motion.span
                            layoutId="hitl-preview-mode-pill"
                            transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                            className="absolute inset-0 rounded-md bg-sky-600 shadow-2xs"
                          />
                        )}
                        <span className="relative z-10">Văn bản</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setPreviewMode("json")}
                        className={`relative rounded-md px-3 py-1 text-xs font-bold transition cursor-pointer ${
                          previewMode === "json" ? "text-white" : "text-slate-600 hover:text-sky-700"
                        }`}
                      >
                        {previewMode === "json" && (
                          <motion.span
                            layoutId="hitl-preview-mode-pill"
                            transition={{ duration: 0.2, ease: SMOOTH_EASE }}
                            className="absolute inset-0 rounded-md bg-sky-600 shadow-2xs"
                          />
                        )}
                        <span className="relative z-10">JSON</span>
                      </button>
                    </div>
                  </div>

                  <div className="max-h-[250px] overflow-auto rounded-2xl border border-sky-100 bg-sky-50/40 p-4 text-sm leading-relaxed text-slate-700">
                    {previewMode === "markdown" ? (
                      <div className="prose prose-sm max-w-none text-slate-700">
                        <Markdown remarkPlugins={[remarkGfm]}>{selected.markdown}</Markdown>
                      </div>
                    ) : (
                      <pre className="font-mono text-xs leading-relaxed text-sky-950 bg-slate-900/5 p-3 rounded-xl overflow-x-auto">
                        {JSON.stringify(selected, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2.5 border-t border-white/70 bg-white/40 p-3 sm:px-5">
                  <Button
                    variant="secondary"
                    icon={RefreshCw}
                    onClick={() => updateStatus("REJECTED")}
                    className="!min-h-9 !px-4 !text-xs !text-rose-700 hover:!bg-rose-50"
                  >
                    Từ chối
                  </Button>
                  <Button
                    icon={Check}
                    onClick={() => updateStatus("APPROVED")}
                    className="!min-h-9 !px-4 !text-xs !bg-emerald-600 hover:!bg-emerald-700"
                  >
                    Phê duyệt
                  </Button>
                </div>
              </div>
            ) : (
              <div className="grid place-items-center p-12 text-sm text-slate-400">
                Chọn một bản ghi bên trái để xem nội dung kiểm duyệt.
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
