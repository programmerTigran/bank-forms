-- 006: the "date column is last" rule now runs by itself.
-- After every `python scripts/migrate.py`, a date column (created_at, tx_date, applied_at)
-- that is no longer last (because a new column was added after it) is moved back to the end.
-- Indexes and CHECK / UNIQUE rules on that column are kept. Key columns are never moved.
-- To cover another column name, add it in the list of fix_dates_last (a new migration file).

CREATE OR REPLACE FUNCTION move_column_last(p_table TEXT, p_column TEXT) RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE
    v_oid OID; v_type TEXT; v_default TEXT; v_notnull BOOLEAN; v_pos INTEGER; v_last INTEGER;
    v_stmt TEXT; v_keep TEXT[] := '{}';
BEGIN
    v_oid := to_regclass(quote_ident(p_table));
    IF v_oid IS NULL THEN RETURN FALSE; END IF;
    SELECT format_type(a.atttypid, a.atttypmod), pg_get_expr(d.adbin, d.adrelid), a.attnotnull, a.attnum
      INTO v_type, v_default, v_notnull, v_pos
      FROM pg_attribute a
      LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
     WHERE a.attrelid = v_oid AND a.attname = p_column AND NOT a.attisdropped;
    IF v_pos IS NULL THEN RETURN FALSE; END IF;
    SELECT max(attnum) INTO v_last FROM pg_attribute
     WHERE attrelid = v_oid AND attnum > 0 AND NOT attisdropped;
    IF v_pos = v_last THEN RETURN FALSE; END IF;                          -- already last
    IF EXISTS (SELECT 1 FROM pg_constraint
                WHERE conrelid = v_oid AND contype IN ('p', 'f') AND v_pos = ANY(conkey)) THEN
        RETURN FALSE;                                                      -- key columns stay
    END IF;

    -- remember what uses the column, so it can be created again afterwards
    FOR v_stmt IN
        SELECT format('ALTER TABLE %s ADD CONSTRAINT %I %s', v_oid::regclass, conname, pg_get_constraintdef(oid))
          FROM pg_constraint WHERE conrelid = v_oid AND contype IN ('c', 'u') AND v_pos = ANY(conkey)
    LOOP v_keep := v_keep || v_stmt; END LOOP;
    FOR v_stmt IN
        SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
         WHERE i.indrelid = v_oid AND v_pos = ANY(i.indkey::int2[]) AND NOT i.indisprimary
           AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conindid = i.indexrelid)
    LOOP v_keep := v_keep || v_stmt; END LOOP;

    EXECUTE format('ALTER TABLE %I ADD COLUMN %I %s', p_table, p_column || '__new', v_type);
    EXECUTE format('UPDATE %I SET %I = %I', p_table, p_column || '__new', p_column);
    EXECUTE format('ALTER TABLE %I DROP COLUMN %I', p_table, p_column);
    EXECUTE format('ALTER TABLE %I RENAME COLUMN %I TO %I', p_table, p_column || '__new', p_column);
    IF v_default IS NOT NULL THEN
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I SET DEFAULT %s', p_table, p_column, v_default);
    END IF;
    IF v_notnull THEN
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I SET NOT NULL', p_table, p_column);
    END IF;
    FOREACH v_stmt IN ARRAY v_keep LOOP EXECUTE v_stmt; END LOOP;
    RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION fix_dates_last(p_names TEXT[] DEFAULT ARRAY['created_at', 'tx_date', 'applied_at'])
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    r RECORD; v_moved INTEGER := 0;
BEGIN
    FOR r IN
        SELECT c.relname AS tbl, a.attname AS col
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_attribute a ON a.attrelid = c.oid
         WHERE n.nspname = 'public' AND c.relkind = 'r'
           AND a.attname = ANY(p_names) AND a.attnum > 0 AND NOT a.attisdropped
    LOOP
        IF move_column_last(r.tbl, r.col) THEN v_moved := v_moved + 1; END IF;
    END LOOP;
    RETURN v_moved;
END;
$$;
