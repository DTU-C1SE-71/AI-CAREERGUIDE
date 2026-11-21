export interface AIProfile {
  source_mode: "DATABASE" | "ENV"
  protocol: "openai_compatible"
  base_url: string
  model: string
  auth_mode: "BEARER" | "NONE"
  credential_binding?: { protocol: string; scheme: string; host: string; port: number; base_path: string }
}
export interface AIConfigDraft extends Omit<AIProfile, "credential_binding"> {
  credential_action: "KEEP" | "REPLACE" | "CLEAR"
  api_key: string
  base_revision_token: string
}
export interface AIProbeResult {
  success: boolean; code: string; message: string; status_code: number; latency_ms: number
  model_used: string; base_url: string; tested_at: string
  probe_request_id: string; draft_digest: string; base_revision_token: string
}
export interface AIConfigStatus {
  persisted: AIProfile | null
  active: AIProfile
  revision_token: string
  runtime_revision_token: string
  sync_state: string
  credential: { state: "SET" | "CLEARED" | "MISSING" | "LOCKED"; source: "DATABASE" | "ENV" | "NONE"; masked: string | null; reveal_supported: boolean }
  encryption: { available: boolean; key_id: string | null; configured_key_id: string | null }
  last_probe: AIProbeResult | null
  available_models?: string[]
}
