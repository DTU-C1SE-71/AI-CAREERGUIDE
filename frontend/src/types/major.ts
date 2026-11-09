export interface MajorFit {
  interest: number
  academic: number
  cognitive: number
}

export interface Major {
  id: string
  code: string
  name: string
  category?: string
  university: string
  match: number
  feasibility: "TARGET" | "REACH" | string
  fit: MajorFit
  explanation: string
  gaps: string[]
}

export interface FunnelTier1Field {
  field_name: string
  icon?: string
  match: number
  majors_count: number
  majors: Major[]
}

export interface FunnelRecommendationData {
  tier1_fields: FunnelTier1Field[]
  all_majors?: Major[]
}
