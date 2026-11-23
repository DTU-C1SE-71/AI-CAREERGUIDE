import hashlib
import hmac
import json
import secrets
import uuid
import math
import logging
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import httpx
import jwt
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import settings
from app.core.email_service import OTPPurpose, send_otp_email

from app.models.identity import EmailVerificationCode, User, UserConsent, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.identity import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserConsentCreate,
    GoogleLoginRequest,
    UserProfileUpdateRequest,
    RegisterOTPVerifyRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    OTPActionResponse,
    MessageResponse,
)


logger = logging.getLogger(__name__)


def _authentication_unavailable() -> HTTPException:
    return HTTPException(503, "Dịch vụ xác thực tạm thời không khả dụng.")


def _require_database(db: Optional[AsyncSession]) -> AsyncSession:
    if db is None:
        raise _authentication_unavailable()
    return db


def _token_response(user: User, needs_profile_setup: bool = False) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse.model_validate(user),
        needs_profile_setup=needs_profile_setup,
    )


async def register_user(db: AsyncSession, payload: UserRegisterRequest) -> User:
    """Đăng ký học sinh và đồng ý sử dụng dữ liệu trong cùng giao dịch."""
    if payload.role == UserRole.ADMIN:
        raise HTTPException(403, "Không được tạo tài khoản Admin qua cổng đăng ký công khai.")
    db = _require_database(db)
    email = str(payload.email).lower().strip()
    try:
        existing = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Địa chỉ email này đã được đăng ký.")
        user = User(
            email=email,
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name.strip(),
            gender=str(payload.gender or "Khác").strip(),
            grade_level=str(payload.grade_level or "Lớp 12").strip(),
            school_class=payload.school_class.strip() if payload.school_class else None,
            school_name=payload.school_name.strip() if payload.school_name else None,
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        db.add(UserConsent(
            user_id=user.id,
            consent_type="INITIAL_ONBOARDING_TERMS_LAW91_2025",
            policy_version="v1.0-Law91/2025/QH15",
            is_granted=True,
            granted_at=datetime.now(timezone.utc),
        ))
        await db.commit()
        return user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Địa chỉ email này đã được đăng ký.") from None
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None


async def update_user_profile(db: AsyncSession, user_id: uuid.UUID, payload: UserProfileUpdateRequest) -> User:
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.gender is not None:
        user.gender = payload.gender.strip()
    if payload.grade_level is not None:
        user.grade_level = payload.grade_level.strip()
    if payload.school_class is not None:
        user.school_class = payload.school_class.strip() if payload.school_class else None
    if payload.school_name is not None:
        user.school_name = payload.school_name.strip() if payload.school_name else None

    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, payload: UserLoginRequest) -> TokenResponse:
    """Không cấp token khi DB lỗi, user vắng hoặc mật khẩu sai."""
    db = _require_database(db)
    normalized_email = str(payload.email).lower().strip()
    try:
        result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
        user = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise _authentication_unavailable() from None
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Sai địa chỉ email hoặc mật khẩu.", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(403, "Tài khoản này đã bị vô hiệu hóa.")
    return _token_response(user)


async def record_user_consent(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: UserConsentCreate,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> UserConsent:
    consent = UserConsent(
        user_id=user_id,
        consent_type=payload.consent_type,
        policy_version=payload.policy_version,
        is_granted=payload.is_granted,
        ip_address=ip_address,
        user_agent=user_agent,
        granted_at=datetime.now(timezone.utc)
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return consent


async def get_user_consents(db: AsyncSession, user_id: uuid.UUID) -> List[UserConsent]:
    query = select(UserConsent).where(UserConsent.user_id == user_id).order_by(UserConsent.granted_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def _verify_google_id_token(credential: str) -> dict:
    """Xác minh chữ ký bằng JWKS Google cố định và toàn bộ claim danh tính."""
    invalid = HTTPException(401, "Thông tin xác thực Google không hợp lệ hoặc đã hết hạn.")
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Đăng nhập Google chưa được cấu hình.")
    try:
        header = jwt.get_unverified_header(credential)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or not 1 <= len(header["kid"]) <= 128:
            logger.warning("[GoogleAuth] Invalid token header: %s", header)
            raise invalid
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            response = await client.get("https://www.googleapis.com/oauth2/v3/certs")
        if response.status_code != 200:
            logger.warning("[GoogleAuth] Google certs status %d", response.status_code)
            raise HTTPException(503, "Không thể xác minh Google lúc này. Vui lòng thử lại.")
        keys = response.json().get("keys", [])
        if not isinstance(keys, list) or len(keys) > 20:
            logger.warning("[GoogleAuth] Unexpected keys payload: %s", keys)
            raise invalid
        matching = [key for key in keys if isinstance(key, dict) and key.get("kid") == header["kid"] and key.get("kty") == "RSA"]
        if len(matching) != 1:
            logger.warning("[GoogleAuth] No matching RSA key found for kid: %s", header.get("kid"))
            raise invalid
        public_key = jwt.PyJWK.from_dict(matching[0], algorithm="RS256").key
        claims = jwt.decode(
            credential,
            public_key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            leeway=60,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("[GoogleAuth] Invalid issuer: %s", claims.get("iss"))
            raise invalid
        aud = claims.get("aud")
        valid_aud = aud == settings.GOOGLE_CLIENT_ID or (isinstance(aud, (list, tuple)) and settings.GOOGLE_CLIENT_ID in aud)
        if not valid_aud:
            logger.warning("[GoogleAuth] Invalid audience: %s != %s", aud, settings.GOOGLE_CLIENT_ID)
            raise invalid
        azp = claims.get("azp")
        if azp is not None and azp != settings.GOOGLE_CLIENT_ID:
            logger.warning("[GoogleAuth] Invalid azp: %s != %s", azp, settings.GOOGLE_CLIENT_ID)
            raise invalid
        if not isinstance(claims.get("sub"), str) or not 1 <= len(claims["sub"]) <= 255 or claims.get("email_verified") is not True:
            logger.warning("[GoogleAuth] Invalid sub or email_verified: sub=%s, email_verified=%s", claims.get("sub"), claims.get("email_verified"))
            raise invalid
        if any(isinstance(claims[key], bool) or not isinstance(claims[key], (int, float)) or not math.isfinite(claims[key]) for key in ("exp", "iat")) or claims["iat"] > claims["exp"]:
            logger.warning("[GoogleAuth] Non-finite or inconsistent exp/iat: iat=%s, exp=%s", claims.get("iat"), claims.get("exp"))
            raise invalid
        claims["email"] = str(TypeAdapter(EmailStr).validate_python(claims.get("email"))).lower().strip()
        return claims
    except httpx.HTTPError as exc:
        logger.warning("[GoogleAuth] HTTP error fetching Google certs: %s", exc)
        raise HTTPException(503, "Không thể xác minh Google lúc này. Vui lòng thử lại.") from None
    except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError, OverflowError, ValidationError) as exc:
        logger.warning("[GoogleAuth] Token verification failed: %s (%s)", type(exc).__name__, exc)
        raise invalid from None


async def authenticate_google_user(db: Optional[AsyncSession], payload: GoogleLoginRequest) -> TokenResponse:
    """Chỉ dùng email đã được Google ký; bỏ qua mọi hint danh tính từ client."""
    db = _require_database(db)
    if not payload.credential:
        raise HTTPException(400, "Cần ID token Google hoặc đăng nhập bằng mã ủy quyền.")
    profile = await _verify_google_id_token(payload.credential)
    email = profile["email"]
    display_name = str(profile.get("name") or email.split("@")[0])[:255]
    try:
        user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        is_new_user = user is None
        if user is None:
            user = User(
                email=email,
                hashed_password=get_password_hash(uuid.uuid4().hex + uuid.uuid4().hex),
                full_name=display_name,
                role=UserRole.STUDENT,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            db.add(UserConsent(
                user_id=user.id,
                consent_type="GOOGLE_OAUTH_ONBOARDING_LAW91_2025",
                policy_version="v1.0-Law91/2025/QH15",
                is_granted=True,
                granted_at=datetime.now(timezone.utc),
            ))
            await db.commit()
        if not user.is_active:
            raise HTTPException(403, "Tài khoản này đã bị vô hiệu hóa.")
        needs_profile_setup = (
            user.role == UserRole.STUDENT
            and (
                is_new_user
                or not (user.gender and user.gender.strip())
                or not (user.grade_level and user.grade_level.strip())
            )
        )
        return _token_response(user, needs_profile_setup=needs_profile_setup)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Tài khoản vừa được tạo bởi phiên khác. Vui lòng đăng nhập lại.") from None
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None


async def handle_google_oauth_callback(
    db: Optional[AsyncSession],
    code: str,
    redirect_uri: Optional[str] = None,
) -> TokenResponse:
    """Đổi mã GIS/redirect qua Google và xác minh ID token trước khi cấp phiên."""
    _require_database(db)
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(503, "Đăng nhập Google chưa được cấu hình.")
    target_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI
    allowed_redirects = {
        settings.GOOGLE_REDIRECT_URI,
        "postmessage",
        "http://localhost:5173/login/callback",
        "http://127.0.0.1:5173/login/callback",
        "http://localhost:3000/login/callback",
        "http://127.0.0.1:3000/login/callback",
    }
    if target_redirect_uri not in allowed_redirects:
        logger.warning("[GoogleAuth] Disallowed redirect URI: %s", target_redirect_uri)
        raise HTTPException(400, "Địa chỉ callback Google không được cho phép.")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": target_redirect_uri,
                "grant_type": "authorization_code",
            })
        if response.status_code != 200:
            logger.warning("[GoogleAuth] Google code exchange failed (%d): %s", response.status_code, response.text)
            raise HTTPException(400, "Mã đăng nhập Google không hợp lệ hoặc đã hết hạn.")
        data = response.json()
        credential = data.get("id_token")
        if not isinstance(credential, str) or not credential:
            logger.warning("[GoogleAuth] Response missing id_token: %s", list(data.keys()) if isinstance(data, dict) else "not-dict")
            raise HTTPException(502, "Google không trả về ID token hợp lệ.")
    except httpx.HTTPError as exc:
        logger.warning("[GoogleAuth] Network error exchanging code: %s", exc)
        raise HTTPException(503, "Không thể kết nối Google lúc này. Vui lòng thử lại.") from None
    except (ValueError, AttributeError) as exc:
        logger.warning("[GoogleAuth] Error parsing Google response: %s", exc)
        raise HTTPException(502, "Phản hồi xác thực Google không hợp lệ.") from None
    return await authenticate_google_user(db, GoogleLoginRequest(credential=credential))


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp_code(email: str, purpose: OTPPurpose, otp_code: str) -> str:
    msg = f"{purpose}:{email.lower().strip()}:{otp_code.strip()}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


async def _enforce_otp_cooldown(db: AsyncSession, email: str, purpose: OTPPurpose) -> None:
    latest = (
        await db.execute(
            select(EmailVerificationCode)
            .where(
                func.lower(EmailVerificationCode.email) == email,
                EmailVerificationCode.purpose == purpose,
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is not None:
        elapsed = (datetime.now(timezone.utc) - _as_utc(latest.created_at)).total_seconds()
        remaining = int(math.ceil(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed))
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Vui lòng đợi {remaining} giây trước khi yêu cầu gửi lại mã xác nhận.",
            )


async def _verify_active_otp(
    db: AsyncSession, email: str, purpose: OTPPurpose, otp_code: str
) -> EmailVerificationCode:
    record = (
        await db.execute(
            select(EmailVerificationCode)
            .where(
                func.lower(EmailVerificationCode.email) == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.is_used.is_(False),
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác nhận không tồn tại hoặc đã được sử dụng. Vui lòng yêu cầu mã mới.",
        )

    now = datetime.now(timezone.utc)
    if _as_utc(record.expires_at) < now:
        record.is_used = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác nhận đã hết hạn. Vui lòng yêu cầu mã mới.",
        )

    if record.attempts >= settings.OTP_MAX_ATTEMPTS:
        record.is_used = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã nhập sai mã quá số lần cho phép. Vui lòng yêu cầu mã mới.",
        )

    expected_hash = _hash_otp_code(email, purpose, otp_code)
    if not hmac.compare_digest(record.code_hash, expected_hash):
        record.attempts += 1
        attempts_left = max(0, settings.OTP_MAX_ATTEMPTS - record.attempts)
        if attempts_left == 0:
            record.is_used = True
        await db.commit()
        if attempts_left == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn đã nhập sai mã quá số lần cho phép. Vui lòng yêu cầu mã mới.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã xác nhận không chính xác (còn {attempts_left} lần thử).",
        )

    return record


async def request_registration_otp(db: AsyncSession, payload: UserRegisterRequest) -> OTPActionResponse:
    """Kiểm tra hợp lệ thông tin đăng ký, lưu bản nháp đã băm Argon2id và gửi mã OTP 6 số qua email."""
    if payload.role == UserRole.ADMIN:
        raise HTTPException(403, "Không được tạo tài khoản Admin qua cổng đăng ký công khai.")
    db = _require_database(db)
    email = str(payload.email).lower().strip()
    try:
        existing = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Địa chỉ email này đã được đăng ký.")

        await _enforce_otp_cooldown(db, email, "REGISTER")

        otp_code = _generate_otp_code()
        now = datetime.now(timezone.utc)
        pending_data = {
            "full_name": payload.full_name.strip(),
            "hashed_password": get_password_hash(payload.password),
            "gender": str(payload.gender or "Khác").strip(),
            "grade_level": str(payload.grade_level or "Lớp 12").strip(),
            "school_class": payload.school_class.strip() if payload.school_class else None,
            "school_name": payload.school_name.strip() if payload.school_name else None,
        }

        await send_otp_email(email, otp_code, "REGISTER")

        await db.execute(
            update(EmailVerificationCode)
            .where(
                func.lower(EmailVerificationCode.email) == email,
                EmailVerificationCode.purpose == "REGISTER",
                EmailVerificationCode.is_used.is_(False),
            )
            .values(is_used=True)
        )
        db.add(
            EmailVerificationCode(
                email=email,
                purpose="REGISTER",
                code_hash=_hash_otp_code(email, "REGISTER", otp_code),
                pending_payload=json.dumps(pending_data, ensure_ascii=False),
                attempts=0,
                is_used=False,
                expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
                created_at=now,
            )
        )
        await db.commit()
        return OTPActionResponse(
            message=f"Mã xác nhận 6 chữ số đã được gửi tới {email}. Vui lòng kiểm tra hộp thư (kể cả mục Spam).",
            email=email,
            expires_in_minutes=settings.OTP_EXPIRE_MINUTES,
            cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
        )
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None


async def verify_registration_otp(db: AsyncSession, payload: RegisterOTPVerifyRequest) -> TokenResponse:
    """Xác minh mã OTP 6 số, tạo tài khoản học sinh + ghi nhận đồng ý dữ liệu và cấp JWT."""
    db = _require_database(db)
    email = str(payload.email).lower().strip()
    try:
        record = await _verify_active_otp(db, email, "REGISTER", payload.otp_code)
        if not record.pending_payload:
            raise HTTPException(400, "Dữ liệu đăng ký không hợp lệ. Vui lòng đăng ký lại.")

        existing = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        if existing:
            record.is_used = True
            await db.commit()
            raise HTTPException(409, "Địa chỉ email này đã được đăng ký.")

        pending = json.loads(record.pending_payload)
        user = User(
            email=email,
            hashed_password=pending["hashed_password"],
            full_name=pending["full_name"],
            gender=pending.get("gender") or "Khác",
            grade_level=pending.get("grade_level") or "Lớp 12",
            school_class=pending.get("school_class"),
            school_name=pending.get("school_name"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        db.add(
            UserConsent(
                user_id=user.id,
                consent_type="INITIAL_ONBOARDING_TERMS_LAW91_2025",
                policy_version="v1.0-Law91/2025/QH15",
                is_granted=True,
                granted_at=datetime.now(timezone.utc),
            )
        )
        record.is_used = True
        await db.commit()
        await db.refresh(user)
        return _token_response(user)
    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Địa chỉ email này đã được đăng ký.") from None
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None


async def request_password_reset_otp(db: AsyncSession, payload: ForgotPasswordRequest) -> OTPActionResponse:
    """Gửi mã OTP đặt lại mật khẩu; phản hồi trung tính để không tiết lộ email tồn tại hay không."""
    db = _require_database(db)
    email = str(payload.email).lower().strip()
    neutral_response = OTPActionResponse(
        message="Nếu địa chỉ email đã được đăng ký, mã xác nhận 6 chữ số đã được gửi tới hộp thư của bạn.",
        email=email,
        expires_in_minutes=settings.OTP_EXPIRE_MINUTES,
        cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
    )
    try:
        user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        if user is None or not user.is_active:
            return neutral_response

        await _enforce_otp_cooldown(db, email, "RESET_PASSWORD")

        otp_code = _generate_otp_code()
        now = datetime.now(timezone.utc)
        await send_otp_email(email, otp_code, "RESET_PASSWORD")

        await db.execute(
            update(EmailVerificationCode)
            .where(
                func.lower(EmailVerificationCode.email) == email,
                EmailVerificationCode.purpose == "RESET_PASSWORD",
                EmailVerificationCode.is_used.is_(False),
            )
            .values(is_used=True)
        )
        db.add(
            EmailVerificationCode(
                email=email,
                purpose="RESET_PASSWORD",
                code_hash=_hash_otp_code(email, "RESET_PASSWORD", otp_code),
                pending_payload=None,
                attempts=0,
                is_used=False,
                expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
                created_at=now,
            )
        )
        await db.commit()
        return neutral_response
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None


async def reset_password_with_otp(db: AsyncSession, payload: ResetPasswordRequest) -> MessageResponse:
    """Xác minh mã OTP 6 số và cập nhật mật khẩu mới đã băm Argon2id."""
    db = _require_database(db)
    email = str(payload.email).lower().strip()
    try:
        record = await _verify_active_otp(db, email, "RESET_PASSWORD", payload.otp_code)
        user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
        if user is None or not user.is_active:
            record.is_used = True
            await db.commit()
            raise HTTPException(400, "Tài khoản không khả dụng để đặt lại mật khẩu.")

        user.hashed_password = get_password_hash(payload.new_password)
        record.is_used = True
        await db.commit()
        return MessageResponse(message="Đặt lại mật khẩu thành công. Bạn có thể đăng nhập bằng mật khẩu mới.")
    except HTTPException:
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise _authentication_unavailable() from None
