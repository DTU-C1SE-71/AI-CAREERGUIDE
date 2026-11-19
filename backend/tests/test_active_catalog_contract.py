"""Authoritative catalog boundary shared across ranking and advisory endpoints."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services.recommender.catalog import load_active_catalog, get_active_major_context


def database(rows):
    return SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: rows))))


@pytest.mark.asyncio
async def test_imported_catalog_never_revives_absent_seed_majors(monkeypatch):
    from app.services.taxonomy import service
    monkeypatch.setattr(service, "load_seed_majors", lambda: [{"major_code": "7480201"}])
    active = SimpleNamespace(major_code="7340101", is_active=True)
    retired = SimpleNamespace(major_code="7480201", is_active=False)
    assert await load_active_catalog(database([active, retired])) == [active]
    with pytest.raises(HTTPException) as error:
        await get_active_major_context(database([active, retired]), "7480201")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_inactive_only_database_stays_empty(monkeypatch):
    from app.services.taxonomy import service
    monkeypatch.setattr(service, "load_seed_majors", lambda: [{"major_code": "7480201"}])
    assert await load_active_catalog(database([SimpleNamespace(is_active=False)])) == []


@pytest.mark.asyncio
async def test_explicit_no_database_mode_uses_active_seed_entries(monkeypatch):
    from app.services.taxonomy import service
    active = {"major_code": "7480201", "name": "Computer Science", "blocks": ["A00"]}
    monkeypatch.setattr(service, "load_seed_majors", lambda: [active, {"major_code": "7340101", "is_active": False}])
    assert await load_active_catalog(None) == [active]
    context = await get_active_major_context(None, "7480201")
    assert context["blocks"] == ["A00"]
    assert context["careers"] == []


@pytest.mark.asyncio
async def test_database_error_does_not_silently_substitute_catalog():
    db = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("private-database-detail")))
    with pytest.raises(HTTPException) as error:
        await load_active_catalog(db)
    assert error.value.status_code == 503
    assert "private-database-detail" not in error.value.detail


@pytest.mark.asyncio
async def test_empty_persisted_catalog_is_not_repopulated(monkeypatch):
    from app.services.taxonomy import service
    monkeypatch.setattr(service, "load_seed_majors", lambda: [{"major_code": "7480201"}])
    assert await load_active_catalog(database([])) == []
