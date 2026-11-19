import { defineConfig } from "@playwright/test"
import { existsSync } from "node:fs"
import path from "node:path"
import os from "node:os"
const bundledChrome = path.join(os.homedir(), "AppData", "Local", "ms-playwright", "chromium-1248", "chrome-win64", "chrome.exe")
const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:18766"
if (!["127.0.0.1", "localhost"].includes(new URL(baseURL).hostname)) throw new Error("E2E chỉ chạy với máy chủ cục bộ và DB tổng hợp.")
export default defineConfig({
  testDir: "./e2e", workers: 1, fullyParallel: false, retries: 0, timeout: 60000,
  expect: { timeout: 10000 }, reporter: "list",
  outputDir: process.env.E2E_ARTIFACT_DIR || path.join(os.tmpdir(), "careerguide-v9-browser"),
  use: { baseURL, browserName: "chromium", headless: true, viewport: { width: 1440, height: 1000 },
    trace: "off", screenshot: "off", video: "off", reducedMotion: "reduce",
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (existsSync(bundledChrome) ? bundledChrome : undefined) },
  },
})
