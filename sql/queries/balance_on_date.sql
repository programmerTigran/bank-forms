SELECT COALESCE(SUM(CASE WHEN tx_type = 'deposit' THEN amount ELSE -amount END), 0) AS balance
FROM transactions
WHERE customer_id = %(customer_id)s
  AND tx_date <= %(as_of)s