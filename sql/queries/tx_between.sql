SELECT tx_date, tx_type, amount, description FROM transactions
WHERE customer_id = %(customer_id)s
  AND tx_date >= %(date_from)s
  AND tx_date <= %(date_to)s
  AND (%(tx_types)s::text[] IS NULL OR tx_type::text = ANY(%(tx_types)s::text[]))
  AND (%(min_amount)s::numeric IS NULL OR amount >= %(min_amount)s::numeric)
  AND (%(max_amount)s::numeric IS NULL OR amount <= %(max_amount)s::numeric)
  AND (%(pattern)s::text IS NULL
       OR description ILIKE %(pattern)s::text
       OR tx_id ILIKE %(pattern)s::text)
ORDER BY tx_date, tx_type
