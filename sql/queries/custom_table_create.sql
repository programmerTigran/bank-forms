INSERT INTO custom_tables (name, title, description, columns, created_by)
VALUES (%(name)s, %(title)s, %(description)s, %(columns)s::jsonb, %(username)s)
RETURNING table_id
