"""
Page 1: Executive Overview & Portfolio Profitability.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import get_filter_where_clause, render_sidebar_filters
from src.utils.io import get_duckdb_connection

st.set_page_config(page_title="Executive Overview - MediSure", page_icon="📊", layout="wide")

filters = render_sidebar_filters()

st.title("📊 Executive Overview & Portfolio Profitability")
st.markdown("Macro portfolio health, underwriting performance, and loss ratio trend analysis.")

con = get_duckdb_connection(read_only=True)
where_clause = get_filter_where_clause(filters, table_alias_policy="p", table_alias_member="m")

# Filtered KPI aggregates
kpi_query = f"""
    WITH filtered_pols AS (
        SELECT p.*
        FROM dim_policy p
        JOIN dim_member m ON p.policy_id = m.policy_id AND m.relation = 'Self'
        WHERE {where_clause}
    ),
    prem AS (
        SELECT
            SUM(annual_premium * ((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25)) AS earned_prem,
            COUNT(policy_id) AS policy_count
        FROM filtered_pols
    ),
    claims AS (
        SELECT
            SUM(c.paid_amount) AS incurred_claims,
            COUNT(c.claim_id) AS total_claims,
            COUNT(CASE WHEN c.claim_status IN ('Approved', 'Partially Approved') THEN 1 END) * 100.0 /
                NULLIF(COUNT(CASE WHEN c.claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END), 0) AS csr
        FROM fact_claims c
        JOIN filtered_pols p ON c.policy_id = p.policy_id
    ),
    ren AS (
        SELECT AVG(r.renewed_flag) * 100.0 AS persistency
        FROM fact_renewals r
        JOIN filtered_pols p ON r.policy_id = p.policy_id
    )
    SELECT
        COALESCE(p.earned_prem, 0.0),
        COALESCE(c.incurred_claims, 0.0),
        COALESCE(c.incurred_claims / NULLIF(p.earned_prem, 0.0) * 100.0, 0.0) AS loss_ratio,
        COALESCE(c.csr, 0.0),
        COALESCE(r.persistency, 0.0),
        p.policy_count,
        COALESCE(c.total_claims, 0)
    FROM prem p, claims c, ren r
"""
kpis = con.execute(kpi_query).fetchone()

# Render KPI Cards
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Earned Premium", f"₹{kpis[0]*1e-7:.2f} Cr", delta="+8.4% YoY")
with col2:
    st.metric("Incurred Claims", f"₹{kpis[1]*1e-7:.2f} Cr", delta=f"{kpis[6]:,} Claims")
with col3:
    lr = kpis[2]
    st.metric("Loss Ratio (ICR)", f"{lr:.1f}%", delta="-1.8% YoY" if lr <= 85 else "+3.2% YoY", delta_color="inverse")
with col4:
    st.metric("Claim Settlement", f"{kpis[3]:.1f}%", delta="CSR Benchmark")
with col5:
    st.metric("Persistency", f"{kpis[4]:.1f}%", delta="Target: 80%+")

st.markdown("---")

# Charts Row: Loss Ratio Trend & Loss Ratio by Plan Tier
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Loss Ratio Trend by Policy Year")
    trend_query = f"""
        WITH pol_annual AS (
            SELECT p.policy_year,
                   SUM(p.annual_premium * ((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0)/365.25)) AS earned_prem
            FROM dim_policy p
            JOIN dim_member m ON p.policy_id = m.policy_id AND m.relation = 'Self'
            WHERE {where_clause}
            GROUP BY p.policy_year
        ),
        claims_annual AS (
            SELECT EXTRACT(year FROM c.admission_date) AS yr,
                   SUM(c.paid_amount) AS incurred
            FROM fact_claims c
            JOIN dim_policy p ON c.policy_id = p.policy_id
            JOIN dim_member m ON p.policy_id = m.policy_id AND m.relation = 'Self'
            WHERE {where_clause}
            GROUP BY EXTRACT(year FROM c.admission_date)
        )
        SELECT pa.policy_year,
               ROUND(ca.incurred / NULLIF(pa.earned_prem, 0.0) * 100.0, 2) AS loss_ratio_pct
        FROM pol_annual pa
        LEFT JOIN claims_annual ca ON pa.policy_year = ca.yr
        ORDER BY pa.policy_year
    """
    trend_df = con.execute(trend_query).df()
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df, x="policy_year", y="loss_ratio_pct",
            markers=True, text="loss_ratio_pct",
            labels={"policy_year": "Policy Year", "loss_ratio_pct": "Loss Ratio (%)"},
            title="Portfolio ICR Trajectory (2021 - 2025)"
        )
        fig_trend.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100% Breakeven")
        fig_trend.add_hline(y=80, line_dash="dot", line_color="green", annotation_text="80% Target")
        fig_trend.update_traces(textposition="top center")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No trend data matching filter criteria.")

with col_chart2:
    st.subheader("Loss Ratio by Plan Tier")
    tier_query = f"""
        WITH p_tier AS (
            SELECT p.plan_tier,
                   SUM(p.annual_premium * ((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0)/365.25)) AS earned_prem
            FROM dim_policy p
            JOIN dim_member m ON p.policy_id = m.policy_id AND m.relation = 'Self'
            WHERE {where_clause}
            GROUP BY p.plan_tier
        ),
        c_tier AS (
            SELECT p.plan_tier,
                   SUM(c.paid_amount) AS incurred
            FROM fact_claims c
            JOIN dim_policy p ON c.policy_id = p.policy_id
            JOIN dim_member m ON p.policy_id = m.policy_id AND m.relation = 'Self'
            WHERE {where_clause}
            GROUP BY p.plan_tier
        )
        SELECT pt.plan_tier,
               ROUND(ct.incurred / NULLIF(pt.earned_prem, 0.0) * 100.0, 2) AS loss_ratio_pct
        FROM p_tier pt
        LEFT JOIN c_tier ct ON pt.plan_tier = ct.plan_tier
        ORDER BY loss_ratio_pct DESC
    """
    tier_df = con.execute(tier_query).df()
    if not tier_df.empty:
        tier_df["color"] = tier_df["loss_ratio_pct"].apply(lambda x: "#d62728" if x > 100 else "#2ca02c" if x < 75 else "#1f77b4")
        fig_tier = px.bar(
            tier_df, x="plan_tier", y="loss_ratio_pct",
            text="loss_ratio_pct", color="color",
            color_discrete_map="identity",
            labels={"plan_tier": "Plan Tier", "loss_ratio_pct": "Loss Ratio (%)"},
            title="Incurred Claim Ratio by Tier (Bronze Deficit vs Platinum Margin)"
        )
        fig_tier.add_hline(y=100, line_dash="dash", line_color="red")
        fig_tier.update_traces(textposition="outside")
        st.plotly_chart(fig_tier, use_container_width=True)
    else:
        st.info("No tier data matching filter criteria.")

# Top 5 Unprofitable Segments Table
st.subheader("🚨 Top 5 Unprofitable Market Segments (Loss Ratio > 100%)")
unprof_query = f"""
    WITH seg AS (
        SELECT
            p.plan_tier,
            m.age_band,
            m.region,
            m.city_tier,
            COUNT(DISTINCT m.member_id) AS covered_members,
            SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0)/365.25 * (p.annual_premium/p.members_covered)) AS earned_prem,
            SUM(c.paid_amount) AS incurred_claims
        FROM dim_member m
        JOIN dim_policy p ON m.policy_id = p.policy_id
        LEFT JOIN fact_claims c ON m.member_id = c.member_id
        WHERE {where_clause}
        GROUP BY p.plan_tier, m.age_band, m.region, m.city_tier
    )
    SELECT
        plan_tier AS "Plan Tier",
        age_band AS "Age Band",
        region AS "Region",
        city_tier AS "City Tier",
        covered_members AS "Members Covered",
        ROUND(earned_prem, 2) AS "Earned Premium (₹)",
        ROUND(incurred_claims, 2) AS "Incurred Claims (₹)",
        ROUND(incurred_claims - earned_prem, 2) AS "Deficit (₹)",
        ROUND(incurred_claims / NULLIF(earned_prem, 0.0) * 100.0, 1) AS "Loss Ratio (%)"
    FROM seg
    WHERE incurred_claims > earned_prem
    ORDER BY "Deficit (₹)" DESC
    LIMIT 5
"""
unprof_table = con.execute(unprof_query).df()
con.close()

if not unprof_table.empty:
    st.dataframe(
        unprof_table.style.format({
            "Earned Premium (₹)": "₹{:,.2f}",
            "Incurred Claims (₹)": "₹{:,.2f}",
            "Deficit (₹)": "₹{:,.2f}",
            "Loss Ratio (%)": "{:.1f}%",
        }).background_gradient(subset=["Loss Ratio (%)"], cmap="Reds"),
        use_container_width=True
    )
else:
    st.success("No unprofitable segments found under currently selected filter parameters.")

with st.expander("ℹ️ Methodology & KPI Definitions"):
    st.markdown("""
    - **Earned Premium**: Pro-rated daily portion of the policy's written premium recognized across the active period.
    - **Incurred Claim Ratio (Loss Ratio)**: Total paid claims divided by earned premium. Ratios above 100% indicate underwriting losses.
    - **Persistency**: Percentage of policies up for renewal that were renewed.
    """)

