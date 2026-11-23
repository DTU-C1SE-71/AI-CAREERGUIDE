"""Migration cộng thêm có phiên bản; không chạy tự động trong HTTP startup."""
from sqlalchemy import inspect, text
from app.core.database import Base
import app.models

VERSIONS = (
    "20261116_001_base",
    "20261116_002_profile_columns",
    "20261116_003_ai_runtime",
    "20261117_004_major_explanation",
    "20261119_005_email_otp",
    "20261123_006_chat_history",
)

async def migrate(engine):
    async with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(2026111601)"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(80) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        applied=set((await conn.execute(text("SELECT version FROM schema_migrations"))).scalars())
        if VERSIONS[0] not in applied:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"),{"v":VERSIONS[0]})
        if VERSIONS[1] not in applied:
            columns=await conn.run_sync(lambda c: {t:{x["name"] for x in inspect(c).get_columns(t)} for t in ("users","majors")})
            additions={"users":{"gender":"VARCHAR(50)","grade_level":"VARCHAR(50)","school_class":"VARCHAR(50)","school_name":"VARCHAR(255)"},"majors":{"category":"VARCHAR(100) NOT NULL DEFAULT 'Khác'"}}
            for table,fields in additions.items():
                for name,ddl in fields.items():
                    if name not in columns[table]:
                        await conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'))
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"),{"v":VERSIONS[1]})
        if VERSIONS[2] not in applied:
            from app.models.ai_config import AIRuntimeConfig, AIConfigAudit
            await conn.run_sync(lambda c: Base.metadata.create_all(c,tables=[AIRuntimeConfig.__table__,AIConfigAudit.__table__]))
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"),{"v":VERSIONS[2]})
        if VERSIONS[3] not in applied:
            from app.models.insight import MajorExplanationInsight
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[MajorExplanationInsight.__table__]))
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"), {"v": VERSIONS[3]})
        if VERSIONS[4] not in applied:
            from app.models.identity import EmailVerificationCode
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[EmailVerificationCode.__table__]))
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"), {"v": VERSIONS[4]})
        if VERSIONS[5] not in applied:
            from app.models.chat import ChatSession, ChatMessage
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=[ChatSession.__table__, ChatMessage.__table__]))
            await conn.execute(text("INSERT INTO schema_migrations(version) VALUES (:v)"), {"v": VERSIONS[5]})
        return list((await conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))).scalars())
