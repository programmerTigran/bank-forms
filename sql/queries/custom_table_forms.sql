SELECT DISTINCT name FROM document_templates WHERE definition->>'source_table' = %(name)s ORDER BY name
