SELECT COUNT(*) FROM customers
WHERE company_id = %(company_id)s
  AND (%(term)s = '' OR customer_id::text = %(term)s
       OR (first_name || ' ' || surname) ILIKE %(pattern)s)
