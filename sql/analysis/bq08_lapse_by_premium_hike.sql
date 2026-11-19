-- Business Question: BQ8 - How does renewal premium price hike affect policy persistency and lapse rates?
-- Techniques demonstrated: Price sensitivity binning, conditional aggregation, elasticity analysis.

SELECT
    CASE
        WHEN premium_change_pct < 0.0 THEN 'Negative (Price Reduction)'
        WHEN premium_change_pct <= 0.05 THEN '0% to 5% (Minimal Hike)'
        WHEN premium_change_pct <= 0.15 THEN '5% to 15% (Moderate Hike)'
        WHEN premium_change_pct <= 0.25 THEN '15% to 25% (Significant Hike)'
        ELSE 'Above 25% (Severe Hike)'
    END AS premium_hike_bracket,
    COUNT(renewal_id) AS total_renewals_due,
    COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) AS policies_renewed,
    COUNT(CASE WHEN renewed_flag = 0 THEN 1 END) AS policies_lapsed,
    ROUND(
        COUNT(CASE WHEN renewed_flag = 1 THEN 1 END) * 100.0 / COUNT(renewal_id),
        2
    ) AS persistency_rate_pct,
    ROUND(
        COUNT(CASE WHEN renewed_flag = 0 THEN 1 END) * 100.0 / COUNT(renewal_id),
        2
    ) AS lapse_rate_pct,
    ROUND(AVG(premium_change_pct) * 100.0, 2) AS mean_actual_hike_pct
FROM fact_renewals
GROUP BY premium_hike_bracket
ORDER BY lapse_rate_pct ASC;

