import uuid
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.identity import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/identity/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/identity/login", auto_error=False)


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _authenticated_user(token: str, db: Optional[AsyncSession]) -> User:
    """Quyền hiện tại luôn lấy từ DB, không tin role cũ trong JWT."""
    payload = decode_access_token(token)
    if payload is None:
        raise _invalid_credentials()
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise _invalid_credentials() from None
    if db is None:
        raise HTTPException(503, "Dịch vụ xác thực tạm thời không khả dụng.")
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(503, "Dịch vụ xác thực tạm thời không khả dụng.") from None
    if user is None:
        raise _invalid_credentials()
    if not user.is_active:
        raise HTTPException(403, "Tài khoản này đã bị vô hiệu hóa.")
    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Optional[AsyncSession] = Depends(get_db),
) -> Optional[User]:
    """Chỉ coi là khách khi không có bearer; phiên sai không được hạ xuống khách."""
    if not token:
        return None
    return await _authenticated_user(token, db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Xác thực chữ ký JWT và trạng thái tài khoản đang tồn tại."""
    return await _authenticated_user(token, db)


def require_role(allowed_roles: list[UserRole]) -> Callable:
    """Chặn hành động bằng quyền DB đã xác thực."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(403, "Tài khoản không có quyền thực hiện thao tác này.")
        return current_user
    return role_checker


require_admin = require_role([UserRole.ADMIN])
require_student = require_role([UserRole.STUDENT])
require_any_authenticated = require_role([UserRole.STUDENT, UserRole.ADMIN])


async def require_admin_actor(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Optional[AsyncSession] = Depends(get_db),
) -> dict:
    """Dùng cùng nguồn quyền DB cho các alias quản trị và lời gọi trực tiếp."""
    if not token:
        raise _invalid_credentials()
    user = await _authenticated_user(token, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, "Chỉ Quản trị viên được phép thực hiện thao tác này.")
    return {"user_id": str(user.id), "role": user.role.value, "email": user.email}
