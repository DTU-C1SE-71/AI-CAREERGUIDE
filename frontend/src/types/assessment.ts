export type RiasecKey = "R" | "I" | "A" | "S" | "E" | "C"

export interface AcademicScore {
  subject: string
  score: number
  zScore: number
}

export interface CareerAspirationInput {
  dreamJob: string
  desiredField?: string
  workValues?: string[]
  preferredEnvironment?: string
  scoreStrategy?: "REALISTIC_SAFE" | "CHALLENGE_TOP" | "FLEXIBLE_PATHWAY"
}

export interface AspirationMajorBrief {
  major_code: string
  major_name: string
  category: string
  overall_match: number
  riasec_fit: number
  academic_fit: number
  cognitive_fit: number
  feasibility_tier: "TARGET" | "REACH"
  feasibility_label: string
  best_matching_block?: string | null
  best_block_score?: number | null
  benchmark_cutoff?: number | null
  score_gap?: number | null
  constraint_passed: boolean
  constraint_violations: string[]
  admission_advice?: string | null
  is_trending?: boolean
  trend_tier?: "TIER_1" | "TIER_2" | "TIER_3" | null
  trend_priority?: number
  trend_label?: string | null
  role_tag: "DREAM" | "SUBSTITUTE" | "BRIDGE" | "TOP_TEST"
}

export interface AspirationAnalysisPayload {
  has_aspiration: boolean
  dream_job: string
  desired_field?: string
  work_values: string[]
  preferred_environment?: string
  score_strategy?: string
  alignment_status:
    | "ALIGNED_AND_ELIGIBLE"
    | "PASSION_MATCH_SCORE_GAP"
    | "TRAIT_DIVERGENCE"
    | "EXPLORATORY_DISCOVERY"
  alignment_label: string
  alignment_score: number
  holland_code: string
  best_block_summary: string
  dream_majors: AspirationMajorBrief[]
  recommended_substitutes: AspirationMajorBrief[]
  bridge_majors: AspirationMajorBrief[]
  agent_verdict: string
  key_takeaways: string[]
  is_llm_enriched?: boolean
}

export interface AssessmentState {
  step: number
  answers: Record<string, number>
  cognitive: Record<string, string | number>
  scores: AcademicScore[]
  aspiration?: CareerAspirationInput
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
  aspiration?: CareerAspirationInput
}
