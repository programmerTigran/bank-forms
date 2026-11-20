SELECT doc_no FROM document_log
WHERE form_name = %(form_name)s AND form_version = %(form_version)s
  AND customer_id IS NOT DISTINCT FROM %(customer_id)s
  AND params = %(params)s::jsonb AND content IS NOT NULL
ORDER BY id DESC LIMIT 1