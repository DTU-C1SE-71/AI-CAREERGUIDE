import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "app" / "db" / "careerguide.db"
conn = sqlite3.connect(str(db_path))
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()
print(f"Total Tables in careerguide.db: {len(tables)}\n")
for t in tables:
    name = t[0]
    count = c.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    print(f"  - {name:<32}: {count} records")
conn.close()
