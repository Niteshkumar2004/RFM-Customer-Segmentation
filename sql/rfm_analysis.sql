-- PostgreSQL RFM aggregation and quintile scoring
WITH customer_rfm AS (
 SELECT customer_id, MAX(email) AS email,
 CURRENT_DATE - MAX(order_date::date) AS recency_days,
 COUNT(DISTINCT order_id) AS frequency, SUM(amount) AS monetary
 FROM transactions WHERE amount >= 0 GROUP BY customer_id
), scored AS (
 SELECT *,
 6-NTILE(5) OVER(ORDER BY recency_days DESC) AS r_score,
 NTILE(5) OVER(ORDER BY frequency ASC) AS f_score,
 NTILE(5) OVER(ORDER BY monetary ASC) AS m_score
 FROM customer_rfm
)
SELECT *, CONCAT(r_score,f_score,m_score) AS rfm_score FROM scored;

-- Example VIP target audience (tune thresholds to your business)
SELECT customer_id,email,MAX(order_date) AS last_order,
 COUNT(DISTINCT order_id) AS frequency,SUM(amount) AS monetary
FROM transactions GROUP BY customer_id,email
HAVING CURRENT_DATE-MAX(order_date::date)<=45
 AND COUNT(DISTINCT order_id)>=8
ORDER BY monetary DESC;
