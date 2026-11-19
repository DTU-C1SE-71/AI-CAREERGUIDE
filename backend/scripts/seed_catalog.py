"""Nạp danh mục/câu hỏi tường minh, không tạo tài khoản hay dữ liệu học sinh mẫu."""
import asyncio,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.core.database import AsyncSessionLocal,engine
from app.services.taxonomy.service import bulk_sync_majors,load_seed_majors
from app.db.seeds.seed_assessment_questions import seed_assessment_questions

async def run():
    async with AsyncSessionLocal() as db:
        result=await bulk_sync_majors(db,load_seed_majors())
        await seed_assessment_questions(db)
    print(f"Đã nạp danh mục {result['total']} ngành và bộ câu hỏi; không tạo tài khoản.")
    await engine.dispose()

if __name__=="__main__": asyncio.run(run())
