"""Dữ liệu tổng hợp cho nghiệm thu; từ chối mọi DB ngoài PostgreSQL audit loopback."""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import text,select
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.core.config import settings
from app.core.database import engine,AsyncSessionLocal
from app.core.security import get_password_hash
from app.db.migrations import migrate
from app.models.identity import User,UserRole
from app.services.taxonomy.service import bulk_sync_majors,load_seed_majors
from app.db.seeds.seed_assessment_questions import seed_assessment_questions

async def prepare():
    if settings.ENVIRONMENT != "test" or engine.url.host not in {"127.0.0.1","localhost","::1"} or engine.url.database != "careerguide_v9_test":
        raise RuntimeError("Từ chối: chỉ cho phép PostgreSQL audit loopback")
    async with engine.connect() as conn:
        actual=(await conn.execute(text("SELECT current_database(), current_setting('server_version_num')"))).one()
        if actual[0]!="careerguide_v9_test" or not str(actual[1]).startswith("16"):
            raise RuntimeError("Đích kết nối không đúng DB/engine audit")
    versions=await migrate(engine)
    async with AsyncSessionLocal() as db:
        for email,role in (("admin-audit@example.com",UserRole.ADMIN),("student-audit@example.com",UserRole.STUDENT),("other-audit@example.com",UserRole.STUDENT)):
            user=(await db.execute(select(User).where(User.email==email))).scalar_one_or_none()
            if user is None:
                db.add(User(id=uuid.uuid5(uuid.NAMESPACE_URL,email),email=email,full_name="Nguyễn Kiểm Thử" if role==UserRole.STUDENT else "Quản trị Kiểm Thử",hashed_password=get_password_hash("synthetic-audit-only-password"),role=role,is_active=True))
        await db.commit()
        await bulk_sync_majors(db,load_seed_majors())
        await seed_assessment_questions(db)
    print("Verified PostgreSQL16 dedicated DB; synthetic accounts, catalog and questionnaires prepared.")
    print("Migration versions: " + ",".join(versions))
    await engine.dispose()

if __name__=="__main__":
    asyncio.run(prepare())
