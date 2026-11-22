CREATE TABLE IF NOT EXISTS rtf_imports (
    import_id  BIGSERIAL PRIMARY KEY,
    filename   TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('table', 'row', 'form')),
    target     TEXT NOT NULL,
    data       BYTEA NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rtf_imports_target ON rtf_imports (target, import_id);
