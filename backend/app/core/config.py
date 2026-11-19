from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True
    )

    PROJECT_NAME: str = "AI CareerGuide Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database Settings (PostgreSQL 16 + pgvector)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_careerguide"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_careerguide",
        description="Async SQLAlchemy database URL"
    )

    # Security & Authentication (OWASP ASVS Level 2, Argon2id, JWT)
    SECRET_KEY: str = "ai_careerguide_super_secret_jwt_key_2026_owasp_compliant"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Argon2id Parameters (OWASP Recommended)
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536  # 64 MiB
    ARGON2_PARALLELISM: int = 2
    ARGON2_HASH_LEN: int = 32
    ARGON2_SALT_LEN: int = 16

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID: str = "1095956825384-f8n2bj0ott0u1sokbegksf7n32tlpn51.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/login/callback"

    # AI Assistant & LLM Services (Persona: Navi - AI CareerGuide)
    AI_ASSISTANT_NAME: str = "Navi"
    LLM_PROTOCOL: str = "openai_compatible"
    LLM_AUTH_MODE: str = "BEARER"
    AI_CONFIG_ENCRYPTION_KEY: str = ""
    AI_CONFIG_ENCRYPTION_KEY_ID: str = "primary"
    AI_LOCAL_ALLOWED_BASE_URLS: List[str] = []
    AI_PROBE_LIMIT_PER_MINUTE: int = 6
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://codex.fosta.app/v1"
    LLM_MODEL: str = "gpt-6-luna"
    LLM_TIMEOUT_SECONDS: float = 120.0
    LLM_MAX_TOKENS: int = 128000
    LLM_MAX_CONTEXT_TOKENS: int = 272000
    LLM_MAX_CONTEXT_CHARS: int = 240000

    # Legacy & Fallback Compatibility Settings
    XKIRO_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://codex.fosta.app/v1"
    XAI_API_KEY: str = ""
    XAI_BASE_URL: str = "https://codex.fosta.app/v1"
    VISION_LLM_MODEL: str = "mistralai/mistral-medium-3.5"
    TAVILY_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # 3-Pillar Scoring Weights (Default: RIASEC 0.45, Academic 0.35, Preference 0.20)
    WEIGHT_RIASEC: float = 0.45
    WEIGHT_ACADEMIC: float = 0.35
    WEIGHT_PREFERENCE: float = 0.20

    # Whitelisted academic domains for Stream B roadmap discovery (Guardrail)
    WHITELISTED_SEARCH_DOMAINS: List[str] = [
        "edu.vn",
        "hust.edu.vn",
        "vnu.edu.vn",
        "vnuhcm.edu.vn",
        "duytan.edu.vn",
        "mit.edu",
        "stanford.edu",
        "coursera.org",
        "edx.org",
        "roadmap.sh"
    ]

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v:
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("["):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173"
        ]





    @model_validator(mode="after")
    def require_production_signing_key(self):
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            key = self.SECRET_KEY
            if len(key) < 32 or key == type(self).model_fields["SECRET_KEY"].default or any(marker in key.lower() for marker in ("change-me", "changeme", "your-secret", "placeholder")):
                raise ValueError("Production yêu cầu SECRET_KEY riêng, ngẫu nhiên và dài ít nhất 32 ký tự.")
        return self


settings = Settings()
