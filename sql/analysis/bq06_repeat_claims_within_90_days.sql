-- Business Question: BQ6 - Identify members with repeat hospitalizations within 90 days (Potential churn/fraud signal).
-- Techniques demonstrated: Self-join on fact_claims, date interval inequality filtering, window ranking.

WITH repeat_admissions AS (
    SELECT
        c1.claim_id AS first_claim_id,
        c1.member_id,
        c1.admission_date AS first_admission_date,
        c1.billed_amount AS first_billed_amount,
        c2.claim_id AS second_claim_id,
        c2.admission_date AS second_admission_date,
        c2.billed_amount AS second_billed_amount,
        c2.is_fraud_flag AS second_claim_fraud_flag,
        DATE_DIFF('day', c1.admission_date, c2.admission_date) AS days_between_admissions
    FROM fact_claims c1
    JOIN fact_claims c2
        ON c1.member_id = c2.member_id
       AND c1.claim_id != c2.claim_id
       AND c2.admission_date > c1.admission_date
       AND DATE_DIFF('day', c1.admission_date, c2.admission_date) <= 90
)
SELECT
    m.member_id,
    m.gender,
    m.age_band,
    m.city,
    m.has_diabetes,
    m.has_cardiac_history,
    ra.first_claim_id,
    ra.first_admission_date,
    ra.first_billed_amount,
    ra.second_claim_id,
    ra.second_admission_date,
    ra.second_billed_amount,
    ra.days_between_admissions,
    ra.second_claim_fraud_flag
FROM repeat_admissions ra
JOIN dim_member m ON ra.member_id = m.member_id
ORDER BY ra.days_between_admissions ASC, ra.second_billed_amount DESC
LIMIT 50;

