"""@blast-radius: api — account demographics come from the saved profile."""
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.recommender import EvaluateProfileRequest

routes = import_module("app.services.recommender.router")
ENDPOINTS = [routes.evaluate_majors_with_constraints, routes.analyze_aspiration_endpoint]


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", ENDPOINTS)
@pytest.mark.parametrize("gender,grade_level", [
    ("Nam", "Lớp 10"), (None, None), ("Nam", None), (None, "Lớp 10"),
])
async def test_signed_in_evaluation_uses_saved_demographics_even_when_missing(monkeypatch, handler, gender, grade_level):
    evaluate = AsyncMock(return_value={"aspirationAnalysis": {}})
    monkeypatch.setattr(routes.service, "evaluate_dashboard_profile_bundle", evaluate)
    user = SimpleNamespace(id=uuid4(), full_name="Synthetic student", gender=gender, grade_level=grade_level)
    payload = EvaluateProfileRequest(gender="Nữ", grade_level="Lớp 12")

    await handler(payload, current_user=user, db=None)

    forwarded = evaluate.await_args.kwargs
    assert forwarded["user_id"] == user.id
    assert forwarded["gender"] == gender
    assert forwarded["grade_level"] == grade_level
    assert forwarded["inline_profile"]["gender"] == gender
    assert forwarded["inline_profile"]["grade_level"] == grade_level


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", ENDPOINTS)
async def test_guest_evaluation_preserves_explicit_demographic_input(monkeypatch, handler):
    evaluate = AsyncMock(return_value={"aspirationAnalysis": {}})
    monkeypatch.setattr(routes.service, "evaluate_dashboard_profile_bundle", evaluate)

    await handler(EvaluateProfileRequest(gender="Nữ", grade_level="Lớp 11"), current_user=None, db=None)

    forwarded = evaluate.await_args.kwargs
    assert forwarded["user_id"] is None
    assert forwarded["gender"] == "Nữ"
    assert forwarded["grade_level"] == "Lớp 11"
    assert forwarded["inline_profile"]["gender"] == "Nữ"
    assert forwarded["inline_profile"]["grade_level"] == "Lớp 11"
