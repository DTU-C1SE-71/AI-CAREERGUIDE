"""Guest evaluation never impersonates a synthetic persisted account."""
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.schemas.recommender import EvaluateProfileRequest
from importlib import import_module

routes = import_module("app.services.recommender.router")

@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [routes.evaluate_majors_with_constraints, routes.analyze_aspiration_endpoint])
async def test_guest_saved_snapshot_is_rejected_before_query(handler):
    db = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await handler(EvaluateProfileRequest(assessment_id=uuid4()), current_user=None, db=db)
    assert error.value.status_code == 401
    db.execute.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [routes.evaluate_majors_with_constraints, routes.analyze_aspiration_endpoint])
async def test_guest_inline_profile_has_no_persisted_user_identity(handler, monkeypatch):
    evaluate = AsyncMock(return_value={"aspirationAnalysis": {}})
    monkeypatch.setattr(routes.service, "evaluate_dashboard_profile_bundle", evaluate)
    await handler(EvaluateProfileRequest(riasec_answers={}, cognitive_answers={}, grades_by_subject={}, aspiration={}), current_user=None, db=None)
    assert evaluate.await_args.kwargs["user_id"] is None
    assert evaluate.await_args.kwargs["persist_history"] is False
