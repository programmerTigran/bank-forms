SELECT COUNT(*) FROM transactions
WHERE customer_id = %(customer_id)s
  AND (NOT %(first_only)s OR right(tx_id, 2) = '.1')
  AND (tx_id ILIKE %(pattern)s OR description ILIKE %(pattern)s
       OR tx_type ILIKE %(pattern)s OR amount::text ILIKE %(pattern)s
       OR tx_date::text ILIKE %(pattern)s)
