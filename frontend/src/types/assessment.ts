export type RiasecKey = "R" | "I" | "A" | "S" | "E" | "C"

export interface AcademicScore {
  subject: string
  score: number
  zScore: number
}

export interface AssessmentState {
  step: number
  answers: Record<string, number>
  cognitive: Record<string, string | number>
  scores: AcademicScore[]
  completed: boolean
  completedAt?: string
}

export interface AssessmentHistoryItem {
  id: string
  createdAt: string
  hollandCode: string
  archetype: string
  topField: string
  topMajorName: string
  topMajorCode: string
  topMatchScore: number
  bestBlock: string
  answers: Record<string, number>
  cognitive: Record<string, string | number>
  scores: AcademicScore[]
}
