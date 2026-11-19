import type { GuidancePersonalization, RoadmapWeek } from "../types/roadmap"

/** Hiển thị nguyên lịch tuần từ Backend, không tự thêm nhiệm vụ khi thiếu dữ liệu. */
export function scheduleToWeeks(result: GuidancePersonalization, majorCode: string): RoadmapWeek[] {
  if (result.major_code !== majorCode || !Array.isArray(result.schedule) || !result.schedule.length || result.schedule.length > 4) {
    throw new Error("Lịch cá nhân hóa không khớp ngành hoặc chưa có dữ liệu hợp lệ.")
  }
  const seen = new Set<number>()
  return result.schedule.map(item => {
    if (!Number.isInteger(item.week_number) || item.week_number < 1 || item.week_number > 4 || seen.has(item.week_number) ||
        typeof item.focus_skill !== "string" || typeof item.recommended_reading !== "string" || !Number.isFinite(item.estimated_hours) ||
        !Array.isArray(item.tasks) || !item.tasks.length || item.tasks.some(task => typeof task !== "string" || !task.trim())) {
      throw new Error("Lịch tuần từ máy chủ chưa hợp lệ. Lộ trình hiện tại được giữ nguyên.")
    }
    seen.add(item.week_number)
    return { id: `week-${item.week_number}`, week: item.week_number,
      eyebrow: result.is_fallback ? "Mẫu khám phá cần đối chiếu" : "Lịch theo hồ sơ",
      title: item.recommended_reading || item.focus_skill,
      description: `${item.focus_skill} · ${item.estimated_hours} giờ/tuần`,
      content: `## ${item.recommended_reading || item.focus_skill}\n\n${item.focus_skill}\n\n${item.tasks.map(task => `- ${task}`).join("\n")}`,
      tasks: [...item.tasks] }
  })
}
