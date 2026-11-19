"""Xoay khóa offline: dừng worker, backup DB, chạy CLI rồi cập nhật ENV mới.

Khóa cũ đọc AI_CONFIG_ENCRYPTION_KEY/ID. Khóa mới chỉ đọc
NEW_AI_CONFIG_ENCRYPTION_KEY và NEW_AI_CONFIG_ENCRYPTION_KEY_ID.
Không truyền khóa qua tham số dòng lệnh và không ghi khóa vào stdout/log.
"""
import asyncio
import hashlib
import hmac
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.ai_runtime import AIConfigError, canonical_target, validate_credential, validate_model
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.ai_config import AIRuntimeConfig, AIConfigAudit
from app.services.ai_config.service import _current, _copy_row, _check_revision


async def rotate_key(db, new_key: str, new_key_id: str, *, expected_revision: str | None = None) -> str:
    """Mã hóa lại cùng credential nguyên tử; caller phải dừng mọi worker trước."""
    if not new_key_id or len(new_key_id) > 64 or not new_key_id.isascii() or not all(c.isalnum() or c in "._-" for c in new_key_id):
        raise AIConfigError("INVALID_KEY_ID", "ID khóa mới không hợp lệ.")
    if not new_key or hmac.compare_digest(new_key, settings.SECRET_KEY) or hmac.compare_digest(new_key, settings.AI_CONFIG_ENCRYPTION_KEY):
        raise AIConfigError("INVALID_ROTATION_KEY", "Khóa mới phải riêng biệt với khóa cũ và khóa JWT.")
    if new_key_id == settings.AI_CONFIG_ENCRYPTION_KEY_ID:
        raise AIConfigError("INVALID_KEY_ID", "Xoay khóa cần ID mới khác ID đang dùng.")
    try:
        target_cipher = Fernet(new_key.encode("ascii"))
    except (ValueError, UnicodeError):
        raise AIConfigError("INVALID_ROTATION_KEY", "Khóa mới không phải khóa Fernet hợp lệ.") from None
    try:
        row = (await db.execute(select(AIRuntimeConfig).where(AIRuntimeConfig.id == 1).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        original = _copy_row(row)
        state = _current(original)
        if expected_revision is not None:
            _check_revision(state, expected_revision)
        if not original or state["locked_code"] or state["credential_state"] != "SET" or state["profile"]["source_mode"] != "DATABASE" or not state["credential"]:
            raise AIConfigError("ROTATION_UNAVAILABLE", "Cần credential DATABASE giải mã được bằng khóa cũ để xoay khóa.", 409)
        profile = state["profile"]
        _, actual_binding = canonical_target(profile["base_url"], profile["protocol"])
        if actual_binding != profile["credential_binding"]:
            raise AIConfigError("TARGET_BINDING_MISMATCH", "Binding credential không hợp lệ; không xoay khóa.")
        validate_model(profile["model"])
        secret = validate_credential(state["credential"])
        ciphertext = target_cipher.encrypt(secret.encode()).decode()
        conditions = [getattr(AIRuntimeConfig, name) == original[name] for name in ("id", "version", "profile", "credential_state", "secret_ciphertext", "secret_fingerprint", "encryption_key_id")]
        result = await db.execute(update(AIRuntimeConfig).where(*conditions).values(secret_ciphertext=ciphertext, encryption_key_id=new_key_id, version=original["version"] + 1).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise AIConfigError("REVISION_CONFLICT", "Cấu hình đã đổi trong lúc xoay khóa.", 409)
        db.add(AIConfigAudit(actor_id="operator:offline-rotation", action="ROTATE_ENCRYPTION_KEY", revision_token=state["revision_token"], summary={"old_key_id": original["encryption_key_id"], "new_key_id": new_key_id}))
        await db.commit()
        return new_key_id
    except Exception:
        await db.rollback()
        raise


async def main():
    try:
        async with AsyncSessionLocal() as db:
            key_id = await rotate_key(db, os.environ.get("NEW_AI_CONFIG_ENCRYPTION_KEY", ""), os.environ.get("NEW_AI_CONFIG_ENCRYPTION_KEY_ID", ""))
        print(f"Đã xoay khóa mã hóa sang ID {key_id}. Cập nhật ENV trước khi khởi động worker.")
        return 0
    except Exception:
        print("Không thể xoay khóa. Kiểm tra khóa/ID, migration và DB backup; không ghi secret vào log.", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
