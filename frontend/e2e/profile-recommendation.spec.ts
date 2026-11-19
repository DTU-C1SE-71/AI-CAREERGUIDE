// @blast-radius: ui — recommendation context comes from the saved profile.
import { expect, test, type Page } from "@playwright/test"
import os from "node:os"
import path from "node:path"

const email = "profile-banner@example.test"
const userId = "00000000-0000-0000-0000-000000000071"
const major = {
  id: "7480107", code: "7480107", name: "Trí tuệ nhân tạo", category: "Máy tính",
  university: "Chương trình kiểm thử", match: 80, feasibility: "NEED_ACADEMIC_DATA",
  fit: { interest: 80, academic: null, cognitive: null },
  explanation: "Gợi ý khám phá theo dữ liệu kiểm thử.", gaps: [],
}

async function mockProfileDashboard(page: Page, profile: { grade_level?: string; gender?: string }) {
  const requests: Record<string, unknown>[] = []
  const profileWrites: string[] = []
  const user = { id: userId, email, name: "Học sinh kiểm thử", role: "student", grade_level: profile.grade_level, gender: profile.gender }
  await page.addInitScript(({ user, email }) => {
    localStorage.setItem("career-guide:token", JSON.stringify("synthetic.profile.token"))
    localStorage.setItem("career-guide:user", JSON.stringify(user))
    // A stale legacy value must never masquerade as the current profile.
    localStorage.setItem("career-guide:profile:grade_level", "Đã tốt nghiệp cấp 3")
    localStorage.setItem("career-guide:profile:gender", "Khác")
    localStorage.setItem(`career-guide:assessment:${email}`, JSON.stringify({
      step: 4, answers: { R1: 4, I1: 5, A1: 2 }, cognitive: {},
      scores: [{ subject: "Toán", score: 8 }, { subject: "Ngữ văn", score: 7 }],
      completed: true,
    }))
  }, { user, email })
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/identity/me")) {
      await route.fulfill({ json: { ...user, full_name: user.name, role: "STUDENT" } })
    } else if (path.endsWith("/identity/profile")) {
      profileWrites.push(route.request().method())
      await route.fulfill({ json: { ...user, full_name: user.name } })
    } else if (path.endsWith("/recommender/evaluate")) {
      const payload = route.request().postDataJSON()
      requests.push(payload)
      await route.fulfill({ json: {
        gender: profile.gender, grade_level: profile.grade_level,
        weights_applied: { w_riasec: 0.5, w_academic: 0.25, w_preference: 0.25 },
        majors: [major], funnel: { tier1_fields: [{
          field_name: "Máy tính", match: 80, majors_count: 1, majors: [major],
        }], all_majors: [major] },
      } })
    } else if (path.includes("/taxonomy/majors")) {
      await route.fulfill({ json: [] })
    } else {
      await route.fulfill({ json: null })
    }
  })
  await page.goto("/dashboard")
  await expect(page.getByText("Lĩnh vực để tìm hiểu", { exact: true })).toBeVisible()
  return { requests, profileWrites }
}

for (const profile of [
  { grade_level: "Lớp 10", gender: "Nam", grade: /lớp 10/i, genderText: /nam/i },
  { grade_level: "Lớp 12", gender: "Nữ", grade: /lớp 12/i, genderText: /nữ/i },
]) {
  test(`saved profile ${profile.grade_level} ${profile.gender} explains recommendations without editable selectors`, async ({ page }) => {
    const { requests, profileWrites } = await mockProfileDashboard(page, profile)
    expect(requests.length).toBeGreaterThan(0)
    for (const payload of requests) {
      expect(payload.grade_level).toBe(profile.grade_level)
      expect(payload.gender).toBe(profile.gender)
    }
    for (const name of ["Lớp 10", "Lớp 11", "Lớp 12", "Đã tốt nghiệp", "Nam", "Nữ", "Khác"]) {
      await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0)
    }
    const banner = page.getByTestId("profile-recommendation-context")
    await expect(banner).toContainText(profile.grade)
    await expect(banner).toContainText(profile.genderText)
    await expect(banner).toContainText(/vì|do|dựa trên/i)
    await expect(banner).toContainText(/không[^.]*?(giới hạn|loại trừ|quyết định|năng lực)/i)
    expect(profileWrites).toEqual([])
    if (profile.grade_level === "Lớp 10") {
      await banner.screenshot({ path: path.join(os.tmpdir(), "careerguide-profile-banner-desktop.png") })
      await page.setViewportSize({ width: 375, height: 812 })
      await expect(banner).toBeVisible()
      await banner.screenshot({ path: path.join(os.tmpdir(), "careerguide-profile-banner-mobile.png") })
    }
  })
}

test("missing profile details prompt completion instead of inventing a grade or gender", async ({ page }) => {
  const { requests, profileWrites } = await mockProfileDashboard(page, {})
  expect(requests.length).toBeGreaterThan(0)
  for (const payload of requests) {
    expect(payload.grade_level).toBeUndefined()
    expect(payload.gender).toBeUndefined()
  }
  const banner = page.getByTestId("profile-recommendation-context")
  await expect(banner).toContainText(/cập nhật|bổ sung|hoàn thiện/i)
  await expect(banner).toContainText(/hồ sơ/i)
  await expect(banner).not.toContainText(/bạn đang học lớp 12|giới tính nam/i)
  for (const name of ["Lớp 10", "Lớp 11", "Lớp 12", "Nam", "Nữ", "Khác"]) {
    await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0)
  }
  expect(profileWrites).toEqual([])
})
