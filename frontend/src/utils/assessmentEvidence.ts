import type { AcademicScore, AssessmentHistoryItem } from "../types/assessment"

const dimensions = ["R", "I", "A", "S", "E", "C"] as const
const blocks: Array<[string, string[]]> = [
  ["A00", ["Toán", "Vật lý", "Hóa học"]],
  ["A01", ["Toán", "Vật lý", "Tiếng Anh"]],
  ["A02", ["Toán", "Vật lý", "Sinh học"]],
  ["B00", ["Toán", "Hóa học", "Sinh học"]],
  ["B08", ["Toán", "Sinh học", "Tiếng Anh"]],
  ["C00", ["Ngữ văn", "Lịch sử", "Địa lý"]],
  ["C01", ["Ngữ văn", "Toán", "Vật lý"]],
  ["C03", ["Ngữ văn", "Toán", "Lịch sử"]],
  ["C04", ["Ngữ văn", "Toán", "Địa lý"]],
  ["D01", ["Toán", "Ngữ văn", "Tiếng Anh"]],
  ["D07", ["Toán", "Hóa học", "Tiếng Anh"]],
  ["D08", ["Toán", "Sinh học", "Tiếng Anh"]],
  ["D10", ["Toán", "Địa lý", "Tiếng Anh"]],
  ["D14", ["Ngữ văn", "Lịch sử", "Tiếng Anh"]],
  ["D15", ["Ngữ văn", "Địa lý", "Tiếng Anh"]],
]

export const CANONICAL_COGNITIVE_SLOTS: ReadonlyArray<{ code: string; dimension: string }> = [
  { code: "COG_V2_1", dimension: "analytical_1" },
  { code: "COG_V2_2", dimension: "abstract_1" },
  { code: "COG_V2_3", dimension: "spatial_1" },
  { code: "COG_V2_4", dimension: "linguistic_1" },
  { code: "COG_V2_5", dimension: "analytical_2" },
  { code: "COG_V2_6", dimension: "abstract_2" },
  { code: "COG_V2_7", dimension: "spatial_2" },
  { code: "COG_V2_8", dimension: "linguistic_2" },
  { code: "COG_V2_9", dimension: "learning_environment" },
  { code: "COG_V2_10", dimension: "teamwork_intensity" },
]

export const LEGACY_COGNITIVE_SLOTS: ReadonlyArray<{ code: string; dimension: string }> = [
  { code: "COG_1", dimension: "learning_style" },
  { code: "COG_2", dimension: "work_environment" },
  { code: "COG_3", dimension: "problem_solving" },
  { code: "COG_4", dimension: "interaction_target" },
  { code: "COG_5", dimension: "gardner_intelligence" },
  { code: "COG_6", dimension: "pressure_tolerance" },
  { code: "COG_7", dimension: "output_preference" },
  { code: "COG_8", dimension: "team_role" },
]

export interface AssessmentMissingRequirement {
  step: 1 | 2 | 3
  label: string
  detail: string
}

export interface AssessmentCompleteness {
  riasecAnswered: number
  riasecTotal: number
  riasecComplete: boolean
  cognitiveAnswered: number
  cognitiveTotal: number
  cognitiveComplete: boolean
  validSubjectCount: number
  hasInvalidScores: boolean
  completeBlocks: ReturnType<typeof completeTranscriptBlocks>
  scoresComplete: boolean
  isComplete: boolean
  missingSteps: Array<1 | 2 | 3>
  missingItems: AssessmentMissingRequirement[]
}
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

function isValidCognitiveValue(value: unknown): boolean {
  return (typeof value === "string" && value.trim() !== "") || (typeof value === "number" && Number.isFinite(value))
}

export function evaluateAssessmentCompleteness(
  input: {
    answers?: Record<string, number>
    cognitive?: Record<string, string | number>
    scores?: AcademicScore[] | Record<string, number>
  },
  cognitiveSpecs: ReadonlyArray<{ code: string; dimension?: string }> = CANONICAL_COGNITIVE_SLOTS,
): AssessmentCompleteness {
  const answers = input.answers || {}
  const cognitive = input.cognitive || {}
  const riasecTotal = 30

  let riasecAnswered = 0
  dimensions.forEach((code, groupIndex) => {
    for (let index = 0; index < 5; index += 1) {
      if (getValidRiasecAnswer(answers, `${code}${index + 1}`, groupIndex * 5 + index) !== undefined) {
        riasecAnswered += 1
      }
    }
  })
  const riasecComplete = riasecAnswered === riasecTotal

  const hasV2Keys = CANONICAL_COGNITIVE_SLOTS.some(
    (s) => s.code in cognitive || (s.dimension !== "learning_environment" && s.dimension !== "teamwork_intensity" && s.dimension in cognitive),
  )
  const hasLegacyKeys = LEGACY_COGNITIVE_SLOTS.some(
    (s) => s.code in cognitive || s.dimension in cognitive,
  )
  const effectiveCognitiveSpecs =
    cognitiveSpecs === CANONICAL_COGNITIVE_SLOTS && !hasV2Keys && hasLegacyKeys
      ? LEGACY_COGNITIVE_SLOTS
      : cognitiveSpecs

  const cognitiveTotal = effectiveCognitiveSpecs.length
  let cognitiveAnswered = 0
  effectiveCognitiveSpecs.forEach((spec, idx) => {
    const candidates = [
      cognitive[spec.code],
      spec.dimension ? cognitive[spec.dimension] : undefined,
      cognitive[`2-${idx}`],
    ]
    if (candidates.some(isValidCognitiveValue)) {
      cognitiveAnswered += 1
    }
  })
  const cognitiveComplete = cognitiveTotal > 0 && cognitiveAnswered === cognitiveTotal

  let hasInvalidScores = false
  let validScores: AcademicScore[] = []

  if (Array.isArray(input.scores)) {
    hasInvalidScores = input.scores.some(
      (s) => typeof s.score !== "number" || !Number.isFinite(s.score) || s.score < 0 || s.score > 10,
    )
    validScores = input.scores.filter(
      (s) => Boolean(s.subject) && typeof s.score === "number" && Number.isFinite(s.score) && s.score >= 0 && s.score <= 10,
    )
  } else if (input.scores && typeof input.scores === "object") {
    const entries = Object.entries(input.scores)
    hasInvalidScores = entries.some(
      ([, v]) => typeof v !== "number" || !Number.isFinite(v) || v < 0 || v > 10,
    )
    validScores = entries
      .filter(
        ([subject, v]) => Boolean(subject) && typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 10,
      )
      .map(([subject, score]) => ({ subject, score, zScore: null }))
  }

  const validSubjectCount = new Set(validScores.map((s) => s.subject)).size
  const completeBlocks = completeTranscriptBlocks(validScores)
  const scoresComplete = !hasInvalidScores && completeBlocks.length >= 1

  const missingSteps: Array<1 | 2 | 3> = []
  const missingItems: AssessmentMissingRequirement[] = []

  if (!riasecComplete) {
    missingSteps.push(1)
    missingItems.push({
      step: 1,
      label: "1. Sở thích (RIASEC)",
      detail: `Mới hoàn thành ${riasecAnswered}/${riasecTotal} câu (còn thiếu ${riasecTotal - riasecAnswered} câu).`,
    })
  }

  if (!cognitiveComplete) {
    missingSteps.push(2)
    missingItems.push({
      step: 2,
      label: "2. Tư duy nhận thức",
      detail: `Mới hoàn thành ${cognitiveAnswered}/${cognitiveTotal} câu (còn thiếu ${cognitiveTotal - cognitiveAnswered} câu).`,
    })
  }

  if (hasInvalidScores) {
    missingSteps.push(3)
    missingItems.push({
      step: 3,
      label: "3. Điểm số học tập",
      detail: "Có điểm môn học không hợp lệ (cần nằm trong khoảng 0 đến 10).",
    })
  } else if (completeBlocks.length === 0) {
    missingSteps.push(3)
    missingItems.push({
      step: 3,
      label: "3. Điểm số học tập",
      detail: "Cần nhập đủ ít nhất 1 tổ hợp 3 môn hợp lệ (ví dụ: A00, A01, D01, C00…).",
    })
  }

  return {
    riasecAnswered,
    riasecTotal,
    riasecComplete,
    cognitiveAnswered,
    cognitiveTotal,
    cognitiveComplete,
    validSubjectCount,
    hasInvalidScores,
    completeBlocks,
    scoresComplete,
    isComplete: riasecComplete && cognitiveComplete && scoresComplete,
    missingSteps,
    missingItems,
  }
}
