SELECT {direction} AS direction, COUNT(*), SUM(t.amount)
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE c.company_id = %(company_id)s
GROUP BY direction
ORDER BY direction DESC
