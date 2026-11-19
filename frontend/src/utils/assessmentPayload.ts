import { getValidRiasecAnswer } from "./assessmentEvidence"
export { getValidRiasecAnswer } from "./assessmentEvidence"
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
  const answers = assessment.answers || {}
  CANONICAL_30_CODES.forEach((code, index) => {
    const value = getValidRiasecAnswer(answers, code, index)
    if (value !== undefined) riasecAnswers[code] = value
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
    : {}

  return {
    riasec_answers: riasecAnswers,
    cognitive_answers: cognitiveAnswers,
    grades_by_subject: gradesBySubject,
    aspiration: aspirationPayload,
    score_context: { kind: "TRANSCRIPT", scale: 10 },
    gender: extraProfile?.gender || undefined,
    grade_level: extraProfile?.grade_level || undefined,
    top_k: topK,
  }
}
