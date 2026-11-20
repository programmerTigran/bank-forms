SELECT c.customer_id, c.first_name, c.surname,
       v.phone, v.email, v.passport_no, v.birth_date, v.address
FROM customers c
LEFT JOIN customers_v2 v ON v.customer_id = c.customer_id
WHERE c.customer_id = %(customer_id)s