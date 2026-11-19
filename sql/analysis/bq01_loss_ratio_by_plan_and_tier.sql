-- Business Question: BQ1 - What is the overall loss ratio, and how does it vary by plan type, plan tier, and policy year?
-- Techniques demonstrated: CTEs, Window functions (LAG for YoY trend, running totals), conditional aggregation.

WITH annual_policy_exposure AS (
    SELECT
        policy_year,
        plan_type,
        plan_tier,
        COUNT(policy_id) AS active_policy_count,
        SUM(annual_premium) AS total_written_premium,
        SUM((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25 * annual_premium) AS total_earned_premium,
        SUM((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25 * members_covered) AS total_member_years
    FROM dim_policy
    GROUP BY policy_year, plan_type, plan_tier
),
annual_claims AS (
    SELECT
        EXTRACT(year FROM c.admission_date) AS claim_year,
        p.plan_type,
        p.plan_tier,
        SUM(c.paid_amount) AS total_paid_claims,
        COUNT(c.claim_id) AS total_claims_count
    FROM fact_claims c
    JOIN dim_policy p ON c.policy_id = p.policy_id
    GROUP BY EXTRACT(year FROM c.admission_date), p.plan_type, p.plan_tier
)
SELECT
    ape.policy_year,
    ape.plan_type,
    ape.plan_tier,
    ape.active_policy_count,
    ROUND(ape.total_earned_premium, 2) AS earned_premium,
    ROUND(COALESCE(ac.total_paid_claims, 0.0), 2) AS incurred_claims,
    ROUND(COALESCE(ac.total_paid_claims, 0.0) / NULLIF(ape.total_earned_premium, 0.0) * 100.0, 2) AS loss_ratio_pct,
    -- YoY Loss Ratio Delta using LAG window function
    ROUND(
        (COALESCE(ac.total_paid_claims, 0.0) / NULLIF(ape.total_earned_premium, 0.0) * 100.0) -
        LAG(COALESCE(ac.total_paid_claims, 0.0) / NULLIF(ape.total_earned_premium, 0.0) * 100.0)
            OVER (PARTITION BY ape.plan_type, ape.plan_tier ORDER BY ape.policy_year),
        2
    ) AS yoy_loss_ratio_change_pct
FROM annual_policy_exposure ape
LEFT JOIN annual_claims ac
    ON ape.policy_year = ac.claim_year
   AND ape.plan_type = ac.plan_type
   AND ape.plan_tier = ac.plan_tier
ORDER BY ape.plan_type, ape.plan_tier, ape.policy_year;

