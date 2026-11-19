-- KPI Group: Retention & Policyholder Churn
-- Computes Persistency (Renewal Rate) and Lapse Rate by Sales Channel and Plan Tier

SELECT
    p.sales_channel,
    p.plan_tier,
    COUNT(r.renewal_id) AS renewals_due,
    COUNT(CASE WHEN r.renewed_flag = 1 THEN 1 END) AS policies_renewed,
    COUNT(CASE WHEN r.renewed_flag = 0 THEN 1 END) AS policies_lapsed,
    -- Persistency Rate = Renewed / Due for Renewal
    ROUND(
        COUNT(CASE WHEN r.renewed_flag = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(r.renewal_id), 0),
        2
    ) AS persistency_rate_pct,
    -- Lapse Rate = 100% - Persistency
    ROUND(
        COUNT(CASE WHEN r.renewed_flag = 0 THEN 1 END) * 100.0 / NULLIF(COUNT(r.renewal_id), 0),
        2
    ) AS lapse_rate_pct,
    -- Avg Premium Hike on Renewal
    ROUND(AVG(r.premium_change_pct) * 100.0, 2) AS avg_premium_change_pct
FROM fact_renewals r
JOIN dim_policy p ON r.policy_id = p.policy_id
GROUP BY p.sales_channel, p.plan_tier
ORDER BY p.sales_channel, p.plan_tier;

