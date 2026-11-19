import { test } from "node:test"
import assert from "node:assert/strict"
import { completeTranscriptBlocks, getValidRiasecAnswer, summarizeAssessmentAttempt } from "../src/utils/assessmentEvidence.ts"

const complete = (value: number) => Object.fromEntries("RIASEC".split("").flatMap(code => Array.from({ length: 5 }, (_, index) => [`${code}${index + 1}`, value])))
test("hồ sơ rỗng không sinh điểm phù hợp hay ngành giả", () => {
  const summary = summarizeAssessmentAttempt({}, {}, [])
  assert.equal(summary.topMatchScore, null)
  assert.equal(summary.topMajorCode, "")
  assert.equal(summary.hollandCode, "")
  assert.equal(summary.bestBlock, "Chưa đủ tổ hợp môn")
})
test("hồ sơ trung lập đủ 30 câu không gán nhóm trội", () => {
  const summary = summarizeAssessmentAttempt(complete(3), {}, [])
  assert.equal(summary.hollandCode, "")
  assert.equal(summary.archetype, "Sở thích chưa phân hóa")
  assert.equal(summary.topMatchScore, null)
})
test("phản sự thật: đổi nhóm I sang nhóm A làm đổi mã sở thích", () => {
  const answers = complete(2)
  for (let i = 1; i <= 5; i++) answers[`I${i}`] = 5
  assert.ok(summarizeAssessmentAttempt(answers, {}, []).hollandCode.startsWith("I"))
  for (let i = 1; i <= 5; i++) { answers[`I${i}`] = 2; answers[`A${i}`] = 5 }
  assert.ok(summarizeAssessmentAttempt(answers, {}, []).hollandCode.startsWith("A"))
})
test("alias mâu thuẫn hoặc câu trả lời sai kiểu không được âm thầm chọn", () => {
  assert.equal(getValidRiasecAnswer({ R1: 5, "1-0": 1 }, "R1", 0), undefined)
  assert.equal(getValidRiasecAnswer({ R1: 4, r1: 5 }, "R1", 0), undefined)
  assert.equal(getValidRiasecAnswer({ R1: Number.NaN }, "R1", 0), undefined)
  assert.equal(getValidRiasecAnswer({ R1: 4, "1-0": 4 }, "R1", 0), 4)
})
test("đủ ba môn đúng tổ hợp mới tính tổng, giữ độ chính xác sát ngưỡng", () => {
  const scores = [{ subject: "Toán", score: 8.125, zScore: 0 }, { subject: "Vật lý", score: 8.125, zScore: 0 }]
  assert.deepEqual(completeTranscriptBlocks(scores), [])
  const completed = completeTranscriptBlocks([...scores, { subject: "Hóa học", score: 8.125, zScore: 0 }])
  assert.equal(completed[0].sum, 24.375)
  assert.equal(completed[0].code, "A00")
})
test("điểm môn mâu thuẫn không tạo ra tổ hợp hợp lệ", () => {
  const scores = [ ["Toán", 8], ["Toán", 9], ["Vật lý", 8], ["Hóa học", 8] ].map(([subject, score]) => ({ subject: String(subject), score: Number(score), zScore: 0 }))
  assert.deepEqual(completeTranscriptBlocks(scores), [])
})
