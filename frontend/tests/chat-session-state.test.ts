import { test } from "node:test"
import assert from "node:assert/strict"
import {
  activeChatStorageKey,
  MAX_PERSISTED_ACTIVE_MESSAGES,
  parsePersistedActiveChat,
  serializePersistedActiveChat,
  type PersistedAdvisorMessage,
} from "../src/utils/chatSessionState.ts"

test("serialize và parse giữ nguyên sessionId, messages, context, effort và activePrompts", () => {
  const raw = serializePersistedActiveChat({
    sessionId: "sess-123",
    context: "7480201",
    effort: "high",
    activePrompts: ["Gợi ý thêm ngành tương tự", "Phân tích khối A00"],
    messages: [
      { id: "m1", role: "user", content: "Tôi hợp ngành nào?" },
      {
        id: "m2",
        role: "assistant",
        content: "Bạn có điểm mạnh nhóm Nghiên cứu.",
        source: "verified_guidance",
        lengthMode: "detailed",
        createdAt: "2026-11-26T00:00:00Z",
      },
    ],
  })
  const parsed = parsePersistedActiveChat(raw)
  assert.ok(parsed)
  assert.equal(parsed.sessionId, "sess-123")
  assert.equal(parsed.context, "7480201")
  assert.equal(parsed.effort, "high")
  assert.deepEqual(parsed.activePrompts, ["Gợi ý thêm ngành tương tự", "Phân tích khối A00"])
  assert.equal(parsed.messages.length, 2)
  assert.equal(parsed.messages[1].lengthMode, "detailed")
})

test("giới hạn tối đa MAX_PERSISTED_ACTIVE_MESSAGES (40) tin nhắn gần nhất", () => {
  const many: PersistedAdvisorMessage[] = Array.from({ length: 55 }, (_, idx) => ({
    id: `m-${idx + 1}`,
    role: idx % 2 === 0 ? "user" : "assistant",
    content: `Tin nhắn ${idx + 1}`,
  }))
  const raw = serializePersistedActiveChat({
    sessionId: null,
    context: "",
    effort: "auto",
    messages: many,
  })
  const parsed = parsePersistedActiveChat(raw)
  assert.ok(parsed)
  assert.equal(parsed.messages.length, MAX_PERSISTED_ACTIVE_MESSAGES)
  assert.equal(parsed.messages[0].id, "m-16")
  assert.equal(parsed.messages[parsed.messages.length - 1].id, "m-55")
})

test("khóa lưu trữ tách biệt theo từng tài khoản đăng nhập", () => {
  const keyA = activeChatStorageKey("u:student-1")
  const keyB = activeChatStorageKey("u:student-2")
  const guest = activeChatStorageKey("guest")
  assert.notEqual(keyA, keyB)
  assert.notEqual(keyA, guest)
})

test("JSON lỗi, null hoặc danh sách tin nhắn rỗng trả về null", () => {
  assert.equal(parsePersistedActiveChat(null), null)
  assert.equal(parsePersistedActiveChat("{invalid"), null)
  assert.equal(
    parsePersistedActiveChat(JSON.stringify({ sessionId: "s1", messages: [] })),
    null,
  )
})
