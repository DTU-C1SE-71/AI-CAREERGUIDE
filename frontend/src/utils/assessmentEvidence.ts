import type { AcademicScore, AssessmentHistoryItem } from "../types/assessment"

const dimensions = ["R", "I", "A", "S", "E", "C"] as const
const blocks: Array<[string, string[]]> = [
  ["A00", ["Toán", "Vật lý", "Hóa học"]], ["A01", ["Toán", "Vật lý", "Tiếng Anh"]],
  ["B00", ["Toán", "Hóa học", "Sinh học"]], ["C00", ["Ngữ văn", "Lịch sử", "Địa lý"]],
  ["D01", ["Toán", "Ngữ văn", "Tiếng Anh"]], ["D07", ["Toán", "Hóa học", "Tiếng Anh"]],
  ["D14", ["Ngữ văn", "Lịch sử", "Tiếng Anh"]], ["D15", ["Ngữ văn", "Địa lý", "Tiếng Anh"]],
]
export function getValidRiasecAnswer(answers: Record<string, number>, code: string, index: number): number | undefined {
  const candidates = Object.entries(answers).filter(([key]) => key.toUpperCase() === code || key === `1-${index}`).map(([, value]) => value)
  if (!candidates.length || candidates.some(value => value !== candidates[0])) return undefined
  const value = candidates[0]
  return typeof value === "number" && Number.isInteger(value) && value >= 1 && value <= 5 ? value : undefined
}
export function completeTranscriptBlocks(scores: AcademicScore[]) {
  const bySubject = new Map<string, number>()
  const conflicts = new Set<string>()
  for (const item of scores) {
    if (bySubject.has(item.subject) && bySubject.get(item.subject) !== item.score) conflicts.add(item.subject)
    if (typeof item.score === "number" && Number.isFinite(item.score) && item.score >= 0 && item.score <= 10) bySubject.set(item.subject, item.score)
  }
  return blocks.filter(([, subjects]) => subjects.every(subject => bySubject.has(subject) && !conflicts.has(subject)))
    .map(([code, subjects]) => ({ code, subjects, sum: subjects.reduce((total, subject) => total + bySubject.get(subject)!, 0) }))
    .sort((a, b) => b.sum - a.sum)
}

/** Lịch sử chỉ tóm tắt bằng chứng đã nhập; điểm phù hợp ngành thuộc kết quả đánh giá Backend. */
export function summarizeAssessmentAttempt(answers: Record<string, number>, cognitive: Record<string, string | number>, scores: AcademicScore[]): Omit<AssessmentHistoryItem, "id" | "createdAt"> {
  const groups = dimensions.map((code, group) => {
    const values = Array.from({ length: 5 }, (_, index) => getValidRiasecAnswer(answers, `${code}${index + 1}`, group * 5 + index))
      .filter((value): value is number => value !== undefined)
    return { code, count: values.length, mean: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null }
  })
  const complete = groups.every(group => group.count === 5)
  const distinct = complete && new Set(groups.map(group => group.mean)).size > 1
  const sorted = distinct ? [...groups].sort((a, b) => b.mean! - a.mean!) : []
  const threshold = sorted[2]?.mean ?? Number.POSITIVE_INFINITY
  const top = sorted.filter(group => group.mean !== null && group.mean >= threshold)
  return {
    hollandCode: top.map(group => group.code).join(" · "),
    archetype: !complete ? "Hồ sơ sở thích chưa đầy đủ" : distinct ? "Sở thích tự khai" : "Sở thích chưa phân hóa",
    topField: "", topMajorName: "Hồ sơ đã lưu", topMajorCode: "", topMatchScore: null,
    bestBlock: completeTranscriptBlocks(scores)[0]?.code || "Chưa đủ tổ hợp môn",
    answers: { ...answers }, cognitive: { ...cognitive }, scores: scores.map(score => ({ ...score })),
  }
}
