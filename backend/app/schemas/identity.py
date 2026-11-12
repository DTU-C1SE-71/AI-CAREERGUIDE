import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from app.models.identity import UserRole


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters compliant with OWASP ASVS")
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = Field(default=UserRole.STUDENT)
    gender: str = Field(default="Khác", description="Giới tính: Nam, Nữ, Khác (bắt buộc)")
    grade_level: str = Field(default="Lớp 12", description="Hiện đang học lớp mấy: Lớp 10, Lớp 11, Lớp 12, Đã tốt nghiệp THPT (bắt buộc)")
    school_class: Optional[str] = None
    school_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_profile_fields(self):
        if not self.gender or not str(self.gender).strip():
            raise ValueError("Giới tính không được phép để trống.")
        if not self.grade_level or not str(self.grade_level).strip():
            raise ValueError("Mục hiện đang học lớp mấy không được phép để trống.")
        return self


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    gender: Optional[str] = None
    grade_level: Optional[str] = None
    school_class: Optional[str] = None
    school_name: Optional[str] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    name: Optional[str] = None
    role: UserRole
    is_active: bool
    grade: Optional[int] = 12
    gender: Optional[str] = None
    grade_level: Optional[str] = None
    school_class: Optional[str] = None
    school_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_fe_compatibility(self):
        if not self.name and self.full_name:
            self.name = self.full_name
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: uuid.UUID
    expires_in_minutes: int
    user: Optional[UserResponse] = None


class UserConsentCreate(BaseModel):
    consent_type: str = Field(
        default="DATA_PRIVACY_LAW91_2025",
        description="TERMS_AND_PRIVACY, DATA_PROCESSING, AI_CAREER_ANALYSIS"
    )
    policy_version: str = Field(default="v1.0-Law91/2025/QH15")
    is_granted: bool = True


class UserConsentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    consent_type: str
    policy_version: str
    is_granted: bool
    granted_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GoogleLoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    access_token: Optional[str] = None
    credential: Optional[str] = None
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None

class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: Optional[str] = None
