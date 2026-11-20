-- 001: users, audit log, gapless document counter, issued_by column.
-- Rule for every table: the date column is the LAST column.
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('clerk', 'admin'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    username    TEXT NOT NULL,
    action      TEXT NOT NULL,
    customer_id INTEGER,
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE document_log ADD COLUMN IF NOT EXISTS issued_by TEXT;

CREATE TABLE IF NOT EXISTS doc_counter (
    year INTEGER PRIMARY KEY,
    last INTEGER NOT NULL
);

INSERT INTO doc_counter (year, last)
SELECT extract(year FROM now())::int,
       coalesce(max(substring(doc_no FROM '(\d+)$')::int), 0)
FROM document_log
WHERE doc_no LIKE 'BF-' || extract(year FROM now())::int || '-%'
ON CONFLICT (year) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_document_log_customer ON document_log (customer_id);
CREATE INDEX IF NOT EXISTS idx_audit_customer ON audit_log (customer_id);
