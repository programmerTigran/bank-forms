"""
queries.py
Loads SQL from sql/queries/<name>.sql (cached after the first read), so the SQL
stays out of the .py files. Used by db.py.
"""

# ============================================================
# 1. IMPORTS AND CONSTANTS
# ============================================================

from functools import lru_cache
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql" / "queries"

# ============================================================
# 2. LOADING
# ============================================================

@lru_cache(maxsize=None)
def _read(name):
    path = SQL_DIR / (name + ".sql")
    if not path.exists():
        raise FileNotFoundError("Query file not found: " + str(path))
    return path.read_text(encoding="utf-8").strip()


def load(name, **parts):
    """Return the SQL for `name`. {key} fragments are replaced with parts.
    Only pass trusted constants here, never user input."""
    sql = _read(name)
    for key, value in parts.items():
        sql = sql.replace("{" + key + "}", value)
    return sql
