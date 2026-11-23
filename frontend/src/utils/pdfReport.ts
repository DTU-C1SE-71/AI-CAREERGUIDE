import type {
  AspirationAIAnalysis,
  StudentSkillAnalysis,
} from "../types/insight"
import type { AspirationAnalysisPayload } from "../types/assessment"

export interface CareerReportMajorItem {
  code: string
  name: string
  category?: string
  match: number | null
  fit?: {
    interest: number | null
    academic: number | null
    cognitive: number | null
  }
  best_matching_block?: string
  best_block_score?: number | null
  benchmark_cutoff?: number
  feasibility_label?: string
  is_trending?: boolean
  trend_label?: string | null
  explanation?: string
  admission_advice?: string
}

export interface CareerReportPdfInput {
  studentName: string
  studentEmail?: string
  gradeLevel?: string
  gender?: string
  schoolClass?: string
  schoolName?: string
  attemptLabel?: string
  completedAt?: string
  hollandCode: string
  archetypeTitle: string
  riasec: Array<{ key: string; label: string; value: number }>
  interestStatus?: string
  bestBlock: {
    block: string
    rawSum?: number | null
    zScore?: string
    percentile?: string
    failingSubjects?: string[]
  }
  scores: Array<{ subject: string; score: number }>
  horizonLabel?: string
  weightsApplied?: {
    w_riasec?: number
    w_academic?: number
    w_preference?: number
  }
  tier1Fields: Array<{
    field_name: string
    match: number | null
    majors_count: number
    eligible_count?: number
  }>
  topMajors: CareerReportMajorItem[]
  skillAnalysis?: StudentSkillAnalysis | null
  aspirationAnalysis?: AspirationAnalysisPayload | null
  aspirationAiAnalysis?: AspirationAIAnalysis | null
}

export interface ChatReportMessageItem {
  role: "user" | "assistant"
  content: string
  lengthLabel?: string
  sourceLabel?: string
  createdAt?: string
}

export interface ChatReportPdfInput {
  title: string
  studentName?: string
  studentEmail?: string
  majorLabel?: string
  exportedAt?: Date
  messages: ChatReportMessageItem[]
}

const RIASEC_GROUP_TITLES: Record<string, string> = {
  R: "R · Kỹ thuật",
  I: "I · Nghiên cứu",
  A: "A · Nghệ thuật",
  S: "S · Xã hội",
  E: "E · Kinh doanh",
  C: "C · Nghiệp vụ",
}

const FIT_BADGE_MAP: Record<string, { bg: string; border: string; text: string }> = {
  HIGH: { bg: "#ecfdf5", border: "#a7f3d0", text: "#047857" },
  MEDIUM: { bg: "#fffbeb", border: "#fde68a", text: "#b45309" },
  LOW: { bg: "#fff1f2", border: "#fecdd3", text: "#be123c" },
  UNKNOWN: { bg: "#f8fafc", border: "#cbd5e1", text: "#475569" },
}

export function escapeHtml(value: string): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

export function buildPdfFilename(
  prefix: string,
  label?: string,
  date: Date = new Date(),
): string {
  const cleanPrefix = (prefix || "Bao-cao")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .replace(/[^A-Za-z0-9-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")

  const cleanSlug = (label || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .replace(/[^A-Za-z0-9-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40)
    .replace(/-$/g, "")

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const datePart = `${year}-${month}-${day}`

  return cleanSlug
    ? `${cleanPrefix || "Bao-cao"}-${cleanSlug}-${datePart}.pdf`
    : `${cleanPrefix || "Bao-cao"}-${datePart}.pdf`
}

function formatInlineMarkdown(escapedLine: string): string {
  // Note: escapedLine has already passed through escapeHtml()
  const codeTokens: string[] = []
  let text = escapedLine.replace(/`([^`]+)`/g, (_m, code) => {
    const token = `__INLINE_CODE_${codeTokens.length}__`
    codeTokens.push(
      `<code style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:4px;padding:1px 5px;font-family:Consolas,monospace;font-size:11px;color:#0f172a;">${code}</code>`,
    )
    return token
  })

  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong style="font-weight:700;color:#0f172a;">$1</strong>')
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>")

  return text.replace(/__INLINE_CODE_(\d+)__/g, (_m, idx) => codeTokens[Number(idx)] ?? "")
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.slice(1, -1).includes("|")
}

function isTableSeparator(line: string): boolean {
  const cells = line
    .trim()
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim())
  return cells.length > 0 && cells.every((c) => /^:?-{2,}:?$/.test(c))
}

function splitTableCells(line: string): string[] {
  return line
    .trim()
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim())
}

export function markdownToSafeHtml(markdown: string): string {
  const raw = String(markdown ?? "").replace(/\r\n/g, "\n")
  if (!raw.trim()) return ""

  const lines = raw.split("\n")
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (!trimmed) {
      i += 1
      continue
    }

    // Fenced code block
    if (trimmed.startsWith("```")) {
      const codeLines: string[] = []
      i += 1
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(escapeHtml(lines[i]))
        i += 1
      }
      if (i < lines.length) i += 1
      out.push(
        `<pre style="margin:8px 0;padding:10px 12px;border-radius:8px;background:#0f172a;color:#f8fafc;font-family:Consolas,monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;word-break:break-word;">${codeLines.join("\n")}</pre>`,
      )
      continue
    }

    // Markdown table
    if (
      isTableRow(line) &&
      i + 1 < lines.length &&
      isTableSeparator(lines[i + 1])
    ) {
      const headers = splitTableCells(line)
      i += 2
      const rows: string[][] = []
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(splitTableCells(lines[i]))
        i += 1
      }
      const headHtml = headers
        .map(
          (cell) =>
            `<th style="padding:6px 8px;border:1px solid #cbd5e1;background:#f0f9ff;text-align:left;font-size:11.5px;font-weight:700;color:#0f172a;">${formatInlineMarkdown(escapeHtml(cell))}</th>`,
        )
        .join("")
      const bodyHtml = rows
        .map((row, rIdx) => {
          const bg = rIdx % 2 === 1 ? "#f8fafc" : "#ffffff"
          const cellsHtml = headers
            .map((_, cIdx) => {
              const cellText = row[cIdx] ?? ""
              return `<td style="padding:6px 8px;border:1px solid #e2e8f0;background:${bg};font-size:11.5px;color:#334155;vertical-align:top;">${formatInlineMarkdown(escapeHtml(cellText))}</td>`
            })
            .join("")
          return `<tr>${cellsHtml}</tr>`
        })
        .join("")
      out.push(
        `<table style="width:100%;border-collapse:collapse;margin:8px 0;"><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`,
      )
      continue
    }

    // Headings (#, ##, ###, ####)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      const level = headingMatch[1].length
      const fontSize = level === 1 ? "15px" : level === 2 ? "14px" : "13px"
      out.push(
        `<div style="margin:8px 0 4px;font-size:${fontSize};font-weight:700;color:#0f172a;line-height:1.4;">${formatInlineMarkdown(escapeHtml(headingMatch[2]))}</div>`,
      )
      i += 1
      continue
    }

    // Unordered list (-, *, •)
    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^[-*•]\s+/.test(lines[i].trim())) {
        const itemText = lines[i].trim().replace(/^[-*•]\s+/, "")
        items.push(
          `<li style="margin:3px 0;color:#334155;">${formatInlineMarkdown(escapeHtml(itemText))}</li>`,
        )
        i += 1
      }
      out.push(
        `<ul style="margin:6px 0 8px 18px;padding:0;list-style-type:disc;font-size:12.5px;line-height:1.55;">${items.join("")}</ul>`,
      )
      continue
    }

    // Ordered list (1. 2. ...)
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        const itemText = lines[i].trim().replace(/^\d+\.\s+/, "")
        items.push(
          `<li style="margin:3px 0;color:#334155;">${formatInlineMarkdown(escapeHtml(itemText))}</li>`,
        )
        i += 1
      }
      out.push(
        `<ol style="margin:6px 0 8px 18px;padding:0;list-style-type:decimal;font-size:12.5px;line-height:1.55;">${items.join("")}</ol>`,
      )
      continue
    }

    // Plain paragraph lines until blank or block start
    const paraLines: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].trim().startsWith("```") &&
      !/^#{1,4}\s+/.test(lines[i].trim()) &&
      !/^[-*•]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !isTableRow(lines[i])
    ) {
      paraLines.push(formatInlineMarkdown(escapeHtml(lines[i].trim())))
      i += 1
    }
    out.push(
      `<p style="margin:5px 0;font-size:12.5px;line-height:1.6;color:#334155;">${paraLines.join("<br />")}</p>`,
    )
  }

  return out.join("")
}

function formatDateTimeLabel(value?: string | Date): string {
  if (!value) {
    return new Date().toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
  }
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return escapeHtml(String(value))
  return date.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
}

function wrapPdfHtmlDocument(title: string, bodyContent: string): string {
  return `<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <title>${escapeHtml(title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap"
      rel="stylesheet"
    />
    <style>
      * {
        box-sizing: border-box;
      }
      html, body {
        margin: 0;
        padding: 0;
        width: 794px;
        background: #ffffff;
        color: #0f172a;
        font-family: 'Be Vietnam Pro', 'Segoe UI', Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
      }
      .pdf-page-root {
        width: 794px;
        padding: 12px 16px;
        background: #ffffff;
      }
      .pdf-block {
        margin-bottom: 14px;
        background: #ffffff;
      }
      .card {
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 18px;
        background: #ffffff;
      }
      .section-title {
        margin: 0 0 10px;
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.02em;
        color: #0284c7;
        text-transform: uppercase;
      }
    </style>
  </head>
  <body>
    <div class="pdf-page-root">
      ${bodyContent}
    </div>
  </body>
</html>`
}

export function buildCareerReportHtml(input: CareerReportPdfInput): string {
  const generatedLabel = formatDateTimeLabel(input.completedAt)
  const schoolSummary = [input.schoolClass, input.schoolName]
    .filter((v) => v && v.trim())
    .join(" — ")

  const profileRows = [
    { label: "Học sinh", value: input.studentName || "Học sinh" },
    ...(input.studentEmail ? [{ label: "Email", value: input.studentEmail }] : []),
    ...(input.gradeLevel ? [{ label: "Khối lớp", value: input.gradeLevel }] : []),
    ...(input.gender ? [{ label: "Giới tính", value: input.gender }] : []),
    ...(schoolSummary ? [{ label: "Trường / Lớp", value: schoolSummary }] : []),
    ...(input.attemptLabel ? [{ label: "Phiên đánh giá", value: input.attemptLabel }] : []),
    { label: "Thời gian lập báo cáo", value: generatedLabel },
  ]

  const headerHtml = `
    <section class="pdf-block">
      <div style="border-radius:16px;border:1px solid #bae6fd;background:linear-gradient(135deg,#f0f9ff 0%,#ffffff 65%,#e0f2fe 100%);padding:18px 20px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div>
            <div style="font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#0284c7;">
              AI CareerGuide · Báo cáo Hướng nghiệp Cá nhân hóa
            </div>
            <h1 style="margin:6px 0 4px;font-size:21px;font-weight:800;color:#0f172a;line-height:1.25;">
              Hồ sơ Định hướng Ngành học 2026
            </h1>
            <p style="margin:0;font-size:12px;color:#475569;">
              Tổng hợp sở thích nghề nghiệp RIASEC, năng lực học tập và đối chiếu 435 ngành chuẩn Bộ GD&amp;ĐT.
            </p>
          </div>
          <div style="shrink:0;text-align:right;background:#0284c7;color:#ffffff;border-radius:12px;padding:8px 14px;">
            <div style="font-size:10px;font-weight:600;opacity:0.9;text-transform:uppercase;">Mã Holland</div>
            <div style="font-size:16px;font-weight:800;letter-spacing:0.04em;margin-top:2px;">
              ${escapeHtml(input.hollandCode || "Chưa xác định")}
            </div>
          </div>
        </div>

        <div style="margin-top:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;border-top:1px solid #e0f2fe;padding-top:12px;">
          ${profileRows
            .map(
              (item) => `
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:7px 10px;">
              <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;">${escapeHtml(item.label)}</div>
              <div style="margin-top:2px;font-size:12px;font-weight:700;color:#0f172a;word-break:break-word;">${escapeHtml(item.value)}</div>
            </div>`,
            )
            .join("")}
        </div>
      </div>
    </section>
  `

  const riasecBarsHtml =
    input.riasec.length > 0
      ? input.riasec
          .map((point) => {
            const pct = Math.max(0, Math.min(100, Math.round(Number(point.value) || 0)))
            const label = RIASEC_GROUP_TITLES[point.key] || `${point.key} · ${point.label}`
            return `
            <div style="margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:600;color:#334155;margin-bottom:3px;">
                <span>${escapeHtml(label)}</span>
                <span style="color:#0284c7;font-weight:700;">${pct}%</span>
              </div>
              <div style="height:8px;width:100%;border-radius:999px;background:#e2e8f0;overflow:hidden;">
                <div style="height:8px;width:${pct}%;border-radius:999px;background:#0ea5e9;"></div>
              </div>
            </div>`
          })
          .join("")
      : `<p style="margin:0;font-size:12px;color:#64748b;">Chưa đủ dữ liệu trắc nghiệm RIASEC.</p>`

  const scoresChipsHtml =
    input.scores.length > 0
      ? input.scores
          .map(
            (s) =>
              `<span style="display:inline-block;margin:0 6px 6px 0;padding:4px 9px;border-radius:8px;border:1px solid #e2e8f0;background:#f8fafc;font-size:11.5px;font-weight:600;color:#1e293b;">${escapeHtml(s.subject)}: <strong style="color:#0284c7;">${Number(s.score).toFixed(1).replace(/\.0$/, "")}đ</strong></span>`,
          )
          .join("")
      : `<span style="font-size:12px;color:#64748b;">Chưa nhập điểm học tập cụ thể.</span>`

  const weightsText = input.weightsApplied
    ? `Trọng số áp dụng${input.horizonLabel ? ` (${escapeHtml(input.horizonLabel)})` : ""}: Sở thích ${Math.round((input.weightsApplied.w_riasec ?? 0) * 100)}% · Học lực ${Math.round((input.weightsApplied.w_academic ?? 0) * 100)}% · Nhận thức ${Math.round((input.weightsApplied.w_preference ?? 0) * 100)}%`
    : ""

  const profileSummaryHtml = `
    <section class="pdf-block">
      <div class="card">
        <div class="section-title">1. Hồ sơ Sở thích &amp; Học lực</div>
        <div style="display:grid;grid-template-columns:1.1fr 0.9fr;gap:16px;">
          <div>
            <div style="font-size:14px;font-weight:800;color:#0f172a;margin-bottom:8px;">
              Hình mẫu nổi bật: ${escapeHtml(input.archetypeTitle)}
            </div>
            ${riasecBarsHtml}
          </div>
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;">
            <div style="font-size:11px;font-weight:800;text-transform:uppercase;color:#0284c7;">
              Tổ hợp môn tốt nhất
            </div>
            <div style="margin-top:4px;font-size:14px;font-weight:800;color:#0f172a;">
              ${escapeHtml(input.bestBlock.block)}${input.bestBlock.rawSum !== null && input.bestBlock.rawSum !== undefined ? ` · ${input.bestBlock.rawSum}đ` : ""}
            </div>
            <div style="margin-top:4px;font-size:11.5px;color:#475569;line-height:1.45;">
              Z-Score: <strong>${escapeHtml(input.bestBlock.zScore || "Chưa xác minh")}</strong><br />
              ${escapeHtml(input.bestBlock.percentile || "")}
            </div>
            ${
              input.bestBlock.failingSubjects && input.bestBlock.failingSubjects.length > 0
                ? `<div style="margin-top:8px;padding:6px 9px;border-radius:8px;background:#fff1f2;border:1px solid #fecdd3;font-size:11.5px;font-weight:700;color:#be123c;">Cảnh báo điểm liệt: ${escapeHtml(input.bestBlock.failingSubjects.join(", "))}</div>`
                : ""
            }
            <div style="margin-top:10px;border-top:1px solid #e2e8f0;padding-top:10px;">
              <div style="font-size:11px;font-weight:700;color:#64748b;margin-bottom:6px;">Bảng điểm đã nhập</div>
              <div>${scoresChipsHtml}</div>
            </div>
          </div>
        </div>
        ${
          weightsText
            ? `<div style="margin-top:10px;padding:8px 12px;border-radius:10px;background:#f0f9ff;border:1px solid #bae6fd;font-size:11.5px;font-weight:600;color:#0369a1;">${weightsText}</div>`
            : ""
        }
      </div>
    </section>
  `

  const tier1Html =
    input.tier1Fields.length > 0
      ? `
    <section class="pdf-block">
      <div class="card">
        <div class="section-title">2. Tầng 1 · Nhóm Lĩnh vực Phù hợp</div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
          ${input.tier1Fields
            .slice(0, 6)
            .map(
              (field) => `
            <div style="border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;background:#f8fafc;display:flex;justify-content:space-between;align-items:center;gap:10px;">
              <div style="min-width:0;">
                <div style="font-size:12.5px;font-weight:700;color:#0f172a;">${escapeHtml(field.field_name)}</div>
                <div style="margin-top:2px;font-size:11px;color:#64748b;">
                  ${field.eligible_count !== undefined ? `${field.eligible_count}/${field.majors_count} ngành đạt ngưỡng` : `${field.majors_count} ngành đào tạo`}
                </div>
              </div>
              <span style="shrink:0;border-radius:999px;background:#e0f2fe;color:#0369a1;padding:3px 9px;font-size:12px;font-weight:800;">
                ${field.match !== null && field.match !== undefined ? `${Math.round(field.match)}%` : "Tham khảo"}
              </span>
            </div>`,
            )
            .join("")}
        </div>
      </div>
    </section>`
      : ""

  const seenCodes = new Set<string>()
  const uniqueMajors = input.topMajors.filter((m) => {
    const key = m.code || m.name
    if (seenCodes.has(key)) return false
    seenCodes.add(key)
    return true
  })

  const majorsSectionHeader =
    uniqueMajors.length > 0
      ? `
    <section class="pdf-block">
      <div style="padding:4px 2px;">
        <div class="section-title" style="margin:0;">3. Tầng 2 · Top Ngành Đào Tạo Đề Xuất (${Math.min(8, uniqueMajors.length)} ngành tiêu biểu)</div>
      </div>
    </section>
    ${uniqueMajors
      .slice(0, 8)
      .map((major, idx) => {
        const matchLabel =
          major.match !== null && major.match !== undefined
            ? `${Math.round(major.match)}% phù hợp`
            : "Mức khám phá"
        const fitParts: string[] = []
        if (major.fit?.interest !== null && major.fit?.interest !== undefined) {
          fitParts.push(`Sở thích: ${Math.round(major.fit.interest)}%`)
        }
        if (major.fit?.academic !== null && major.fit?.academic !== undefined) {
          fitParts.push(`Học lực: ${Math.round(major.fit.academic)}%`)
        }
        if (major.fit?.cognitive !== null && major.fit?.cognitive !== undefined) {
          fitParts.push(`Nhận thức: ${Math.round(major.fit.cognitive)}%`)
        }
        const blockText = [
          major.best_matching_block ? `Tổ hợp ${major.best_matching_block}` : "",
          major.best_block_score !== null && major.best_block_score !== undefined
            ? `Điểm: ${major.best_block_score}`
            : "",
          major.benchmark_cutoff !== undefined
            ? `Sàn/Tham chiếu: ${major.benchmark_cutoff}đ`
            : "",
        ]
          .filter(Boolean)
          .join(" · ")

        return `
      <section class="pdf-block">
        <div class="card" style="padding:13px 16px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;">
                <span style="font-size:13.5px;font-weight:800;color:#0f172a;">#${idx + 1}. ${escapeHtml(major.name)}</span>
                <span style="border-radius:6px;background:#f1f5f9;padding:2px 6px;font-size:11px;font-weight:700;color:#475569;">${escapeHtml(major.code)}</span>
                ${
                  major.is_trending
                    ? `<span style="border-radius:999px;background:#ecfdf5;border:1px solid #a7f3d0;padding:2px 8px;font-size:10.5px;font-weight:700;color:#047857;">${escapeHtml(major.trend_label || "Xu hướng 2026")}</span>`
                    : ""
                }
              </div>
              <div style="margin-top:3px;font-size:11.5px;color:#64748b;">
                ${major.category ? `${escapeHtml(major.category)} · ` : ""}${escapeHtml(blockText || "Đối chiếu đa tổ hợp")}
              </div>
            </div>
            <div style="text-align:right;shrink:0;">
              <span style="display:inline-block;border-radius:999px;background:#0284c7;color:#ffffff;padding:4px 10px;font-size:11.5px;font-weight:800;">
                ${escapeHtml(matchLabel)}
              </span>
              ${
                major.feasibility_label
                  ? `<div style="margin-top:4px;font-size:10.5px;font-weight:700;color:#0369a1;">${escapeHtml(major.feasibility_label)}</div>`
                  : ""
              }
            </div>
          </div>
          ${
            fitParts.length > 0
              ? `<div style="margin-top:8px;font-size:11.5px;font-weight:600;color:#334155;">${escapeHtml(fitParts.join("  |  "))}</div>`
              : ""
          }
          ${
            major.explanation
              ? `<p style="margin:6px 0 0;font-size:12px;line-height:1.5;color:#334155;">${escapeHtml(major.explanation)}</p>`
              : ""
          }
          ${
            major.admission_advice
              ? `<div style="margin-top:6px;font-size:11.5px;color:#475569;background:#f8fafc;border-left:3px solid #0ea5e9;padding:5px 9px;border-radius:0 6px 6px 0;">${escapeHtml(major.admission_advice)}</div>`
              : ""
          }
        </div>
      </section>`
      })
      .join("")}`
      : ""

  const skillHtml = input.skillAnalysis
    ? (() => {
        const s = input.skillAnalysis
        const strengths = (s.strengths || [])
          .slice(0, 4)
          .map(
            (pt) =>
              `<li style="margin:3px 0;"><strong>${escapeHtml(pt.title)}:</strong> ${escapeHtml(pt.detail)}</li>`,
          )
          .join("")
        const weaknesses = (s.weaknesses || [])
          .slice(0, 4)
          .map(
            (pt) =>
              `<li style="margin:3px 0;"><strong>${escapeHtml(pt.title)}:</strong> ${escapeHtml(pt.detail)}</li>`,
          )
          .join("")
        const gaps = (s.skill_gaps || [])
          .slice(0, 4)
          .map(
            (gap) => `
          <div style="border:1px solid #e2e8f0;border-radius:10px;padding:9px 11px;margin-top:7px;background:#f8fafc;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
              <strong style="font-size:12px;color:#0f172a;">${escapeHtml(gap.skill)}</strong>
              <span style="border-radius:999px;background:#e0f2fe;padding:2px 8px;font-size:10px;font-weight:700;color:#0369a1;">Ưu tiên: ${escapeHtml(gap.priority)}</span>
            </div>
            <p style="margin:4px 0;font-size:11.5px;color:#475569;">${escapeHtml(gap.why)}</p>
            ${
              gap.how_to_improve?.length
                ? `<ul style="margin:4px 0 0 16px;padding:0;font-size:11px;color:#334155;">${gap.how_to_improve.slice(0, 3).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ul>`
                : ""
            }
          </div>`,
          )
          .join("")

        return `
      <section class="pdf-block">
        <div class="card">
          <div class="section-title">4. Phân tích Kỹ năng &amp; Điểm cần Bồi dưỡng</div>
          <p style="margin:0 0 10px;font-size:12.5px;line-height:1.55;color:#1e293b;">${escapeHtml(s.summary)}</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div style="border:1px solid #a7f3d0;background:#ecfdf5;border-radius:10px;padding:10px 12px;">
              <div style="font-size:11.5px;font-weight:800;color:#047857;margin-bottom:5px;">Điểm mạnh nổi bật</div>
              <ul style="margin:0 0 0 16px;padding:0;font-size:11.5px;line-height:1.5;color:#1e293b;">${strengths || "<li>Đang cập nhật</li>"}</ul>
            </div>
            <div style="border:1px solid #fde68a;background:#fffbeb;border-radius:10px;padding:10px 12px;">
              <div style="font-size:11.5px;font-weight:800;color:#b45309;margin-bottom:5px;">Điểm cần cải thiện</div>
              <ul style="margin:0 0 0 16px;padding:0;font-size:11.5px;line-height:1.5;color:#1e293b;">${weaknesses || "<li>Không có cảnh báo lớn</li>"}</ul>
            </div>
          </div>
          ${gaps ? `<div style="margin-top:10px;"><div style="font-size:12px;font-weight:800;color:#0f172a;">Kỹ năng nên rèn luyện thêm</div>${gaps}</div>` : ""}
        </div>
      </section>`
      })()
    : ""

  const aspirationHtml =
    input.aspirationAiAnalysis || input.aspirationAnalysis?.has_aspiration
      ? (() => {
          const ai = input.aspirationAiAnalysis
          const rule = input.aspirationAnalysis
          const dreamJob = ai?.dream_job || rule?.dream_job || ""
          const badge = FIT_BADGE_MAP[ai?.fit_level || "UNKNOWN"] || FIT_BADGE_MAP.UNKNOWN
          const label = ai?.fit_label || rule?.alignment_label || "Tham khảo nguyện vọng"
          const summary = ai?.summary || rule?.agent_verdict || ""
          const fitReasons = (ai?.reasons_fit || [])
            .slice(0, 3)
            .map((r) => `<li><strong>${escapeHtml(r.title)}:</strong> ${escapeHtml(r.detail)}</li>`)
            .join("")
          const gapReasons = (ai?.reasons_gap || [])
            .slice(0, 3)
            .map((r) => `<li><strong>${escapeHtml(r.title)}:</strong> ${escapeHtml(r.detail)}</li>`)
            .join("")
          const better = (ai?.better_majors || [])
            .slice(0, 3)
            .map(
              (b) =>
                `<li style="margin:3px 0;"><strong>${escapeHtml(b.major_name)} (${escapeHtml(b.major_code)}):</strong> ${escapeHtml(b.reason)}</li>`,
            )
            .join("")

          return `
        <section class="pdf-block">
          <div class="card">
            <div class="section-title">5. Đánh giá Nghề Mơ Ước &amp; Nguyện Vọng</div>
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px;">
              <div style="font-size:13.5px;font-weight:800;color:#0f172a;">
                Mục tiêu nghề nghiệp: ${escapeHtml(dreamJob)}
              </div>
              <span style="border-radius:999px;border:1px solid ${badge.border};background:${badge.bg};color:${badge.text};padding:3px 10px;font-size:11px;font-weight:700;">
                ${escapeHtml(label)}
              </span>
            </div>
            ${summary ? `<p style="margin:0 0 8px;font-size:12px;line-height:1.55;color:#334155;">${escapeHtml(summary)}</p>` : ""}
            ${
              fitReasons || gapReasons
                ? `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    ${fitReasons ? `<div style="border:1px solid #e2e8f0;border-radius:10px;padding:9px 11px;"><div style="font-size:11px;font-weight:800;color:#0284c7;margin-bottom:4px;">Yếu tố phù hợp</div><ul style="margin:0 0 0 15px;padding:0;font-size:11.5px;color:#334155;">${fitReasons}</ul></div>` : ""}
                    ${gapReasons ? `<div style="border:1px solid #e2e8f0;border-radius:10px;padding:9px 11px;"><div style="font-size:11px;font-weight:800;color:#b45309;margin-bottom:4px;">Thách thức cần lưu ý</div><ul style="margin:0 0 0 15px;padding:0;font-size:11.5px;color:#334155;">${gapReasons}</ul></div>` : ""}
                  </div>`
                : ""
            }
            ${better ? `<div style="margin-top:8px;border:1px solid #bae6fd;background:#f0f9ff;border-radius:10px;padding:9px 12px;"><div style="font-size:11px;font-weight:800;color:#0369a1;margin-bottom:4px;">Ngành thay thế / song hành gợi ý</div><ul style="margin:0 0 0 15px;padding:0;font-size:11.5px;color:#1e293b;">${better}</ul></div>` : ""}
          </div>
        </section>`
        })()
      : ""

  const disclaimerHtml = `
    <section class="pdf-block">
      <div style="border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc;padding:11px 14px;font-size:11px;line-height:1.5;color:#475569;">
        <strong style="color:#0f172a;">Lưu ý minh bạch:</strong>
        Các chỉ số phù hợp, mức khả thi và phân tích AI trong báo cáo này chỉ mang tính chất <strong>tham khảo định hướng</strong> dựa trên dữ liệu sở thích RIASEC và điểm học tập bạn đã cung cấp; không phải xác suất trúng tuyển hay quyết định tuyển sinh chính thức của các trường đại học.
      </div>
    </section>
  `

  return wrapPdfHtmlDocument(
    `Bao cao Huong nghiep - ${input.studentName || "Hoc sinh"}`,
    headerHtml +
      profileSummaryHtml +
      tier1Html +
      majorsSectionHeader +
      skillHtml +
      aspirationHtml +
      disclaimerHtml,
  )
}

export function buildChatReportHtml(input: ChatReportPdfInput): string {
  const exportedLabel = formatDateTimeLabel(input.exportedAt || new Date())
  const metaItems = [
    ...(input.studentName ? [`Học sinh: <strong>${escapeHtml(input.studentName)}</strong>`] : []),
    ...(input.studentEmail ? [`Email: <strong>${escapeHtml(input.studentEmail)}</strong>`] : []),
    ...(input.majorLabel ? [`Ngành quan tâm: <strong>${escapeHtml(input.majorLabel)}</strong>`] : []),
    `Số tin nhắn: <strong>${input.messages.length}</strong>`,
    `Xuất lúc: <strong>${escapeHtml(exportedLabel)}</strong>`,
  ]

  const headerHtml = `
    <section class="pdf-block">
      <div style="border-radius:16px;border:1px solid #bae6fd;background:linear-gradient(135deg,#f0f9ff 0%,#ffffff 70%,#e0f2fe 100%);padding:18px 20px;">
        <div style="font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#0284c7;">
          AI CareerGuide · Biên bản Tư vấn Cố vấn AI
        </div>
        <h1 style="margin:6px 0 6px;font-size:19px;font-weight:800;color:#0f172a;line-height:1.3;">
          ${escapeHtml(input.title || "Cuộc trò chuyện Hướng nghiệp")}
        </h1>
        <div style="display:flex;flex-wrap:wrap;gap:8px 14px;font-size:11.5px;color:#334155;">
          ${metaItems.map((m) => `<span>${m}</span>`).join("")}
        </div>
      </div>
    </section>
  `

  const messagesHtml = input.messages
    .map((msg) => {
      const isUser = msg.role === "user"
      const timeLabel = msg.createdAt ? formatDateTimeLabel(msg.createdAt) : ""
      if (isUser) {
        return `
        <section class="pdf-block">
          <div style="border:1px solid #bae6fd;background:#f0f9ff;border-radius:14px;padding:12px 15px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
              <span style="font-size:11px;font-weight:800;text-transform:uppercase;color:#0369a1;">Học sinh đặt câu hỏi</span>
              ${timeLabel ? `<span style="font-size:10.5px;color:#64748b;">${escapeHtml(timeLabel)}</span>` : ""}
            </div>
            <div style="font-size:13px;font-weight:600;color:#0f172a;line-height:1.55;white-space:pre-wrap;word-break:break-word;">${escapeHtml(msg.content)}</div>
          </div>
        </section>`
      }

      const badges = [
        msg.lengthLabel
          ? `<span style="border-radius:999px;border:1px solid #bae6fd;background:#f0f9ff;padding:2px 8px;font-size:10.5px;font-weight:700;color:#0369a1;">Suy luận: ${escapeHtml(msg.lengthLabel)}</span>`
          : "",
        msg.sourceLabel
          ? `<span style="font-size:10.5px;font-weight:600;color:#64748b;">${escapeHtml(msg.sourceLabel)}</span>`
          : "",
      ]
        .filter(Boolean)
        .join(" ")

      return `
      <section class="pdf-block">
        <div style="border:1px solid #e2e8f0;background:#ffffff;border-radius:14px;padding:13px 16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;border-bottom:1px solid #f1f5f9;padding-bottom:6px;">
            <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;">
              <span style="font-size:11px;font-weight:800;text-transform:uppercase;color:#0284c7;">Cố vấn AI</span>
              ${badges}
            </div>
            ${timeLabel ? `<span style="font-size:10.5px;color:#64748b;">${escapeHtml(timeLabel)}</span>` : ""}
          </div>
          <div>${markdownToSafeHtml(msg.content)}</div>
        </div>
      </section>`
    })
    .join("")

  const disclaimerHtml = `
    <section class="pdf-block">
      <div style="border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc;padding:10px 14px;font-size:11px;line-height:1.5;color:#475569;">
        <strong style="color:#0f172a;">Lưu ý:</strong> Nội dung tư vấn trong tệp PDF này chỉ mang tính chất hỗ trợ tham khảo định hướng học tập và nghề nghiệp.
      </div>
    </section>
  `

  return wrapPdfHtmlDocument(
    `Tu van AI - ${input.title || "Lich su"}`,
    headerHtml + messagesHtml + disclaimerHtml,
  )
}

async function waitForIframeReady(iframeDoc: Document): Promise<void> {
  try {
    if (iframeDoc.fonts?.ready) {
      await Promise.race([
        iframeDoc.fonts.ready,
        new Promise<void>((resolve) => window.setTimeout(resolve, 1500)),
      ])
    }
  } catch {
    // Fallback to system sans font cleanly
  }
  await new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => {
      window.setTimeout(resolve, 60)
    })
  })
}

async function renderHtmlDocumentToPdf(
  html: string,
  filename: string,
): Promise<void> {
  if (typeof document === "undefined") {
    throw new Error("Trình duyệt chưa sẵn sàng để xuất PDF.")
  }

  const [{ jsPDF }, html2canvasMod] = await Promise.all([
    import("jspdf"),
    import("html2canvas"),
  ])
  const html2canvas = html2canvasMod.default

  const iframe = document.createElement("iframe")
  iframe.setAttribute("aria-hidden", "true")
  iframe.style.position = "fixed"
  iframe.style.left = "-10000px"
  iframe.style.top = "0"
  iframe.style.width = "794px"
  iframe.style.height = "1123px"
  iframe.style.opacity = "0"
  iframe.style.pointerEvents = "none"
  iframe.style.border = "0"
  document.body.appendChild(iframe)

  try {
    const iframeDoc = iframe.contentDocument
    if (!iframeDoc) {
      throw new Error("Không khởi tạo được khung kết xuất PDF.")
    }
    iframeDoc.open()
    iframeDoc.write(html)
    iframeDoc.close()

    await waitForIframeReady(iframeDoc)

    const doc = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
      compress: true,
    })

    const marginX = 12
    const marginTop = 12
    const maxY = 283
    const usableWidth = 186
    const maxPageContentHeightMm = maxY - marginTop
    let cursorY = marginTop

    const rawBlocks = Array.from(iframeDoc.querySelectorAll<HTMLElement>(".pdf-block"))
    const blocks = rawBlocks.length > 0 ? rawBlocks : [iframeDoc.body]

    for (const block of blocks) {
      const canvas = await html2canvas(block, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#ffffff",
        logging: false,
        windowWidth: 794,
      })

      if (canvas.width === 0 || canvas.height === 0) continue

      const blockHeightMm = (canvas.height * usableWidth) / canvas.width

      if (blockHeightMm <= maxPageContentHeightMm) {
        if (cursorY > marginTop && cursorY + blockHeightMm > maxY) {
          doc.addPage()
          cursorY = marginTop
        }
        doc.addImage(
          canvas.toDataURL("image/png"),
          "PNG",
          marginX,
          cursorY,
          usableWidth,
          blockHeightMm,
          undefined,
          "FAST",
        )
        cursorY += blockHeightMm + 3
        continue
      }

      // Slice oversized blocks vertically across A4 pages cleanly
      let offsetPx = 0
      while (offsetPx < canvas.height) {
        const remainingMm = maxY - cursorY
        if (remainingMm < 24 && cursorY > marginTop) {
          doc.addPage()
          cursorY = marginTop
        }
        const availableMm = maxY - cursorY
        const sliceHeightPx = Math.min(
          canvas.height - offsetPx,
          Math.max(1, Math.floor((availableMm * canvas.width) / usableWidth)),
        )
        const sliceCanvas = document.createElement("canvas")
        sliceCanvas.width = canvas.width
        sliceCanvas.height = sliceHeightPx
        const ctx = sliceCanvas.getContext("2d")
        if (!ctx) break
        ctx.fillStyle = "#ffffff"
        ctx.fillRect(0, 0, sliceCanvas.width, sliceCanvas.height)
        ctx.drawImage(
          canvas,
          0,
          offsetPx,
          canvas.width,
          sliceHeightPx,
          0,
          0,
          sliceCanvas.width,
          sliceHeightPx,
        )
        const sliceHeightMm = (sliceHeightPx * usableWidth) / sliceCanvas.width
        doc.addImage(
          sliceCanvas.toDataURL("image/png"),
          "PNG",
          marginX,
          cursorY,
          usableWidth,
          sliceHeightMm,
          undefined,
          "FAST",
        )
        offsetPx += sliceHeightPx
        cursorY += sliceHeightMm
        if (offsetPx < canvas.height) {
          doc.addPage()
          cursorY = marginTop
        }
      }
      cursorY += 3
    }

    const totalPages = doc.getNumberOfPages()
    doc.setFont("helvetica", "normal")
    doc.setFontSize(8.5)
    doc.setTextColor(100, 116, 139)
    for (let page = 1; page <= totalPages; page += 1) {
      doc.setPage(page)
      doc.text(
        `AI CareerGuide  |  Trang ${page} / ${totalPages}`,
        105,
        291,
        { align: "center" },
      )
    }

    doc.save(filename)
  } finally {
    iframe.remove()
  }
}

export async function exportCareerReportPdf(
  input: CareerReportPdfInput,
): Promise<string> {
  const filename = buildPdfFilename("Bao-cao-Huong-nghiep", input.studentName)
  const html = buildCareerReportHtml(input)
  await renderHtmlDocumentToPdf(html, filename)
  return filename
}

export async function exportChatReportPdf(
  input: ChatReportPdfInput,
): Promise<string> {
  const filename = buildPdfFilename("Tu-van-AI", input.title, input.exportedAt)
  const html = buildChatReportHtml(input)
  await renderHtmlDocumentToPdf(html, filename)
  return filename
}
