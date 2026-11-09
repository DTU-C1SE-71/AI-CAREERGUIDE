from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.identity import User
from app.schemas.identity import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserConsentCreate,
    UserConsentResponse,
    GoogleLoginRequest,
    GoogleOAuthCallbackRequest,
)
from app.services.identity import service

router = APIRouter(prefix="/identity", tags=["Identity & Privacy Consent"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registers a new user account with Argon2id password hashing and logs Law 91/2025/QH15 consent."""
    user = await service.register_user(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates credentials against Argon2id hash and issues a JWT token."""
    return await service.authenticate_user(db, payload)


@router.get("/me", response_model=UserResponse)
async def get_current_profile(current_user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return current_user


@router.post("/consent", response_model=UserConsentResponse)
async def record_consent(
    payload: UserConsentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Records an explicit consent entry compliant with Vietnamese Law No. 91/2025/QH15."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.record_user_consent(db, current_user.id, payload, ip_address=ip, user_agent=user_agent)


@router.get("/consents", response_model=List[UserConsentResponse])
async def list_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all historical consent audit trails for the current user."""
    return await service.get_user_consents(db, current_user.id)


@router.post("/google-login", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates or automatically registers a student via Google OAuth."""
    return await service.authenticate_google_user(db, payload)

@router.post("/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    payload: GoogleOAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handles standard Google OAuth 2.0 authorization code exchange callback."""
    return await service.handle_google_oauth_callback(db, payload.code, payload.redirect_uri)
