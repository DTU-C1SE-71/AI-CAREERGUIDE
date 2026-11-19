"""@blast-radius: api — những route alias trước đây chưa được đi qua."""
import pytest
import httpx
from app.main import app
from app.core.database import get_db

@pytest.mark.asyncio
async def test_guest_recommended_majors_is_empty_or_unassessed_never_500():
    async def no_db(): yield None
    app.dependency_overrides[get_db]=no_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url="http://test") as client:
            for prefix in ("/api","/api/v1"):
                response=await client.get(prefix+"/recommender/majors")
                assert response.status_code==422
                assert response.json()["detail"]["code"]=="CHUA_HOAN_THANH_BAI_TEST"
    finally: app.dependency_overrides.pop(get_db,None)


@pytest.mark.asyncio
async def test_short_roadmap_has_four_weeks_of_existing_topics(monkeypatch):
    import uuid
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.services.gap_roadmap_engine import service as gaps
    from app.services.llamaindex_rag_orchestrator.guidance_rag import personalize_guidance
    from app.schemas.rag import GuidancePersonalizationRequest
    monkeypatch.setattr(gaps,"get_cached_major_roadmap",AsyncMock(return_value=SimpleNamespace(roadmap_data={"milestones":[{"title":"Chủ đề đã có","actions":["Thực hành cơ bản"]}]},title="Mẫu khám phá",is_fallback=True)))
    monkeypatch.setattr(gaps,"get_student_major_skill_gaps",AsyncMock(return_value={"missing_prerequisites":[],"missing_target_skills":[]}))
    result=await personalize_guidance(None,GuidancePersonalizationRequest(major_code="7480101",user_id=uuid.uuid4(),weekly_hours_available=6))
    assert len(result.schedule)==4
    assert [week.week_number for week in result.schedule]==[1,2,3,4]
    assert all(week.estimated_hours==6 and week.recommended_reading=="Chủ đề đã có" for week in result.schedule)
    assert result.is_fallback
