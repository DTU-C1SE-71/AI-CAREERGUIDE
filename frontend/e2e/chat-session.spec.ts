import { expect, test } from "@playwright/test"

test("chat probes once per opening and keeps the session through local replies and profile changes", async ({ page }) => {
  let probes = 0
  let messages = 0
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/rag-governance/chat/connection")) {
      probes += 1
      await route.fulfill({ json: { available: true, code: "OK", message: "Đã kết nối", checked_at: new Date().toISOString(), latency_ms: 1, revision_token: "synthetic-chat-session-receipt-000000" } })
    } else if (path.endsWith("/rag-governance/chat")) {
      messages += 1
      expect(route.request().postDataJSON().connection_revision).toBe("synthetic-chat-session-receipt-000000")
      await route.fulfill({ json: { reply: "Bạn hãy hỏi rõ hơn về hướng nghiệp hoặc học tập.", suggested_followups: [], context_major_code: null, is_ai_generated: false, is_fallback: false, response_source: "verified_guidance", connection_available: false } })
    } else {
      await route.fulfill({ json: {} })
    }
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Mở Cố vấn AI", exact: true }).click()
  await expect(page.getByRole("status").filter({ hasText: "Đang hoạt động" })).toBeVisible()
  expect(probes).toBe(1)

  // Advancing beyond the former five-minute receipt timeout must not lock chat.
  await page.clock.install()
  await page.clock.fastForward(360_000)
  await expect(page.getByLabel("Câu hỏi hướng nghiệp", { exact: true })).toBeEnabled()
  expect(probes).toBe(1)
  await page.getByLabel("Câu hỏi hướng nghiệp", { exact: true }).fill("như có bị dth kh")
  await page.getByRole("button", { name: "Gửi tin nhắn", exact: true }).click()
  await expect(page.getByText("Bạn hãy hỏi rõ hơn về hướng nghiệp hoặc học tập.", { exact: true })).toBeVisible()
  await expect(page.getByLabel("Câu hỏi hướng nghiệp", { exact: true })).toBeEnabled()
  expect(messages).toBe(1)
  expect(probes).toBe(1)

  await page.evaluate(() => {
    const key = "career-guide:assessment:guest"
    const value = JSON.stringify({ step: 1, answers: {}, cognitive: {}, scores: [{ subject: "Toán", score: 8 }], completed: false })
    localStorage.setItem(key, value)
    window.dispatchEvent(new StorageEvent("storage", { key, newValue: value }))
  })
  await expect(page.getByText("Bạn hãy hỏi rõ hơn về hướng nghiệp hoặc học tập.", { exact: true })).toHaveCount(0)
  await expect(page.getByRole("status").filter({ hasText: "Đang hoạt động" })).toBeVisible()
  expect(probes).toBe(1)

  await page.getByRole("button", { name: "Đóng chat", exact: true }).click()
  await page.getByRole("button", { name: "Mở Cố vấn AI", exact: true }).click()
  await page.clock.runFor(50)
  await expect(page.getByRole("status").filter({ hasText: "Đang hoạt động" })).toBeVisible()
  expect(probes).toBe(2)
})

test("chat exposes manual retry without automatically probing after an API failure", async ({ page }) => {
  let probes = 0
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/rag-governance/chat/connection")) {
      probes += 1
      await route.fulfill({ json: { available: true, code: "OK", checked_at: new Date().toISOString(), revision_token: "synthetic-chat-session-receipt-000000" } })
    } else if (path.endsWith("/rag-governance/chat")) {
      await route.fulfill({ status: 409, json: { detail: "Cấu hình đã thay đổi" } })
    } else {
      await route.fulfill({ json: {} })
    }
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Mở Cố vấn AI", exact: true }).click()
  await expect(page.getByLabel("Câu hỏi hướng nghiệp", { exact: true })).toBeEnabled()
  await page.getByLabel("Câu hỏi hướng nghiệp", { exact: true }).fill("Em muốn tìm hiểu nghề lập trình viên")
  await page.getByRole("button", { name: "Gửi tin nhắn", exact: true }).click()
  await expect(page.getByRole("button", { name: "Kiểm tra lại kết nối AI", exact: true })).toBeVisible()
  expect(probes).toBe(1)
  await page.getByRole("button", { name: "Kiểm tra lại kết nối AI", exact: true }).click()
  await expect(page.getByRole("status").filter({ hasText: "Đang hoạt động" })).toBeVisible()
  expect(probes).toBe(2)
})
