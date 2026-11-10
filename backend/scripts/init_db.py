import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import engine, Base
import app.models  # Ensure all models are registered
import app.modules.assessment.models  # Ensure modular assessment models are registered


async def init_database():
    print(f"Initializing database ({engine.name})...")
    async with engine.begin() as conn:
        if engine.name == "postgresql":
            print("Ensuring pgvector extension is enabled...")
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as exc:
                print(f"pgvector extension notice: {exc}")
        print("Creating database schema tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_database())
