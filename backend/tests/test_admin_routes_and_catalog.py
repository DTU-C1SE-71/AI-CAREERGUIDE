"""API quyền thực và danh mục không tự hồi sinh khi đã xóa/vô hiệu hóa."""
import uuid
from unittest.mock import AsyncMock
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.identity import User, UserRole
from app.models.taxonomy import Major
from app.main import app
from app.services.taxonomy import service

@pytest_asyncio.fixture
async def catalog_db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'catalog.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    student=User(id=uuid.uuid4(),email="student-audit@example.test",full_name="Học sinh kiểm thử",hashed_password=get_password_hash("synthetic-only-password"),role=UserRole.STUDENT,is_active=True)
    admin=User(id=uuid.uuid4(),email="admin-audit@example.test",full_name="Quản trị kiểm thử",hashed_password=get_password_hash("synthetic-only-password"),role=UserRole.ADMIN,is_active=True)
    async with sessions() as db:
        db.add_all([student,admin]);await db.commit()
    async def override():
        async with sessions() as db: yield db
    app.dependency_overrides[get_db]=override
    yield sessions,student,admin
    app.dependency_overrides.pop(get_db,None)
    await engine.dispose()

@pytest.mark.asyncio
async def test_catalog_mutations_are_guarded_on_both_aliases(catalog_db):
    _,student,_=catalog_db
    token=create_access_token(str(student.id),role="STUDENT")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
        for prefix in ("/api","/api/v1"):
            for path,body in (("/taxonomy/sync-tt09",{}),("/taxonomy/publish-majors",{"majors":[]}),("/assessments/seed",{})):
                guest=await client.post(prefix+path,json=body)
                denied=await client.post(prefix+path,json=body,headers={"Authorization":f"Bearer {token}"})
                assert guest.status_code==401,(path,guest.status_code)
                assert denied.status_code==403,(path,denied.status_code)
            for headers,expected in (({},401),({"Authorization":f"Bearer {token}"},403)):
                response=await client.post(prefix+"/taxonomy/import-excel",files={"file":("sample.csv",b"code,name\n", "text/csv")},headers=headers)
                assert response.status_code==expected

@pytest.mark.asyncio
async def test_empty_catalog_get_never_seeds_or_resurrects(catalog_db):
    sessions,_,_=catalog_db
    async with sessions() as db:
        assert await service.list_majors(db)==[]
        assert list((await db.execute(select(Major))).scalars())==[]

@pytest.mark.asyncio
async def test_inactive_detail_does_not_fall_back_to_seed(catalog_db):
    sessions,_,_=catalog_db
    async with sessions() as db:
        db.add(Major(id=uuid.uuid4(),major_code="7480101",name="Ngành đã tắt",riasec_vector={"I": 1},cognitive_attributes={},industry_outlook="Dữ liệu kiểm thử",is_active=False))
        await db.commit()
        assert await service.get_major_by_code(db,"7480101") is None

@pytest.mark.asyncio
async def test_catalog_database_error_is_not_success_or_seed():
    from fastapi import HTTPException
    db=AsyncMock();db.execute.side_effect=RuntimeError("synthetic-sensitive-db-error")
    with pytest.raises(HTTPException) as caught:
        await service.list_majors(db)
    assert caught.value.status_code==503
    assert "synthetic-sensitive" not in str(caught.value.detail)
