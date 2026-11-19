"""Áp dụng migration cộng thêm trên DB đã cấu hình; không seed tài khoản mặc định."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.core.database import engine
from app.db.migrations import migrate

async def init_database():
    try:
        versions = await asyncio.wait_for(migrate(engine), timeout=20.0)
        print("Applied schema versions: " + ", ".join(versions), flush=True)
    except asyncio.TimeoutError:
        print("WARNING: init_db migration timed out after 20s; continuing startup.", flush=True)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
