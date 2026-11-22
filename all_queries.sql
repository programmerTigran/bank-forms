-- FILE: sql/queries/audit_insert.sql
INSERT INTO audit_log (username, action, customer_id, detail)
VALUES (%(username)s, %(action)s, %(customer_id)s, %(detail)s)

-- FILE: sql/queries/balance_on_date.sql
SELECT COALESCE(SUM(CASE WHEN tx_type = 'deposit' THEN amount ELSE -amount END), 0) AS balance
FROM transactions
WHERE customer_id = %(customer_id)s
  AND tx_date <= %(as_of)s
-- FILE: sql/queries/company_customer_count.sql
SELECT COUNT(*) FROM customers
WHERE company_id = %(company_id)s
  AND (%(term)s = '' OR customer_id::text = %(term)s
       OR (first_name || ' ' || surname) ILIKE %(pattern)s)

-- FILE: sql/queries/company_customers.sql
SELECT p.customer_id, p.first_name, p.surname,
       COUNT(t.amount), COALESCE(SUM(t.amount), 0)
FROM (
  SELECT customer_id, first_name, surname FROM customers
  WHERE company_id = %(company_id)s
    AND (%(term)s = '' OR customer_id::text = %(term)s
         OR (first_name || ' ' || surname) ILIKE %(pattern)s)
  ORDER BY customer_id
  LIMIT %(limit)s OFFSET %(offset)s
) p
LEFT JOIN transactions t ON t.customer_id = p.customer_id
GROUP BY p.customer_id, p.first_name, p.surname
ORDER BY p.customer_id

-- FILE: sql/queries/company_direction_totals.sql
SELECT {direction} AS direction, COUNT(*), SUM(t.amount)
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE c.company_id = %(company_id)s
GROUP BY direction
ORDER BY direction DESC

-- FILE: sql/queries/company_logo_by_id.sql
SELECT logo_data FROM companies WHERE company_id = %(company_id)s

-- FILE: sql/queries/company_logo_data.sql
SELECT logo_data FROM companies WHERE name = %(name)s

-- FILE: sql/queries/company_logo_set.sql
UPDATE companies SET logo_data = %(data)s WHERE company_id = %(company_id)s

-- FILE: sql/queries/company_summary.sql
WITH tx AS (
  SELECT customer_id, COUNT(*) AS n, SUM(amount) AS total
  FROM transactions
  GROUP BY customer_id
)
SELECT co.company_id, co.name, co.logo,
       COUNT(c.customer_id),
       COALESCE(SUM(tx.n), 0),
       COALESCE(SUM(tx.total), 0)
FROM companies co
LEFT JOIN customers c ON c.company_id = co.company_id
LEFT JOIN tx ON tx.customer_id = c.customer_id
GROUP BY co.company_id, co.name, co.logo, co.sort_order
ORDER BY co.sort_order, co.name

-- FILE: sql/queries/company_type_totals.sql
SELECT t.tx_type, COUNT(*), SUM(t.amount)
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE c.company_id = %(company_id)s AND {direction} = %(direction)s
GROUP BY t.tx_type
ORDER BY t.tx_type

-- FILE: sql/queries/custom_rows_add.sql
INSERT INTO custom_rows (table_id, data, created_by) VALUES (%(table_id)s, %(data)s::jsonb, %(username)s)

-- FILE: sql/queries/custom_rows_count.sql
SELECT count(*) FROM custom_rows WHERE table_id = %(table_id)s

-- FILE: sql/queries/custom_rows_get.sql
SELECT row_id, data FROM custom_rows WHERE table_id = %(table_id)s ORDER BY row_id LIMIT %(limit)s OFFSET %(offset)s

-- FILE: sql/queries/custom_table_create.sql
INSERT INTO custom_tables (name, title, description, columns, created_by)
VALUES (%(name)s, %(title)s, %(description)s, %(columns)s::jsonb, %(username)s)
RETURNING table_id

-- FILE: sql/queries/custom_table_delete.sql
DELETE FROM custom_tables WHERE table_id = %(table_id)s

-- FILE: sql/queries/custom_table_forms.sql
SELECT DISTINCT name FROM document_templates WHERE definition->>'source_table' = %(name)s ORDER BY name

-- FILE: sql/queries/custom_table_get.sql
SELECT table_id, name, title, description, columns, created_by, created_at FROM custom_tables WHERE name = %(name)s

-- FILE: sql/queries/custom_tables_count.sql
SELECT count(*) FROM custom_tables t
WHERE %(term)s::text = '' OR t.name ILIKE %(pattern)s OR t.title ILIKE %(pattern)s
   OR t.description ILIKE %(pattern)s

-- FILE: sql/queries/custom_tables_search.sql
SELECT t.table_id, t.name, t.title, t.description,
       jsonb_array_length(t.columns) AS column_count,
       (SELECT count(*) FROM custom_rows r WHERE r.table_id = t.table_id) AS row_count,
       t.created_by, t.created_at
FROM custom_tables t
WHERE %(term)s::text = '' OR t.name ILIKE %(pattern)s OR t.title ILIKE %(pattern)s
   OR t.description ILIKE %(pattern)s
ORDER BY t.title, t.table_id
LIMIT %(limit)s

-- FILE: sql/queries/customer_full.sql
SELECT c.customer_id, c.first_name, c.surname,
       v.phone, v.email, v.passport_no, v.birth_date, v.address
FROM customers c
LEFT JOIN customers_v2 v ON v.customer_id = c.customer_id
WHERE c.customer_id = %(customer_id)s
-- FILE: sql/queries/customer_get.sql
SELECT c.first_name, c.surname, COALESCE(co.name, '')
FROM customers c
LEFT JOIN companies co ON co.company_id = c.company_id
WHERE c.customer_id = %(customer_id)s

-- FILE: sql/queries/customers_search.sql
SELECT customer_id, first_name, surname FROM customers
WHERE %(term)s = ''
   OR customer_id::text = %(term)s
   OR (first_name || ' ' || surname) ILIKE %(pattern)s
ORDER BY customer_id
LIMIT %(limit)s
   
-- FILE: sql/queries/doc_file_insert.sql
INSERT INTO document_files (doc_no, fmt, data)
VALUES (%(doc_no)s, %(fmt)s, %(data)s)

-- FILE: sql/queries/doc_files_get.sql
SELECT fmt, data FROM document_files WHERE doc_no = %(doc_no)s ORDER BY fmt

-- FILE: sql/queries/doc_log_insert.sql
INSERT INTO document_log (doc_no, form_name, form_version, customer_id, params, issued_by)
VALUES (%(doc_no)s, %(form_name)s, %(form_version)s, %(customer_id)s,
        %(params)s::jsonb, %(issued_by)s)

-- FILE: sql/queries/doc_no_next.sql
INSERT INTO doc_counter (year, last)
VALUES (extract(year FROM now())::int, 1)
ON CONFLICT (year) DO UPDATE SET last = doc_counter.last + 1
RETURNING 'BF-' || year || '-' || lpad(last::text, 6, '0')

-- FILE: sql/queries/form_create.sql
SELECT create_form_version(%(name)s, %(definition)s::jsonb)

-- FILE: sql/queries/issued_search.sql
SELECT doc_no, form_name, form_version, customer_id, created_at, issued_by
FROM document_log
WHERE %(term)s::text = ''
   OR doc_no ILIKE %(pattern)s
   OR form_name ILIKE %(pattern)s
   OR customer_id::text = %(term)s
ORDER BY id DESC
LIMIT %(limit)s

-- FILE: sql/queries/rtf_import_get.sql
SELECT filename, data FROM rtf_imports WHERE import_id = %(import_id)s
-- FILE: sql/queries/rtf_import_insert.sql
INSERT INTO rtf_imports (filename, kind, target, data, created_by)
VALUES (%(filename)s, %(kind)s, %(target)s, %(data)s, %(username)s)
RETURNING import_id
-- FILE: sql/queries/rtf_imports_ensure.sql
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

-- FILE: sql/queries/transaction_get.sql
SELECT t.tx_id, t.tx_date, t.tx_type, t.amount, t.description,
       CASE WHEN t.tx_type = 'deposit' THEN 'Credit' ELSE 'Debit' END AS direction
FROM transactions t
WHERE t.tx_id = %(tx_id)s;
-- FILE: sql/queries/tx_belongs.sql
SELECT 1 FROM transactions WHERE tx_id = %(tx_id)s AND customer_id = %(customer_id)s

-- FILE: sql/queries/tx_between.sql
SELECT tx_date, tx_type, amount, description FROM transactions
WHERE customer_id = %(customer_id)s
  AND tx_date >= %(date_from)s
  AND tx_date <= %(date_to)s
  AND (%(tx_types)s::text[] IS NULL OR tx_type::text = ANY(%(tx_types)s::text[]))
  AND (%(min_amount)s::numeric IS NULL OR amount >= %(min_amount)s::numeric)
  AND (%(max_amount)s::numeric IS NULL OR amount <= %(max_amount)s::numeric)
  AND (%(pattern)s::text IS NULL
       OR description ILIKE %(pattern)s::text
       OR tx_id ILIKE %(pattern)s::text)
ORDER BY tx_date, tx_type

-- FILE: sql/queries/tx_count.sql
SELECT COUNT(*) FROM transactions
WHERE customer_id = %(customer_id)s
  AND (NOT %(first_only)s OR right(tx_id, 2) = '.1')
  AND (tx_id ILIKE %(pattern)s OR description ILIKE %(pattern)s
       OR tx_type ILIKE %(pattern)s OR amount::text ILIKE %(pattern)s
       OR tx_date::text ILIKE %(pattern)s)

-- FILE: sql/queries/tx_search.sql
SELECT tx_id, tx_date, tx_type, amount, description FROM transactions
WHERE customer_id = %(customer_id)s
  AND (NOT %(first_only)s OR right(tx_id, 2) = '.1')
  AND (tx_id ILIKE %(pattern)s OR description ILIKE %(pattern)s
       OR tx_type ILIKE %(pattern)s OR amount::text ILIKE %(pattern)s
       OR tx_date::text ILIKE %(pattern)s)
ORDER BY tx_date DESC, tx_id
LIMIT %(limit)s

-- FILE: sql/queries/user_get.sql
SELECT user_id, username, password_hash, role FROM users WHERE username = %(username)s

-- FILE: sql/queries/user_insert.sql
INSERT INTO users (username, password_hash, role)
VALUES (%(username)s, %(password_hash)s, %(role)s)

