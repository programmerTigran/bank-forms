SELECT p.customer_id, p.first_name, p.surname,
       COUNT(t.amount), COALESCE(SUM(t.amount), 0)
FROM (
  SELECT customer_id, first_name, surname FROM customers
  WHERE company_id = %(company_id)s
    AND (%(term)s = '' OR customer_id::text = %(term)s
         OR (first_name || ' ' || surname) ILIKE %(pattern)s)
  ORDER BY customer_id
  LIMIT %(limit)s OFFSET %(offset)s
) p
LEFT JOIN transactions t ON t.customer_id = p.customer_id
GROUP BY p.customer_id, p.first_name, p.surname
ORDER BY p.customer_id
