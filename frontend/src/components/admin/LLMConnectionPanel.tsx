import { useCallback, useEffect, useRef, useState } from "react"
import { RefreshCw, ShieldCheck } from "lucide-react"
import { requestJSON } from "../../services/api"
import type { AIConfigStatus } from "../../types/aiConfig"

const ENDPOINT = "/v1/admin/ai-config"
const POLL_INTERVAL_MS = 5000

export interface LLMConnectionPanelProps {
  onNotify?: (message: string, error?: boolean) => void
}

export function LLMConnectionPanel(_props: LLMConnectionPanelProps) {
  const [status, setStatus] = useState<AIConfigStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(true)
  const loadRequest = useRef<AbortController | null>(null)

  const loadStatus = useCallback(async (foreground = false) => {
    loadRequest.current?.abort()
    const controller = new AbortController()
    loadRequest.current = controller
    if (foreground) setLoading(true)
    try {
      const next = await requestJSON<AIConfigStatus>(ENDPOINT, { signal: controller.signal })
      if (!mounted.current || controller.signal.aborted) return
      setStatus(next)
      setError(null)
    } catch (err) {
      if (mounted.current && !controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Không tải được thông tin kết nối AI.")
      }
    } finally {
      if (mounted.current && !controller.signal.aborted) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    void loadStatus(true)

    const handleFocus = () => {
      void loadStatus(false)
    }
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void loadStatus(false)
      }
    }
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadStatus(false)
      }
    }, POLL_INTERVAL_MS)

    window.addEventListener("focus", handleFocus)
    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      mounted.current = false
      loadRequest.current?.abort()
      window.clearInterval(timer)
      window.removeEventListener("focus", handleFocus)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [loadStatus])

  return (
    <div className="admin-ai-settings">
      {error && (
        <p role="alert" className="admin-notice is-error">
          {error}
        </p>
      )}
      <section className="admin-panel admin-ai-current" aria-labelledby="ai-current-title">
        <div className="admin-section-heading">
          <h2 id="ai-current-title">
            <span className="admin-section-icon">
              <ShieldCheck size={21} aria-hidden="true" />
            </span>
            Kết nối AI đang sử dụng
          </h2>
          <button
            type="button"
            className="admin-button"
            disabled={loading}
            onClick={() => void loadStatus(true)}
          >
            <RefreshCw size={17} aria-hidden="true" />
            Làm mới
          </button>
        </div>

        {loading && !status ? (
          <p role="status" className="text-sm text-slate-600">
            Đang tải thông tin kết nối AI…
          </p>
        ) : status ? (
          <>
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Base URL
                </dt>
                <dd
                  className="mt-1 break-all font-mono text-sm font-medium text-slate-800"
                  data-testid="active-base-url"
                >
                  {status.active.base_url}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Model
                </dt>
                <dd
                  className="mt-1 break-all font-mono text-sm font-medium text-slate-800"
                  data-testid="active-model"
                >
                  {status.active.model}
                </dd>
              </div>
            </dl>
            <p className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-600">
              Giá trị được đọc trực tiếp từ biến môi trường máy chủ (<code>LLM_BASE_URL</code>,{" "}
              <code>LLM_MODEL</code>) và tự động cập nhật khi cấu hình thay đổi.
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-600">
            Chưa tải được thông tin kết nối AI. Bấm “Làm mới” để thử lại.
          </p>
        )}
      </section>
    </div>
  )
}
