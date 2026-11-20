SELECT doc_no, form_name, form_version, customer_id, created_at, issued_by
FROM document_log
WHERE %(term)s::text = ''
   OR doc_no ILIKE %(pattern)s
   OR form_name ILIKE %(pattern)s
   OR customer_id::text = %(term)s
ORDER BY id DESC
LIMIT %(limit)s
