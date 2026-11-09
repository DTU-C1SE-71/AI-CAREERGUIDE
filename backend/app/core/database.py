import logging
import sqlite3
import uuid
from pathlib import Path
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings

logger = logging.getLogger("careerguide.database")

# Register UUID adapter for SQLite so uuid.UUID objects bind seamlessly as strings
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

# ---------------------------------------------------------------------------
# Cross-Dialect SQLite Type Compilers
# Ensures PostgreSQL-specific types (UUID, JSONB, Vector) compile seamlessly on SQLite
# ---------------------------------------------------------------------------
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

try:
    from pgvector.sqlalchemy import Vector
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except ImportError:
    pass


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Database Engine Initialization
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = BACKEND_DIR / "backend" / "app" / "db" / "careerguide_active.db"
if not DEFAULT_SQLITE_PATH.exists():
    DEFAULT_SQLITE_PATH = BACKEND_DIR / "app" / "db" / "careerguide_active.db"

raw_url = settings.DATABASE_URL or ""

# Resolve relative sqlite paths if needed
if "careerguide_active.db" in raw_url:
    db_url = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
elif raw_url.startswith("sqlite"):
    db_url = raw_url
else:
    db_url = raw_url

is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
    logger.info("Using SQLite async database engine: %s", db_url)
else:
    connect_args = {}
    if "supabase.com" in db_url or "aws-" in db_url:
        connect_args["ssl"] = "require"
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
    )
    logger.info("Using PostgreSQL async database engine.")

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Dependency that provides an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
