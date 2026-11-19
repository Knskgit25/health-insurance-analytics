-- Business Question: BQ3 - How does claim cost, billing severity, and length of stay vary across hospital tiers?
-- Techniques demonstrated: ANOVA-style summary statistics, percentile distributions, Tier 1 vs Tier 3 pricing ratio.

SELECT
    p.hospital_tier,
    COUNT(c.claim_id) AS total_claims,
    ROUND(AVG(c.billed_amount), 2) AS avg_billed_amount,
    ROUND(MEDIAN(c.billed_amount), 2) AS median_billed_amount,
    ROUND(QUANTILE_CONT(c.billed_amount, 0.90), 2) AS p90_billed_amount,
    ROUND(AVG(c.paid_amount), 2) AS avg_paid_amount,
    ROUND(AVG(c.length_of_stay), 2) AS avg_length_of_stay_days,
    ROUND(AVG(c.icu_days), 2) AS avg_icu_days,
    -- Ratio of billed amount relative to Tier 3 benchmark
    ROUND(
        AVG(c.billed_amount) /
        FIRST_VALUE(AVG(c.billed_amount)) OVER (ORDER BY p.hospital_tier DESC),
        2
    ) AS cost_multiplier_vs_tier3
FROM fact_claims c
JOIN dim_provider p ON c.provider_id = p.provider_id
GROUP BY p.hospital_tier
ORDER BY p.hospital_tier;

