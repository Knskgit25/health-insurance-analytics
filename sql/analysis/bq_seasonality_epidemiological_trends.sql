-- Business Question: BQ3/BQ10 - Seasonality: How do respiratory and infectious claims surge across calendar months and regions?
-- Techniques demonstrated: Epidemiological monthly trend, cross-tabular matrix, regional surge analysis.

SELECT
    d.month,
    d.month_name,
    m.region,
    COUNT(CASE WHEN diag.diagnosis_category = 'Respiratory' THEN 1 END) AS respiratory_claims,
    COUNT(CASE WHEN diag.diagnosis_category = 'Infectious' THEN 1 END) AS infectious_claims,
    COUNT(CASE WHEN diag.diagnosis_category = 'Cardiac' THEN 1 END) AS cardiac_claims,
    COUNT(c.claim_id) AS total_monthly_claims,
    ROUND(SUM(c.paid_amount), 2) AS total_monthly_paid_inr
FROM fact_claims c
JOIN dim_date d ON c.admission_date = d.date
JOIN dim_member m ON c.member_id = m.member_id
JOIN dim_diagnosis diag ON c.diagnosis_id = diag.diagnosis_id
GROUP BY d.month, d.month_name, m.region
ORDER BY d.month, m.region;

