-- 002: bigger money, rules and links the database enforces, safe form saving.
-- Can run more than once (every step drops its old version first).

-- 1. Money: NUMERIC(12,2) stops at 9,999,999,999.99. Now far beyond any bank amount.
ALTER TABLE transactions ALTER COLUMN amount TYPE NUMERIC(20, 2);

-- 2. Rules the database checks itself
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_tx_amount;
ALTER TABLE transactions ADD CONSTRAINT chk_tx_amount CHECK (amount >= 0);
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_tx_type;
ALTER TABLE transactions ADD CONSTRAINT chk_tx_type
    CHECK (tx_type IN ('deposit', 'withdrawal', 'transfer', 'payment'));

-- 3. Links between tables. NOT VALID = old rows are not checked, every new row is.
--    (audit_log is left unlinked on purpose: an audit trail must never block or vanish.)
ALTER TABLE document_log DROP CONSTRAINT IF EXISTS fk_document_log_customer;
ALTER TABLE document_log ADD CONSTRAINT fk_document_log_customer
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id) NOT VALID;
ALTER TABLE document_log DROP CONSTRAINT IF EXISTS fk_document_log_form;
ALTER TABLE document_log ADD CONSTRAINT fk_document_log_form
    FOREIGN KEY (form_name, form_version) REFERENCES document_templates (name, version) NOT VALID;

-- 4. Saving a form = one database function. Two admins saving the same form at the
--    same moment can no longer get the same version number.
CREATE OR REPLACE FUNCTION create_form_version(p_name TEXT, p_definition JSONB)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_version INTEGER;
BEGIN
    IF p_name !~ '^[a-z0-9_]+$' THEN
        RAISE EXCEPTION 'Form name: only a-z, 0-9 and _';
    END IF;
    IF NOT (p_definition ? 'title' AND p_definition ? 'inputs' AND p_definition ? 'query') THEN
        RAISE EXCEPTION 'A form needs title, inputs and query';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtext(p_name));
    SELECT coalesce(max(version), 0) + 1 INTO v_version
    FROM document_templates WHERE name = p_name;
    INSERT INTO document_templates (name, version, definition)
    VALUES (p_name, v_version, p_definition);
    RETURN v_version;
END;
$$;
