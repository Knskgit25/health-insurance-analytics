-- Business Question: BQ3/BQ6 - Catastrophic Tail Risk: What share of portfolio liability is driven by the 95th and 99th percentile claims?
-- Techniques demonstrated: PERCENT_RANK, NTILE, cumulative liability concentration.

WITH claim_percentiles AS (
    SELECT
        c.claim_id,
        c.diagnosis_id,
        d.diagnosis_name,
        d.diagnosis_category,
        p.hospital_tier,
        c.billed_amount,
        c.paid_amount,
        PERCENT_RANK() OVER (ORDER BY c.billed_amount) AS billed_pct_rank
    FROM fact_claims c
    JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
    JOIN dim_provider p ON c.provider_id = p.provider_id
    WHERE c.paid_amount > 0
),
tiered_claims AS (
    SELECT
        CASE
            WHEN billed_pct_rank >= 0.99 THEN 'Top 1% (P99+ Extreme Catastrophic)'
            WHEN billed_pct_rank >= 0.95 THEN 'Top 5% (P95-P99 High Catastrophic)'
            WHEN billed_pct_rank >= 0.80 THEN 'Top 20% (P80-P95 Elevated)'
            ELSE 'Bottom 80% (Standard Claims)'
        END AS tail_risk_tier,
        claim_id,
        diagnosis_category,
        hospital_tier,
        billed_amount,
        paid_amount
    FROM claim_percentiles
)
SELECT
    tail_risk_tier,
    COUNT(claim_id) AS claim_count,
    ROUND(COUNT(claim_id) * 100.0 / (SELECT COUNT(*) FROM tiered_claims), 2) AS volume_share_pct,
    ROUND(SUM(paid_amount), 2) AS total_paid_inr,
    ROUND(SUM(paid_amount) * 100.0 / (SELECT SUM(paid_amount) FROM tiered_claims), 2) AS payout_share_pct,
    ROUND(AVG(paid_amount), 2) AS avg_paid_amount,
    ROUND(MAX(billed_amount), 2) AS max_billed_amount
FROM tiered_claims
GROUP BY tail_risk_tier
ORDER BY total_paid_inr DESC;

