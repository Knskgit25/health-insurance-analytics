-- Business Question: BQ8 - What is the renewal (persistency) trajectory across policy-year cohorts over tenure?
-- Techniques demonstrated: Cohort retention matrix, tenure tracking, renewal decay rate.

WITH cohort_renewals AS (
    SELECT
        p.policy_year AS cohort_year,
        p.sales_channel,
        r.renewal_id,
        r.renewed_flag,
        EXTRACT(year FROM r.renewal_due_date) - p.policy_year AS policy_tenure_year
    FROM fact_renewals r
    JOIN dim_policy p ON r.policy_id = p.policy_id
)
SELECT
    cohort_year,
    sales_channel,
    policy_tenure_year,
    COUNT(renewal_id) AS policies_eligible,
    COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) AS policies_renewed,
    ROUND(
        COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(renewal_id), 0),
        2
    ) AS persistency_rate_pct
FROM cohort_renewals
WHERE policy_tenure_year >= 1
GROUP BY cohort_year, sales_channel, policy_tenure_year
ORDER BY cohort_year, sales_channel, policy_tenure_year;

