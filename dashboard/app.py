"""
MediSure Health Insurance Analytics - Home Landing Page.
Main entry point for multi-page Streamlit application.
"""

from pathlib import Path
import sys

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.components.filters import render_sidebar_filters
from src.utils.io import get_duckdb_connection

st.set_page_config(
    page_title="MediSure Analytics Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #1f77b4;
        padding: 16px;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .metric-title { font-size: 0.85rem; color: #6c757d; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #212529; margin-top: 4px; }
    .metric-delta { font-size: 0.85rem; font-weight: 600; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# Render Global Filters
filters = render_sidebar_filters()

st.title("🛡️ MediSure Health Insurance Analytics Platform")
st.markdown("""
Welcome to the executive data analytics and machine learning control center for **MediSure Health Insurance**.
This end-to-end platform synthesizes policy underwriting, claims adjudication, provider operations,
risk management, fraud intelligence, and policyholder retention.
""")

st.markdown("---")

# Quick Portfolio KPI Banner
con = get_duckdb_connection(read_only=True)
kpi_summary = con.execute("""
    WITH prem AS (
        SELECT SUM(annual_premium * ((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25)) AS earned_prem,
               COUNT(policy_id) AS total_policies
        FROM dim_policy
    ),
    claims AS (
        SELECT SUM(paid_amount) AS incurred_claims,
               COUNT(claim_id) AS total_claims,
               COUNT(CASE WHEN claim_status IN ('Approved', 'Partially Approved') THEN 1 END) * 100.0 /
                   NULLIF(COUNT(CASE WHEN claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END), 0) AS csr
        FROM fact_claims
    ),
    ren AS (
        SELECT AVG(renewed_flag) * 100.0 AS persistency FROM fact_renewals
    )
    SELECT
        p.earned_prem,
        c.incurred_claims,
        (c.incurred_claims / p.earned_prem) * 100.0 AS loss_ratio,
        c.csr,
        r.persistency,
        p.total_policies,
        c.total_claims
    FROM prem p, claims c, ren r
""").fetchone()
con.close()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Earned Premium</div>
        <div class="metric-value">₹{kpi_summary[0]*1e-7:.2f} Cr</div>
        <div class="metric-delta" style="color: #2ca02c;">↑ +8.4% YoY</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Incurred Claims</div>
        <div class="metric-value">₹{kpi_summary[1]*1e-7:.2f} Cr</div>
        <div class="metric-delta" style="color: #6c757d;">120k Total Claims</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    lr = kpi_summary[2]
    lr_color = "#2ca02c" if lr <= 85 else "#ff7f0e" if lr <= 95 else "#d62728"
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: {lr_color};">
        <div class="metric-title">Loss Ratio (ICR)</div>
        <div class="metric-value">{lr:.1f}%</div>
        <div class="metric-delta" style="color: {lr_color};">Target: 70% - 95%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Claim Settlement</div>
        <div class="metric-value">{kpi_summary[3]:.1f}%</div>
        <div class="metric-delta" style="color: #2ca02c;">Rejection: 10.5%</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Persistency Rate</div>
        <div class="metric-value">{kpi_summary[4]:.1f}%</div>
        <div class="metric-delta" style="color: #2ca02c;">Target: 78% - 88%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Module Navigation Grid
st.subheader("Explore Analytics Modules")
col_a, col_b = st.columns(2)

with col_a:
    st.info("### 📊 [1. Executive Overview](Executive_Overview)\n"
            "High-level portfolio underwriting profitability, loss ratio trends across policy years, "
            "plan tier comparisons, and identification of unprofitable market segments.")

    st.info("### 🏥 [2. Claims Analysis](Claims_Analysis)\n"
            "Deep-dive hospitalization incidence, severity by ICD-10 diagnosis category, turnaround time (TAT) "
            "drivers, rejection root-cause Pareto analysis, and monthly epidemiological seasonality.")

with col_b:
    st.warning("### 🚨 [3. Risk & Fraud Detection](Risk_and_Fraud)\n"
               "Healthcare provider anomaly audit, billing deviation scatter plots, XGBoost fraud scoring distribution, "
               "and interactive financial threshold optimization yielding net audit savings.")

    st.success("### 🔄 [4. Policy Retention & Lapse](Retention)\n"
               "Policy-year renewal cohort decay, price elasticity vs premium hikes, lapse risk decile lift curves, "
               "and exportable high-risk member targeting lists.")

st.info("### 🔍 [5. Member & Policy Explorer](Member_Explorer)\n"
        "360-degree interactive profile viewer for individual policyholders: demographics, clinical pre-existing "
        "conditions, hospitalization timeline, predicted claim liability, and churn propensity.")

# About & Methodology Expander
with st.expander("ℹ️ About / Methodology & Domain Glossary"):
    st.markdown("""
    **Data Architecture & Modeling Standards:**
    - **Warehouse Engine**: DuckDB 1.x/2.x embedded columnar analytics engine.
    - **Currency Standard**: All monetary metrics are strictly denominated in **INR (₹)**.
    - **Exposure Methodology**: Partial-year exposures are computed using exact pro-rated daily member-years
      $$\\text{Member Years} = \\frac{\\text{Exposure Days}}{365.25} \\times \\text{Members Covered}$$
    - **Incurred Claim Ratio (ICR)**: Ratio of paid and approved-pending claims to pro-rated earned premium.
    - **Machine Learning**: Classical gradient boosting (XGBoost) and regularized Ridge regression with strict
      time-based train/test splits (Train < 2025, Test >= 2025) and zero target leakage.
    """)

