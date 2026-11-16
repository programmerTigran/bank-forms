SELECT definition FROM document_templates
WHERE name = %(name)s
ORDER BY version DESC
LIMIT 1
