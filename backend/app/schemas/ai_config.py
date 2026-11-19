"""DTO quản trị AI; credential mới luôn tách khỏi trạng thái đã che."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AIConfigDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_mode: Literal["DATABASE", "ENV"]
    protocol: Literal["openai_compatible"]
    base_url: str = Field(min_length=1, max_length=512)
    model: str = Field(min_length=1, max_length=160)
    auth_mode: Literal["BEARER", "NONE"]
    credential_action: Literal["KEEP", "REPLACE", "CLEAR"]
    api_key: Optional[SecretStr] = None
    base_revision_token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


class AIConfigProbe(AIConfigDraft):
    probe_request_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    draft_digest: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")


class AIActiveProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_revision_token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    probe_request_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    draft_digest: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")


class AIRevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_revision_token: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


class AITargetBinding(BaseModel):
    protocol: Literal["openai_compatible"]
    scheme: Literal["https", "http"]
    host: str
    port: int
    base_path: str


class AIProfile(BaseModel):
    source_mode: Literal["DATABASE", "ENV"]
    protocol: Literal["openai_compatible"]
    base_url: str
    model: str
    auth_mode: Literal["BEARER", "NONE"]
    credential_binding: AITargetBinding


class AICredentialStatus(BaseModel):
    state: Literal["SET", "CLEARED", "MISSING", "LOCKED"]
    source: Literal["DATABASE", "ENV", "NONE"]
    masked: Optional[str]
    reveal_supported: bool


class AIEncryptionStatus(BaseModel):
    available: bool
    key_id: Optional[str]
    configured_key_id: Optional[str]


class AIProbeResult(BaseModel):
    success: bool
    code: str
    message: str
    status_code: int
    latency_ms: float
    model_used: str
    base_url: str
    tested_at: str
    probe_request_id: str
    draft_digest: str
    base_revision_token: str


class AIConfigStatus(BaseModel):
    persisted: Optional[AIProfile]
    active: AIProfile
    revision_token: str
    runtime_revision_token: str
    sync_state: Literal["current"]
    credential: AICredentialStatus
    encryption: AIEncryptionStatus
    last_probe: Optional[AIProbeResult]


class AIRevealResponse(BaseModel):
    api_key: str
    expires_in_seconds: int
    revision_token: str
