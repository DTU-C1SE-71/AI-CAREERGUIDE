import uuid
from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.identity import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/identity/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/identity/login", auto_error=False)


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Optional[AsyncSession] = Depends(get_db)
) -> Optional[User]:
    """Optionally authenticates user via JWT without raising 401 if missing."""
    if not token or db is None:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and not user.is_active:
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Authenticates user via JWT and loads from database."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return user


def require_role(allowed_roles: list[UserRole]) -> Callable:
    """Role-Based Access Control (RBAC) dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


require_admin = require_role([UserRole.ADMIN])
require_student = require_role([UserRole.STUDENT])
require_any_authenticated = require_role([UserRole.STUDENT, UserRole.ADMIN])


async def require_admin_actor(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Optional[AsyncSession] = Depends(get_db),
) -> dict:
    """
    Xác thực quyền Quản trị viên (ADMIN) bằng chữ ký JWT HS256 hợp lệ.
    Hỗ trợ cả Admin lưu trong DB và Admin mặc định ký bởi identity service;
    từ chối tuyệt đối tài khoản Student (403) hoặc chưa đăng nhập / token giả (401).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập bằng tài khoản Quản trị viên (ADMIN) để thực hiện thao tác này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập quản trị không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_claim = str(payload.get("role") or "").upper()
    if role_claim != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Quản trị viên (ADMIN) mới được phép chạy thao tác này.",
        )

    user_id_str = payload.get("sub")
    admin_email = "admin@careerguide.vn"
    if db is not None and user_id_str:
        try:
            uid = uuid.UUID(str(user_id_str))
            result = await db.execute(select(User).where(User.id == uid))
            user_row = result.scalar_one_or_none()
            if user_row is not None:
                if not user_row.is_active or user_row.role != UserRole.ADMIN:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tài khoản quản trị đã bị khóa hoặc không đủ quyền.",
                    )
                admin_email = user_row.email
        except HTTPException:
            raise
        except Exception:
            pass

    return {"user_id": user_id_str, "role": "ADMIN", "email": admin_email}
