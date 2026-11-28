import { test } from "node:test"
import assert from "node:assert/strict"
import {
  CANONICAL_COGNITIVE_SLOTS,
  LEGACY_COGNITIVE_SLOTS,
  completeTranscriptBlocks,
  evaluateAssessmentCompleteness,
  getValidRiasecAnswer,
  summarizeAssessmentAttempt,
} from "../src/utils/assessmentEvidence.ts"

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

const fullCognitiveByCode = () =>
  Object.fromEntries(CANONICAL_COGNITIVE_SLOTS.map((slot) => [slot.code, "A"]))

const blockA00Scores = { "Toán": 8, "Vật lý": 7.5, "Hóa học": 7 }

test("hồ sơ rỗng bị chặn phân tích và báo thiếu cả 3 phần", () => {
  const res = evaluateAssessmentCompleteness({ answers: {}, cognitive: {}, scores: {} })
  assert.equal(res.isComplete, false)
  assert.deepEqual(res.missingSteps, [1, 2, 3])
  assert.equal(res.missingItems.length, 3)
})

test("thiếu 1 câu RIASEC (29/30) vẫn bị chặn phân tích dù đủ Tư duy và Điểm", () => {
  const answers = complete(4)
  delete answers.C5
  const res = evaluateAssessmentCompleteness({
    answers,
    cognitive: fullCognitiveByCode(),
    scores: blockA00Scores,
  })
  assert.equal(res.riasecAnswered, 29)
  assert.equal(res.riasecComplete, false)
  assert.equal(res.isComplete, false)
  assert.deepEqual(res.missingSteps, [1])
})

test("thiếu 1 câu Tư duy (9/10) bị chặn phân tích dù đủ RIASEC và Điểm", () => {
  const cognitive = fullCognitiveByCode()
  delete cognitive.COG_V2_10
  const res = evaluateAssessmentCompleteness({
    answers: complete(4),
    cognitive,
    scores: blockA00Scores,
  })
  assert.equal(res.cognitiveAnswered, 9)
  assert.equal(res.cognitiveComplete, false)
  assert.equal(res.isComplete, false)
  assert.deepEqual(res.missingSteps, [2])
})

test("nhập 2 môn chưa đủ tổ hợp 3 môn bị chặn phân tích ở bước Điểm số", () => {
  const res = evaluateAssessmentCompleteness({
    answers: complete(4),
    cognitive: fullCognitiveByCode(),
    scores: { "Toán": 8, "Vật lý": 8 },
  })
  assert.equal(res.completeBlocks.length, 0)
  assert.equal(res.scoresComplete, false)
  assert.equal(res.isComplete, false)
  assert.deepEqual(res.missingSteps, [3])
})

test("có điểm ngoài khoảng 0-10 bị chặn dù đã đủ 1 tổ hợp hợp lệ", () => {
  const res = evaluateAssessmentCompleteness({
    answers: complete(4),
    cognitive: fullCognitiveByCode(),
    scores: { ...blockA00Scores, "Tiếng Anh": 11 },
  })
  assert.equal(res.hasInvalidScores, true)
  assert.equal(res.scoresComplete, false)
  assert.equal(res.isComplete, false)
  assert.deepEqual(res.missingSteps, [3])
})

test("hỗ trợ tương thích ngược hồ sơ Tư duy cũ 8 câu (COG_1..COG_8)", () => {
  const legacyCognitive = Object.fromEntries(
    LEGACY_COGNITIVE_SLOTS.map((slot) => [slot.code, "A"]),
  )
  const res = evaluateAssessmentCompleteness({
    answers: complete(4),
    cognitive: legacyCognitive,
    scores: blockA00Scores,
  })
  assert.equal(res.cognitiveTotal, 8)
  assert.equal(res.cognitiveAnswered, 8)
  assert.equal(res.isComplete, true)
})

test("đủ 30 câu RIASEC, 10 câu Tư duy theo nhiều dạng khóa và 1 tổ hợp hợp lệ (C03/D01) cho phép phân tích", () => {
  const cognitiveByIndex = Object.fromEntries(
    CANONICAL_COGNITIVE_SLOTS.map((_, idx) => [`2-${idx}`, "B"]),
  )
  const cognitiveByDim = Object.fromEntries(
    CANONICAL_COGNITIVE_SLOTS.map((slot) => [slot.dimension, "C"]),
  )
  for (const cog of [fullCognitiveByCode(), cognitiveByIndex, cognitiveByDim]) {
    const resC03 = evaluateAssessmentCompleteness({
      answers: complete(4),
      cognitive: cog,
      scores: [
        { subject: "Ngữ văn", score: 8, zScore: null },
        { subject: "Toán", score: 8.5, zScore: null },
        { subject: "Lịch sử", score: 7.5, zScore: null },
      ],
    })
    assert.equal(resC03.isComplete, true)
    assert.deepEqual(resC03.missingSteps, [])
    assert.deepEqual(resC03.missingItems, [])
    assert.equal(resC03.completeBlocks[0].code, "C03")
  }
})
