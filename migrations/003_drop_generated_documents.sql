-- 003: generated_documents is the old way of saving documents. It was replaced by
-- document_log + document_files. This drops the old table; remove this file only if you still use it.
DROP TABLE IF EXISTS generated_documents;
