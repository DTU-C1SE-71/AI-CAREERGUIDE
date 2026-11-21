"""Áp dụng migration cộng thêm trên DB đã cấu hình; hỗ trợ bootstrap Admin qua biến môi trường (không hardcode mật khẩu)."""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.db.migrations import migrate
from app.models.identity import User, UserRole


async def bootstrap_admin_from_env() -> None:
    """Tạo hoặc cấp quyền Admin khi đặt BOOTSTRAP_ADMIN_EMAIL (và BOOTSTRAP_ADMIN_PASSWORD nếu tạo mới)."""
    email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
    if not email:
        return
    password = (os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
    full_name = (os.getenv("BOOTSTRAP_ADMIN_NAME") or "Quản trị viên Hệ thống").strip() or "Quản trị viên Hệ thống"
    reset_pw = (os.getenv("BOOTSTRAP_ADMIN_RESET_PASSWORD") or "").strip().lower() in {"1", "true", "yes"}

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            changed = False
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if reset_pw and len(password) >= 8:
                existing.hashed_password = get_password_hash(password)
                changed = True
            if changed:
                await db.commit()
                print(f"Bootstrap Admin: updated ADMIN privileges for {email}.", flush=True)
            else:
                print(f"Bootstrap Admin: {email} is already an active ADMIN.", flush=True)
            return

        if len(password) < 8:
            print(
                f"WARNING: BOOTSTRAP_ADMIN_EMAIL={email} is set, but BOOTSTRAP_ADMIN_PASSWORD is missing or < 8 chars; skipping creation.",
                flush=True,
            )
            return

        db.add(
            User(
                email=email,
                full_name=full_name,
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        await db.commit()
        print(f"Bootstrap Admin: created ADMIN account for {email}.", flush=True)


async def init_database():
    try:
        versions = await asyncio.wait_for(migrate(engine), timeout=20.0)
        print("Applied schema versions: " + ", ".join(versions), flush=True)
    except asyncio.TimeoutError:
        print("WARNING: init_db migration timed out after 20s; continuing startup.", flush=True)

    try:
        await asyncio.wait_for(bootstrap_admin_from_env(), timeout=15.0)
    except Exception as exc:
        print(f"WARNING: bootstrap_admin_from_env failed: {exc}", flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
