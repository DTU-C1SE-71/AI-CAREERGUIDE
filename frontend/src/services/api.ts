import { readStorage } from "./storage"

export const SESSION_INVALID_EVENT = "career-guide:session-invalid"
export const SESSION_CHANGED_EVENT = "career-guide:session-changed"

export class ApiError extends Error {
  status: number
  code: string
  constructor(message: string, status = 0, code = "NETWORK_ERROR") {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
  }
}

export function currentToken() {
  return readStorage<string | null>("career-guide:token", null)
}

export function expireSession(token: string | null, message: string) {
  if (token && token === currentToken()) {
    window.dispatchEvent(new CustomEvent(SESSION_INVALID_EVENT, { detail: { token, message } }))
  }
}

/** Chỉ dùng HTTP thật; không lưu phản hồi quản trị hoặc dữ liệu người khác vào bộ nhớ bền. */
export async function apiFetch(path: string, init: RequestInit = {}, timeoutMs = 20000): Promise<Response> {
  const token = currentToken()
  const controller = new AbortController()
  const cancel = () => controller.abort()
  init.signal?.addEventListener("abort", cancel, { once: true })
  if (init.signal?.aborted) controller.abort()
  const timer = window.setTimeout(cancel, timeoutMs)
  const headers = new Headers(init.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  try {
    const response = await fetch(path.startsWith("/api/") ? path : `/api${path}`, {
      ...init, headers, signal: controller.signal, cache: "no-store",
    })
    // Giữ timeout và AbortSignal đến khi nhận đủ body, kể cả máy chủ đã gửi headers.
    const body = await response.arrayBuffer()
    if (currentToken() !== token) throw new DOMException("Phiên đăng nhập đã thay đổi.", "AbortError")
    if (response.status === 401) expireSession(token, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    if (response.status === 403 && token && !path.endsWith("/identity/me")) {
      window.dispatchEvent(new CustomEvent(SESSION_CHANGED_EVENT))
    }
    return new Response([204, 205, 304].includes(response.status) ? null : body, { status: response.status, statusText: response.statusText, headers: response.headers })
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error
    if (error instanceof ApiError) throw error
    throw new ApiError("Không kết nối được máy chủ. Kiểm tra mạng và thử lại.")
  } finally {
    window.clearTimeout(timer)
    init.signal?.removeEventListener("abort", cancel)
  }
}

export async function requestJSON<T>(path: string, init: RequestInit = {}, timeoutMs = 20000): Promise<T> {
  const token = currentToken()
  const response = await apiFetch(path, init, timeoutMs)
  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null)
  if (currentToken() !== token) throw new DOMException("Phiên đăng nhập đã thay đổi.", "AbortError")
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : null
    const message = typeof detail === "string" ? detail
      : detail && typeof detail === "object" && "message" in detail ? String(detail.message)
      : response.status === 422 ? "Dữ liệu chưa hợp lệ. Kiểm tra lại các trường đã nhập."
      : `Không thể hoàn tất yêu cầu (HTTP ${response.status}).`
    const code = detail && typeof detail === "object" && "code" in detail ? String(detail.code) : `HTTP_${response.status}`
    throw new ApiError(message, response.status, code)
  }
  return data as T
}

/** Các màn hình đọc có thể cung cấp trạng thái rỗng; lỗi ghi dùng requestJSON để hiển thị đúng. */
export async function apiRequest<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    return await requestJSON<T>(path, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error
    if (path.startsWith("/admin/") || path.includes("llm-config") || path.includes("llm-status")) throw error
    return fallback
  }
}

export function authPost<T>(path: string, body: unknown): Promise<T> {
  return requestJSON<T>(path, { method: "POST", body: JSON.stringify(body) })
}

export function authPut<T>(path: string, body: unknown): Promise<T> {
  return requestJSON<T>(path, { method: "PUT", body: JSON.stringify(body) })
}
