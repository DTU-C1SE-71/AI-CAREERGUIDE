import { ModelQuickSelect } from "./ModelQuickSelect"
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import { KeyRound, PencilLine, RefreshCw, Save, ShieldCheck, TestTube2 } from "lucide-react"
import { ApiError, requestJSON, SESSION_INVALID_EVENT, SESSION_CHANGED_EVENT } from "../../services/api"
import type { AIConfigDraft, AIConfigStatus, AIProbeResult, AIProfile } from "../../types/aiConfig"

const endpoint = "/v1/admin/ai-config"
const revisionEvent = "career-guide:ai-revision"
const blankDraft: AIConfigDraft = { source_mode: "DATABASE", protocol: "openai_compatible", base_url: "", model: "", auth_mode: "BEARER", credential_action: "KEEP", api_key: "", base_revision_token: "" }
const credentialLabels = { SET: "Đã cấu hình", CLEARED: "Đã xóa", MISSING: "Chưa cấu hình", LOCKED: "Thiếu khóa giải mã" }
function formFrom(status: AIConfigStatus): AIConfigDraft {
  const { source_mode, protocol, base_url, model, auth_mode } = status.active
  return { source_mode, protocol, base_url, model, auth_mode, credential_action: "KEEP", api_key: "", base_revision_token: status.revision_token }
}
async function digestDraft(draft: AIConfigDraft) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(draft)))
  return Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, "0")).join("")
}
function ProfileDetails({ title, profile }: { title: string; profile: AIProfile | null }) {
  return <div className="admin-profile-block"><h3>{title}</h3>{profile ? <dl className="admin-profile-details">
    <div><dt className="text-slate-600">Nguồn cấu hình</dt><dd>{profile.source_mode === "ENV" ? "ENV / hồ sơ mặc định" : "Cơ sở dữ liệu"}</dd></div>
    <div><dt className="text-slate-600">Model</dt><dd className="break-all font-mono">{profile.model}</dd></div>
    <div><dt className="text-slate-600">Base URL</dt><dd className="break-all font-mono">{profile.base_url}</dd></div>
    <div><dt className="text-slate-600">Giao thức / Xác thực</dt><dd>OpenAI Compatible · {profile.auth_mode === "NONE" ? "Không dùng key" : "Bearer key"}</dd></div>
  </dl> : <p className="mt-3 text-sm text-slate-600">Chưa lưu hồ sơ trong cơ sở dữ liệu. Runtime đang sử dụng hồ sơ mặc định.</p>}</div>
}

export function LLMConnectionPanel({ onNotify }: { onNotify?: (message: string, error?: boolean) => void }) {
  const [status, setStatus] = useState<AIConfigStatus | null>(null)
  const [draft, setDraft] = useState<AIConfigDraft>(blankDraft)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<"draft" | "active" | null>(null)
  const [probe, setProbe] = useState<{ result: AIProbeResult; scope: "draft" | "active"; stale: boolean } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const mounted = useRef(true)
  const generation = useRef(0)
  const draftRef = useRef(draft)
  const statusRef = useRef<AIConfigStatus | null>(null)
  const busy = useRef(false)
  const probing = useRef(false)
  const probeRequest = useRef<AbortController | null>(null)
  const loadRequest = useRef<AbortController | null>(null)
  const errorRef = useRef<HTMLParagraphElement>(null)

  const invalidate = useCallback(() => {
    generation.current += 1
    probeRequest.current?.abort()
    probing.current = false
    setTesting(null)
    setProbe(current => current ? { ...current, stale: true } : null)
  }, [])
  const installStatus = useCallback((next: AIConfigStatus, reset: boolean) => {
    if (!statusRef.current && next.last_probe) setProbe({ result: next.last_probe, scope: "active", stale: true })
    if (statusRef.current?.revision_token !== next.revision_token) invalidate()
    statusRef.current = next
    setStatus(next)
    if (reset) {
      const fresh = formFrom(next); draftRef.current = fresh; setDraft(fresh); setDirty(false)
    }
  }, [invalidate])
  const loadStatus = useCallback(async (reset = false, foreground = false) => {
    loadRequest.current?.abort()
    const controller = new AbortController(); loadRequest.current = controller
    if (foreground) setLoading(true)
    try {
      const next = await requestJSON<AIConfigStatus>(endpoint, { signal: controller.signal })
      if (!mounted.current || controller.signal.aborted) return
      installStatus(next, reset || statusRef.current === null)
      setError(null)
    } catch (err) {
      if (mounted.current && !controller.signal.aborted) setError(err instanceof Error ? err.message : "Không tải được cấu hình AI.")
    } finally { if (mounted.current && !controller.signal.aborted) setLoading(false) }
  }, [installStatus])
  useEffect(() => {
    mounted.current = true
    void loadStatus(false, true)
    const refresh = () => { if (document.visibilityState === "visible" && !busy.current) void loadStatus() }
    const hidden = () => { if (document.visibilityState === "hidden") invalidate() }
    const leave = () => { invalidate(); draftRef.current = { ...draftRef.current, api_key: "" }; setDraft(draftRef.current) }
    const navigation = (event: MouseEvent) => {
      const anchor = (event.target as Element | null)?.closest("a[href]")
      if (anchor && new URL(anchor.getAttribute("href")!, location.href).pathname !== location.pathname) leave()
    }
    const storage = (event: StorageEvent) => { if (event.key === revisionEvent) refresh() }
    const sessionInvalid = () => { invalidate(); draftRef.current = { ...draftRef.current, api_key: "" }; setDraft(draftRef.current) }
    const timer = window.setInterval(refresh, 10000)
    window.addEventListener("focus", refresh)
    window.addEventListener("storage", storage)
    window.addEventListener(SESSION_INVALID_EVENT, sessionInvalid)
    window.addEventListener(SESSION_CHANGED_EVENT, sessionInvalid)
    document.addEventListener("visibilitychange", hidden)
    document.addEventListener("click", navigation, true)
    window.addEventListener("popstate", leave)
    window.addEventListener("pagehide", leave)
    return () => {
      mounted.current = false; generation.current += 1
      loadRequest.current?.abort(); probeRequest.current?.abort()
      draftRef.current = { ...draftRef.current, api_key: "" }
      window.clearInterval(timer)
      window.removeEventListener("focus", refresh)
      window.removeEventListener("storage", storage)
      window.removeEventListener(SESSION_INVALID_EVENT, sessionInvalid)
      window.removeEventListener(SESSION_CHANGED_EVENT, sessionInvalid)
      document.removeEventListener("visibilitychange", hidden)
      document.removeEventListener("click", navigation, true)
      window.removeEventListener("popstate", leave)
      window.removeEventListener("pagehide", leave)
    }
  }, [loadStatus, invalidate])
  const change = (patch: Partial<AIConfigDraft>) => {
    invalidate()
    const next = { ...draftRef.current, ...patch }
    if (patch.source_mode === "ENV") { next.credential_action = "KEEP"; next.api_key = "" }
    if (patch.credential_action && patch.credential_action !== "REPLACE") next.api_key = ""
    draftRef.current = next; setDraft(next); setDirty(true); setError(null)
  }
  const validateDraft = () => {
    const current = draftRef.current
    if (!current.model.trim()) { setError("Nhập hoặc chọn một model để tiếp tục."); return false }
    if (current.source_mode === "ENV") return true
    if (!current.base_url.trim()) { setError("Nhập Base URL và model để tiếp tục."); return false }
    if (current.credential_action === "REPLACE" && (!current.api_key.trim() || /[•*]|your[_ -]?|placeholder/i.test(current.api_key))) {
      setError("Nhập credential mới thực sự; không sử dụng chuỗi che hoặc giá trị mẫu."); return false
    }
    return true
  }
  const payload = (value: AIConfigDraft) => ({ ...value, api_key: value.credential_action === "REPLACE" ? value.api_key : undefined })
  const test = async (scope: "draft" | "active") => {
    if (!statusRef.current || probing.current || busy.current || (scope === "draft" && !validateDraft())) return
    const snapshot = { ...draftRef.current }
    const base = scope === "draft" ? snapshot.base_revision_token : statusRef.current.revision_token
    const version = ++generation.current
    const controller = new AbortController(); probeRequest.current = controller
    const id = crypto.randomUUID()
    probing.current = true; setTesting(scope); setError(null); setProbe(current => current ? { ...current, stale: true } : null)
    try {
      const digest = await digestDraft(scope === "draft" ? snapshot : { ...formFrom(statusRef.current), api_key: "" })
      if (version !== generation.current || controller.signal.aborted) return
      const body = { ...(scope === "draft" ? payload(snapshot) : {}), base_revision_token: base, probe_request_id: id, draft_digest: digest }
      const result = await requestJSON<AIProbeResult>(`${endpoint}/${scope === "draft" ? "probe" : "probe-active"}`, { method: "POST", body: JSON.stringify(body), signal: controller.signal }, 15000)
      if (!mounted.current || version !== generation.current || controller.signal.aborted || statusRef.current?.revision_token !== base || result.probe_request_id !== id || result.draft_digest !== digest || result.base_revision_token !== base) return
      setProbe({ result, scope, stale: false })
    } catch (err) {
      if (version !== generation.current || controller.signal.aborted || !mounted.current) return
      if (err instanceof ApiError && err.status === 409) { setProbe(current => current ? { ...current, stale: true } : null); void loadStatus() }
      setError(err instanceof DOMException && err.name === "AbortError" ? "Kiểm tra quá thời gian chờ. Bạn có thể thử lại." : err instanceof Error ? err.message : "Không kiểm tra được kết nối.")
    } finally {
      if (version === generation.current && mounted.current) { probing.current = false; setTesting(null) }
    }
  }
  const apply = async (event: FormEvent) => {
    event.preventDefault()
    if (busy.current || !validateDraft()) { errorRef.current?.focus(); return }
    busy.current = true; loadRequest.current?.abort(); invalidate(); setSaving(true); setError(null)
    try {
      const result = await requestJSON<AIConfigStatus>(endpoint, { method: "PUT", body: JSON.stringify(payload(draftRef.current)) })
      if (!mounted.current) return
      installStatus(result, true)
      localStorage.setItem(revisionEvent, result.revision_token)
      onNotify?.("Đã lưu và áp dụng cấu hình AI cho các tác vụ mới.")
    } catch (err) {
      if (!mounted.current) return
      if (err instanceof ApiError && err.status === 409) void loadStatus()
      setError(err instanceof Error ? err.message : "Chưa lưu được cấu hình. Cấu hình đang chạy được giữ nguyên.")
    } finally { busy.current = false; if (mounted.current) setSaving(false) }
  }
  const staleBase = Boolean(status && draft.base_revision_token !== status.revision_token)
  const disabled = saving || loading || !status
  return <div className="admin-ai-settings">
    {error && <p role="alert" ref={errorRef} tabIndex={-1} className="admin-notice is-error">{error}</p>}
    <section className="admin-panel admin-ai-current" aria-labelledby="ai-current-title">
      <div className="admin-section-heading"><h2 id="ai-current-title"><span className="admin-section-icon"><ShieldCheck size={21} aria-hidden="true" /></span>Cấu hình hiện tại</h2><button type="button" className="admin-button" disabled={saving || loading} onClick={() => void loadStatus(false, true)}><RefreshCw size={17} aria-hidden="true" />Tải lại trạng thái</button></div>
      {loading && !status ? <p role="status">Đang tải cấu hình…</p> : status ? <>
        <div className="admin-profile-grid"><ProfileDetails title="Cấu hình đã lưu (Persisted)" profile={status.persisted} /><ProfileDetails title="Cấu hình hiệu lực (Runtime)" profile={status.active} /></div>
        <dl className="admin-revision-grid"><div><dt className="font-semibold">Revision đã lưu</dt><dd className="mt-1 break-all font-mono" data-testid="persisted-revision">{status.revision_token}</dd></div><div><dt className="font-semibold">Revision tại Runtime</dt><dd className="mt-1 break-all font-mono" data-testid="runtime-revision">{status.runtime_revision_token}</dd><dd className="mt-1 text-slate-600">{status.sync_state === "current" ? "Tác vụ mới sử dụng revision này; tác vụ đang chạy giữ snapshot cũ." : "Đang đồng bộ cấu hình giữa các worker."}</dd></div></dl>
        <div className="admin-credential-summary"><div><p className="font-semibold flex items-center gap-2"><KeyRound size={17} aria-hidden="true" />Credential: {credentialLabels[status.credential.state]}</p><p className="mt-1 text-sm text-slate-600">Nguồn: {status.credential.source} · <span data-testid="masked-credential">{status.credential.masked || "Không có key"}</span></p></div></div>
        {!status.encryption.available && <p role="status" className="mt-4 text-sm text-amber-900">Khóa mã hóa chưa sẵn sàng. Cấu hình dùng credential trong DB cần được khôi phục khóa trước khi sử dụng.</p>}
      </> : <p className="text-slate-600">Chưa tải được trạng thái. Dùng “Tải lại trạng thái” để thử lại.</p>}
    </section>
    <form className="admin-panel admin-ai-draft" aria-labelledby="ai-draft-title" onSubmit={apply}>
      <div className="admin-section-heading"><h2 id="ai-draft-title"><span className="admin-section-icon"><PencilLine size={20} aria-hidden="true" /></span>Bản nháp cấu hình</h2><span className={`admin-draft-badge ${dirty ? "has-changes" : ""}`}>{dirty ? "Có thay đổi chưa lưu" : "Chưa chỉnh sửa"}</span></div><p className="mt-2 mb-5 max-w-3xl text-sm text-slate-600">Thử bản nháp không thay đổi cấu hình đang chạy. Chỉ “Lưu & áp dụng” mới cập nhật hồ sơ hiệu lực.</p>
      {staleBase && <div role="alert" className="admin-notice is-error"><span>Cấu hình nền đã thay đổi ở phiên khác. Bản nháp này đã cũ; tải cấu hình mới trước khi lưu hoặc giữ key.</span><button type="button" className="admin-button" onClick={() => void loadStatus(true, true)}>Tải cấu hình mới</button></div>}
      <fieldset disabled={disabled} className="grid gap-5"><legend className="sr-only">Thông tin kết nối AI</legend>
        <label htmlFor="ai-source" className="admin-field">Nguồn cấu hình<select id="ai-source" name="source_mode" value={draft.source_mode} onChange={event => change({ source_mode: event.target.value as AIConfigDraft["source_mode"] })}><option value="DATABASE">Hồ sơ trong cơ sở dữ liệu</option><option value="ENV">ENV / hồ sơ mặc định nguyên khối</option></select></label>
        {draft.source_mode === "ENV" && <p className="text-sm text-slate-600">Đang dùng Base URL và API key từ ENV. Bạn có thể chọn nhanh model bên dưới rồi bấm “Lưu & áp dụng”, hoặc chuyển sang hồ sơ cơ sở dữ liệu để đổi endpoint/key.</p>}
        <div className="grid gap-5 md:grid-cols-2"><label htmlFor="ai-protocol" className="admin-field">Giao thức<select id="ai-protocol" name="protocol" value={draft.protocol} disabled={draft.source_mode === "ENV"} onChange={() => change({ protocol: "openai_compatible" })}><option value="openai_compatible">OpenAI Compatible</option></select></label><label htmlFor="ai-auth" className="admin-field">Cách xác thực<select id="ai-auth" name="auth_mode" value={draft.auth_mode} disabled={draft.source_mode === "ENV"} onChange={event => change({ auth_mode: event.target.value as AIConfigDraft["auth_mode"] })}><option value="BEARER">Bearer credential</option><option value="NONE">Không dùng credential</option></select></label></div>
        <label htmlFor="ai-base-url" className="admin-field">Base URL<input id="ai-base-url" name="base_url" type="url" required={draft.source_mode === "DATABASE"} disabled={draft.source_mode === "ENV"} value={draft.base_url} spellCheck={false} autoCapitalize="none" onChange={event => change({ base_url: event.target.value })} aria-describedby="ai-binding-hint" /><span id="ai-binding-hint" className="font-normal text-sm text-slate-600">Đổi host, cổng hoặc đường dẫn tenant cần cung cấp credential mới.</span></label>
        <ModelQuickSelect value={draft.model} activeModel={status?.active.model} availableModels={status?.available_models} disabled={disabled} onSelect={model => change({ model })} />
        <label htmlFor="ai-model" className="admin-field">Model<input id="ai-model" name="model" required value={draft.model} maxLength={160} spellCheck={false} autoCapitalize="none" onChange={event => change({ model: event.target.value })} /></label>
        <fieldset disabled={draft.source_mode === "ENV"} className="admin-key-actions"><legend className="font-semibold">Thao tác với credential</legend><div className="mt-2 grid gap-3 sm:grid-cols-3">{([['KEEP','Giữ key hiện tại'],['REPLACE','Thay key mới'],['CLEAR','Xóa key']] as const).map(([value,label]) => <label key={value} className="flex min-h-12 cursor-pointer items-center gap-3 text-sm"><input type="radio" name="credential_action" value={value} checked={draft.credential_action === value} onChange={() => change({ credential_action: value })} />{label}</label>)}</div></fieldset>
        {draft.credential_action === "REPLACE" && draft.source_mode === "DATABASE" && <label htmlFor="ai-new-key" className="admin-field">Credential mới<input id="ai-new-key" name="new_credential" type="password" value={draft.api_key} autoComplete="new-password" required spellCheck={false} onChange={event => change({ api_key: event.target.value })} aria-describedby="ai-key-hint" /><span id="ai-key-hint" className="font-normal text-sm text-slate-600">Ô này luôn trống khi tải cấu hình. Key che ở trên chỉ để đọc.</span></label>}
        {draft.credential_action === "CLEAR" && <p className="text-sm text-amber-900">Xóa credential sẽ không tự dùng lại key từ ENV. Chế độ Bearer sẽ không gọi provider cho đến khi bạn cấp key mới.</p>}
      </fieldset>
      <div className="admin-form-actions"><button type="button" className="admin-button" disabled={disabled || Boolean(testing) || staleBase} onClick={() => void test("draft")}><TestTube2 size={17} aria-hidden="true" />{testing === "draft" ? "Đang kiểm tra bản nháp…" : "Test Draft"}</button><button type="button" className="admin-button" disabled={disabled || Boolean(testing)} onClick={() => void test("active")}>{testing === "active" ? "Đang kiểm tra runtime…" : "Test Active"}</button><button type="submit" className="admin-button primary" disabled={disabled || staleBase}><Save size={17} aria-hidden="true" />{saving ? "Đang áp dụng…" : "Lưu & áp dụng"}</button><button type="button" className="admin-button" disabled={disabled || !dirty} onClick={() => { invalidate(); if (statusRef.current) installStatus(statusRef.current, true) }}>Hủy bản nháp</button></div>
    </form>
    <section className="admin-panel admin-ai-probe" aria-labelledby="ai-probe-title"><div className="admin-section-heading"><h2 id="ai-probe-title"><span className="admin-section-icon"><TestTube2 size={20} aria-hidden="true" /></span>Kết quả kiểm tra gần nhất</h2></div>{probe ? <div className="mt-4" role="status"><p className={`font-semibold ${probe.stale ? "text-amber-800" : probe.result.success ? "text-emerald-800" : "text-rose-800"}`}>{probe.stale ? "Kết quả đã cũ — không xác nhận bản nháp hiện tại" : probe.result.success ? "Kết nối thành công" : "Kiểm tra không thành công"}</p><p className="mt-2 text-sm">{probe.result.message}</p><p className="mt-2 text-sm text-slate-600">{probe.scope === "draft" ? "Bản nháp" : "Runtime"} · {probe.result.latency_ms} ms · {probe.result.code} · {new Date(probe.result.tested_at).toLocaleString("vi-VN")}</p></div> : <p className="mt-3 text-sm text-slate-600">Chưa có kết quả kiểm tra trong phiên này. Test Draft kiểm tra bản nháp; Test Active kiểm tra hồ sơ đang chạy.</p>}</section>
  </div>
}
