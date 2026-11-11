import type { AssessmentState } from "../types/assessment"

/**
 * Chuẩn hóa dữ liệu bài làm từ AssessmentContext thành payload gửi cho Backend `/recommender/evaluate`.
 */
export function buildEvaluateProfilePayload(
  assessment: Pick<
    AssessmentState,
    "answers" | "cognitive" | "scores" | "aspiration"
  >,
  topK = 435,
) {
  const riasecAnswers: Record<string, number> = {}
  Object.entries(assessment.answers || {}).forEach(([key, val]) => {
    if (/^[RIASEC]\d+$/i.test(key) && typeof val === "number") {
      riasecAnswers[key.toUpperCase()] = val
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
    top_k: topK,
  }
}
