from pathlib import Path
from db import get_connection

sql = (Path(__file__).parent.parent / "sql" / "seed_forms.sql").read_text(encoding="utf-8")
with get_connection() as conn:
    conn.execute(sql)
print("Seeded") 