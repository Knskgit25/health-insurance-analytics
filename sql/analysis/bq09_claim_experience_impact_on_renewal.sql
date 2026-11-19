-- Business Question: BQ9 - Does claim experience (rejection, slow settlement) affect policy renewal?
-- Techniques demonstrated: Anti-join / outer join categorization, customer journey experience segmentation.

WITH policy_claims_experience AS (
    SELECT
        c.policy_id,
        COUNT(c.claim_id) AS claims_count,
        COUNT(CASE WHEN c.claim_status = 'Rejected' THEN 1 END) AS rejected_claims_count,
        MAX(c.settlement_tat_days) AS max_tat_experienced,
        AVG(c.settlement_tat_days) AS avg_tat_experienced
    FROM fact_claims c
    GROUP BY c.policy_id
),
policy_experience_category AS (
    SELECT
        p.policy_id,
        r.renewal_id,
        r.renewed_flag,
        CASE
            WHEN pce.policy_id IS NULL THEN 'No Claims Filed'
            WHEN pce.rejected_claims_count > 0 THEN 'Experienced Rejection'
            WHEN pce.max_tat_experienced > 20 THEN 'Slow Settlement (TAT > 20d)'
            WHEN pce.avg_tat_experienced <= 5 THEN 'Fast Settlement (TAT <= 5d)'
            ELSE 'Standard Approved Claims'
        END AS claim_experience_segment
    FROM fact_renewals r
    JOIN dim_policy p ON r.policy_id = p.policy_id
    LEFT JOIN policy_claims_experience pce ON p.policy_id = pce.policy_id
)
SELECT
    claim_experience_segment,
    COUNT(renewal_id) AS total_policies_due,
    COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) AS policies_renewed,
    COUNT(CASE WHEN renewed_flag = 0 THEN 1 END) AS policies_lapsed,
    ROUND(
        COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) * 100.0 / COUNT(renewal_id),
        2
    ) AS persistency_rate_pct,
    ROUND(
        COUNT(CASE WHEN renewed_flag = 0 THEN 1 END) * 100.0 / COUNT(renewal_id),
        2
    ) AS lapse_rate_pct
FROM policy_experience_category
GROUP BY claim_experience_segment
ORDER BY persistency_rate_pct DESC;

