-- Business Question: BQ4 - How long does claim settlement take, and what key operational factors drive turnaround delays?
-- Techniques demonstrated: Operational breakdown by claim type, network status, and clinical emergency flag.

SELECT
    c.claim_type,
    p.network_status,
    CASE WHEN c.is_emergency = 1 THEN 'Emergency' ELSE 'Planned' END AS admission_nature,
    COUNT(c.claim_id) AS settled_claims_count,
    ROUND(AVG(c.settlement_tat_days), 2) AS mean_tat_days,
    ROUND(MEDIAN(c.settlement_tat_days), 2) AS median_tat_days,
    ROUND(QUANTILE_CONT(c.settlement_tat_days, 0.90), 2) AS p90_tat_days,
    ROUND(COUNT(CASE WHEN c.settlement_tat_days > 20 THEN 1 END) * 100.0 / COUNT(c.claim_id), 2) AS delayed_claims_pct_gt_20d
FROM fact_claims c
JOIN dim_provider p ON c.provider_id = p.provider_id
WHERE c.claim_status IN ('Approved', 'Partially Approved', 'Rejected')
GROUP BY c.claim_type, p.network_status, admission_nature
ORDER BY mean_tat_days DESC;

