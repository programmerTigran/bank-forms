INSERT INTO rtf_imports (filename, kind, target, data, created_by)
VALUES (%(filename)s, %(kind)s, %(target)s, %(data)s, %(username)s)
RETURNING import_id