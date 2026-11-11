export interface MajorFit {
  interest: number
  academic: number
  cognitive: number
}

export interface TrendSourceItem {
  title: string
  url: string
  source?: string
}

export interface Major {
  id: string
  code: string
  name: string
  category?: string
  university: string
  match: number
  feasibility: "TARGET" | "REACH" | string
  feasibility_label?: string
  best_matching_block?: string
  best_block_score?: number | null
  benchmark_cutoff?: number
  min_recommended?: number
  score_gap?: number
  constraint_passed?: boolean
  constraint_violations?: string[]
  admission_advice?: string
  is_trending?: boolean
  trend_tier?: "TIER_1" | "TIER_2" | "TIER_3" | null
  trend_priority?: number
  trend_label?: string | null
  trend_reason?: string | null
  trend_sources?: TrendSourceItem[]
  fit: MajorFit
  explanation: string
  gaps: string[]
}

export interface FunnelTier1Field {
  field_name: string
  icon?: string
  match: number
  majors_count: number
  eligible_count?: number
  majors: Major[]
}

export interface FunnelRecommendationData {
  tier1_fields: FunnelTier1Field[]
  all_majors?: Major[]
  total_evaluated?: number
  total_eligible?: number
  total_blocked?: number
}
