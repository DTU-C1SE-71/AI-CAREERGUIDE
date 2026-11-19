import { test } from "node:test"
import assert from "node:assert/strict"
import { loadCatalogPages } from "../src/utils/loadCatalogPages.ts"
const row = (index: number) => ({ major_code: String(7000000 + index), name: `Ngành ${index}` })

test("tải đủ hơn 1000 ngành qua offset, tổng không dừng ở trang đầu", async () => {
  const data = Array.from({ length: 1201 }, (_, index) => row(index))
  const calls: number[] = []
  const actual = await loadCatalogPages(async (limit, offset) => { calls.push(offset); return data.slice(offset, offset + limit) })
  assert.equal(actual.length, 1201)
  assert.deepEqual(calls, [0, 500, 1000])
  assert.deepEqual(actual.at(-1), row(1200))
})
test("danh mục rỗng trả 0 thật, lỗi trang sau không trả danh mục một phần", async () => {
  assert.deepEqual(await loadCatalogPages(async () => []), [])
  await assert.rejects(loadCatalogPages(async (_, offset) => {
    if (offset) throw new Error("offline")
    return Array.from({ length: 500 }, (_, index) => row(index))
  }), /offline/)
})
test("hủy tải không tiếp tục sang trang sau", async () => {
  const controller = new AbortController()
  let calls = 0
  await assert.rejects(loadCatalogPages(async () => { calls += 1; controller.abort(); return [] }, controller.signal), { name: "AbortError" })
  assert.equal(calls, 1)
})
test("mã lặp hoặc quá giới hạn hiển thị lỗi, không báo tổng hoàn chỉnh", async () => {
  await assert.rejects(loadCatalogPages(async () => [row(0), row(0)]), /mã trùng/)
  await assert.rejects(loadCatalogPages(async (limit, offset) => Array.from({ length: limit }, (_, index) => row(offset + index))), /10.000/)
})
