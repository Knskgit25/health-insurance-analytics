-- KPI Group: Risk & Concentration
-- Computes Provider Concentration (Top 10 Share) and High-Value Catastrophic Claim Share (P95)

WITH provider_totals AS (
    SELECT
        p.provider_id,
        p.provider_name,
        p.hospital_tier,
        SUM(c.paid_amount) AS provider_paid_claims,
        COUNT(c.claim_id) AS provider_claim_count
    FROM fact_claims c
    JOIN dim_provider p ON c.provider_id = p.provider_id
    GROUP BY p.provider_id, p.provider_name, p.hospital_tier
),
ranked_providers AS (
    SELECT
        provider_id,
        provider_name,
        hospital_tier,
        provider_paid_claims,
        provider_claim_count,
        DENSE_RANK() OVER (ORDER BY provider_paid_claims DESC) AS provider_rank,
        SUM(provider_paid_claims) OVER () AS portfolio_total_paid
    FROM provider_totals
),
p95_threshold AS (
    SELECT QUANTILE_CONT(billed_amount, 0.95) AS p95_billed_amount FROM fact_claims
),
high_value_claims AS (
    SELECT
        COUNT(CASE WHEN c.billed_amount >= t.p95_billed_amount THEN 1 END) AS high_val_claim_count,
        SUM(CASE WHEN c.billed_amount >= t.p95_billed_amount THEN c.paid_amount ELSE 0.0 END) AS high_val_paid_amount,
        COUNT(c.claim_id) AS total_claim_count,
        SUM(c.paid_amount) AS total_paid_amount
    FROM fact_claims c
    CROSS JOIN p95_threshold t
)
SELECT
    -- Provider Concentration: Top 10 Provider Share
    (SELECT ROUND(SUM(provider_paid_claims) * 100.0 / MAX(portfolio_total_paid), 2)
     FROM ranked_providers WHERE provider_rank <= 10) AS top10_provider_concentration_pct,
    -- Total P95 claims count share
    ROUND(h.high_val_claim_count * 100.0 / h.total_claim_count, 2) AS high_val_claim_volume_pct,
    -- Share of total paid claims originating from P95 catastrophic claims
    ROUND(h.high_val_paid_amount * 100.0 / h.total_paid_amount, 2) AS high_val_claim_cost_share_pct
FROM high_value_claims h;

