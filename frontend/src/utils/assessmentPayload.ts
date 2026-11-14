import type { AssessmentState } from "../types/assessment"

const CANONICAL_30_CODES: string[] = [
  "R1", "R2", "R3", "R4", "R5",
  "I1", "I2", "I3", "I4", "I5",
  "A1", "A2", "A3", "A4", "A5",
  "S1", "S2", "S3", "S4", "S5",
  "E1", "E2", "E3", "E4", "E5",
  "C1", "C2", "C3", "C4", "C5",
]

/**
 * Chuẩn hóa dữ liệu bài làm từ AssessmentContext thành payload gửi cho Backend `/recommender/evaluate`.
 */
export function buildEvaluateProfilePayload(
  assessment: Pick<
    AssessmentState,
    "answers" | "cognitive" | "scores" | "aspiration"
  >,
  topK = 435,
  extraProfile?: { gender?: string; grade_level?: string },
) {
  const riasecAnswers: Record<string, number> = {}
  Object.entries(assessment.answers || {}).forEach(([key, val]) => {
    if (typeof val === "number") {
      if (/^[RIASEC]\d+$/i.test(key)) {
        riasecAnswers[key.toUpperCase()] = val
      } else if (/^1-(\d+)$/.test(key)) {
        const idx = parseInt(key.split("-")[1], 10)
        if (idx >= 0 && idx < CANONICAL_30_CODES.length) {
          riasecAnswers[CANONICAL_30_CODES[idx]] = val
        }
      }
    }
  })

  const cognitiveAnswers: Record<string, string | number> = {
    ...(assessment.cognitive || {}),
  }

  const gradesBySubject: Record<string, number> = {}
  ;(assessment.scores || []).forEach((s) => {
    if (s.subject && typeof s.score === "number" && Number.isFinite(s.score)) {
      gradesBySubject[s.subject] = s.score
    }
  })

  const asp = assessment.aspiration
  const aspirationPayload = asp
    ? {
        dream_job: asp.dreamJob || "",
        desired_field: asp.desiredField || "",
        work_values: asp.workValues || [],
        preferred_environment: asp.preferredEnvironment || "",
        score_strategy: asp.scoreStrategy || "FLEXIBLE_PATHWAY",
      }
    : undefined

  return {
    riasec_answers:
      Object.keys(riasecAnswers).length > 0 ? riasecAnswers : undefined,
    cognitive_answers:
      Object.keys(cognitiveAnswers).length > 0 ? cognitiveAnswers : undefined,
    grades_by_subject:
      Object.keys(gradesBySubject).length > 0 ? gradesBySubject : undefined,
    aspiration: aspirationPayload,
    gender: extraProfile?.gender || undefined,
    grade_level: extraProfile?.grade_level || undefined,
    top_k: topK,
  }
}
