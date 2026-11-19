-- Business Question: BQ10 - How do cashless vs reimbursement claims differ in cost, turnaround, and rejection?
-- Techniques demonstrated: Comparative operational matrix, out-of-pocket patient load, statistical discrepancy analysis.

SELECT
    c.claim_type,
    COUNT(c.claim_id) AS total_claims,
    ROUND(COUNT(c.claim_id) * 100.0 / SUM(COUNT(c.claim_id)) OVER (), 2) AS volume_share_pct,
    ROUND(AVG(c.billed_amount), 2) AS avg_billed_amount,
    ROUND(AVG(c.paid_amount), 2) AS avg_paid_amount,
    ROUND(AVG(c.patient_paid_amount), 2) AS avg_patient_out_of_pocket,
    ROUND(SUM(c.patient_paid_amount) * 100.0 / NULLIF(SUM(c.billed_amount), 0.0), 2) AS patient_burden_pct,
    ROUND(AVG(c.settlement_tat_days), 2) AS avg_tat_days,
    ROUND(MEDIAN(c.settlement_tat_days), 2) AS median_tat_days,
    ROUND(
        COUNT(CASE WHEN c.claim_status = 'Rejected' THEN 1 END) * 100.0 /
        NULLIF(COUNT(CASE WHEN c.claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END), 0),
        2
    ) AS rejection_rate_pct
FROM fact_claims c
GROUP BY c.claim_type
ORDER BY c.claim_type;

