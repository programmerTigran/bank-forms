SELECT t.table_id, t.name, t.title, t.description,
       jsonb_array_length(t.columns) AS column_count,
       (SELECT count(*) FROM custom_rows r WHERE r.table_id = t.table_id) AS row_count,
       t.created_by, t.created_at
FROM custom_tables t
WHERE %(term)s::text = '' OR t.name ILIKE %(pattern)s OR t.title ILIKE %(pattern)s
   OR t.description ILIKE %(pattern)s
ORDER BY t.title, t.table_id
LIMIT %(limit)s
