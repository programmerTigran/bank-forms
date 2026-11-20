SELECT c.first_name, c.surname, COALESCE(co.name, '')
FROM customers c
LEFT JOIN companies co ON co.company_id = c.company_id
WHERE c.customer_id = %(customer_id)s
