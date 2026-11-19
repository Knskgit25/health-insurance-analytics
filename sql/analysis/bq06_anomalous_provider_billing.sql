-- Business Question: BQ6 - Which healthcare providers exhibit anomalous billing, short LOS, and elevated repudiation/fraud rates?
-- Techniques demonstrated: Complex provider risk scoring, z-score billing ratio, DENSE_RANK.

WITH provider_stats AS (
    SELECT
        p.provider_id,
        p.provider_name,
        p.city,
        p.hospital_tier,
        p.network_status,
        COUNT(c.claim_id) AS total_claims,
        AVG(c.billed_amount) AS avg_billed,
        AVG(c.length_of_stay) AS avg_los,
        AVG(c.is_fraud_flag) * 100.0 AS fraud_rate_pct,
        COUNT(CASE WHEN c.claim_status = 'Rejected' THEN 1 END) * 100.0 / COUNT(c.claim_id) AS rejection_rate_pct,
        COUNT(CASE WHEN c.length_of_stay <= 1 AND c.billed_amount > 100000 THEN 1 END) AS short_los_high_bill_count
    FROM dim_provider p
    JOIN fact_claims c ON p.provider_id = c.provider_id
    GROUP BY p.provider_id, p.provider_name, p.city, p.hospital_tier, p.network_status
    HAVING COUNT(c.claim_id) >= 20
)
SELECT
    provider_id,
    provider_name,
    city,
    hospital_tier,
    network_status,
    total_claims,
    ROUND(avg_billed, 2) AS avg_billed_inr,
    ROUND(avg_los, 1) AS avg_los_days,
    ROUND(fraud_rate_pct, 2) AS fraud_rate_pct,
    ROUND(rejection_rate_pct, 2) AS rejection_rate_pct,
    short_los_high_bill_count,
    -- Anomalous Risk Ranking
    DENSE_RANK() OVER (ORDER BY fraud_rate_pct DESC, avg_billed DESC) AS risk_rank
FROM provider_stats
ORDER BY risk_rank ASC
LIMIT 20;

