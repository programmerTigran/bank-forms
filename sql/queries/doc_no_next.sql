INSERT INTO doc_counter (year, last)
VALUES (extract(year FROM now())::int, 1)
ON CONFLICT (year) DO UPDATE SET last = doc_counter.last + 1
RETURNING 'BF-' || year || '-' || lpad(last::text, 6, '0')
