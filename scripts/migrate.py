"""
scripts/migrate.py
Applies the files in migrations/ (000_..., 001_..., in name order) that have not run yet.
One transaction per file; a file that fails changes nothing. Done files are remembered
in the table schema_migrations, so running it again is safe.
To change the database later: add the next file (007_what_it_does.sql) and run this.
After every run, a date column (created_at, tx_date, applied_at) that a new column pushed out of the
last place is moved back to the end automatically (see move_dates_last).
Uses the same database as the app (your .env). Stop the app first.
Run from the project root (venv active): python scripts/migrate.py
"""

import sys
from pathlib import Path

import psycopg

sys.path.append(str(Path(__file__).resolve().parent.parent))

from db import new_connection

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

DATE_COLUMNS = ["created_at", "tx_date", "applied_at"]

def move_dates_last(conn):
    """Every date column that is not the last column of its table: re-create it at the end.
    Data, type, default, NOT NULL and indexes are kept. Primary/foreign key columns stay."""
    found = conn.execute("""
        SELECT c.oid::regclass::text, a.attname, format_type(a.atttypid, a.atttypmod),
               pg_get_expr(d.adbin, d.adrelid), a.attnotnull
          FROM pg_class c JOIN pg_attribute a ON a.attrelid = c.oid
          LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
         WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r' AND a.attnum > 0
           AND NOT a.attisdropped AND a.attname = ANY(%s)
           AND a.attnum < (SELECT max(attnum) FROM pg_attribute WHERE attrelid = c.oid)
           AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conrelid = c.oid
                           AND k.contype IN ('p', 'f') AND a.attnum = ANY(k.conkey))""",
        (DATE_COLUMNS,)).fetchall()
    for table, col, kind, default, notnull in found:
        indexes = [r[0] for r in conn.execute(
            "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid = %s::regclass "
            "AND NOT indisprimary AND %s = ANY(SELECT attname FROM pg_attribute WHERE attrelid = indrelid "
            "AND attnum = ANY(indkey::int2[]))", (table, col))]
        conn.execute("ALTER TABLE " + table + " ADD COLUMN tmp_col " + kind)
        conn.execute("UPDATE " + table + " SET tmp_col = " + col)
        conn.execute("ALTER TABLE " + table + " DROP COLUMN " + col)
        conn.execute("ALTER TABLE " + table + " RENAME COLUMN tmp_col TO " + col)
        if default:
            conn.execute("ALTER TABLE " + table + " ALTER COLUMN " + col + " SET DEFAULT " + default)
        if notnull:
            conn.execute("ALTER TABLE " + table + " ALTER COLUMN " + col + " SET NOT NULL")
        for sql in indexes:
            conn.execute(sql)
        print("  moved", table + "." + col, "to the end")

def main():
    with new_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        print("Database:", conn.execute("SELECT current_database()").fetchone()[0])
    for stray in sorted(MIGRATIONS.iterdir()):
        if stray.is_file() and stray.suffix != ".sql":
            print("  WARNING", stray.name, "does not end in .sql, so it is NOT applied")
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
    with new_connection() as conn:         # one transaction: all or nothing
        move_dates_last(conn)

if __name__ == "__main__":
    main()
    