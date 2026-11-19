"""Khóa test vào DB tổng hợp trước khi import app/connection pool."""
import os
from urllib.parse import urlsplit

test_url=os.environ.get("AUDIT_TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
if not test_url.startswith("sqlite"):
    parsed=urlsplit(test_url)
    if parsed.hostname not in {"127.0.0.1","localhost","::1"} or parsed.path != "/careerguide_v9_test":
        raise RuntimeError("Chỉ cho phép PostgreSQL audit loopback chuyên dụng")
os.environ["ENVIRONMENT"]="test"
os.environ["DATABASE_URL"]="sqlite+aiosqlite:///:memory:"  # PG acceptance tạo pool/schema riêng.
os.environ["SECRET_KEY"]="synthetic-audit-test-signing-key-only"
for name in ("LLM_API_KEY","OPENAI_API_KEY","XAI_API_KEY","XKIRO_API_KEY","TAVILY_API_KEY","OPENROUTER_API_KEY","GOOGLE_CLIENT_SECRET","AI_CONFIG_ENCRYPTION_KEY"):
    os.environ[name]=""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base
import app.models

@pytest_asyncio.fixture
async def ai_runtime_db(tmp_path):
    engine=create_async_engine(f"sqlite+aiosqlite:///{(tmp_path/'runtime.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with sessions() as db:
        yield db
    await engine.dispose()


import asyncio
import pytest
from app.core.security import get_password_hash
from app.models.identity import User,UserRole
from app.services.taxonomy.service import bulk_sync_majors,load_seed_majors

@pytest.fixture
def real_catalog_api_db(tmp_path):
    import uuid
    from sqlalchemy.pool import NullPool
    path=tmp_path/"catalog-auth.db"
    engine=create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}",poolclass=NullPool)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async def prepare():
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            hashed=get_password_hash("synthetic-api-test-only")
            db.add_all([User(id=uuid.UUID("00000000-0000-0000-0000-000000000099"),email="admin-existing@example.com",full_name="Quản trị",hashed_password=hashed,role=UserRole.ADMIN,is_active=True),User(id=uuid.UUID("00000000-0000-0000-0000-000000000002"),email="student-existing@example.com",full_name="Học sinh",hashed_password=hashed,role=UserRole.STUDENT,is_active=True)])
            await db.commit()
            await bulk_sync_majors(db,load_seed_majors())
    asyncio.run(prepare())
    async def override():
        async with sessions() as db: yield db
    yield override
    asyncio.run(engine.dispose())
