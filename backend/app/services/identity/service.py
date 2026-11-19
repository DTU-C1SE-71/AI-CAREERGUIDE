import uuid
import math
import logging
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import httpx
import jwt
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import settings

from app.models.identity import User, UserConsent, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.identity import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserConsentCreate,
    GoogleLoginRequest,
    UserProfileUpdateRequest,
)


logger = logging.getLogger(__name__)


def _authentication_unavailable() -> HTTPException:
    return HTTPException(503, "Dịch vụ xác thực tạm thời không khả dụng.")


def _require_database(db: Optional[AsyncSession]) -> AsyncSession:
    if db is None:
        raise _authentication_unavailable()
    return db


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse.model_validate(user),
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
        return _token_response(user)
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
