import { test } from "node:test"
import assert from "node:assert/strict"
import {
  buildCareerReportHtml,
  buildChatReportHtml,
  buildPdfFilename,
  escapeHtml,
  markdownToSafeHtml,
} from "../src/utils/pdfReport.ts"

test("escapeHtml vô hiệu hóa các ký tự HTML nguy hiểm", () => {
  const escaped = escapeHtml(`<script>alert("x" & 'y')</script>`)
  assert.equal(escaped.includes("<script>"), false)
  assert.ok(escaped.includes("&lt;script&gt;"))
  assert.ok(escaped.includes("&quot;x&quot;"))
  assert.ok(escaped.includes("&amp;"))
  assert.ok(escaped.includes("&#39;y&#39;"))
})

test("buildPdfFilename bỏ dấu tiếng Việt và gắn ngày chuẩn ISO", () => {
  const fixedDate = new Date(2026, 10, 23, 19, 30, 0)
  assert.equal(
    buildPdfFilename("Báo cáo Hướng nghiệp", "Nguyễn Thị Đan", fixedDate),
    "Bao-cao-Huong-nghiep-Nguyen-Thi-Dan-2026-11-23.pdf",
  )
  assert.equal(
    buildPdfFilename("Tư vấn AI", "   ", fixedDate),
    "Tu-van-AI-2026-11-23.pdf",
  )
})

test("markdownToSafeHtml dựng bảng, danh sách, tiêu đề và chống XSS", () => {
  const html = markdownToSafeHtml(`### Lộ trình gợi ý

- **Toán học**: Ôn hàm số & *tích phân*
- Lập \`Python\` cơ bản

| Môn | Điểm |
| --- | --- |
| Toán | 8.5 |

<img src=x onerror=alert(1)>`)

  assert.ok(html.includes("<strong"))
  assert.ok(html.includes("<em>tích phân</em>"))
  assert.ok(html.includes("<code"))
  assert.ok(html.includes("<ul"))
  assert.ok(html.includes("<table"))
  assert.ok(html.includes("Toán"))
  assert.equal(html.includes("<img"), false)
  assert.ok(html.includes("&lt;img src=x onerror=alert(1)&gt;"))
})

test("buildCareerReportHtml dựng báo cáo đầy đủ tiếng Việt không dùng oklch", () => {
  const html = buildCareerReportHtml({
    studentName: "Trần Minh Anh",
    studentEmail: "minhanh@example.com",
    gradeLevel: "Lớp 12",
    gender: "Nữ",
    schoolClass: "12A1",
    schoolName: "THPT Lê Quý Đôn",
    attemptLabel: "Lần #1",
    completedAt: "2026-11-23T12:00:00Z",
    hollandCode: "I · R · C",
    archetypeTitle: "Nhà nghiên cứu Khoa học",
    riasec: [
      { key: "R", label: "Kỹ thuật", value: 78 },
      { key: "I", label: "Nghiên cứu", value: 92 },
    ],
    bestBlock: {
      block: "Khối A00 (Toán, Lý, Hóa)",
      rawSum: 26.5,
      zScore: "+1.42",
      percentile: "Top 12%",
    },
    scores: [
      { subject: "Toán", score: 9.0 },
      { subject: "Vật lý", score: 8.8 },
    ],
    horizonLabel: "Ngắn hạn (Lớp 12)",
    weightsApplied: { w_riasec: 0.45, w_academic: 0.4, w_preference: 0.15 },
    tier1Fields: [
      {
        field_name: "Máy tính và Công nghệ thông tin",
        match: 91,
        majors_count: 14,
        eligible_count: 12,
      },
    ],
    topMajors: [
      {
        code: "7480101",
        name: "Khoa học máy tính",
        category: "Máy tính và Công nghệ thông tin",
        match: 92,
        fit: { interest: 95, academic: 90, cognitive: 88 },
        best_matching_block: "A00",
        best_block_score: 26.5,
        benchmark_cutoff: 24.5,
        feasibility_label: "Phù hợp cao",
        is_trending: true,
        trend_label: "Xu hướng Bậc 1",
        explanation: "Khớp mạnh sở thích nhóm Nghiên cứu (I).",
      },
    ],
    skillAnalysis: {
      profile_hash: "hash-1",
      major_code: "7480101",
      summary: "Nền tảng tư duy logic tốt.",
      strengths: [{ title: "Toán học", detail: "Điểm số ổn định ở mức khá giỏi." }],
      weaknesses: [{ title: "Ngoại ngữ", detail: "Cần tăng cường đọc tài liệu chuyên ngành." }],
      skill_gaps: [
        {
          skill: "Lập trình Python",
          why: "Cần thiết cho năm nhất CNTT",
          how_to_improve: ["Thực hành giải bài tập cơ bản 30 phút mỗi ngày"],
          priority: "HIGH",
        },
      ],
      is_ai_generated: true,
      cached: false,
    },
    aspirationAiAnalysis: {
      profile_hash: "hash-1",
      dream_job: "Kỹ sư AI",
      fit_level: "HIGH",
      fit_label: "Phù hợp rất cao",
      summary: "Định hướng Kỹ sư AI tương thích tốt với nhóm I và điểm Toán.",
      reasons_fit: [{ title: "Sở thích", detail: "Nhóm I đạt 92%." }],
      reasons_gap: [],
      better_majors: [
        {
          major_code: "7480107",
          major_name: "Trí tuệ nhân tạo",
          reason: "Chuyên sâu trực tiếp vào hệ thống thông minh.",
        },
      ],
      is_ai_generated: true,
      cached: false,
    },
  })

  assert.ok(html.includes("Trần Minh Anh"))
  assert.ok(html.includes("7480101"))
  assert.ok(html.includes("Khoa học máy tính"))
  assert.ok(html.includes("Lập trình Python"))
  assert.ok(html.includes("Kỹ sư AI"))
  assert.ok(html.includes("Lưu ý minh bạch"))
  assert.equal(/oklch/i.test(html), false)
})

test("buildChatReportHtml dựng biên bản chat đầy đủ và không chứa oklch", () => {
  const html = buildChatReportHtml({
    title: "So sánh CNTT và AI",
    studentName: "Lê Hoàng Nam",
    majorLabel: "Khoa học máy tính (7480101)",
    exportedAt: new Date(2026, 10, 23, 19, 30, 0),
    messages: [
      { role: "user", content: "So sánh ngành CNTT và AI giúp mình" },
      {
        role: "assistant",
        content: "**Khoa học máy tính** rộng hơn về nền tảng, còn **Trí tuệ nhân tạo** tập trung vào học máy.",
        lengthLabel: "Cao",
        sourceLabel: "Dữ liệu hệ thống",
      },
    ],
  })

  assert.ok(html.includes("So sánh CNTT và AI"))
  assert.ok(html.includes("Lê Hoàng Nam"))
  assert.ok(html.includes("Khoa học máy tính (7480101)"))
  assert.ok(html.includes("Suy luận: Cao"))
  assert.ok(html.includes("<strong"))
  assert.equal(/oklch/i.test(html), false)
})
