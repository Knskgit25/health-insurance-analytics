-- KPI Group: Profitability & Underwriting
-- Computes Earned Premium, Incurred Claims, Loss Ratio (ICR), Pure Premium, and Avg Premium per Member

WITH policy_exposure AS (
    SELECT
        p.policy_id,
        p.plan_type,
        p.plan_tier,
        p.sales_channel,
        p.policy_year,
        p.annual_premium,
        p.members_covered,
        p.policy_start_date,
        p.policy_end_date,
        -- Exposure in member-years (pro-rated days / 365.25 * members_covered)
        ROUND(
            (DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25 * p.members_covered,
            4
        ) AS member_years_exposure,
        -- Earned premium pro-rated
        ROUND(
            p.annual_premium * ((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25),
            2
        ) AS earned_premium
    FROM dim_policy p
),
claims_liability AS (
    SELECT
        c.policy_id,
        SUM(c.paid_amount) AS paid_claims,
        SUM(CASE WHEN c.claim_status = 'Pending' THEN c.approved_amount ELSE 0.0 END) AS pending_claims,
        SUM(c.paid_amount + CASE WHEN c.claim_status = 'Pending' THEN c.approved_amount ELSE 0.0 END) AS incurred_claims,
        COUNT(c.claim_id) AS total_claims
    FROM fact_claims c
    GROUP BY c.policy_id
)
SELECT
    pe.plan_type,
    pe.plan_tier,
    COUNT(pe.policy_id) AS total_policies,
    SUM(pe.members_covered) AS total_members,
    ROUND(SUM(pe.member_years_exposure), 2) AS total_member_years,
    ROUND(SUM(pe.earned_premium), 2) AS total_earned_premium,
    ROUND(COALESCE(SUM(cl.incurred_claims), 0.0), 2) AS total_incurred_claims,
    -- Loss Ratio (ICR) = Incurred Claims / Earned Premium
    ROUND(
        COALESCE(SUM(cl.incurred_claims), 0.0) / NULLIF(SUM(pe.earned_premium), 0.0) * 100.0,
        2
    ) AS loss_ratio_pct,
    -- Pure Premium = Incurred Claims / Member-Years
    ROUND(
        COALESCE(SUM(cl.incurred_claims), 0.0) / NULLIF(SUM(pe.member_years_exposure), 0.0),
        2
    ) AS pure_premium,
    -- Avg Premium per Member
    ROUND(
        SUM(pe.annual_premium) / NULLIF(SUM(pe.members_covered), 0.0),
        2
    ) AS avg_premium_per_member
FROM policy_exposure pe
LEFT JOIN claims_liability cl ON pe.policy_id = cl.policy_id
GROUP BY pe.plan_type, pe.plan_tier
ORDER BY pe.plan_type, pe.plan_tier;

