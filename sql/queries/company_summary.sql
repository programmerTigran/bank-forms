WITH tx AS (
  SELECT customer_id, COUNT(*) AS n, SUM(amount) AS total
  FROM transactions
  GROUP BY customer_id
)
SELECT co.company_id, co.name, co.logo,
       COUNT(c.customer_id),
       COALESCE(SUM(tx.n), 0),
       COALESCE(SUM(tx.total), 0)
FROM companies co
LEFT JOIN customers c ON c.company_id = co.company_id
LEFT JOIN tx ON tx.customer_id = c.customer_id
GROUP BY co.company_id, co.name, co.logo, co.sort_order
ORDER BY co.sort_order, co.name
