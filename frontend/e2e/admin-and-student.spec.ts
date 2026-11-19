import path from "node:path"
import os from "node:os"
import { test, expect, type Page } from "@playwright/test"
const adminEmail = "admin-audit@example.com"
const studentEmail = "student-audit@example.com"
const password = "synthetic-audit-only-password"
const syntheticKey = "sk-synth-test-only-ui-00001234"
const provider = process.env.E2E_PROVIDER_URL || "http://127.0.0.1:18081/v1"

async function login(page: Page, email = adminEmail) {
  await page.goto("/login")
  await page.locator('input[type="email"]').fill(email)
  await page.locator('input[type="password"]').fill(password)
  await page.locator('form button[type="submit"]').click()
  await expect(page).toHaveURL(email === adminEmail ? /\/admin\/governance$/ : /\/dashboard$/)
}
async function openConfig(page: Page) {
  await page.getByRole("link", { name: "Cấu hình AI & API", exact: true }).click()
  await expect(page.getByTestId("persisted-revision")).toBeVisible()
  await expect(page.getByRole("combobox", { name: "Nguồn cấu hình", exact: true })).toBeEnabled()
}
async function draft(page: Page, model: string, key = syntheticKey) {
  await page.getByRole("combobox", { name: "Nguồn cấu hình", exact: true }).selectOption("DATABASE")
  await page.getByRole("textbox", { name: /^Base URL/ }).fill(provider)
  await page.getByLabel("Model", { exact: true }).fill(model)
  await page.getByRole("combobox", { name: "Cách xác thực", exact: true }).selectOption("BEARER")
  await page.getByRole("radio", { name: "Thay key mới", exact: true }).check()
  await page.locator("#ai-new-key").fill(key)
}
async function apply(page: Page) {
  const saved = page.waitForResponse(response => response.url().endsWith("/admin/ai-config") && response.request().method() === "PUT")
  await page.getByRole("button", { name: "Lưu & áp dụng", exact: true }).click()
  expect((await saved).status()).toBe(200)
  await expect(page.getByRole("status").filter({ hasText: "Đã lưu và áp dụng" })).toBeVisible()
}

test("core: admin applies encrypted synthetic credential, reloads, reveals temporarily and clears", async ({ page }) => {
  const errors: string[] = []
  page.on("pageerror", error => errors.push(error.message))
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()) })
  await login(page); await openConfig(page)
  await draft(page, "synth-ui-save")
  await apply(page)
  await page.reload()
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("synth-ui-save")
  await page.getByRole("radio", { name: "Thay key mới", exact: true }).check()
  await expect(page.locator("#ai-new-key")).toHaveValue("")
  const stored = await page.evaluate(() => Object.values(localStorage).join(" "))
  expect(stored).not.toContain(syntheticKey)
  await page.getByRole("button", { name: "Hiện key trong 15 giây", exact: true }).click()
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveText(syntheticKey)
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveCount(0, { timeout: 18000 })
  await page.getByRole("radio", { name: "Xóa key", exact: true }).check()
  await apply(page)
  await page.reload()
  await expect(page.getByText("Credential: Đã xóa", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Test Active", exact: true }).click()
  await expect(page.getByText(/UNCONFIGURED_CREDENTIAL/)).toBeVisible()
  expect(errors).toEqual([])
})

test("core: two admin tabs invalidate stale draft after another tab applies", async ({ page, context }) => {
  await login(page); await openConfig(page)
  const second = await context.newPage()
  await second.goto("/admin/ai-settings")
  await expect(second.getByLabel("Model", { exact: true })).toBeEnabled()
  await second.getByLabel("Model", { exact: true }).fill("synth-stale-tab")
  await draft(page, "synth-two-tabs")
  await apply(page)
  await expect(second.getByRole("alert").filter({ hasText: "Cấu hình nền đã thay đổi" })).toBeVisible()
  await expect(second.getByRole("button", { name: "Lưu & áp dụng", exact: true })).toBeDisabled()
  await second.getByRole("button", { name: "Tải cấu hình mới", exact: true }).click()
  await expect(second.getByLabel("Model", { exact: true })).toHaveValue("synth-two-tabs")
  await second.close()
})

test("core: admin navigation, catalog search, keyboard and 375px layout", async ({ page }) => {
  await login(page)
  await expect(page.getByText(/Chưa có dữ liệu chờ kiểm duyệt/)).toBeVisible()
  await page.getByRole("link", { name: "Danh mục ngành", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Danh mục ngành", exact: true })).toBeVisible()
  await expect(page.locator("input[type=file]")).toHaveCount(0)
  const importNavigation = page.getByRole("navigation", { name: "Điều hướng quản trị" }).getByRole("link", { name: "Nhập danh mục", exact: true })
  await expect(importNavigation).toBeVisible()
  await importNavigation.click()
  await expect(page.getByRole("heading", { name: "Nhập danh mục", exact: true })).toBeVisible()
  await expect(page.getByLabel("Tệp dữ liệu", { exact: true })).toBeVisible()
  await expect(page.getByRole("link", { name: "Tải mẫu Excel", exact: true })).toBeVisible()
  await expect(page.getByLabel("Tìm ngành theo mã, tên hoặc khối thi")).toHaveCount(0)
  await expect(page.getByRole("link", { name: "Xem danh mục đã lưu", exact: true })).toBeVisible()
  await page.getByRole("link", { name: "Xem danh mục đã lưu", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Danh mục ngành", exact: true })).toBeVisible()
  await expect(page.locator("tbody tr")).toHaveCount(50)
  await page.getByRole("button", { name: "Trang sau", exact: true }).click()
  await expect(page.locator("tbody tr").first().locator("td").first()).toHaveText("51")
  await page.getByLabel("Tìm ngành theo mã, tên hoặc khối thi").fill("7480101")
  await expect(page.locator("tbody tr").filter({ hasText: "7480101" })).toBeVisible()
  await page.getByLabel("Tìm ngành theo mã, tên hoặc khối thi").fill("khong-co-nganh-synthetic")
  await expect(page.getByText("Không có ngành nào khớp bộ lọc hiện tại.", { exact: true })).toBeVisible()
  await page.getByRole("link", { name: "Cấu hình AI & API", exact: true }).click()
  await page.setViewportSize({ width: 375, height: 812 })
  await expect(page.getByRole("heading", { name: "Cấu hình AI & API", exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.keyboard.press("Tab")
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY")
  await page.screenshot({ path: process.env.E2E_MOBILE_SCREENSHOT || path.join(os.tmpdir(), "careerguide-admin-mobile.png"), fullPage: true })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.screenshot({ path: process.env.E2E_DESKTOP_SCREENSHOT || path.join(os.tmpdir(), "careerguide-admin-desktop.png"), fullPage: true })
})

test("core: student completes real assessment with blank scores retained as missing", async ({ page }) => {
  await login(page, studentEmail)
  await page.goto("/assessment?new=true")
  await page.getByRole("button", { name: "Danh sách", exact: true }).click()
  for (const code of "RIASEC") {
    for (let number = 1; number <= 5; number++) {
      const row = page.getByTestId(`riasec-${code}${number}`)
      await row.getByRole("button", { name: code === "I" ? /Rất thích/ : /Phân vân/ }).click()
    }
  }
  await page.getByRole("button", { name: "Tiếp tục", exact: true }).click()
  for (let index = 0; index < 8; index++) {
    const option = page.locator('[data-testid^="cognitive-"]').first()
    const prior = await option.getAttribute("data-testid")
    await option.click()
    if (index < 7) await expect(page.locator('[data-testid^="cognitive-"]').first()).not.toHaveAttribute("data-testid", prior!)
  }
  await page.getByRole("button", { name: "Tiếp tục", exact: true }).click()
  await expect(page.getByLabel("Điểm môn Toán", { exact: true })).toHaveValue("")
  await page.getByLabel("Điểm môn Toán", { exact: true }).fill("8.125")
  await page.getByLabel("Điểm môn Toán", { exact: true }).fill("")
  await page.getByRole("button", { name: "Tiếp tục: Nguyện vọng", exact: true }).click()
  const submitted = page.waitForResponse(response => response.url().endsWith("/assessment/submit") && response.request().method() === "POST")
  await page.getByRole("button", { name: "Bỏ qua & Xem kết quả", exact: true }).click()
  const response = await submitted
  expect(response.status()).toBe(200)
  const body = response.request().postDataJSON()
  expect(Object.keys(body.riasec_answers)).toHaveLength(30)
  expect(body.grades_by_subject).toEqual({})
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.reload()
  await expect(page.getByText(/Hồ sơ Định hướng/)).toBeVisible()
  await page.goto("/roadmap?major=7480101")
  const personalize = page.getByRole("button", { name: "Cá nhân hóa theo hồ sơ", exact: true })
  await expect(personalize).toBeEnabled()
  const personalizedResponse = page.waitForResponse(response => response.url().includes("/roadmap/roadmaps/7480101/personalized") && response.request().method() === "POST")
  await personalize.click()
  const actualSchedule = await personalizedResponse
  expect(actualSchedule.status()).toBe(200)
  const schedule = await actualSchedule.json()
  expect(schedule.schedule).toHaveLength(4)
  await expect(page.getByTestId("roadmap-provenance")).toContainText(schedule.personalization_summary)
  for (const week of schedule.schedule) {
    for (let index = 0; index < week.tasks.length; index++) {
      await expect(page.getByTestId(`roadmap-task-week-${week.week_number}-${index}`).first()).toContainText(week.tasks[index])
    }
  }
  const firstTask = page.getByTestId("roadmap-task-week-1-0").first()
  await firstTask.getByRole("button", { name: "Đánh dấu hoàn thành", exact: true }).click()
  const savedProgress = page.waitForResponse(response => response.url().endsWith("/roadmap/progress") && response.request().method() === "POST")
  await page.getByRole("button", { name: "Lưu tiến độ", exact: true }).click()
  expect((await savedProgress).status()).toBe(200)
  await page.evaluate(() => { for (const key of Object.keys(localStorage)) if (key.startsWith("career-guide:roadmap:")) localStorage.removeItem(key) })
  await page.reload()
  await expect(page.getByTestId("roadmap-provenance")).toContainText(schedule.personalization_summary)
  await expect(page.getByTestId("roadmap-task-week-1-0").first().getByRole("button", { name: "Đánh dấu chưa hoàn thành", exact: true })).toBeVisible()

})

test("UI controlled network: login failure never creates fake account or stores password", async ({ page }) => {
  await page.route("**/api/identity/login", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: { code: "DB_UNAVAILABLE", message: "Kết nối thử nghiệm đang gián đoạn." } }) }))
  await page.goto("/login")
  await page.locator('input[type="email"]').fill(adminEmail)
  await page.locator('input[type="password"]').fill(password)
  await page.locator('form button[type="submit"]').click()
  await expect(page.getByRole("alert")).toContainText("gián đoạn")
  expect(await page.evaluate(() => localStorage.getItem("career-guide:token"))).toBeNull()
  expect(await page.evaluate(() => Object.values(localStorage).join(" "))).not.toContain(password)
})

test("UI controlled network: late probe cannot certify an edited draft", async ({ page }) => {
  await login(page); await openConfig(page); await draft(page, "synth-late-probe")
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let observed!: () => void
  const started = new Promise<void>(resolve => { observed = resolve })
  await page.route("**/api/v1/admin/ai-config/probe", async route => {
    const response = await route.fetch()
    observed()
    await gate
    await route.fulfill({ response }).catch(() => {})
  })
  await page.getByRole("button", { name: "Test Draft", exact: true }).click()
  await started
  await page.getByLabel("Model", { exact: true }).fill("synth-edited-after-probe")
  release()
  await expect(page.getByRole("button", { name: "Test Draft", exact: true })).toBeEnabled()
  await expect(page.getByText("Kết nối thành công", { exact: true })).toHaveCount(0)
})


test("core: reveal disappears on navigation, back restores blank replacement and logout clears second tab", async ({ page, context }) => {
  await login(page); await openConfig(page); await draft(page, "synth-navigation")
  await apply(page)
  await page.getByRole("button", { name: "Hiện key trong 15 giây", exact: true }).click()
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveText(syntheticKey)
  await page.getByRole("link", { name: "Kiểm duyệt dữ liệu", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Kiểm duyệt dữ liệu", exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole("heading", { name: "Cấu hình AI & API", exact: true })).toBeVisible()
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveCount(0)
  const other = await context.newPage(); await other.goto("/admin/ai-settings")
  await expect(other.getByTestId("persisted-revision")).toBeVisible()
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).filter({ visible: true }).click()
  await expect(other).toHaveURL(/\/login$/)
  expect(await other.evaluate(() => localStorage.getItem("career-guide:token"))).toBeNull()
})

test("UI controlled network: 401 clears displayed credential and redirects to login", async ({ page }) => {
  await login(page); await openConfig(page); await draft(page, "synth-expiry")
  await apply(page)
  await page.getByRole("button", { name: "Hiện key trong 15 giây", exact: true }).click()
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveText(syntheticKey)
  await page.route("**/api/v1/admin/ai-config", route => route.request().method() === "GET" ? route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: { code: "EXPIRED", message: "Phiên đã hết hạn." } }) }) : route.continue())
  await page.getByRole("button", { name: "Tải lại trạng thái", exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByLabel("Credential đang hiển thị")).toHaveCount(0)
  expect(await page.evaluate(() => Object.values(localStorage).join(" "))).not.toContain(syntheticKey)
})


test("UI: quick model selection edits only draft and preserves the active profile", async ({ page }) => {
  await login(page)
  await openConfig(page)
  await page.getByRole("combobox", { name: "Nguồn cấu hình", exact: true }).selectOption("DATABASE")
  const endpointBefore = await page.getByRole("textbox", { name: /^Base URL/ }).inputValue()
  const runtimeBefore = await page.getByTestId("runtime-revision").textContent()
  const requests: string[] = []
  const observe = (request: import("@playwright/test").Request) => {
    if (request.url().includes("/admin/ai-config") && request.method() !== "GET") requests.push(request.method())
  }
  page.on("request", observe)
  await page.getByRole("button", { name: "Chọn 6.1 Sol", exact: true }).click()
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("gpt-6.1-sol")
  await expect(page.getByRole("button", { name: "Chọn 6.1 Sol", exact: true })).toHaveAttribute("aria-pressed", "true")
  await page.getByRole("button", { name: "Chọn 6 Astra", exact: true }).click()
  await expect(page.getByLabel("Model", { exact: true })).toHaveValue("gpt-6-astra")
  await expect(page.getByRole("textbox", { name: /^Base URL/ })).toHaveValue(endpointBefore)
  await expect(page.getByTestId("runtime-revision")).toHaveText(runtimeBefore!)
  await expect(page.getByRole("radio", { name: "Giữ key hiện tại", exact: true })).toBeChecked()
  await page.getByRole("button", { name: "Hủy bản nháp", exact: true }).click()
  expect(requests).toEqual([])
  page.off("request", observe)
})
