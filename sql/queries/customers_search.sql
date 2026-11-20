SELECT customer_id, first_name, surname FROM customers
WHERE %(term)s = ''
   OR customer_id::text = %(term)s
   OR (first_name || ' ' || surname) ILIKE %(pattern)s
ORDER BY customer_id
LIMIT %(limit)s
   