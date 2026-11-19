export interface RoadmapWeek {
  id: string
  week: number
  title: string
  eyebrow: string
  description: string
  content: string
  tasks: string[]
}

export interface GuidancePersonalization {
  major_code: string
  personalization_summary: string
  schedule: Array<{ week_number: number; focus_skill: string; tasks: string[]; recommended_reading: string; estimated_hours: number }>
  is_fallback: boolean
}
export interface SavedRoadmapProgress {
  major_code: string
  completed_milestones: number[]
  personalized_schedule: { completed_tasks?: string[]; guidance?: GuidancePersonalization } | null
}
