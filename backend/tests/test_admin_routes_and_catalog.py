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


@pytest.mark.asyncio
async def test_list_majors_includes_moet_floor_and_imported_benchmark_score(catalog_db):
    from app.services.taxonomy.tt74_reference import parse_excel_or_csv_sheets

    sessions, _, _ = catalog_db
    csv_bytes = (
        "field_code,field_name,group_code,group_name,major_code,major_name,benchmark_score\n"
        "72,SỨC KHỎE,7201,Y học,7720101,Y khoa,\n"
        "14,KHOA HỌC GIÁO DỤC,1402,Đào tạo giáo viên,7140201,Giáo dục Mầm non,\n"
        "38,PHÁP LUẬT,3801,Luật,7380101,Luật,\n"
        "48,CNTT,4801,Máy tính,7480101,Khoa học máy tính,\n"
        "48,CNTT,4802,CNTT,7480201,Công nghệ thông tin,26.5\n"
    ).encode("utf-8")

    _, parsed_majors, _ = parse_excel_or_csv_sheets(csv_bytes, "sample.csv")
    assert len(parsed_majors) == 5

    async with sessions() as db:
        await service.bulk_sync_majors(db, parsed_majors, deactivate_missing=True)
        listed = await service.list_majors(db)

    by_code = {item["major_code"]: item for item in listed}
    assert by_code["7720101"]["benchmark_score"] == 22.5
    assert by_code["7720101"]["benchmark_source"] == "MOET_FLOOR"
    assert by_code["7140201"]["benchmark_score"] == 19.0
    assert by_code["7380101"]["benchmark_score"] == 18.0
    assert by_code["7480101"]["benchmark_score"] == 15.0
    assert by_code["7480201"]["benchmark_score"] == 26.5
    assert by_code["7480201"]["cutoff_score"] == 26.5
    assert by_code["7480201"]["benchmark_source"] == "IMPORTED"


def test_excel_template_includes_benchmark_score_columns():
    from pathlib import Path
    from app.services.taxonomy.tt74_reference import _parse_xlsx_all_sheets

    template_path = (
        Path(__file__).resolve().parent.parent
        / "app"
        / "db"
        / "seeds"
        / "MOET_Major_Import_Template_Standard.xlsx"
    )
    sheets, _ = _parse_xlsx_all_sheets(template_path.read_bytes())
    by_name = {name: rows for name, rows in sheets}

    sheet1_headers = by_name["MAU_NHAP_NGANH_CHUAN"][0]
    assert len(sheet1_headers) == 21
    assert sheet1_headers[-1] == "benchmark_score"

    sheet2_headers = by_name["BANG_TRA_CUU_CIP_RIASEC"][0]
    assert sheet2_headers[-1] == "default_benchmark_score"
    assert any("benchmark_score" in cell for row in by_name["HUONG_DAN_VA_PROMPT_AI"] for cell in row if cell)
