import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Cpu,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Globe,
  KeyRound,
  ChevronDown,
  ChevronUp,
  Save,
  ShieldCheck,
} from "lucide-react"
import { apiRequest } from "../../services/api"
import { Badge } from "../common/Badge"
import { Button } from "../common/Button"
import { readStorage } from "../../services/storage"

interface LLMStatusPayload {
  model: string
  base_url: string
  is_key_configured: boolean
  masked_key?: string | null
  embedding_model?: string
  max_tokens?: number
  context_window?: number
}

interface LLMConnectionTestResponse {
  success: boolean
  status_code: number
  latency_ms: number
  model_used: string
  base_url: string
  is_configured: boolean
  message: string
  preview_reply?: string | null
  tested_at: string
}

interface LLMConnectionPanelProps {
  onNotify?: (message: string, isError?: boolean) => void
}

export function LLMConnectionPanel({ onNotify }: LLMConnectionPanelProps) {
  const [status, setStatus] = useState<LLMStatusPayload | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<LLMConnectionTestResponse | null>(null)
  const [showConfigEdit, setShowConfigEdit] = useState(false)

  // Form states for updating config
  const [formModel, setFormModel] = useState("")
  const [formBaseUrl, setFormBaseUrl] = useState("")
  const [formApiKey, setFormApiKey] = useState("")
  const [savingConfig, setSavingConfig] = useState(false)

  const fetchStatus = useCallback(async () => {
    setLoadingStatus(true)
    try {
      const res = await apiRequest<LLMStatusPayload | null>(
        "/rag-governance/llm-status",
        null,
      )
      if (res) {
        setStatus(res)
        setFormModel(res.model)
        setFormBaseUrl(res.base_url)
      }
    } catch (err) {
      console.warn("Could not load LLM status:", err)
    } finally {
      setLoadingStatus(false)
    }
  }, [])

  useEffect(() => {
    void fetchStatus()
  }, [fetchStatus])

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiRequest<LLMConnectionTestResponse | null>(
        "/rag-governance/test-llm-connection",
        null,
        {
          method: "POST",
          body: JSON.stringify({}),
        },
      )
      if (res) {
        setTestResult(res)
        if (res.success) {
          onNotify?.(
            `Kết nối AI thành công! Độ trễ: ${res.latency_ms}ms`,
            false,
          )
        } else {
          onNotify?.(
            res.message || "Kiểm tra kết nối thất bại.",
            true,
          )
        }
      } else {
        throw new Error("Không nhận được phản hồi từ máy chủ kiểm tra.")
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Lỗi kết nối Backend."
      setTestResult({
        success: false,
        status_code: 500,
        latency_ms: 0,
        model_used: status?.model || "gpt-6-luna",
        base_url: status?.base_url || "Default endpoint",
        is_configured: false,
        message: errMsg,
        tested_at: new Date().toISOString(),
      })
      onNotify?.(errMsg, true)
    } finally {
      setTesting(false)
    }
  }

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = readStorage<string | null>("career-guide:token", null)
    if (!token) {
      onNotify?.("Cần đăng nhập tài khoản ADMIN để lưu cấu hình AI.", true)
      return
    }

    setSavingConfig(true)
    try {
      const res = await fetch("/api/rag-governance/update-llm-config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          model: formModel.trim() || undefined,
          base_url: formBaseUrl.trim() || undefined,
          api_key: formApiKey.trim() || undefined,
        }),
      })

      if (!res.ok) {
        const errJson = await res.json().catch(() => null)
        throw new Error(errJson?.detail || `HTTP ${res.status}`)
      }

      const updated: LLMStatusPayload = await res.json()
      setStatus(updated)
      setFormApiKey("")
      setShowConfigEdit(false)
      onNotify?.("Đã cập nhật cấu hình mô hình AI thành công!", false)
      void handleTestConnection()
    } catch (err) {
      onNotify?.(
        err instanceof Error ? err.message : "Cập nhật cấu hình thất bại.",
        true,
      )
    } finally {
      setSavingConfig(false)
    }
  }

  return (
    <div className="glass-card mb-5 overflow-hidden rounded-2xl border border-sky-200/80 bg-white/95 p-4 sm:p-5 shadow-sm sm:rounded-3xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="grid size-9 sm:size-10 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-sm shadow-sky-500/20">
            <Cpu size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold text-slate-900">
                Trạng thái Kết nối AI & API Key
              </h2>
              {status?.is_key_configured ? (
                <Badge tone="emerald">
                  <ShieldCheck size={12} className="mr-1 inline" /> Sẵn sàng
                </Badge>
              ) : (
                <Badge tone="amber">
                  <AlertTriangle size={12} className="mr-1 inline" /> Chưa có Key
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Kiểm tra trực tiếp độ trễ, tính hợp lệ của API Key và khả năng phản hồi của LLM.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={fetchStatus}
            disabled={loadingStatus}
            title="Tải lại trạng thái"
          >
            <RefreshCw size={14} className={loadingStatus ? "animate-spin" : ""} />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={handleTestConnection}
            disabled={testing}
          >
            {testing ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Đang kiểm tra...</span>
              </>
            ) : (
              <>
                <Zap size={14} />
                <span>Kiểm tra kết nối</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Info Grid */}
      <div className="mt-3.5 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        <div className="flex items-center gap-2.5 rounded-xl border border-slate-100 bg-slate-50/60 p-2.5">
          <Cpu size={16} className="text-sky-600 shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-slate-500">Mô hình AI (Model)</div>
            <div className="truncate text-xs font-bold text-slate-800 font-mono">
              {status?.model || "gpt-6-luna"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 rounded-xl border border-slate-100 bg-slate-50/60 p-2.5">
          <Globe size={16} className="text-indigo-600 shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-slate-500">API Endpoint (Base URL)</div>
            <div className="truncate text-xs font-semibold text-slate-800 font-mono">
              {status?.base_url || "https://codex.fosta.app/v1"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 rounded-xl border border-slate-100 bg-slate-50/60 p-2.5">
          <KeyRound size={16} className="text-amber-600 shrink-0" />
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-slate-500">Trạng thái API Key</div>
            <div className="truncate text-xs font-semibold text-slate-800 font-mono">
              {status?.masked_key ? `Đã nạp: ${status.masked_key}` : "Chưa cấu hình"}
            </div>
          </div>
        </div>
      </div>

      {/* Live Test Result Banner */}
      <AnimatePresence>
        {testResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 overflow-hidden"
          >
            <div
              className={`rounded-2xl border p-3.5 text-xs transition ${
                testResult.success
                  ? "border-emerald-200 bg-emerald-50/90 text-emerald-950"
                  : "border-rose-200 bg-rose-50/90 text-rose-950"
              }`}
            >
              <div className="flex items-start gap-2.5">
                {testResult.success ? (
                  <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 font-bold">
                    <span>
                      {testResult.success
                        ? "Kết nối API hoàn toàn bình thường!"
                        : "Lỗi kết nối API"}
                    </span>
                    <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-mono border border-slate-200/60">
                      HTTP {testResult.status_code}
                    </span>
                    {testResult.latency_ms > 0 && (
                      <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-mono border border-slate-200/60 text-sky-700">
                        {testResult.latency_ms.toLocaleString()} ms
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-slate-700 leading-relaxed">
                    {testResult.message}
                  </p>
                  {testResult.preview_reply && (
                    <div className="mt-2 rounded-xl bg-white/70 p-2 font-mono text-[11px] text-slate-600 border border-slate-200/60">
                      <span className="font-bold text-slate-800">Phản hồi mẫu:</span>{" "}
                      {testResult.preview_reply}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle Edit Config Form */}
      <div className="mt-3.5 pt-2 border-t border-slate-100 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setShowConfigEdit((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-sky-600 transition"
        >
          {showConfigEdit ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          <span>{showConfigEdit ? "Đóng cấu hình tùy chỉnh" : "Đổi Model / Endpoint / API Key"}</span>
        </button>
        <span className="text-[11px] text-slate-400">
          Chỉ Quản trị viên (ADMIN) mới có quyền đổi API Key
        </span>
      </div>

      <AnimatePresence>
        {showConfigEdit && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleSaveConfig}
            className="mt-3 overflow-hidden rounded-2xl border border-slate-200/70 bg-slate-50/70 p-3.5 text-xs"
          >
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Tên Mô hình (Model)
                </label>
                <input
                  type="text"
                  value={formModel}
                  onChange={(e) => setFormModel(e.target.value)}
                  placeholder="gpt-6-luna hoặc mistralai/..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-mono text-slate-800 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Base URL Endpoint
                </label>
                <input
                  type="text"
                  value={formBaseUrl}
                  onChange={(e) => setFormBaseUrl(e.target.value)}
                  placeholder="https://codex.fosta.app/v1"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-mono text-slate-800 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 mb-1">
                  API Key mới (Để trống nếu giữ nguyên key hiện tại)
                </label>
                <input
                  type="password"
                  value={formApiKey}
                  onChange={(e) => setFormApiKey(e.target.value)}
                  placeholder="Nhập API Key mới..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-mono text-slate-800 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/15"
                />
              </div>
            </div>

            <div className="mt-3 flex justify-end gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setShowConfigEdit(false)}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                size="sm"
                variant="primary"
                disabled={savingConfig}
              >
                <Save size={14} />
                <span>{savingConfig ? "Đang lưu..." : "Lưu cấu hình"}</span>
              </Button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  )
}
