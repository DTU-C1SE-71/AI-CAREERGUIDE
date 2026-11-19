// @blast-radius: ui — major browsing is separate from assessment recommendations.
import { expect, test, type Page } from "@playwright/test"
import os from "node:os"
import path from "node:path"

const email = "major-catalog@example.test"
const user = {
  id: "00000000-0000-0000-0000-000000000072",
  email,
  name: "Học sinh kiểm thử",
  role: "student",
}
const computing = "MÁY TÍNH VÀ CÔNG NGHỆ THÔNG TIN"
const business = "KINH DOANH VÀ QUẢN LÝ"
const catalog = [
  { major_code: "7480103", name: "Kỹ thuật phần mềm", category: computing },
  { major_code: "7340201", name: "Tài chính - Ngân hàng", category: business },
  { major_code: "7480101", name: "Khoa học máy tính", category: computing },
  ...Array.from({ length: 8 }, (_, index) => ({
    major_code: `900000${index}`,
    name: `Ngành kiểm thử ${index + 1}`,
    category: business,
  })),
].map(item => ({ ...item, name_vi: item.name, subject_blocks: ["A00", "A01", "D01"] }))

async function mockStudentCatalog(page: Page, failInitially = false, completedAssessment = false) {
  const requests: string[] = []
  let failCatalog = failInitially
  await page.addInitScript(({ user, completedAssessment }) => {
    localStorage.setItem("career-guide:token", JSON.stringify("synthetic.catalog.token"))
    localStorage.setItem("career-guide:user", JSON.stringify(user))
    if (completedAssessment) {
      localStorage.setItem(`career-guide:assessment:${user.email}`, JSON.stringify({
        step: 4,
        answers: { R1: 4, I1: 5, A1: 2 },
        cognitive: {},
        scores: [{ subject: "Toán", score: 8 }, { subject: "Ngữ văn", score: 7 }],
        completed: true,
      }))
    }
  }, { user, completedAssessment })
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname
    requests.push(path)
    if (path.endsWith("/identity/me")) {
      await route.fulfill({ json: { ...user, full_name: user.name, role: "STUDENT" } })
    } else if (path.endsWith("/taxonomy/majors")) {
      await route.fulfill(failCatalog
        ? { status: 503, json: { detail: "Không tải được danh mục thử nghiệm." } }
        : { json: catalog })
    } else {
      await route.fulfill({ json: null })
    }
  })
  return { requests, allowCatalog: () => { failCatalog = false } }
}

test("catalog and recommendations have separate pages and active navigation", async ({ page }) => {
  const { requests } = await mockStudentCatalog(page)
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" })
  await page.goto("/dashboard")
  await expect(page.getByRole("heading", { name: /Làm bài đánh giá để mở khóa/ })).toBeVisible()
  await expect(page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })).toHaveCount(0)
  await expect(navigation.getByRole("link", { name: "Đề xuất ngành học", exact: true })).toHaveAttribute("aria-current", "page")
  await expect(navigation.getByRole("link", { name: "Danh mục ngành", exact: true })).not.toHaveAttribute("aria-current", "page")
  expect(requests.some(path => path.endsWith("/taxonomy/majors"))).toBe(false)

  await navigation.getByRole("link", { name: "Danh mục ngành", exact: true }).click()
  await expect(page).toHaveURL(/\/majors$/)
  await expect(page.getByRole("heading", { name: "Danh mục ngành", exact: true })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Khám phá 11 ngành đào tạo", exact: true })).toBeVisible()
  await expect(navigation.getByRole("link", { name: "Danh mục ngành", exact: true })).toHaveAttribute("aria-current", "page")
  await expect(navigation.getByRole("link", { name: "Đề xuất ngành học", exact: true })).not.toHaveAttribute("aria-current", "page")
  await expect(page.getByRole("heading", { name: /Làm bài đánh giá để mở khóa/ })).toHaveCount(0)
  expect(requests.some(path => path.endsWith("/recommender/evaluate"))).toBe(false)

  await navigation.getByRole("link", { name: "Đề xuất ngành học", exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })).toHaveCount(0)
})

test("major code, name and category filters combine and can be cleared", async ({ page }) => {
  await mockStudentCatalog(page)
  await page.goto("/majors")
  const search = page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })
  const category = page.getByRole("combobox", { name: "Lĩnh vực đào tạo" })
  const cards = page.locator("main a[href^='/majors/']")
  await expect(cards).toHaveCount(9)

  await search.fill("7480103")
  await expect(cards).toHaveCount(1)
  await expect(cards.first()).toContainText("Kỹ thuật phần mềm")
  await search.fill("Tài chính")
  await expect(cards).toHaveCount(1)
  await expect(cards.first()).toContainText("7340201")

  await search.fill("")
  await category.selectOption(computing)
  await expect(cards).toHaveCount(2)
  await search.fill("7480103")
  await expect(cards).toHaveCount(1)
  await category.selectOption(business)
  await expect(cards).toHaveCount(0)
  await expect(page.getByText("Không tìm thấy ngành phù hợp.", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Xóa bộ lọc", exact: true }).click()
  await expect(search).toHaveValue("")
  await expect(category).toHaveValue("ALL")
  await expect(cards).toHaveCount(9)

  await page.getByRole("button", { name: "Xem tất cả 11 ngành", exact: true }).click()
  await expect(cards).toHaveCount(11)
  await page.getByRole("button", { name: "Thu gọn danh sách", exact: true }).click()
  await expect(cards).toHaveCount(9)
})

test("a failed catalog request exposes a working retry", async ({ page }) => {
  const { allowCatalog } = await mockStudentCatalog(page, true)
  await page.goto("/majors")
  await expect(page.getByRole("alert")).toBeVisible()
  await expect(page.locator("main a[href^='/majors/']")).toHaveCount(0)
  allowCatalog()
  await page.getByRole("button", { name: "Thử lại", exact: true }).click()
  await expect(page.getByRole("heading", { name: "Khám phá 11 ngành đào tạo", exact: true })).toBeVisible()
  await expect(page.getByRole("alert")).toHaveCount(0)
  await expect(page.locator("main a[href^='/majors/']")).toHaveCount(9)
})

test("quick search opens the catalog and focuses its search field", async ({ page }) => {
  await mockStudentCatalog(page)
  await page.goto("/dashboard")
  await page.getByRole("button", { name: "Tìm kiếm nhanh", exact: true }).click()
  await expect(page).toHaveURL(/\/majors\?search=1$/)
  const search = page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })
  await expect(search).toBeFocused()
  await page.getByRole("combobox", { name: "Lĩnh vực đào tạo" }).selectOption(computing)
  await page.getByRole("heading", { name: "Danh mục ngành", exact: true }).click()
  await page.getByRole("button", { name: "Tìm kiếm nhanh", exact: true }).click()
  await expect(page).toHaveURL(/\/majors\?search=1$/)
  await expect(search).toBeFocused()
})

test("legacy recommendation search redirects and focuses without loading profile analysis", async ({ page }) => {
  const { requests } = await mockStudentCatalog(page, false, true)
  await page.goto("/dashboard?search=1")
  await expect(page).toHaveURL(/\/majors\?search=1$/)
  await expect(page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })).toBeFocused()
  expect(requests.some(path => path.endsWith("/recommender/evaluate"))).toBe(false)
  expect(requests.some(path => path.endsWith("/major-insights/student-skills"))).toBe(false)
})

test("opening a catalog card offers a return to the catalog", async ({ page }) => {
  await mockStudentCatalog(page)
  await page.goto("/majors")
  await page.locator("main a[href^='/majors/']").filter({ hasText: "Kỹ thuật phần mềm" }).click()
  await expect(page).toHaveURL(/\/majors\/7480103$/)
  await expect(page.getByRole("heading", { name: "Kỹ thuật phần mềm", exact: true })).toBeVisible()
  await page.getByRole("link", { name: "Quay lại danh mục ngành", exact: true }).click()
  await expect(page).toHaveURL(/\/majors$/)
  await expect(page.getByRole("heading", { name: "Khám phá 11 ngành đào tạo", exact: true })).toBeVisible()
})

test("search controls keep visible boundaries and fit desktop, tablet and mobile", async ({ page }) => {
  await mockStudentCatalog(page)
  await page.goto("/majors")
  const search = page.getByRole("searchbox", { name: "Tìm mã hoặc tên ngành" })
  const category = page.getByRole("combobox", { name: "Lĩnh vực đào tạo" })
  await expect(page.locator("main a[href^='/majors/']")).toHaveCount(9)
  for (const width of [1440, 1024, 768, 375]) {
    await page.setViewportSize({ width, height: 900 })
    await expect.poll(() => page.locator("main").locator("..").evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBe(width >= 1024 ? 284 : 0)
    await expect(search).toBeVisible()
    await expect(category).toBeVisible()
    for (const control of [search, category]) {
      const bounds = await control.boundingBox()
      expect(bounds).not.toBeNull()
      expect(bounds!.x).toBeGreaterThanOrEqual(0)
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
      expect(bounds!.height).toBeGreaterThanOrEqual(40)
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    if (width === 1440 || width === 375) {
      await page.screenshot({ path: path.join(os.tmpdir(), `careerguide-major-catalog-${width === 1440 ? "desktop" : "mobile"}.png`), fullPage: true })
    }
  }

  const fieldContrast = await search.evaluate(input => {
    let boundary: Element | null = input
    while (boundary && !(parseFloat(getComputedStyle(boundary).borderTopWidth) > 0)) boundary = boundary.parentElement
    if (!boundary) return 1
    const style = getComputedStyle(boundary)
    const canvas = document.createElement("canvas")
    canvas.width = canvas.height = 1
    const context = canvas.getContext("2d")!
    const luminance = (color: string) => {
      context.clearRect(0, 0, 1, 1)
      context.fillStyle = color
      context.fillRect(0, 0, 1, 1)
      const values = Array.from(context.getImageData(0, 0, 1, 1).data)
      const channels = values.slice(0, 3).map(value => {
        const s = (value * values[3] / 255 + 255 - values[3]) / 255
        return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
    const border = luminance(style.borderTopColor)
    const background = luminance(style.backgroundColor)
    return (Math.max(border, background) + 0.05) / (Math.min(border, background) + 0.05)
  })
  expect(fieldContrast).toBeGreaterThan(1.3)
})
