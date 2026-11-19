"""Tests for strong password policy, email OTP registration, and forgot/reset password."""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.identity import EmailVerificationCode, User, UserConsent, UserRole

STRONG_PASS = "CareerGuide@2026"
STRONG_PASS_NEW = "NewSecurePass#99"
EXISTING_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000042")


@pytest_asyncio.fixture
async def otp_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "synthetic-otp-signing-secret-only-0123456789abcdef")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
    monkeypatch.setattr(settings, "OTP_MAX_ATTEMPTS", 5)

    sent_emails = []

    async def fake_send_otp(to_email: str, otp_code: str, purpose: str) -> str:
        sent_emails.append({"to": to_email, "otp": otp_code, "purpose": purpose})
        return "mock"

    monkeypatch.setattr("app.services.identity.service.send_otp_email", fake_send_otp)

    db_path = tmp_path / "otp-isolated.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as db:
        db.add(
            User(
                id=EXISTING_USER_ID,
                email="student.existing@example.com",
                full_name="Học sinh Hiện tại",
                hashed_password=get_password_hash(STRONG_PASS),
                role=UserRole.STUDENT,
                is_active=True,
            )
        )
        await db.commit()

    async def isolated_db():
        async with sessions() as db:
            yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = isolated_db
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield client, sessions, sent_emails
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "weak_password",
    [
        "Ab1!xyz",         # too short (7 chars)
        "alllowercase1!",  # missing uppercase
        "ALLUPPERCASE1!",  # missing lowercase
        "NoDigitsHere!",   # missing digit
        "NoSpecialChar1",  # missing special char
    ],
)
async def test_weak_passwords_rejected_on_register_and_reset(otp_client, weak_password):
    client, _, sent = otp_client
    r1 = await client.post(
        "/api/identity/register/request-otp",
        json={
            "email": "weak@example.com",
            "password": weak_password,
            "full_name": "Học sinh yếu",
        },
    )
    assert r1.status_code == 422
    assert not sent

    r2 = await client.post(
        "/api/identity/reset-password",
        json={
            "email": "student.existing@example.com",
            "otp_code": "123456",
            "new_password": weak_password,
        },
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_register_email_otp_full_flow_and_security(otp_client):
    client, sessions, sent = otp_client
    payload = {
        "email": "New.Student@Example.com",
        "password": STRONG_PASS,
        "full_name": "Nguyễn Văn A",
        "gender": "Nam",
        "grade_level": "Lớp 11",
    }

    req = await client.post("/api/identity/register/request-otp", json=payload)
    assert req.status_code == 200
    assert len(sent) == 1
    assert sent[0]["to"] == "new.student@example.com"
    assert sent[0]["purpose"] == "REGISTER"
    otp = sent[0]["otp"]
    assert len(otp) == 6 and otp.isdigit()

    # Cooldown prevents immediate resend spam
    spam = await client.post("/api/identity/register/request-otp", json=payload)
    assert spam.status_code == 429

    # Stored record hashes OTP and never stores plaintext password
    async with sessions() as db:
        rec = (
            await db.execute(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.email == "new.student@example.com"
                )
            )
        ).scalar_one()
        assert rec.code_hash != otp
        assert STRONG_PASS not in (rec.pending_payload or "")

    # Wrong OTP fails and decrements remaining attempts
    wrong = await client.post(
        "/api/identity/register/verify-otp",
        json={"email": "new.student@example.com", "otp_code": "000000" if otp != "000000" else "999999"},
    )
    assert wrong.status_code == 400

    # Valid OTP creates user + consent and returns working JWT
    verified = await client.post(
        "/api/identity/register/verify-otp",
        json={"email": "new.student@example.com", "otp_code": otp},
    )
    assert verified.status_code == 201
    token = verified.json()["access_token"]
    me = await client.get("/api/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new.student@example.com"
    assert me.json()["grade_level"] == "Lớp 11"

    # Replay same OTP is rejected
    replay = await client.post(
        "/api/identity/register/verify-otp",
        json={"email": "new.student@example.com", "otp_code": otp},
    )
    assert replay.status_code == 400

    # Consent recorded
    async with sessions() as db:
        consents = (
            await db.execute(
                select(UserConsent).where(UserConsent.user_id == uuid.UUID(me.json()["id"]))
            )
        ).scalars().all()
        assert len(consents) == 1


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow_and_anti_enumeration(otp_client):
    client, _, sent = otp_client

    # Non-existent email returns neutral 200 and sends NO email
    ghost = await client.post(
        "/api/identity/forgot-password",
        json={"email": "ghost.user@example.com"},
    )
    assert ghost.status_code == 200
    assert len(sent) == 0

    # Existing email sends RESET_PASSWORD OTP
    req = await client.post(
        "/api/identity/forgot-password",
        json={"email": "student.existing@example.com"},
    )
    assert req.status_code == 200
    assert len(sent) == 1
    assert sent[0]["purpose"] == "RESET_PASSWORD"
    otp = sent[0]["otp"]

    # Reset with valid OTP & strong password succeeds
    reset = await client.post(
        "/api/identity/reset-password",
        json={
            "email": "student.existing@example.com",
            "otp_code": otp,
            "new_password": STRONG_PASS_NEW,
        },
    )
    assert reset.status_code == 200

    # Old password fails, new password succeeds
    old_login = await client.post(
        "/api/identity/login",
        json={"email": "student.existing@example.com", "password": STRONG_PASS},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/identity/login",
        json={"email": "student.existing@example.com", "password": STRONG_PASS_NEW},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    # Replay OTP fails
    replay = await client.post(
        "/api/identity/reset-password",
        json={
            "email": "student.existing@example.com",
            "otp_code": otp,
            "new_password": "AnotherStrong#88",
        },
    )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_expired_otp_and_max_attempts_lockout(otp_client):
    client, sessions, sent = otp_client
    await client.post(
        "/api/identity/forgot-password",
        json={"email": "student.existing@example.com"},
    )
    otp = sent[0]["otp"]
    wrong_otp = "111111" if otp != "111111" else "222222"

    # 5 wrong attempts lock out the OTP
    for _ in range(5):
        r = await client.post(
            "/api/identity/reset-password",
            json={
                "email": "student.existing@example.com",
                "otp_code": wrong_otp,
                "new_password": STRONG_PASS_NEW,
            },
        )
        assert r.status_code == 400

    # Even the correct OTP no longer works after lockout
    locked = await client.post(
        "/api/identity/reset-password",
        json={
            "email": "student.existing@example.com",
            "otp_code": otp,
            "new_password": STRONG_PASS_NEW,
        },
    )
    assert locked.status_code == 400

    # Expired OTP rejected
    async with sessions() as db:
        from app.services.identity.service import _hash_otp_code

        db.add(
            EmailVerificationCode(
                email="student.existing@example.com",
                purpose="RESET_PASSWORD",
                code_hash=_hash_otp_code("student.existing@example.com", "RESET_PASSWORD", "654321"),
                attempts=0,
                is_used=False,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                created_at=datetime.now(timezone.utc) - timedelta(minutes=11),
            )
        )
        await db.commit()

    expired = await client.post(
        "/api/identity/reset-password",
        json={
            "email": "student.existing@example.com",
            "otp_code": "654321",
            "new_password": STRONG_PASS_NEW,
        },
    )
    assert expired.status_code == 400
    assert "hết hạn" in expired.text


@pytest.mark.asyncio
async def test_email_service_fails_closed_in_production_without_provider(monkeypatch):
    from fastapi import HTTPException
    from app.core.email_service import send_otp_email

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")

    with pytest.raises(HTTPException) as exc:
        await send_otp_email("user@example.com", "123456", "REGISTER")
    assert exc.value.status_code == 503
