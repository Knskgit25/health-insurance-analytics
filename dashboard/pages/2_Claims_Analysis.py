"""
Page 2: Claims Analysis & Operations.
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

st.set_page_config(page_title="Claims Analysis - MediSure", page_icon="🏥", layout="wide")

filters = render_sidebar_filters()

st.title("🏥 Claims Analytics & Clinical Incidence")
st.markdown("Detailed breakdown of claim frequency, severity by ICD-10 category, settlement TAT, and repudiations.")

con = get_duckdb_connection(read_only=True)
where_clause = get_filter_where_clause(filters, table_alias_policy="p", table_alias_member="m")

# Row 1: Frequency & Severity Scatter + Cost Distribution
col1, col2 = st.columns(2)

with col1:
    st.subheader("Frequency vs Severity by Diagnosis Category")
    dx_query = f"""
        SELECT
            d.diagnosis_category,
            COUNT(c.claim_id) AS total_claims,
            ROUND(AVG(c.paid_amount), 2) AS avg_severity,
            ROUND(SUM(c.paid_amount), 2) AS total_payout
        FROM fact_claims c
        JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        WHERE {where_clause} AND c.paid_amount > 0
        GROUP BY d.diagnosis_category
        ORDER BY total_claims DESC
    """
    dx_df = con.execute(dx_query).df()
    if not dx_df.empty:
        fig_dx = px.scatter(
            dx_df, x="total_claims", y="avg_severity",
            size="total_payout", color="avg_severity",
            hover_name="diagnosis_category",
            text="diagnosis_category",
            labels={"total_claims": "Incurred Claim Volume", "avg_severity": "Average Severity (₹)"},
            title="Diagnosis Portfolio Incidence vs Cost (Bubble = Total Payout)",
            color_continuous_scale="Viridis"
        )
        fig_dx.update_traces(textposition="top right")
        st.plotly_chart(fig_dx, use_container_width=True)
    else:
        st.info("No claim records matching filter.")

with col2:
    st.subheader("Claim Cost Distribution (Log vs Linear)")
    cost_query = f"""
        SELECT c.paid_amount
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        WHERE {where_clause} AND c.paid_amount > 0
        LIMIT 10000
    """
    cost_sample = con.execute(cost_query).df()
    if not cost_sample.empty:
        fig_cost = px.histogram(
            cost_sample, x="paid_amount", nbins=50,
            labels={"paid_amount": "Paid Amount in INR (₹)"},
            title="Claim Paid Amount Distribution (Sampled)",
            color_discrete_sequence=["#1f77b4"]
        )
        st.plotly_chart(fig_cost, use_container_width=True)

st.markdown("---")

# Row 2: Settlement TAT by Claim Type & Rejection Reasons Breakdown
col3, col4 = st.columns(2)

with col3:
    st.subheader("Settlement Turnaround Time (TAT) by Claim Type")
    tat_query = f"""
        SELECT
            c.claim_type,
            prv.network_status,
            c.settlement_tat_days
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        JOIN dim_provider prv ON c.provider_id = prv.provider_id
        WHERE {where_clause} AND c.claim_status IN ('Approved', 'Partially Approved', 'Rejected')
        LIMIT 10000
    """
    tat_sample = con.execute(tat_query).df()
    if not tat_sample.empty:
        fig_tat = px.box(
            tat_sample, x="claim_type", y="settlement_tat_days",
            color="network_status",
            labels={"claim_type": "Claim Type", "settlement_tat_days": "TAT (Days)", "network_status": "Network"},
            title="Settlement TAT: Cashless (Fast) vs Reimbursement (Lagged)"
        )
        st.plotly_chart(fig_tat, use_container_width=True)

with col4:
    st.subheader("Claim Repudiation / Rejection Reasons")
    rej_query = f"""
        SELECT
            c.rejection_reason,
            COUNT(c.claim_id) AS rejection_count
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        WHERE {where_clause} AND c.claim_status = 'Rejected'
        GROUP BY c.rejection_reason
        ORDER BY rejection_count DESC
    """
    rej_df = con.execute(rej_query).df()
    if not rej_df.empty:
        fig_rej = px.pie(
            rej_df, names="rejection_reason", values="rejection_count",
            title="Repudiation Reason Distribution",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_rej, use_container_width=True)

st.markdown("---")

# Row 3: Monthly Epidemiological Seasonality Heatmap
st.subheader("📅 Monthly Epidemiological Seasonality Heatmap")
season_query = f"""
    SELECT
        EXTRACT(month FROM c.admission_date) AS month_num,
        d.diagnosis_category,
        COUNT(c.claim_id) AS admission_count
    FROM fact_claims c
    JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
    JOIN dim_policy p ON c.policy_id = p.policy_id
    JOIN dim_member m ON c.member_id = m.member_id
    WHERE {where_clause}
    GROUP BY EXTRACT(month FROM c.admission_date), d.diagnosis_category
    ORDER BY month_num
"""
season_df = con.execute(season_query).df()
con.close()

if not season_df.empty:
    pivot_season = season_df.pivot(index="diagnosis_category", columns="month_num", values="admission_count").fillna(0)
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivot_season.columns = [month_names[int(m)-1] for m in pivot_season.columns]

    fig_heat = px.imshow(
        pivot_season,
        labels=dict(x="Calendar Month", y="Diagnosis Category", color="Hospital Admissions"),
        title="Hospitalization Volume Surges (Monsoon Q3 & Winter Q4 Surges in Respiratory / Infectious)",
        color_continuous_scale="YlOrRd",
        text_auto=True
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with st.expander("ℹ️ Methodology & Insights"):
    st.markdown("""
    - **Cashless Settlement**: Authorized directly between network hospital and insurer with median turnaround under 4 days.
    - **Reimbursement**: Submitted post-discharge by the patient, requiring bills and discharge audit (median TAT ~16 days).
    - **Waiting Period**: Incurred hospitalization within initial 30 days is the leading cause of legitimate claim repudiation.
    """)

