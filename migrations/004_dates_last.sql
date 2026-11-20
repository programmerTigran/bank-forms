-- 004: the date column is the last column of every table, so you can see where a table ends.
-- Postgres cannot reorder columns, so the date column is re-created at the end.
-- Type, default and NOT NULL are copied from the old column; the data is kept.
CREATE FUNCTION pg_temp.move_column_last(p_table TEXT, p_column TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    v_type TEXT; v_default TEXT; v_notnull BOOLEAN; v_pos INTEGER; v_last INTEGER;
BEGIN
    IF to_regclass(p_table) IS NULL THEN RETURN; END IF;
    SELECT format_type(a.atttypid, a.atttypmod), pg_get_expr(d.adbin, d.adrelid), a.attnotnull, a.attnum
      INTO v_type, v_default, v_notnull, v_pos
      FROM pg_attribute a
      LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
     WHERE a.attrelid = p_table::regclass AND a.attname = p_column AND NOT a.attisdropped;
    IF v_pos IS NULL THEN RETURN; END IF;
    SELECT max(attnum) INTO v_last FROM pg_attribute
     WHERE attrelid = p_table::regclass AND attnum > 0 AND NOT attisdropped;
    IF v_pos = v_last THEN RETURN; END IF;                       -- already last
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
END;
$$;

SELECT pg_temp.move_column_last('audit_log', 'created_at');
SELECT pg_temp.move_column_last('document_log', 'created_at');
SELECT pg_temp.move_column_last('customers_v2', 'created_at');
SELECT pg_temp.move_column_last('transactions', 'tx_date');

-- dropping a column drops the indexes on it: put it back
CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions (customer_id, tx_date);
