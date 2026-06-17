-- MySQL 8.x
-- Customers whose advertising campaigns produced more than 3 'failure' events
-- in total. Output: full name and the number of failures, busiest first.
SELECT
    CONCAT(c.first_name, ' ', c.last_name) AS customer,
    COUNT(*)                               AS failures
FROM customers AS c
JOIN campaigns AS cp ON cp.customer_id = c.id
JOIN events    AS e  ON e.campaign_id  = cp.id
WHERE e.status = 'failure'
GROUP BY c.id, c.first_name, c.last_name   -- non-aggregated columns (ONLY_FULL_GROUP_BY safe)
HAVING COUNT(*) > 3                         -- strictly more than 3
ORDER BY failures DESC, customer ASC;       -- customer ASC is a deterministic tie-breaker
