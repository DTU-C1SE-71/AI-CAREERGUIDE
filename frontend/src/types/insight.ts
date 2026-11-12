export interface TrainingContent {
  overview: string
  core_knowledge: string[]
  practical_skills: string[]
  curriculum_highlights: string[]
  study_duration?: string | null
}

export interface CareerPosition {
  title: string
  description?: string | null
  career_level?: string | null
}

export interface MajorInsight {
  major_code: string
  major_name: string
  training_content: TrainingContent
  career_positions: CareerPosition[]
  subject_blocks: string[]
  is_ai_generated: boolean
  cached: boolean
  generated_at?: string | null
}

export interface InsightPoint {
  title: string
  detail: string
}

export interface SkillGapItem {
  skill: string
  why: string
  how_to_improve: string[]
  priority: "HIGH" | "MEDIUM" | "LOW" | string
}

export interface StudentSkillAnalysis {
  profile_hash: string
  major_code: string
  summary: string
  strengths: InsightPoint[]
  weaknesses: InsightPoint[]
  skill_gaps: SkillGapItem[]
  is_ai_generated: boolean
  cached: boolean
  insight_id?: string | null
}
