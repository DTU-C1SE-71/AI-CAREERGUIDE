"""Hồi quy xác thực qua API và DB tổng hợp, không kết nối provider thật."""
import asyncio
import json
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.identity import User, UserConsent, UserRole

PASSWORD = "Synthetic-Password-123!"
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
STUDENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
PREFIXES = ["/api", "/api/v1"]


@pytest_asyncio.fixture
async def auth_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "synthetic-auth-signing-secret-only-0123456789abcdef")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "synthetic-client.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "synthetic-google-client-secret")
    db_path = tmp_path / "auth-isolated.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as connection:
        actual = (await connection.execute(text("PRAGMA database_list"))).fetchall()
        assert str(db_path.resolve()) == str(__import__("pathlib").Path(actual[0][2]).resolve())
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    password_hash = get_password_hash(PASSWORD)
    async with sessions() as db:
        db.add_all([
            User(id=ADMIN_ID, email="admin@example.com", full_name="Quản trị Tổng hợp", hashed_password=password_hash, role=UserRole.ADMIN),
            User(id=STUDENT_ID, email="student@example.com", full_name="Học sinh Tổng hợp", hashed_password=password_hash, role=UserRole.STUDENT),
            User(id=OTHER_ID, email="other@example.com", full_name="Người khác", hashed_password=password_hash, role=UserRole.STUDENT),
        ])
        await db.commit()
    async def isolated_db():
        async with sessions() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = isolated_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
            yield client, sessions
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()


async def login(client, prefix="/api/v1", email="admin@example.com"):
    response = await client.post(f"{prefix}/identity/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_unknown_admin_email_cannot_receive_token(auth_client, prefix):
    client, _ = auth_client
    response = await client.post(f"{prefix}/identity/login", json={"email": "unknown-admin@example.com", "password": PASSWORD})
    assert response.status_code == 401
    assert "access_token" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_real_login_and_wrong_password(auth_client, prefix):
    client, _ = auth_client
    headers = await login(client, prefix)
    profile = await client.get(f"{prefix}/identity/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == str(ADMIN_ID)
    assert "hashed_password" not in profile.text
    failed = await client.post(f"{prefix}/identity/login", json={"email": "admin@example.com", "password": "incorrect-password"})
    assert failed.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_google_email_only_cannot_impersonate_admin(auth_client, prefix):
    client, _ = auth_client
    response = await client.post(f"{prefix}/identity/google-login", json={"email": "admin@example.com", "full_name": "Forged"})
    assert response.status_code in (400, 401, 422)
    assert "access_token" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("claims", [
    {"sub": str(ADMIN_ID), "role": "ADMIN"},
    {"exp": 4102444800, "iat": 1, "role": "ADMIN"},
    {"sub": "not-a-uuid", "exp": 4102444800, "iat": 1},
    {"sub": str(ADMIN_ID), "exp": True, "iat": 1},
])
async def test_malformed_jwt_claims_rejected(auth_client, prefix, claims):
    client, _ = auth_client
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await client.get(f"{prefix}/identity/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_expired_or_invalid_bearer_never_becomes_guest(auth_client, prefix):
    client, _ = auth_client
    expired = create_access_token(str(STUDENT_ID), "STUDENT", timedelta(seconds=-30))
    for token in (expired, "synthetic-invalid-token"):
        response = await client.post(f"{prefix}/rag-governance/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "Tìm hiểu ngành An toàn thông tin"})
        assert response.status_code == 401
    guest = await client.post(f"{prefix}/rag-governance/chat", json={"message": "Tìm hiểu ngành An toàn thông tin"})
    assert guest.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_db_role_and_active_state_override_stale_token(auth_client, prefix):
    client, sessions = auth_client
    headers = await login(client, prefix)
    assert (await client.get(f"{prefix}/rag-governance/llm-status", headers=headers)).status_code == 200
    async with sessions() as db:
        await db.execute(update(User).where(User.id == ADMIN_ID).values(role=UserRole.STUDENT))
        await db.commit()
    for path, method in [("/rag-governance/llm-status", "get"), ("/major-insights/7480101/regenerate", "post")]:
        assert (await getattr(client, method)(prefix + path, headers=headers)).status_code == 403
    async with sessions() as db:
        await db.execute(update(User).where(User.id == ADMIN_ID).values(is_active=False))
        await db.commit()
    assert (await client.get(f"{prefix}/identity/me", headers=headers)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_nonexistent_admin_and_database_failure_fail_closed(auth_client, prefix):
    client, _ = auth_client
    missing = create_access_token(str(uuid.uuid4()), "ADMIN")
    response = await client.post(f"{prefix}/major-insights/7480101/regenerate", headers={"Authorization": f"Bearer {missing}"})
    assert response.status_code == 401
    headers = await login(client, prefix)
    async def unavailable():
        yield SimpleNamespace(execute=AsyncMock(side_effect=OperationalError("synthetic-database-details", {}, Exception("private-db-password"))))
    app.dependency_overrides[get_db] = unavailable
    for path, method, kwargs in [("/identity/me", "get", {"headers": headers}), ("/major-insights/7480101/regenerate", "post", {"headers": headers}), ("/identity/login", "post", {"json": {"email": "admin@example.com", "password": PASSWORD}})]:
        failed = await getattr(client, method)(prefix + path, **kwargs)
        assert failed.status_code == 503
        assert "private-db-password" not in failed.text
        assert "access_token" not in failed.text


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_profile_cannot_mutate_other_user_or_role(auth_client, prefix):
    client, sessions = auth_client
    headers = await login(client, prefix, "student@example.com")
    response = await client.put(f"{prefix}/identity/profile", headers=headers, json={"full_name": "Tên học sinh mới", "user_id": str(OTHER_ID), "role": "ADMIN", "is_active": False})
    assert response.status_code in (200, 422)
    async with sessions() as db:
        own = await db.get(User, STUDENT_ID)
        other = await db.get(User, OTHER_ID)
        assert own.role == UserRole.STUDENT and own.is_active
        assert other.full_name == "Người khác"


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_registration_normalizes_email_and_never_allows_admin(auth_client, prefix):
    client, sessions = auth_client
    registration = {"email": "Fresh.Student@Example.com", "password": PASSWORD, "full_name": "Học sinh mới"}
    created = await client.post(f"{prefix}/identity/register", json=registration)
    assert created.status_code == 201
    assert created.json()["email"] == "fresh.student@example.com"
    assert created.json()["role"] == "STUDENT"
    assert (await client.post(f"{prefix}/identity/login", json={"email": "fresh.student@example.com", "password": PASSWORD})).status_code == 200
    duplicate = await client.post(f"{prefix}/identity/register", json=registration)
    assert duplicate.status_code == 409
    forbidden = await client.post(f"{prefix}/identity/register", json={**registration, "email": "new-admin@example.com", "role": "ADMIN"})
    assert forbidden.status_code == 403
    async with sessions() as db:
        consents = (await db.execute(select(UserConsent).where(UserConsent.user_id == uuid.UUID(created.json()["id"])))).scalars().all()
        assert len(consents) == 1


@pytest.fixture(scope="module")
def google_signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def google_provider(monkeypatch, google_signing_key):
    jwk = json.loads(RSAAlgorithm.to_jwk(google_signing_key.public_key()))
    jwk.update({"kid": "synthetic-google-key", "use": "sig", "alg": "RS256"})
    calls = []
    state = {"token_error": False, "id_token": None}
    original_client = httpx.AsyncClient
    def handle(request):
        calls.append(request)
        assert request.url.host in ("www.googleapis.com", "oauth2.googleapis.com")
        assert not request.url.query
        if request.url.path.endswith("/certs"):
            return httpx.Response(200, json={"keys": [jwk]})
        if request.url.path == "/token":
            assert request.method == "POST"
            assert parse_qs(request.content.decode())["grant_type"] == ["authorization_code"]
            if state["token_error"]:
                return httpx.Response(400, text="synthetic-secret-must-not-be-echoed")
            return httpx.Response(200, json={"id_token": state["id_token"], "access_token": "synthetic-unused-access-token"})
        return httpx.Response(404)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    def signed(**overrides):
        claims = {"iss": "https://accounts.google.com", "aud": settings.GOOGLE_CLIENT_ID, "sub": "synthetic-google-user", "email": "student@example.com", "email_verified": True, "name": "Tên từ Google", "iat": int(time.time()), "exp": int(time.time()) + 300}
        claims.update(overrides)
        return jwt.encode(claims, google_signing_key, algorithm="RS256", headers={"kid": "synthetic-google-key"})
    return signed, calls, state


@pytest.mark.asyncio
async def test_google_signed_identity_ignores_forged_client_email(auth_client, google_provider):
    client, _ = auth_client
    signed, calls, _ = google_provider
    response = await client.post("/api/v1/identity/google-login", json={"credential": signed(), "email": "admin@example.com", "full_name": "Forged"})
    assert response.status_code == 200
    assert response.json()["user_id"] == str(STUDENT_ID)
    assert response.json()["role"] == "STUDENT"
    assert calls and all("authorization" not in request.headers for request in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [{"aud": "wrong-client"}, {"iss": "https://attacker.example"}, {"exp": 1}, {"email_verified": False}, {"email_verified": "true"}, {"sub": ""}])
async def test_google_invalid_claims_are_rejected(auth_client, google_provider, changes):
    client, _ = auth_client
    signed, _, _ = google_provider
    response = await client.post("/api/identity/google-login", json={"credential": signed(**changes)})
    assert response.status_code == 401
    assert "access_token" not in response.text


@pytest.mark.asyncio
async def test_google_code_callback_checks_redirect_and_hides_provider_error(auth_client, google_provider):
    client, _ = auth_client
    signed, calls, state = google_provider
    state["id_token"] = signed()
    rejected = await client.post("/api/v1/identity/google/callback", json={"code": "synthetic-code", "redirect_uri": "https://attacker.example/callback"})
    assert rejected.status_code == 400
    assert not calls
    accepted = await client.post("/api/v1/identity/google/callback", json={"code": "synthetic-code", "redirect_uri": "postmessage"})
    assert accepted.status_code == 200
    assert accepted.json()["user_id"] == str(STUDENT_ID)
    state["token_error"] = True
    failed = await client.post("/api/v1/identity/google/callback", json={"code": "synthetic-code", "redirect_uri": "postmessage"})
    assert failed.status_code in (400, 401)
    assert "synthetic-secret-must-not-be-echoed" not in failed.text


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_all_existing_admin_actions_reject_guest_and_student(auth_client, prefix):
    client, _ = auth_client
    student = await login(client, prefix, "student@example.com")
    record = "00000000-0000-0000-0000-000000000001"
    actions = [
        ("post", "/taxonomy/sync-tt09", {}),
        ("post", "/taxonomy/publish-majors", {"json": {"majors": []}}),
        ("post", "/taxonomy/import-excel?preview_only=true", {"files": {"file": ("test.csv", b"major_code,name\n7480101,Computer Science", "text/csv")}}),
        ("post", "/taxonomy/trend-agent/run", {"json": {}}),
        ("post", "/taxonomy/trend-agent/save", {"json": {"majors": []}}),
        ("patch", "/taxonomy/trend-agent/majors/7480101", {"json": {"trend_tier": "TIER_1"}}),
        ("delete", "/taxonomy/trend-agent/clear", {}),
        ("get", "/major-insights/7480101?refresh=true", {}),
        ("post", "/major-insights/7480101/regenerate", {}),
        ("delete", "/major-insights/7480101", {}),
        ("post", "/assessments/seed", {}),
        ("get", "/rag-governance/staging", {}),
        ("post", "/rag-governance/staging", {"json": {}}),
        ("get", f"/rag-governance/staging/{record}", {}),
        ("put", f"/rag-governance/staging/{record}", {"json": {}}),
        ("post", f"/rag-governance/staging/{record}/review", {"json": {}}),
        ("post", "/rag-governance/ingest/stream-a/upload", {"files": {"file": ("test.pdf", b"synthetic", "application/pdf")}}),
        ("post", "/rag-governance/discover/stream-b", {"json": {"major_code": "7480101", "major_title": "Computer Science"}}),
        ("get", "/rag-governance/llm-status", {}),
        ("post", "/rag-governance/test-llm-connection", {"json": {}}),
        ("post", "/rag-governance/update-llm-config", {"json": {}}),
    ]
    for headers, expected in (({}, 401), (student, 403)):
        for method, path, kwargs in actions:
            response = await getattr(client, method)(prefix + path, headers=headers, **kwargs)
            assert response.status_code == expected, (method, path, response.status_code)


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", PREFIXES)
async def test_cross_user_assessment_and_guidance_are_private(auth_client, prefix):
    from app.models.assessment import StudentAssessment
    client, sessions = auth_client
    assessment_id = uuid.uuid4()
    async with sessions() as db:
        db.add(StudentAssessment(id=assessment_id, user_id=OTHER_ID, riasec_scores={}, cognitive_preferences={}, raw_responses={"private_marker": "other-user-only"}))
        await db.commit()
    student = await login(client, prefix, "student@example.com")
    for path, body in [
        ("/rag-governance/chat", {"message": "Ngành học phù hợp", "assessment_id": str(assessment_id)}),
        ("/recommender/evaluate", {"assessment_id": str(assessment_id)}),
    ]:
        denied = await client.post(prefix + path, headers=student, json=body)
        assert denied.status_code == 404
        assert "other-user-only" not in denied.text
        guest = await client.post(prefix + path, json=body)
        assert guest.status_code == 401
    for path, body in [
        ("/rag-governance/chat", {"message": "Ngành học phù hợp", "user_id": str(OTHER_ID)}),
        ("/rag-governance/guidance-personalize", {"major_code": "7480101", "user_id": str(OTHER_ID)}),
    ]:
        assert (await client.post(prefix + path, headers=student, json=body)).status_code == 403


@pytest.mark.asyncio
async def test_google_forged_signature_and_disabled_db_user_rejected(auth_client, google_provider):
    client, sessions = auth_client
    signed, _, _ = google_provider
    credential = signed()
    header, payload, signature = credential.split(".")
    wrong = ".".join((header, payload, ("A" if signature[0] != "A" else "B") + signature[1:]))
    assert (await client.post("/api/identity/google-login", json={"credential": wrong})).status_code == 401
    async with sessions() as db:
        await db.execute(update(User).where(User.id == STUDENT_ID).values(is_active=False))
        await db.commit()
    assert (await client.post("/api/identity/google-login", json={"credential": credential})).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("field,limit", [("gender", 50), ("grade_level", 50), ("school_class", 50), ("school_name", 255)])
async def test_profile_fields_respect_database_width(auth_client, field, limit):
    client, _ = auth_client
    headers = await login(client, email="student@example.com")
    response = await client.put("/api/identity/profile", headers=headers, json={field: "x" * (limit + 1)})
    assert response.status_code == 422
    registered = await client.post("/api/identity/register", json={"email": "bounded@example.com", "password": PASSWORD, "full_name": "Học sinh", field: "x" * (limit + 1)})
    assert registered.status_code == 422


@pytest.mark.asyncio
async def test_google_nonfinite_expiry_is_unauthorized(auth_client, google_provider):
    client, _ = auth_client
    signed, _, _ = google_provider
    response = await client.post("/api/identity/google-login", json={"credential": signed(exp=float("inf"))})
    assert response.status_code == 401
