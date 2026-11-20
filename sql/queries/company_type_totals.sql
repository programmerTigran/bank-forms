SELECT t.tx_type, COUNT(*), SUM(t.amount)
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE c.company_id = %(company_id)s AND {direction} = %(direction)s
GROUP BY t.tx_type
ORDER BY t.tx_type
