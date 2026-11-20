INSERT INTO document_log (doc_no, form_name, form_version, customer_id, params, issued_by, content)
VALUES (%(doc_no)s, %(form_name)s, %(form_version)s, %(customer_id)s,
        %(params)s::jsonb, %(issued_by)s, %(content)s::jsonb)