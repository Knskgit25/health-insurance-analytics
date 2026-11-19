-- Business Question: BQ7 - How do pre-existing chronic conditions impact member-level annual claim costs at policy-issue time?
-- Techniques demonstrated: Clinical cohort aggregation, risk multiplier computation vs healthy baseline.

WITH member_annual_claims AS (
    SELECT
        m.member_id,
        m.age_band,
        m.smoker_flag,
        m.has_diabetes,
        m.has_hypertension,
        m.has_cardiac_history,
        CASE
            WHEN m.has_cardiac_history = 1 THEN 'Cardiac History'
            WHEN m.has_diabetes = 1 AND m.has_hypertension = 1 THEN 'Diabetes + Hypertension'
            WHEN m.has_diabetes = 1 THEN 'Diabetes Only'
            WHEN m.has_hypertension = 1 THEN 'Hypertension Only'
            ELSE 'No Chronic Conditions'
        END AS chronic_profile,
        COALESCE(SUM(c.paid_amount), 0.0) AS total_paid_claims,
        COUNT(c.claim_id) AS total_claims
    FROM dim_member m
    LEFT JOIN fact_claims c ON m.member_id = c.member_id
    GROUP BY
        m.member_id, m.age_band, m.smoker_flag,
        m.has_diabetes, m.has_hypertension, m.has_cardiac_history
)
SELECT
    chronic_profile,
    age_band,
    COUNT(member_id) AS total_members,
    COUNT(CASE WHEN total_claims > 0 THEN 1 END) AS members_with_claims,
    ROUND(COUNT(CASE WHEN total_claims > 0 THEN 1 END) * 100.0 / COUNT(member_id), 2) AS claim_incidence_pct,
    ROUND(AVG(total_paid_claims), 2) AS avg_annual_claim_cost_per_member,
    ROUND(MEDIAN(total_paid_claims), 2) AS median_annual_claim_cost,
    ROUND(QUANTILE_CONT(total_paid_claims, 0.90), 2) AS p90_annual_claim_cost
FROM member_annual_claims
GROUP BY chronic_profile, age_band
ORDER BY chronic_profile, age_band;

