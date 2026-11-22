-- Q1: Top 5 funds by AUM
SELECT f.scheme_name, f.fund_house, p.aum_crore
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
ORDER BY p.aum_crore DESC
LIMIT 5;

-- Q2: Average NAV per fund per month (excludes forward-filled weekend/holiday rows)
SELECT n.amfi_code, d.year_month, ROUND(AVG(n.nav), 2) AS avg_nav
FROM fact_nav n
JOIN dim_date d ON d.date = n.date
WHERE n.nav_filled = 0
GROUP BY n.amfi_code, d.year_month
ORDER BY n.amfi_code, d.year_month;

-- Q3: SIP year-over-year growth (Jan to May only, so 2024 and 2025 are compared like for like)
WITH yearly AS (
    SELECT strftime('%Y', transaction_date) AS yr,
           SUM(amount_inr) AS sip_amount
    FROM fact_transactions
    WHERE transaction_type = 'SIP'
      AND strftime('%m', transaction_date) <= '05'
    GROUP BY yr
)
SELECT yr,
       sip_amount,
       LAG(sip_amount) OVER (ORDER BY yr) AS prev_year_amount,
       ROUND(100.0 * (sip_amount - LAG(sip_amount) OVER (ORDER BY yr))
             / LAG(sip_amount) OVER (ORDER BY yr), 2) AS yoy_growth_pct
FROM yearly
ORDER BY yr;

-- Q4: Transactions and value by state
SELECT state,
       COUNT(*) AS transactions,
       ROUND(SUM(amount_inr), 0) AS total_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_inr DESC;

-- Q5: Funds with expense ratio below 1%
SELECT f.fund_house, f.scheme_name, p.expense_ratio_pct
FROM fact_performance p
JOIN dim_fund f ON f.amfi_code = p.amfi_code
WHERE p.expense_ratio_pct < 1
ORDER BY p.expense_ratio_pct;

-- Q6: Latest AUM by fund house
SELECT fund_house, aum_crore, num_schemes
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
ORDER BY aum_crore DESC;

-- Q7: Net investor flow by fund house (invested minus redeemed)
SELECT f.fund_house,
       ROUND(SUM(CASE WHEN t.transaction_type IN ('SIP', 'Lumpsum') THEN t.amount_inr ELSE 0 END), 0) AS invested,
       ROUND(SUM(CASE WHEN t.transaction_type = 'Redemption' THEN t.amount_inr ELSE 0 END), 0) AS redeemed,
       ROUND(SUM(CASE WHEN t.transaction_type IN ('SIP', 'Lumpsum') THEN t.amount_inr
                      ELSE -t.amount_inr END), 0) AS net_flow
FROM fact_transactions t
JOIN dim_fund f ON f.amfi_code = t.amfi_code
GROUP BY f.fund_house
ORDER BY net_flow DESC;

-- Q8: Top 3 funds per category by 3-year return (window function)
WITH ranked AS (
    SELECT f.category,
           f.scheme_name,
           p.return_3yr_pct,
           RANK() OVER (PARTITION BY f.category ORDER BY p.return_3yr_pct DESC) AS rnk
    FROM fact_performance p
    JOIN dim_fund f ON f.amfi_code = p.amfi_code
)
SELECT category, rnk, scheme_name, return_3yr_pct
FROM ranked
WHERE rnk <= 3
ORDER BY category, rnk;

-- Q9: Average ticket size by city tier and KYC status
SELECT city_tier,
       kyc_status,
       COUNT(*) AS transactions,
       ROUND(AVG(amount_inr), 0) AS avg_amount_inr
FROM fact_transactions
GROUP BY city_tier, kyc_status
ORDER BY city_tier, kyc_status;

-- Q10: Monthly transaction value with running total (window function)
WITH monthly AS (
    SELECT d.year_month,
           SUM(t.amount_inr) AS total_amount
    FROM fact_transactions t
    JOIN dim_date d ON d.date = t.transaction_date
    GROUP BY d.year_month
)
SELECT year_month,
       ROUND(total_amount, 0) AS total_amount,
       ROUND(SUM(total_amount) OVER (ORDER BY year_month), 0) AS running_total
FROM monthly
ORDER BY year_month;