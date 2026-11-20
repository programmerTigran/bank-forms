SELECT row_id, data FROM custom_rows WHERE table_id = %(table_id)s ORDER BY row_id LIMIT %(limit)s OFFSET %(offset)s
