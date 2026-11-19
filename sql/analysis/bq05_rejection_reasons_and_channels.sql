-- Business Question: BQ5 - What is the claim rejection rate, and what are the primary root causes across sales channels?
-- Techniques demonstrated: Conditional aggregation, Pareto contribution calculation, channel comparison.

WITH channel_decided_claims AS (
    SELECT
        p.sales_channel,
        COUNT(c.claim_id) AS total_decided_claims,
        COUNT(CASE WHEN c.claim_status = 'Rejected' THEN 1 END) AS total_rejected_claims
    FROM fact_claims c
    JOIN dim_policy p ON c.policy_id = p.policy_id
    WHERE c.claim_status IN ('Approved', 'Partially Approved', 'Rejected')
    GROUP BY p.sales_channel
),
rejection_breakdown AS (
    SELECT
        p.sales_channel,
        c.rejection_reason,
        COUNT(c.claim_id) AS reason_count
    FROM fact_claims c
    JOIN dim_policy p ON c.policy_id = p.policy_id
    WHERE c.claim_status = 'Rejected'
    GROUP BY p.sales_channel, c.rejection_reason
)
SELECT
    rb.sales_channel,
    rb.rejection_reason,
    rb.reason_count,
    ROUND(rb.reason_count * 100.0 / cdc.total_rejected_claims, 2) AS pct_of_channel_rejections,
    ROUND(cdc.total_rejected_claims * 100.0 / cdc.total_decided_claims, 2) AS channel_overall_rejection_rate_pct,
    -- Cumulative Pareto share of rejections within channel
    ROUND(
        SUM(rb.reason_count) OVER (PARTITION BY rb.sales_channel ORDER BY rb.reason_count DESC) * 100.0 / cdc.total_rejected_claims,
        2
    ) AS pareto_cumulative_share_pct
FROM rejection_breakdown rb
JOIN channel_decided_claims cdc ON rb.sales_channel = cdc.sales_channel
ORDER BY rb.sales_channel, rb.reason_count DESC;

