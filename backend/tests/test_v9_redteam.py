"""Phản ví dụ độc lập cho các bất biến V9 chưa được đóng."""
import uuid

from app.schemas.recommender import MajorRecommendationItem


def _item(breakdown):
    return MajorRecommendationItem(
        rank=1,
        major_id=uuid.uuid4(),
        major_code="7480101",
        major_name="Khoa học máy tính",
        overall_score=0.97,
        score_riasec=0.97,
        score_academic=0.97,
        score_preference=0.97,
        score_breakdown=breakdown,
        explanation="Xếp hạng tạm thời",
    )


def test_unknown_interest_evidence_never_becomes_published_match_score():
    """Counterfactual: điểm xếp hạng cao nhưng không có evidence không được thành 97% phù hợp."""
    item = _item({"pillar_availability": {}, "interest_evidence_status": "UNKNOWN"})
    assert item.match is None
    assert item.score_breakdown.get("suitability_status") in {None, "UNDETERMINED"}


def test_missing_interest_evidence_status_fails_closed_for_serialization():
    """Counterfactual: DTO legacy thiếu metadata không được mặc định là COMPLETE."""
    item = _item({"pillar_availability": {"w_academic": True}})
    assert item.match is None
    assert item.score_breakdown.get("suitability_status") in {None, "UNDETERMINED"}


import httpx
import pytest
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.identity import User, UserRole
from app.models.taxonomy import Major


@pytest.mark.asyncio
@pytest.mark.parametrize("incoming", [[{}], [{"major_code": "invalid-code", "name": "Không phải ngành hợp lệ"}]])
async def test_invalid_catalog_publish_cannot_destroy_existing_catalog(ai_runtime_db, incoming):
    db = ai_runtime_db
    admin = User(email="redteam-admin@example.com", full_name="Quản trị tổng hợp", hashed_password=get_password_hash("synthetic-redteam-password"), role=UserRole.ADMIN)
    existing = Major(major_code="7480101", name="Khoa học máy tính", riasec_vector={code: 0.5 for code in "RIASEC"}, cognitive_attributes={}, industry_outlook="Tổng hợp")
    db.add_all([admin, existing])
    await db.commit()
    async def isolated_db():
        yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = isolated_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
            login = await client.post("/api/identity/login", json={"email": "redteam-admin@example.com", "password": "synthetic-redteam-password"})
            assert login.status_code == 200
            response = await client.post("/api/taxonomy/publish-majors", headers={"Authorization": "Bearer " + login.json()["access_token"]}, json={"majors": incoming})
            rows = (await db.execute(select(Major))).scalars().all()
            assert response.status_code == 422
            assert [row.major_code for row in rows] == ["7480101"]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_import_rejects_invented_codes_missing_names_and_partial_invalid_rows():
    from app.services.taxonomy.tt74_reference import parse_excel_or_csv_sheets
    for csv_data in (
        "major_code,name\n7480101,\n",
        "major_code,name\ncode7480101,Khoa học máy tính\n",
        "major_code,name\n7480101,Khoa học máy tính\ninvalid,Bản ghi lỗi\n",
    ):
        with pytest.raises(ValueError):
            parse_excel_or_csv_sheets(csv_data.encode(), "test.csv")


def test_catalog_enrichment_preserves_explicit_inactive_and_real_identity():
    from app.services.taxonomy.tt74_reference import auto_enrich_major_record, parse_excel_or_csv_sheets
    item = auto_enrich_major_record({"major_code": "480101", "name": "Khoa học máy tính", "is_active": False})
    assert item["major_code"] == "7480101" and item["is_active"] is False
    _, rows, _ = parse_excel_or_csv_sheets("major_code,name,is_active\n7480101,Khoa học máy tính,false\n".encode(), "test.csv")
    assert rows[0]["is_active"] is False
