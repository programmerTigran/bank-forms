SELECT count(*) FROM custom_tables t
WHERE %(term)s::text = '' OR t.name ILIKE %(pattern)s OR t.title ILIKE %(pattern)s
   OR t.description ILIKE %(pattern)s
