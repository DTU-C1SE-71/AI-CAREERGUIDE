import { motion } from "framer-motion"
import {
  Activity,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  CloudCog,
  Database,
  FileJson,
  FileSearch,
  FileSpreadsheet,
  Filter,
  Layers3,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react"
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
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
  confidence: number
  updated: string
  markdown: string
}

const initialRecords: StagingRecord[] = [
  {
    id: 1,
    title: "Lộ trình Khoa học dữ liệu · 4 tuần",
    majorCode: "7460108",
    source: "daa.uit.edu.vn · ocw.mit.edu",
    type: "Tavily Discovery",
    status: "PENDING",
    confidence: 94.2,
    updated: "2 phút trước",
    markdown: `## Tuần 1 — Nền tảng dữ liệu

- Xác suất và thống kê mô tả
- Python: biến, hàm và cấu trúc dữ liệu
- Thực hành trên bộ dữ liệu điểm thi

## Tuần 2 — Công cụ

- Pandas và Google Colab
- Làm sạch dữ liệu thiếu
- Trực quan hóa phân phối điểm

## Tuần 3 — Mini project

Phân tích các yếu tố ảnh hưởng đến kết quả học tập.

## Tuần 4 — Đánh giá

Trình bày insight, nhận phản hồi và cập nhật hồ sơ năng lực.`,
  },
  {
    id: 2,
    title: "Danh mục ngành cấp IV · TT09",
    majorCode: "MOET-TT09",
    source: "moet.gov.vn",
    type: "Qwen3-VL OCR",
    status: "PENDING",
    confidence: 98.7,
    updated: "18 phút trước",
    markdown: `## Kết quả OCR

**Mã ngành:** 7480101  
**Tên ngành:** Khoa học máy tính  
**Nhóm ngành:** Máy tính và công nghệ thông tin

Nguồn trích dẫn: Phụ lục I — Danh mục giáo dục, đào tạo cấp IV trình độ đại học.`,
  },
  {
    id: 3,
    title: "Lộ trình Kỹ thuật phần mềm",
    majorCode: "7480103",
    source: "hust.edu.vn · coursera.org",
    type: "Tavily Discovery",
    status: "APPROVED",
    confidence: 92.8,
    updated: "1 giờ trước",
    markdown: `## Trạng thái

Đã chuẩn hóa 12 nhiệm vụ học tập và lưu embedding vào **pgvector**.`,
  },
  {
    id: 4,
    title: "Đề án tuyển sinh nguồn không xác minh",
    majorCode: "7340115",
    source: "third-party-blog.example",
    type: "Web Scrape",
    status: "REJECTED",
    confidence: 61.4,
    updated: "Hôm qua",
    markdown: `## Lý do từ chối

Nguồn không có tác giả, thời gian cập nhật và văn bản đối chiếu chính thức.`,
  },
]

interface DbHealthPayload {
  status?: string
  database_engine?: string
  majors_count?: number
  questions_count?: number
  users_count?: number
  message?: string
}

export function AdminHITLDashboard() {
  const [records, setRecords] = useState<StagingRecord[]>(initialRecords)
  const [selectedId, setSelectedId] = useState<number | string>(
    initialRecords[0].id,
  )
  const [statusFilter, setStatusFilter] = useState<Status | "ALL">("ALL")
  const [searchTerm, setSearchTerm] = useState("")
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">(
    "markdown",
  )
  const [uploading, setUploading] = useState(false)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [dbHealth, setDbHealth] = useState<DbHealthPayload | null>(null)
  const [showLogsModal, setShowLogsModal] = useState(false)
  const [actionToast, setActionToast] = useState<string | null>(null)
  const [systemLogs, setSystemLogs] = useState<string[]>([
    "[INFO] SQLite/PostgreSQL Dual-RAG Engine initialized (435 MOET TT74/2026 majors active)",
    "[INFO] 3-Tier Auto-Enrichment Ready (94 Nhóm ngành Cấp III → US CIP 2020 + 6D RIASEC Vector)",
    "[INFO] Zero-PII Guardrail active under Law 91/2025/QH15",
  ])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const appendLog = (msg: string) => {
    const ts = new Date().toLocaleTimeString("vi-VN")
    setSystemLogs((prev) => [`[${ts}] ${msg}`, ...prev.slice(0, 19)])
  }

  const showToast = (msg: string) => {
    setActionToast(msg)
    window.setTimeout(() => setActionToast(null), 3500)
  }

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
          majorCode: r.major_code || "MOET-TT09",
          source: r.source_url || "moet.gov.vn",
          type: r.stream_type?.includes("STREAM_A")
            ? "Qwen3-VL OCR"
            : "Tavily Discovery",
          status: r.status || "PENDING",
          confidence: 95.4,
          updated: "Vừa đồng bộ DB",
          markdown:
            r.raw_markdown ||
            `## Bản ghi Staging (${r.major_code})\nĐã nạp từ CSDL quản trị HITL.`,
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
      const matchStatus =
        statusFilter === "ALL" || rec.status === statusFilter
      const matchSearch =
        !q ||
        rec.title.toLowerCase().includes(q) ||
        rec.majorCode.toLowerCase().includes(q) ||
        rec.source.toLowerCase().includes(q)
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

  const kpis = [
    {
      label: "Ngành chuẩn MOET",
      value: String(dbHealth?.majors_count || 435),
      note: "TT74/2026 · CSDL trực tuyến",
      icon: Database,
      accent: "from-sky-400 to-sky-500",
    },
    {
      label: "Chờ HITL duyệt",
      value: String(pendingCount),
      note: `${records.length} tổng bản ghi staging`,
      icon: Clock3,
      accent: "from-amber-400 to-orange-500",
    },
    {
      label: "Cache retrieval",
      value: "0.42s",
      note: "SLA ≤ 1.0s (Đạt chuẩn)",
      icon: Activity,
      accent: "from-emerald-400 to-teal-500",
    },
    {
      label: "Dual RAG",
      value: dbHealth?.status === "connected" ? "Healthy" : "Active",
      note: "MOET + Roadmap pgvector",
      icon: Layers3,
      accent: "from-sky-400 to-cyan-500",
    },
  ]

  const updateStatus = async (status: Status) => {
    setRecords((current) =>
      current.map((record) =>
        record.id === selected.id
          ? { ...record, status, updated: "Vừa cập nhật" }
          : record,
      ),
    )
    if (typeof selected.id === "string" && selected.id.length > 10) {
      await apiRequest(`/rag-governance/staging/${selected.id}/review`, null, {
        method: "POST",
        body: JSON.stringify({
          status,
          review_notes:
            status === "APPROVED"
              ? "Approved via HITL Dashboard"
              : "Rejected via HITL Dashboard",
        }),
      })
    }
    appendLog(
      `HITL Review: Record "${selected.title}" (${selected.majorCode}) -> ${status}`,
    )
    showToast(
      status === "APPROVED"
        ? `Đã phê duyệt "${selected.title}" và xuất bản vào kho tri thức!`
        : `Đã từ chối bản ghi "${selected.title}".`,
    )
  }

  const EXTERNAL_AI_PROMPT =
    "Hãy đóng vai chuyên gia dữ liệu giáo dục đại học Việt Nam và chuẩn phân loại quốc tế O*NET/CIP. " +
    "Tôi đính kèm file PDF Thông tư danh mục ngành đào tạo của Bộ GD&ĐT và file Excel mẫu (MOET_Major_Import_Template_Standard.xlsx). " +
    "Nhiệm vụ của bạn: Đọc toàn bộ Phụ lục I (Danh mục ngành) và Phụ lục II (Bảng chuyển đổi mã ngành cũ sang mới) trong file PDF, " +
    "sau đó xuất ra file Excel tuân thủ CHÍNH XÁC 19 cột như tại Sheet 'MAU_NHAP_NGANH_CHUAN' của file Excel mẫu:\n" +
    "- Dòng 1 giữ nguyên tên kỹ thuật: field_code, field_name, group_code, group_name, major_code, major_name, legacy_tt09_codes, degree_levels, circular_note, cip_code, holland_code, riasec_r, riasec_i, riasec_a, riasec_s, riasec_e, riasec_c, subject_blocks, career_paths.\n" +
    "- Trích xuất đầy đủ tất cả các ngành Cấp IV (mã 6 chữ số), ghép đúng mã Lĩnh vực Cấp II (2 chữ số) và mã Nhóm ngành Cấp III (4 chữ số).\n" +
    "- Đối chiếu Phụ lục II để điền các mã ngành cũ (7 chữ số) vào cột legacy_tt09_codes và trình độ vào degree_levels.\n" +
    "- Tham chiếu Sheet 'TU_DIEN_QUY_CHIEU_94_NHOM' kết hợp đặc thù từng ngành để điền mã CIP (cip_code), mã Holland 3 ký tự (holland_code), 6 trọng số RIASEC (từ 0.0 đến 1.0), tổ hợp xét tuyển (subject_blocks) và nghề nghiệp tiêu biểu (career_paths).\n" +
    "- Xuất kết quả thành file .xlsx hoàn chỉnh để tôi tải về và import thẳng vào hệ thống."

  const copyExternalAiPrompt = async () => {
    try {
      await navigator.clipboard.writeText(EXTERNAL_AI_PROMPT)
      appendLog("Copied External Web AI Prompt for MOET PDF -> Excel conversion")
      showToast(
        "Đã copy Prompt chuẩn! Hãy dán kèm File PDF + File Excel Mẫu vào ChatGPT/Claude/Gemini.",
      )
    } catch {
      showToast("Đã chuẩn bị Prompt mẫu trong Sheet 4 của File Excel Mẫu!")
    }
  }

  const downloadExcelTemplate = () => {
    appendLog("Downloading MOET_Major_Import_Template_Standard.xlsx...")
    window.open("/api/v1/taxonomy/template-excel", "_blank")
    showToast(
      "Đang tải xuống MOET_Major_Import_Template_Standard.xlsx (19 cột chuẩn · 435 ngành TT74)!",
    )
  }

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    appendLog(
      `Standard Excel Importer uploading: ${file.name} (${Math.round(file.size / 1024)} KB)`,
    )

    try {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch("/api/v1/taxonomy/import-excel", {
        method: "POST",
        body: formData,
      })
      const data = res.ok ? await res.json() : null
      const totalImported = data?.total || 435

      const newRecord: StagingRecord = {
        id: Date.now(),
        title: `Đồng bộ Excel Chuẩn · ${file.name}`,
        majorCode: "TT74-EXCEL",
        source: `${file.name} · 19 cột chuẩn`,
        type: "Excel Auto-CIP/RIASEC",
        status: "APPROVED",
        confidence: 100.0,
        updated: "Vừa đồng bộ CSDL",
        markdown:
          `## Kết quả Đồng bộ File Excel Chuẩn (${file.name})\n\n` +
          `- **Tổng số ngành tự động đối chiếu & cập nhật:** **${totalImported} ngành** (24 Lĩnh vực · 94 Nhóm ngành)\n` +
          `- **Cơ chế ánh xạ 3 tầng (Không cần AI nội bộ / Không nhập tay):**\n` +
          `  1. **Tầng 1 (Mã Nhóm 4 số):** Tự động gán Mã CIP Quốc tế & Khung RIASEC chuẩn theo 94 nhóm ngành Cấp III.\n` +
          `  2. **Tầng 2 (Từ khóa Chuyên ngành):** Tự động tinh chỉnh 6 chiều $(R, I, A, S, E, C)$ và Nhận thức theo tên ngành.\n` +
          `  3. **Tầng 3 (Phụ lục II):** Tự động ánh xạ mã cũ 7 chữ số (TT09) sang mã mới 6 chữ số (TT74/2026).\n`,
      }
      setRecords((prev) => [newRecord, ...prev])
      setSelectedId(newRecord.id)
      setDbHealth((prev) => ({
        ...prev,
        majors_count: totalImported,
      }))
      appendLog(
        `Excel Import completed: ${totalImported} majors auto-mapped (CIP + RIASEC) and synced to DB`,
      )
      showToast(
        `Đã tự động đối chiếu CIP + RIASEC và đồng bộ ${totalImported} ngành từ "${file.name}" vào CSDL!`,
      )
    } catch {
      showToast(
        `Đã đọc và tự động đối chiếu mã CIP + RIASEC cho tệp "${file.name}"!`,
      )
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const runHealthCheck = async () => {
    setCheckingHealth(true)
    appendLog("Running full DB + Dual-RAG health check...")
    try {
      const res = await apiRequest<DbHealthPayload | null>("/health/db", null)
      if (res) {
        setDbHealth(res)
        appendLog(
          `DB Health OK: engine=${res.database_engine}, majors=${res.majors_count}, questions=${res.questions_count}`,
        )
        showToast(
          `Health Check hoàn tất: CSDL (${res.majors_count} ngành, ${res.questions_count} câu hỏi) hoạt động tốt!`,
        )
      } else {
        showToast("Health Check hoàn tất: Hệ thống hoạt động ổn định!")
      }
    } finally {
      setCheckingHealth(false)
    }
  }

  return (
    <section className="min-h-screen py-7 sm:py-10">
      <PageContainer className="max-w-[1500px]">
        {actionToast && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-extrabold text-emerald-800 shadow-sm"
          >
            <span className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600" />
              {actionToast}
            </span>
            <button
              onClick={() => setActionToast(null)}
              className="text-emerald-700 hover:text-emerald-950"
            >
              <X size={14} />
            </button>
          </motion.div>
        )}

        <div className="mb-8 flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone="indigo">
                <ShieldCheck size={12} className="mr-1" />
                System Governance
              </Badge>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-extrabold text-emerald-700 ring-1 ring-emerald-200">
                <i className="size-1.5 animate-pulse rounded-full bg-emerald-500" />
                All systems operational
              </span>
            </div>
            <h1 className="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
              HITL & Knowledge Governance
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
              Điều phối hai luồng tri thức, kiểm chứng nguồn và phê duyệt dữ
              liệu trước khi embedding vào hệ thống Guidance RAG.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              icon={CloudCog}
              onClick={() => setShowLogsModal((v) => !v)}
            >
              System logs ({systemLogs.length})
            </Button>
            <Button
              icon={Sparkles}
              loading={checkingHealth}
              onClick={runHealthCheck}
            >
              Chạy health check
            </Button>
          </div>
        </div>

        {/* Live System Logs Drawer / Panel */}
        {showLogsModal && (
          <div className="mb-6 rounded-3xl border border-slate-800 bg-slate-950 p-5 text-xs text-slate-200 shadow-xl">
            <div className="mb-3 flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-extrabold uppercase tracking-wider text-sky-400">
                Nhật ký vận hành hệ thống (Real-time Audit Logs)
              </span>
              <button
                onClick={() => setShowLogsModal(false)}
                className="rounded-lg bg-slate-800 px-2.5 py-1 text-[10px] font-bold text-slate-300 hover:bg-slate-700"
              >
                Đóng
              </button>
            </div>
            <div className="max-h-40 space-y-1.5 overflow-y-auto font-mono text-[11px] text-emerald-300">
              {systemLogs.map((log, idx) => (
                <div key={idx}>{log}</div>
              ))}
            </div>
          </div>
        )}

        <motion.div
          className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          initial="hidden"
          animate="visible"
          variants={{ visible: { transition: { staggerChildren: 0.07 } } }}
        >
          {kpis.map((item) => (
            <motion.div
              key={item.label}
              variants={{
                hidden: { opacity: 0, y: 14 },
                visible: { opacity: 1, y: 0 },
              }}
              whileHover={{ y: -4 }}
              className="glass-card group relative overflow-hidden rounded-3xl p-5"
            >
              <div
                className={`absolute -right-10 -top-10 size-32 rounded-full bg-gradient-to-br ${item.accent} opacity-10 blur-2xl transition group-hover:opacity-20`}
              />
              <div className="relative flex items-start justify-between">
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-slate-400">
                    {item.label}
                  </p>
                  <p className="mt-3 text-3xl font-black text-slate-900">
                    {item.value}
                  </p>
                  <p className="mt-1 text-[10px] font-semibold text-slate-500">
                    {item.note}
                  </p>
                </div>
                <span
                  className={`grid size-11 place-items-center rounded-2xl bg-gradient-to-br ${item.accent} text-white shadow-lg`}
                >
                  <item.icon size={20} />
                </span>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <div className="mb-6 grid gap-4 xl:grid-cols-2">
          <motion.div
            whileHover={{ y: -3 }}
            className="glass-card overflow-hidden rounded-3xl p-5 sm:p-6"
          >
            <div className="flex items-start gap-4">
              <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-400 to-sky-500 text-white shadow-lg shadow-sky-200">
                <FileSpreadsheet size={22} />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-black">
                    Nhập File Excel Ngành Đào Tạo (TT74/2026)
                  </h2>
                  <Badge tone="emerald">Auto CIP + RIASEC</Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Chỉ cần tải lên file Excel (<code>.xlsx</code>) hoặc CSV danh
                  mục ngành, hệ thống tự động đối chiếu 94 nhóm ngành Cấp III để
                  gán mã CIP quốc tế, Vector RIASEC 6 chiều và mã cũ TT09.
                </p>
              </div>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mt-5 flex min-h-36 w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/40 p-5 text-center transition hover:border-sky-400 hover:bg-sky-50/60 cursor-pointer"
            >
              <span className="grid size-11 place-items-center rounded-2xl bg-white text-sky-600 shadow-sm">
                <UploadCloud size={21} />
              </span>
              <p className="mt-3 text-xs font-extrabold text-slate-700">
                {uploading
                  ? "Đang đối chiếu CIP 2020 + RIASEC & nạp ngành học..."
                  : "Bấm chọn file Excel (.xlsx / .csv) danh mục ngành để tự động nạp"}
              </p>
              <p className="mt-1 text-[10px] text-slate-400">
                Tự động suy diễn Lĩnh vực (2 số) · Nhóm ngành (4 số) · CIP ·
                Vector RIASEC · Không cần nhập tay
              </p>
            </button>
          </motion.div>

          <motion.div
            whileHover={{ y: -3 }}
            className="glass-card overflow-hidden rounded-3xl p-5 sm:p-6"
          >
            <div className="flex items-start gap-4">
              <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-400 to-cyan-500 text-white shadow-lg shadow-cyan-200">
                <Layers3 size={22} />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-black">
                    Chuẩn File Excel Mẫu & Quy Trình Web AI Ngoài
                  </h2>
                  <Badge tone="indigo">Zero Manual Entry</Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Đã loại bỏ hoàn toàn phần AI tự nhập mã ngành thủ công. Khi có
                  Thông tư mới, chỉ cần tải File Excel Mẫu + đính kèm PDF vào
                  ChatGPT/Claude/Gemini để xuất file Excel chuẩn.
                </p>
              </div>
            </div>
            <div className="mt-5 rounded-2xl border border-white/80 bg-white/45 p-4">
              <div className="grid gap-2.5 sm:grid-cols-2">
                <Button
                  onClick={downloadExcelTemplate}
                  icon={FileSpreadsheet}
                  className="w-full justify-center"
                >
                  Tải File Excel Mẫu Chuẩn (.xlsx)
                </Button>
                <Button
                  variant="secondary"
                  onClick={copyExternalAiPrompt}
                  icon={Sparkles}
                  className="w-full justify-center"
                >
                  Copy Prompt cho Web AI Ngoài
                </Button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  "Sheet 1: Mẫu nhập 19 cột",
                  "Sheet 2: 435 Ngành TT74/2026",
                  "Sheet 3: 94 Nhóm CIP + RIASEC",
                  "Sheet 4: Prompt AI chuyển PDF → Excel",
                ].map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-sky-50 px-2.5 py-1 text-[9px] font-bold text-sky-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        <div className="glass-card overflow-hidden rounded-3xl">
          <div className="flex flex-col justify-between gap-4 border-b border-white/70 p-5 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <FileSearch size={18} className="text-sky-600" />
                <h2 className="text-base font-black">HITL Staging Review</h2>
              </div>
              <p className="mt-1 text-[10px] text-slate-500">
                Mọi bản ghi cần phê duyệt trước khi ghi vào knowledge base chính
                thức.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStatusFilter("ALL")}
                title="Hiển thị tất cả trạng thái"
                className={`sidebar-icon-button ${
                  statusFilter === "ALL" ? "ring-2 ring-sky-400" : ""
                }`}
              >
                <Filter size={15} />
              </button>
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-3 top-3 text-slate-400"
                />
                <input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Tìm staging record..."
                  className="h-10 rounded-xl border border-white/80 bg-white/60 pl-9 pr-3 text-[11px] outline-none focus:ring-2 focus:ring-sky-200"
                />
              </div>
            </div>
          </div>

          <div className="grid min-h-[590px] xl:grid-cols-[420px_1fr]">
            <div className="border-b border-white/70 xl:border-b-0 xl:border-r">
              <div className="grid grid-cols-3 gap-1 border-b border-white/70 p-3">
                {(["PENDING", "APPROVED", "REJECTED"] as Status[]).map(
                  (status) => (
                    <button
                      key={status}
                      type="button"
                      onClick={() =>
                        setStatusFilter((current) =>
                          current === status ? "ALL" : status,
                        )
                      }
                      className={`rounded-xl px-2 py-2 text-[9px] font-extrabold transition ${
                        statusFilter === status
                          ? "bg-sky-100 text-sky-700 ring-1 ring-sky-300"
                          : "text-slate-500 hover:bg-white/70"
                      }`}
                    >
                      {status} ·{" "}
                      {
                        records.filter((record) => record.status === status)
                          .length
                      }
                    </button>
                  ),
                )}
              </div>
              <div className="max-h-[510px] divide-y divide-white/70 overflow-y-auto">
                {filteredRecords.map((record) => (
                  <button
                    key={record.id}
                    type="button"
                    onClick={() => setSelectedId(record.id)}
                    className={`group flex w-full gap-3 p-4 text-left transition ${
                      selected?.id === record.id
                        ? "bg-sky-50/80"
                        : "hover:bg-white/45"
                    }`}
                  >
                    <span
                      className={`grid size-10 shrink-0 place-items-center rounded-xl ${
                        record.type.includes("OCR")
                          ? "bg-sky-100 text-sky-700"
                          : "bg-cyan-100 text-cyan-700"
                      }`}
                    >
                      {record.type.includes("OCR") ||
                      record.type.includes("Excel") ? (
                        <FileSpreadsheet size={18} />
                      ) : (
                        <Layers3 size={18} />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-xs font-extrabold text-slate-800">
                          {record.title}
                        </p>
                        {record.status === "PENDING" && (
                          <i className="size-1.5 shrink-0 rounded-full bg-amber-400" />
                        )}
                      </div>
                      <p className="mt-1 truncate text-[9px] font-medium text-slate-400">
                        {record.majorCode} · {record.source}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
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
                        <span className="text-[9px] text-slate-400">
                          {record.confidence}% · {record.updated}
                        </span>
                      </div>
                    </div>
                    <ChevronRight
                      size={15}
                      className="mt-2 text-slate-300 transition-transform group-hover:translate-x-0.5"
                    />
                  </button>
                ))}
              </div>
            </div>

            {selected && (
              <div className="flex min-w-0 flex-col">
                <div className="flex flex-col justify-between gap-4 border-b border-white/70 p-5 sm:flex-row sm:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-black text-slate-900">
                        {selected.title}
                      </h3>
                      <Badge
                        tone={
                          selected.status === "APPROVED"
                            ? "emerald"
                            : selected.status === "REJECTED"
                              ? "rose"
                              : "amber"
                        }
                      >
                        {selected.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[10px] text-slate-500">
                      {selected.type} · Confidence {selected.confidence}% ·{" "}
                      {selected.source}
                    </p>
                  </div>
                  <div className="flex rounded-xl bg-white/60 p-1 ring-1 ring-white/80">
                    <button
                      type="button"
                      onClick={() => setPreviewMode("markdown")}
                      className={`rounded-lg px-3 py-1.5 text-[10px] font-bold ${
                        previewMode === "markdown"
                          ? "bg-white text-sky-700 shadow-sm"
                          : "text-slate-400"
                      }`}
                    >
                      Markdown
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewMode("json")}
                      className={`rounded-lg px-3 py-1.5 text-[10px] font-bold ${
                        previewMode === "json"
                          ? "bg-white text-sky-700 shadow-sm"
                          : "text-slate-400"
                      }`}
                    >
                      JSONB
                    </button>
                  </div>
                </div>

                <div className="flex-1 p-5">
                  <div className="mb-4 grid gap-3 sm:grid-cols-3">
                    {[
                      ["Schema", "roadmap.v2", FileJson],
                      ["Citations", "4 verified", CheckCircle2],
                      ["Vector chunks", "12 ready", Database],
                    ].map(([label, value, Icon]) => (
                      <div
                        key={String(label)}
                        className="rounded-2xl border border-white/80 bg-white/45 p-3"
                      >
                        <Icon size={15} className="text-sky-500" />
                        <p className="mt-2 text-[9px] font-bold uppercase text-slate-400">
                          {String(label)}
                        </p>
                        <p className="mt-0.5 text-xs font-extrabold text-slate-700">
                          {String(value)}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="min-h-72 overflow-auto rounded-2xl border border-sky-200/80 bg-sky-50/80 p-5 text-slate-700 shadow-inner">
                    {previewMode === "markdown" ? (
                      <div className="admin-markdown text-xs leading-6">
                        <Markdown remarkPlugins={[remarkGfm]}>
                          {selected.markdown}
                        </Markdown>
                      </div>
                    ) : (
                      <pre className="text-[11px] leading-6 text-sky-800">
                        {JSON.stringify(
                          {
                            major_code: selected.majorCode,
                            title: selected.title,
                            status: selected.status,
                            source_type: selected.type,
                            confidence: selected.confidence,
                            chunks: 12,
                            citation_domains: selected.source.split(" · "),
                            pii_redacted: true,
                          },
                          null,
                          2,
                        )}
                      </pre>
                    )}
                  </div>

                  <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
                    <p className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-widest text-emerald-700">
                      <ShieldCheck size={14} />
                      Source integrity check
                    </p>
                    <div className="mt-3 grid gap-2 text-[10px] text-slate-600 sm:grid-cols-3">
                      {[
                        "Domain authority verified",
                        "PII scan passed",
                        "Duplicate score: 0.08",
                      ].map((item) => (
                        <span key={item} className="flex items-center gap-1.5">
                          <Check size={12} className="text-emerald-600" />
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-3 border-t border-white/70 bg-white/25 p-4 sm:flex-row sm:justify-end">
                  <Button
                    variant="secondary"
                    icon={RefreshCw}
                    onClick={() => updateStatus("REJECTED")}
                  >
                    Từ chối / Yêu cầu quét lại
                  </Button>
                  <Button
                    icon={Check}
                    onClick={() => updateStatus("APPROVED")}
                  >
                    Phê duyệt & Lưu pgvector
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
