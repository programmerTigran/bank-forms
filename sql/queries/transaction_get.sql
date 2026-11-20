SELECT t.tx_id, t.tx_date, t.tx_type, t.amount, t.description,
       CASE WHEN t.tx_type = 'deposit' THEN 'Credit' ELSE 'Debit' END AS direction
FROM transactions t
WHERE t.tx_id = %(tx_id)s;