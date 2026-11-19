import time
import weakref
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.ai_runtime import AIConfigError, ConfigSnapshot
from app.services.ai_config import service as config_service
from app.services.llamaindex_rag_orchestrator import counselor_connection


def snapshot(revision="a" * 64):
    return ConfigSnapshot(
        source_mode="DATABASE", protocol="openai_compatible",
        canonical_base_url="https://provider.example/v1", model="synthetic-model",
        auth_mode="BEARER", credential_binding=("openai_compatible", "https", "provider.example", 443, "/v1"),
        revision_token=revision, credential="synthetic-credential",
    )


@pytest.mark.asyncio
async def test_open_chat_receipt_has_no_five_minute_expiry_or_extra_provider_probe(monkeypatch):
    current = snapshot()
    monkeypatch.setattr(config_service, "resolve_snapshot", AsyncMock(return_value=current))
    provider = AsyncMock(return_value="OK")
    monkeypatch.setattr(counselor_connection.adapter, "chat", provider)
    clock = [100.0]
    monkeypatch.setattr(counselor_connection, "time", SimpleNamespace(
        monotonic=lambda: clock[0], perf_counter=time.perf_counter,
    ))
    opened = await counselor_connection.check_connection(object())
    clock[0] += 24 * 60 * 60
    for _ in range(3):
        assert await counselor_connection.verify_receipt(object(), opened["revision_token"])
    provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_chat_receipt_survives_worker_local_probe_state_reset(monkeypatch):
    monkeypatch.setattr(config_service, "resolve_snapshot", AsyncMock(return_value=snapshot()))
    provider = AsyncMock(return_value="OK")
    monkeypatch.setattr(counselor_connection.adapter, "chat", provider)
    opened = await counselor_connection.check_connection(object())
    monkeypatch.setattr(counselor_connection, "_STATES", weakref.WeakKeyDictionary())
    assert await counselor_connection.verify_receipt(object(), opened["revision_token"])
    provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_chat_receipt_is_opaque_bounded_and_rejects_tampering_or_rotation(monkeypatch):
    current = snapshot()
    resolver = AsyncMock(return_value=current)
    monkeypatch.setattr(config_service, "resolve_snapshot", resolver)
    provider = AsyncMock(return_value="OK")
    monkeypatch.setattr(counselor_connection.adapter, "chat", provider)
    opened = await counselor_connection.check_connection(object())
    token = opened["revision_token"]
    assert 32 <= len(token) <= 100
    assert current.revision_token not in token
    assert current.credential not in token
    tampered = ("B" if token[0] == "A" else "A") + token[1:]
    for invalid in (None, "", "x" * 101, "!" * len(token), tampered):
        assert not await counselor_connection.verify_receipt(object(), invalid)
    assert await counselor_connection.verify_receipt(object(), token)
    resolver.return_value = snapshot("b" * 64)
    assert not await counselor_connection.verify_receipt(object(), token)
    provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_config_resolution_failure_invalidates_receipt_without_probing(monkeypatch):
    resolver = AsyncMock(return_value=snapshot())
    monkeypatch.setattr(config_service, "resolve_snapshot", resolver)
    provider = AsyncMock(return_value="OK")
    monkeypatch.setattr(counselor_connection.adapter, "chat", provider)
    opened = await counselor_connection.check_connection(object())
    resolver.side_effect = AIConfigError("CONFIGURATION_CHANGED", "Configuration changed")
    assert not await counselor_connection.verify_receipt(object(), opened["revision_token"])
    provider.assert_awaited_once()
