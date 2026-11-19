-- Business Question: BQ1 - How does loss ratio vary across member age bands and geographic regions?
-- Techniques demonstrated: CTEs, Multi-table joins across 3 tables, conditional aggregation, loss ratio ranking.

WITH member_exposure AS (
    SELECT
        m.region,
        m.age_band,
        COUNT(DISTINCT m.member_id) AS total_members,
        COUNT(DISTINCT p.policy_id) AS policy_count,
        SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25 * (p.annual_premium / p.members_covered)) AS earned_premium,
        SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25) AS member_years
    FROM dim_member m
    JOIN dim_policy p ON m.policy_id = p.policy_id
    GROUP BY m.region, m.age_band
),
member_claims AS (
    SELECT
        m.region,
        m.age_band,
        COUNT(c.claim_id) AS total_claims,
        SUM(c.paid_amount) AS incurred_claims
    FROM fact_claims c
    JOIN dim_member m ON c.member_id = m.member_id
    GROUP BY m.region, m.age_band
)
SELECT
    me.region,
    me.age_band,
    me.total_members,
    ROUND(me.member_years, 2) AS member_years_exposure,
    ROUND(me.earned_premium, 2) AS earned_premium,
    ROUND(COALESCE(mc.incurred_claims, 0.0), 2) AS incurred_claims,
    ROUND(COALESCE(mc.incurred_claims, 0.0) / NULLIF(me.earned_premium, 0.0) * 100.0, 2) AS loss_ratio_pct,
    ROUND(COALESCE(mc.total_claims, 0) * 1.0 / NULLIF(me.member_years, 0.0), 4) AS claim_frequency,
    DENSE_RANK() OVER (PARTITION BY me.region ORDER BY (COALESCE(mc.incurred_claims, 0.0) / NULLIF(me.earned_premium, 0.0)) DESC) AS regional_risk_rank
FROM member_exposure me
LEFT JOIN member_claims mc
    ON me.region = mc.region AND me.age_band = mc.age_band
ORDER BY me.region, loss_ratio_pct DESC;

