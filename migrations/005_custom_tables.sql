-- 005: tables that users create themselves (any kind of info), stored in the database.
-- custom_tables = the definition (name, title, columns); custom_rows = the rows (JSON per row).
-- The app never runs CREATE TABLE for users: it only writes rows into these two tables.
CREATE TABLE IF NOT EXISTS custom_tables (
    table_id    SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE CHECK (name ~ '^[a-z0-9_]+$'),
    title       TEXT NOT NULL,
    description TEXT,
    columns     JSONB NOT NULL,
    created_by  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS custom_rows (
    row_id     BIGSERIAL PRIMARY KEY,
    table_id   INTEGER NOT NULL REFERENCES custom_tables (table_id) ON DELETE CASCADE,
    data       JSONB NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_custom_rows_table ON custom_rows (table_id, row_id);