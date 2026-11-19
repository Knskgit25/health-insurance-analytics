-- Business Question: BQ2 - Which demographic & policy segments are unprofitable (Loss Ratio > 100%)?
-- Techniques demonstrated: Multi-dimensional segment grouping, HAVING filtering, underwriting deficit ranking.

WITH segment_performance AS (
    SELECT
        p.plan_tier,
        m.age_band,
        m.region,
        m.city_tier,
        COUNT(DISTINCT m.member_id) AS covered_members,
        SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25 * (p.annual_premium / p.members_covered)) AS earned_premium,
        SUM(c.paid_amount) AS incurred_claims,
        COUNT(c.claim_id) AS claim_count
    FROM dim_member m
    JOIN dim_policy p ON m.policy_id = p.policy_id
    LEFT JOIN fact_claims c ON m.member_id = c.member_id
    GROUP BY p.plan_tier, m.age_band, m.region, m.city_tier
)
SELECT
    plan_tier,
    age_band,
    region,
    city_tier,
    covered_members,
    claim_count,
    ROUND(earned_premium, 2) AS earned_premium,
    ROUND(incurred_claims, 2) AS incurred_claims,
    ROUND(incurred_claims - earned_premium, 2) AS underwriting_deficit_inr,
    ROUND(incurred_claims / NULLIF(earned_premium, 0.0) * 100.0, 2) AS loss_ratio_pct,
    DENSE_RANK() OVER (ORDER BY (incurred_claims - earned_premium) DESC) AS deficit_rank
FROM segment_performance
WHERE (incurred_claims / NULLIF(earned_premium, 0.0)) > 1.0
ORDER BY underwriting_deficit_inr DESC;

