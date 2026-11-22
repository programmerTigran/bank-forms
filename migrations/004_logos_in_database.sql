-- 004: company logos live in the database (image bytes), not as files on disk.
-- The old companies.logo column (a file path) stays; scripts/load_logos.py reads it once.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_data BYTEA;