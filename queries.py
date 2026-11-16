"""Loads SQL from sql/<name>.sql. Cached after first read."""
from functools import lru_cache
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"


@lru_cache(maxsize=None)
def _read(name: str) -> str:
    path = SQL_DIR / f"{name}.sql"
    if not path.exists():
        raise FileNotFoundError(f"Query file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def load(name: str, **parts: str) -> str:
    """Return the SQL for `name`. {key} fragments are replaced with parts.
    Only pass trusted constants here, never user input."""
    sql = _read(name)
    for key, value in parts.items():
        sql = sql.replace("{" + key + "}", value)
    return sql
