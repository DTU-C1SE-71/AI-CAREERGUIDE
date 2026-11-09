import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    sys.stdout.reconfigure(encoding='utf-8')
    url = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_careerguide"
    print(f"Connecting to: {url}")
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT version();"))
            print("PostgreSQL Version:", res.scalar())
            
            tables_res = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
            ))
            tables = [r[0] for r in tables_res.fetchall()]
            print(f"Total tables ({len(tables)}):", tables)
            
            # Check row counts in key tables
            for table in tables:
                count_res = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}";'))
                print(f"  - {table}: {count_res.scalar()} rows")
        print("\nDATABASE STATUS: CONNECTED AND OPERATIONAL!")
    except Exception as e:
        print("\nDATABASE STATUS: FAILED TO CONNECT!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
