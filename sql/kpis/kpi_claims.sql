-- KPI Group: Claims Analytics
-- Computes Claim Frequency, Claim Severity, Claim Settlement Ratio (CSR), and Rejection Rate

WITH exposure AS (
    SELECT
        p.policy_id,
        ROUND((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0) / 365.25 * p.members_covered, 4) AS member_years
    FROM dim_policy p
),
claims_agg AS (
    SELECT
        c.diagnosis_id,
        d.diagnosis_category,
        COUNT(c.claim_id) AS total_claims_count,
        COUNT(CASE WHEN c.claim_status IN ('Approved', 'Partially Approved') THEN 1 END) AS approved_count,
        COUNT(CASE WHEN c.claim_status = 'Rejected' THEN 1 END) AS rejected_count,
        COUNT(CASE WHEN c.claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END) AS decided_count,
        SUM(c.paid_amount) AS total_paid_amount,
        COUNT(CASE WHEN c.paid_amount > 0 THEN 1 END) AS paid_claims_count
    FROM fact_claims c
    JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
    GROUP BY c.diagnosis_id, d.diagnosis_category
),
total_exposure AS (
    SELECT SUM(member_years) AS portfolio_member_years FROM exposure
)
SELECT
    ca.diagnosis_category,
    SUM(ca.total_claims_count) AS total_claims,
    -- Claim Frequency = Claims / Member-Years
    ROUND(
        SUM(ca.total_claims_count) * 1.0 / NULLIF(MAX(te.portfolio_member_years), 0.0),
        4
    ) AS claim_frequency_per_member_year,
    -- Claim Severity = Total Paid / Count of Paid Claims
    ROUND(
        SUM(ca.total_paid_amount) / NULLIF(SUM(ca.paid_claims_count), 0.0),
        2
    ) AS claim_severity_avg_paid,
    -- Claim Settlement Ratio (CSR) = Approved / Decided Claims
    ROUND(
        SUM(ca.approved_count) * 100.0 / NULLIF(SUM(ca.decided_count), 0),
        2
    ) AS settlement_ratio_pct,
    -- Rejection Rate = Rejected / Decided Claims
    ROUND(
        SUM(ca.rejected_count) * 100.0 / NULLIF(SUM(ca.decided_count), 0),
        2
    ) AS rejection_rate_pct
FROM claims_agg ca
CROSS JOIN total_exposure te
GROUP BY ca.diagnosis_category
ORDER BY total_claims DESC;

