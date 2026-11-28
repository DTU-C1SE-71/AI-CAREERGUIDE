import { test } from "node:test"
import assert from "node:assert/strict"
import {
  AI_OFFLINE_CACHE_TTL_MS,
  AI_ONLINE_CACHE_TTL_MS,
  parseCachedAIConnection,
  serializeCachedAIConnection,
} from "../src/utils/aiConnectionCache.ts"

test("trạng thái online còn hạn được khôi phục từ cache mà không cần gọi lại AI", () => {
  const now = 1_700_000_000_000
  const raw = serializeCachedAIConnection(
    { state: "online", revisionToken: "tok-abc-123", checkedAt: "2026-11-26T00:00:00Z" },
    now,
  )
  assert.ok(raw)
  const parsed = parseCachedAIConnection(raw, now + AI_ONLINE_CACHE_TTL_MS - 1_000)
  assert.deepEqual(parsed, {
    state: "online",
    revisionToken: "tok-abc-123",
    checkedAt: "2026-11-26T00:00:00Z",
  })
})

test("trạng thái online hết hạn TTL (>= 10 phút) bị loại để kiểm tra lại", () => {
  const now = 1_700_000_000_000
  const raw = serializeCachedAIConnection(
    { state: "online", revisionToken: "tok-abc-123", checkedAt: "2026-11-26T00:00:00Z" },
    now,
  )
  assert.equal(parseCachedAIConnection(raw, now + AI_ONLINE_CACHE_TTL_MS), null)
})

test("cache online thiếu revisionToken không hợp lệ", () => {
  const now = 1_700_000_000_000
  const raw = JSON.stringify({ state: "online", revisionToken: "", checkedAt: "", cachedAtMs: now })
  assert.equal(parseCachedAIConnection(raw, now + 1000), null)
})

test("trạng thái offline dùng TTL ngắn (60s) rồi mới cho kiểm tra lại", () => {
  const now = 1_700_000_000_000
  const raw = serializeCachedAIConnection(
    { state: "offline", message: "Chưa kết nối" },
    now,
  )
  assert.ok(raw)
  assert.deepEqual(parseCachedAIConnection(raw, now + AI_OFFLINE_CACHE_TTL_MS - 100), {
    state: "offline",
    message: "Chưa kết nối",
  })
  assert.equal(parseCachedAIConnection(raw, now + AI_OFFLINE_CACHE_TTL_MS), null)
})

test("trạng thái checking không được lưu cache và JSON hỏng trả về null", () => {
  assert.equal(serializeCachedAIConnection({ state: "checking" }), null)
  assert.equal(parseCachedAIConnection("{broken-json"), null)
  assert.equal(parseCachedAIConnection(null), null)
})
