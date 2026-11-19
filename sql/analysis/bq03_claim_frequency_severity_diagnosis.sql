-- Business Question: BQ3 - What are claim frequency and severity by diagnosis category and age band?
-- Techniques demonstrated: CTEs, Exposure pro-rating, severity vs frequency matrix, pure premium calculation.

WITH member_exposure_by_age AS (
    SELECT
        m.age_band,
        SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25) AS member_years
    FROM dim_member m
    JOIN dim_policy p ON m.policy_id = p.policy_id
    GROUP BY m.age_band
),
diagnosis_claims AS (
    SELECT
        d.diagnosis_category,
        m.age_band,
        COUNT(c.claim_id) AS total_claims,
        SUM(c.paid_amount) AS total_paid,
        COUNT(CASE WHEN c.paid_amount > 0 THEN 1 END) AS paid_claims_count
    FROM fact_claims c
    JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
    JOIN dim_member m ON c.member_id = m.member_id
    GROUP BY d.diagnosis_category, m.age_band
)
SELECT
    dc.diagnosis_category,
    dc.age_band,
    dc.total_claims,
    ROUND(mea.member_years, 2) AS cohort_member_years,
    -- Frequency
    ROUND(dc.total_claims * 1.0 / NULLIF(mea.member_years, 0.0), 4) AS claim_frequency,
    -- Severity
    ROUND(dc.total_paid / NULLIF(dc.paid_claims_count, 0.0), 2) AS claim_severity_avg_paid,
    -- Pure Premium
    ROUND(dc.total_paid / NULLIF(mea.member_years, 0.0), 2) AS pure_premium_per_member_year
FROM diagnosis_claims dc
JOIN member_exposure_by_age mea ON dc.age_band = mea.age_band
ORDER BY dc.diagnosis_category, dc.age_band;

