"""Áp dụng migration cộng thêm trên DB đã cấu hình; không seed tài khoản mặc định."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.core.database import engine
from app.db.migrations import migrate

async def init_database():
    try:
        versions=await migrate(engine)
        print("Applied schema versions: " + ", ".join(versions))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
