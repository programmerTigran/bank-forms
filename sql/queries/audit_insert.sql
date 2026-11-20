INSERT INTO audit_log (username, action, customer_id, detail)
VALUES (%(username)s, %(action)s, %(customer_id)s, %(detail)s)
