"""@blast-radius: integration — provider và DB không tạo bằng chứng xu hướng giả."""
import json
import pytest
from fastapi import HTTPException
from app.core.ai_runtime import ConfigSnapshot,canonical_target
from app.services.taxonomy import trend_agent

@pytest.mark.asyncio
@pytest.mark.parametrize("output", [
    "not-json", "{}", "[]",
    '[{"major_code":7480101,"trend_tier":"TIER_1","trend_reason":"reason"}]',
    '[{"major_code":"9999999","trend_tier":"TIER_1","trend_reason":"reason"}]',
    '[{"major_code":"7480101","trend_tier":"TIER_1","trend_reason":7}]',
])
async def test_malformed_provider_never_becomes_deterministic_success(monkeypatch,output):
    from app.services.ai_config import adapter
    async def controlled_provider(*args,**kwargs): return output
    monkeypatch.setattr(adapter,"chat",controlled_provider)
    base,binding=canonical_target("https://example.com/v1")
    snapshot=ConfigSnapshot("DATABASE","openai_compatible",base,"test-model","NONE",tuple(binding.values()),"a"*64,None)
    candidate={"major_code":"7480101","major_name":"Khoa học máy tính","category":"CNTT","macro_suggested_tier":"TIER_1","matched_topics":[]}
    with pytest.raises(HTTPException) as error:
        await trend_agent._refine_tiers_with_llm("synthetic",[],[candidate],["CNTT"],snapshot=snapshot)
    assert error.value.status_code==502

@pytest.mark.asyncio
async def test_failed_trend_write_never_reports_saved(ai_runtime_db,monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr(ai_runtime_db,"commit",AsyncMock(side_effect=RuntimeError("synthetic-private-database-error")))
    with pytest.raises(HTTPException) as error:
        await trend_agent.apply_trending_markers(ai_runtime_db,{"majors":{}})
    assert error.value.status_code==503
    assert "synthetic-private" not in str(error.value.detail)
