export type RiasecKey = "R" | "I" | "A" | "S" | "E" | "C"

export interface AcademicScore {
  subject: string
  score: number
  zScore?: number | null
}

export interface CareerAspirationInput {
  dreamJob: string
  desiredField?: string
  workValues?: string[]
  preferredEnvironment?: string
  scoreStrategy?: "REALISTIC_SAFE" | "CHALLENGE_TOP" | "FLEXIBLE_PATHWAY"
}

export interface InterestEvidence {
  status: "COMPLETE" | "NON_DISCRIMINATING" | "PARTIAL" | "MISSING" | "LEGACY_UNVERIFIED"
  groups: Array<{ code: RiasecKey; percent: number | null; answered: number | null; total: number }>
}

export interface AspirationReadiness {
  status: "READY_REFERENCE" | "NEEDS_IMPROVEMENT" | "UNKNOWN"
  reason?: string
  message?: string
  block?: string | null
  block_score?: number | null
  benchmark_cutoff?: number | null
  missing_subjects?: string[]
  violations?: string[]
  gaps?: Array<{ kind: "SUBJECT_SCORE" | "TOTAL_SCORE"; subject?: string; actual?: number; required?: number; delta?: number; amount?: number }>
  reference_kind?: string | null
  reference_method?: string | null
  score_kind?: string | null
  policy_version?: string
}

export interface AspirationMajorBrief {
  readiness?: AspirationReadiness
  relation_reason?: string
  major_code: string
  major_name: string
  category: string
  overall_match: number | null
  riasec_fit: number | null
  academic_fit: number | null
  cognitive_fit: number | null
  feasibility_tier: "TARGET" | "REACH" | "UNKNOWN"
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
  role_tag: "DREAM" | "SUBSTITUTE" | "BRIDGE" | "TOP_TEST" | "CURRENT" | "EXPLORATION"
}

export interface AspirationAnalysisPayload {
  preference_evidence?: { work_values?: { status?: string }; environment?: { status?: string }; meaning?: string }
  match_status?: "EMPTY" | "MATCHED" | "UNRECOGNIZED" | "AMBIGUOUS"
  interest_evidence?: InterestEvidence
  current_options?: AspirationMajorBrief[]
  exploration_options?: AspirationMajorBrief[]
  intent_candidates?: Array<{ id: string; label: string; canonicalDreamJob: string; evidence?: unknown }>
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
    | "NEED_ACADEMIC_DATA"
    | "NO_CURRENT_OPTIONS"
    | "CURRENT_REFERENCE_OPTIONS"
    | "UNRECOGNIZED_ASPIRATION"
    | "AMBIGUOUS_ASPIRATION"
  alignment_label: string
  alignment_score: number | null
  holland_code: string
  best_block_summary: string
  dream_majors: AspirationMajorBrief[]
  recommended_substitutes: AspirationMajorBrief[]
  bridge_majors: AspirationMajorBrief[]
  agent_verdict: string
  key_takeaways: string[]
  is_llm_enriched?: boolean
  has_academic_data?: boolean
  score_basis?: string
}

export interface AssessmentState {
  syncStatus?: "LOCAL_ONLY" | "SYNCED"
  submissionId?: string
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
  topMatchScore: number | null
  bestBlock: string
  answers: Record<string, number>
  cognitive: Record<string, string | number>
  scores: AcademicScore[]
  aspiration?: CareerAspirationInput
}
