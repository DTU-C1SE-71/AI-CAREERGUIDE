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


def test_removed_fabrication_tables_do_not_exist():
    for forbidden in (
        "CATEGORY_BASELINE_REPRESENTATIVES",
        "CATEGORY_TREND_QUOTA",
        "TREND_TOPIC_CLUSTERS",
    ):
        assert not hasattr(trend_agent, forbidden)


def test_extract_candidates_strict_evidence_only_no_fabrication():
    catalog = [
        {"major_code": "7480107", "name": "Trí tuệ nhân tạo", "category": "Máy tính và công nghệ thông tin"},
        {"major_code": "7640101", "name": "Thú y", "category": "Thú y"},
        {"major_code": "7220205", "name": "Ngôn ngữ Đức", "category": "Nhân văn"},
        {"major_code": "7440118", "name": "Hóa phân tích", "category": "Khoa học tự nhiên"},
        {"major_code": "7380101", "name": "Luật", "category": "Pháp luật"},
    ]
    articles = [
        {
            "title": "Nhu cầu tuyển dụng ngành Trí tuệ nhân tạo tăng mạnh trong năm 2026",
            "url": "https://example.com/ai-1",
            "source": "VnExpress",
            "snippet": "Nhiều doanh nghiệp công nghệ mở rộng đội ngũ kỹ sư Trí tuệ nhân tạo.",
        },
        {
            "title": "Các tập đoàn tăng tốc tuyển kỹ sư AI và Generative AI tại Việt Nam",
            "url": "https://example.com/ai-2",
            "source": "Tuổi Trẻ",
            "snippet": "Xu hướng tuyển dụng tập trung vào Generative AI và Machine Learning.",
        },
        {
            "title": "Dự báo thời tiết miền Trung cuối tuần có mưa rào và luật giao thông mới",
            "url": "https://example.com/weather",
            "source": "Báo Thời Tiết",
            "snippet": "Ai cũng nên mang theo áo mưa khi di chuyển ngoài trời.",
        },
    ]

    candidates, all_categories = trend_agent._extract_candidates_from_articles(articles, catalog)
    assert len(all_categories) == 5
    assert [c["major_code"] for c in candidates] == ["7480107"]
    source_urls = [s["url"] for s in candidates[0]["sources"]]
    assert set(source_urls) == {"https://example.com/ai-1", "https://example.com/ai-2"}
    assert "https://example.com/weather" not in source_urls


def test_extract_candidates_zero_mentions_returns_empty():
    catalog = [
        {"major_code": "7480107", "name": "Trí tuệ nhân tạo", "category": "Máy tính và công nghệ thông tin"},
        {"major_code": "7640101", "name": "Thú y", "category": "Thú y"},
        {"major_code": "7380101", "name": "Luật", "category": "Pháp luật"},
    ]
    articles = [
        {
            "title": "Ai cũng nên theo dõi bản tin thời tiết cuối tuần",
            "url": "https://example.com/unrelated",
            "source": "Tin Tổng Hợp",
            "snippet": "Không có thông tin tuyển dụng hay đào tạo ngành nghề đại học nào ở đây.",
        }
    ]
    candidates, _ = trend_agent._extract_candidates_from_articles(articles, catalog)
    assert candidates == []


@pytest.mark.asyncio
async def test_run_trend_discovery_agent_returns_empty_honestly(monkeypatch):
    from app.services.ai_config import service as ai_cfg_service
    from app.services.taxonomy import service as tax_service

    base, binding = canonical_target("https://example.com/v1")
    snapshot = ConfigSnapshot(
        "DATABASE", "openai_compatible", base, "test-model", "NONE", tuple(binding.values()), "a" * 64, None
    )

    async def fake_resolve(*args, **kwargs):
        return snapshot

    monkeypatch.setattr(ai_cfg_service, "resolve_snapshot", fake_resolve)
    monkeypatch.setattr(
        tax_service,
        "load_seed_majors",
        lambda: [
            {"major_code": "7480107", "name": "Trí tuệ nhân tạo", "category": "CNTT"},
            {"major_code": "7640101", "name": "Thú y", "category": "Thú y"},
        ],
    )

    result = await trend_agent.run_trend_discovery_agent(
        db=None,
        focus_query="thời tiết cuối tuần",
        override_articles=[
            {
                "title": "Bản tin thời tiết không nhắc ngành học nào",
                "url": "https://example.com/weather",
                "source": "Báo Thời Tiết",
                "snippet": "Trời nắng nhẹ trên diện rộng.",
            }
        ],
    )
    assert result["status"] == "no_matching_majors"
    assert result["trending_majors"] == []
    assert result["total_trending_marked"] == 0
    assert result["pending_save"] is False

