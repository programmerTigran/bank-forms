"""
scripts/migrate.py
Applies the files in migrations/ (000_..., 001_..., in name order) that have not run yet.
One transaction per file; a file that fails changes nothing. Done files are remembered
in the table schema_migrations, so running it again is safe.
To change the database later: add the next file (007_what_it_does.sql) and run this.
Date columns that a new column pushed out of the last place are moved back automatically.
Uses the same database as the app (your .env). Stop the app first.
Run from the project root (venv active): python scripts/migrate.py
"""

import sys
from pathlib import Path

import psycopg

sys.path.append(str(Path(__file__).resolve().parent.parent))

from db import new_connection

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

def main():
    with new_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        print("Database:", conn.execute("SELECT current_database()").fetchone()[0])
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name in done:
            print("  skip   ", path.name)
            continue
        try:
            with new_connection() as conn:
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        except psycopg.Error as e:
            sys.exit("  FAILED " + path.name + ": " + str(e).strip() + "\nNothing from this file was saved.")
        print("  applied", path.name)
    # the "date column last" rule (migration 006) runs by itself after every migration run
    with new_connection() as conn:
        if conn.execute("SELECT to_regproc('fix_dates_last') IS NOT NULL").fetchone()[0]:
            moved = conn.execute("SELECT fix_dates_last()").fetchone()[0]
            if moved:
                print("  moved", moved, "date column(s) to the end of their table")

if __name__ == "__main__":
    main()
