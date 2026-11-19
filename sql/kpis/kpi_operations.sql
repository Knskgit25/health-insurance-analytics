-- KPI Group: Operations
-- Computes Average Settlement TAT and Cashless Share

SELECT
    c.claim_type,
    p.hospital_tier,
    COUNT(c.claim_id) AS claim_count,
    -- Cashless Share
    ROUND(
        COUNT(CASE WHEN c.claim_type = 'Cashless' THEN 1 END) * 100.0 / COUNT(c.claim_id),
        2
    ) AS cashless_share_pct,
    -- Average Settlement TAT (Days)
    ROUND(AVG(c.settlement_tat_days), 2) AS avg_settlement_tat_days,
    -- Median TAT
    MEDIAN(c.settlement_tat_days) AS median_settlement_tat_days,
    -- 90th Percentile TAT
    QUANTILE_CONT(c.settlement_tat_days, 0.90) AS p90_settlement_tat_days,
    -- Out-of-pocket patient ratio
    ROUND(
        SUM(c.patient_paid_amount) * 100.0 / NULLIF(SUM(c.billed_amount), 0.0),
        2
    ) AS patient_cost_share_pct
FROM fact_claims c
JOIN dim_provider p ON c.provider_id = p.provider_id
WHERE c.claim_status IN ('Approved', 'Partially Approved', 'Rejected')
GROUP BY c.claim_type, p.hospital_tier
ORDER BY c.claim_type, p.hospital_tier;

