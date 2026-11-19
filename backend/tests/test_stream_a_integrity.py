"""@blast-radius: integration — StreamA không được giả vờ lưu khi DB lỗi."""
from unittest.mock import AsyncMock,MagicMock
import pytest
from fastapi import HTTPException
from app.services.llamaindex_rag_orchestrator.stream_a_ingest import ingest_moet_circular

@pytest.mark.asyncio
async def test_staging_database_failure_never_returns_invented_ids():
    db=AsyncMock();db.add=MagicMock();result=MagicMock();result.scalar_one_or_none.return_value=None;db.execute.return_value=result
    db.commit.side_effect=RuntimeError("synthetic-private-db-error")
    with pytest.raises(HTTPException) as caught:
        await ingest_moet_circular(db,"7480201 Công nghệ thông tin A00".encode(),"sample.txt")
    assert caught.value.status_code==503
    assert "synthetic-private" not in str(caught.value.detail)
    db.rollback.assert_awaited()
