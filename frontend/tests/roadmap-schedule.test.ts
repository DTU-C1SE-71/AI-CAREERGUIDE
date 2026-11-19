import { test } from "node:test"
import assert from "node:assert/strict"
import { scheduleToWeeks } from "../src/utils/roadmapSchedule.ts"
const result = { major_code: "7480101", personalization_summary: "Mẫu tổng hợp", is_fallback: true,
  schedule: Array.from({ length: 4 }, (_, index) => ({ week_number: index + 1, focus_skill: "Đọc nguồn", recommended_reading: `Chủ đề ${index + 1}`, estimated_hours: 10, tasks: [`Nhiệm vụ ${index + 1}`] })) }
test("hợp đồng schedule giữ nguyên 4 tuần/nhiệm vụ và nhãn mẫu", () => {
  const weeks = scheduleToWeeks(result, "7480101")
  assert.equal(weeks.length, 4)
  assert.deepEqual(weeks.map(week => week.tasks), result.schedule.map(week => week.tasks))
  assert.ok(weeks.every(week => week.eyebrow === "Mẫu khám phá cần đối chiếu"))
})
test("schedule khác ngành/tuần trùng/nhiệm vụ thiếu không bị thay bằng nội dung giả", () => {
  assert.throws(() => scheduleToWeeks(result, "7480103"))
  assert.throws(() => scheduleToWeeks({ ...result, schedule: [result.schedule[0], result.schedule[0]] }, "7480101"))
  assert.throws(() => scheduleToWeeks({ ...result, schedule: [{ ...result.schedule[0], tasks: [] }] }, "7480101"))
})
