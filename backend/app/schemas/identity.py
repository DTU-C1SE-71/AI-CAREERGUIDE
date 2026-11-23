import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from app.models.identity import UserRole

_UPPER_RE = re.compile(r"[A-Z]")
_LOWER_RE = re.compile(r"[a-z]")
_DIGIT_RE = re.compile(r"[0-9]")
_SPECIAL_RE = re.compile(r"[^A-Za-z0-9\s]")


def validate_strong_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Mật khẩu phải có tối thiểu 8 ký tự.")
    if not _UPPER_RE.search(value):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái in hoa (A-Z).")
    if not _LOWER_RE.search(value):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ cái thường (a-z).")
    if not _DIGIT_RE.search(value):
        raise ValueError("Mật khẩu phải có ít nhất 1 chữ số (0-9).")
    if not _SPECIAL_RE.search(value):
        raise ValueError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt (ví dụ: !@#$%^&*).")
    return value


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=1024, description="Minimum 8 chars with uppercase, lowercase, digit, special char")
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = Field(default=UserRole.STUDENT)
    gender: str = Field(default="Khác", max_length=50, description="Giới tính: Nam, Nữ, Khác (bắt buộc)")
    grade_level: str = Field(default="Lớp 12", max_length=50, description="Hiện đang học lớp mấy: Lớp 10, Lớp 11, Lớp 12, Đã tốt nghiệp THPT (bắt buộc)")
    school_class: Optional[str] = Field(None, max_length=50)
    school_name: Optional[str] = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)

    @model_validator(mode="after")
    def validate_profile_fields(self):
        if not self.gender or not str(self.gender).strip():
            raise ValueError("Giới tính không được phép để trống.")
        if not self.grade_level or not str(self.grade_level).strip():
            raise ValueError("Mục hiện đang học lớp mấy không được phép để trống.")
        return self


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    gender: Optional[str] = Field(None, max_length=50)
    grade_level: Optional[str] = Field(None, max_length=50)
    school_class: Optional[str] = Field(None, max_length=50)
    school_name: Optional[str] = Field(None, max_length=255)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    name: Optional[str] = None
    role: UserRole
    is_active: bool
    grade: Optional[int] = 12
    gender: Optional[str] = Field(None, max_length=50)
    grade_level: Optional[str] = Field(None, max_length=50)
    school_class: Optional[str] = Field(None, max_length=50)
    school_name: Optional[str] = Field(None, max_length=255)
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
    needs_profile_setup: bool = False


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
    access_token: Optional[str] = Field(None, max_length=16384)
    credential: Optional[str] = Field(None, min_length=1, max_length=16384)
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None

class GoogleOAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    redirect_uri: Optional[str] = Field(None, max_length=2048)


class RegisterOTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(pattern=r"^[0-9]{6}$", description="Mã xác nhận 6 chữ số")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(pattern=r"^[0-9]{6}$", description="Mã xác nhận 6 chữ số")
    new_password: str = Field(min_length=8, max_length=1024)

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, v: str) -> str:
        return validate_strong_password(v)


class OTPActionResponse(BaseModel):
    message: str
    email: EmailStr
    expires_in_minutes: int
    cooldown_seconds: int


class MessageResponse(BaseModel):
    message: str
