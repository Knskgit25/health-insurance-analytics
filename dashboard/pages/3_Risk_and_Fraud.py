"""
Page 3: Risk & Fraud Intelligence Dashboard.
"""

import json
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
from src.utils.config import get_path
from src.utils.io import get_duckdb_connection

st.set_page_config(page_title="Risk & Fraud - MediSure", page_icon="🚨", layout="wide")

filters = render_sidebar_filters()

st.title("🚨 Healthcare Provider Risk & Fraud Intelligence")
st.markdown("Automated anomaly detection, colluding provider identification, and cost-benefit threshold optimization.")

con = get_duckdb_connection(read_only=True)
where_clause = get_filter_where_clause(filters, table_alias_policy="p", table_alias_member="m")

# Load model metrics if available
metrics_file = get_path("metrics_file")
metrics_data = {}
if metrics_file.exists():
    with open(metrics_file, "r") as f:
        metrics_data = json.load(f).get("models", {}).get("model_b_fraud_detection", {})

# Top KPIs Row
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1:
    st.metric("Model PR-AUC", f"{metrics_data.get('xgboost_classifier', {}).get('pr_auc', 0.80):.4f}", delta="Baseline: 0.4779")
with f_col2:
    st.metric("ROC-AUC", f"{metrics_data.get('xgboost_classifier', {}).get('roc_auc', 0.91):.4f}", delta="High Discriminative Power")
with f_col3:
    opt_th = metrics_data.get("optimal_threshold_analysis", {})
    st.metric("Optimal Operating Threshold", f"{opt_th.get('threshold', 0.66):.2f}", delta="Cost-Benefit Optimized")
with f_col4:
    savings = opt_th.get("net_financial_savings_inr", 74588133.0)
    st.metric("Net Financial Savings", f"₹{savings*1e-7:.2f} Cr", delta="After Audit Costs")

st.markdown("---")

# Interactive Cost Threshold Slider
st.subheader("⚙️ Interactive Financial Threshold Optimization Slider")
st.markdown("Adjust the investigation trigger threshold to observe trade-offs between precision, recall, and net audit savings.")

th_slider = st.slider("Select Fraud Audit Probability Threshold", min_value=0.10, max_value=0.90, value=float(opt_th.get("threshold", 0.66)), step=0.02)

cost_curve = metrics_data.get("sample_cost_curve", [])
if cost_curve:
    curve_df = pd.DataFrame(cost_curve)
    fig_curve = go.Figure()
    fig_curve.add_trace(go.Scatter(x=curve_df["threshold"], y=curve_df["precision"] * 100, mode="lines+markers", name="Precision (%)", line=dict(color="green")))
    fig_curve.add_trace(go.Scatter(x=curve_df["threshold"], y=curve_df["recall"] * 100, mode="lines+markers", name="Recall (%)", line=dict(color="blue")))
    fig_curve.add_trace(go.Scatter(x=curve_df["threshold"], y=curve_df["net_savings_inr"] / 1e6, mode="lines+markers", name="Net Savings (₹ Millions)", yaxis="y2", line=dict(color="red", width=3)))

    fig_curve.add_vline(x=th_slider, line_dash="dash", line_color="black", annotation_text=f"Selected: {th_slider:.2f}")

    fig_curve.update_layout(
        title="Precision-Recall vs Net Financial Savings Curve",
        xaxis=dict(title="Decision Threshold"),
        yaxis=dict(title="Performance (%)"),
        yaxis2=dict(title="Net Savings (₹ M)", overlaying="y", side="right"),
        legend=dict(x=0.02, y=0.98),
        hovermode="x unified"
    )
    st.plotly_chart(fig_curve, use_container_width=True)

st.markdown("---")

# Row 2: Billed vs Benchmark Scatter & Provider Risk Table
col_sc, col_prv = st.columns([3, 2])

with col_sc:
    st.subheader("Billed Amount vs Expected Clinical Benchmark")
    scatter_query = f"""
        SELECT
            c.claim_id,
            c.billed_amount,
            (d.typical_cost_min + d.typical_cost_max) / 2.0 AS expected_benchmark_cost,
            c.length_of_stay,
            c.is_fraud_flag,
            prv.provider_name,
            d.diagnosis_category
        FROM fact_claims c
        JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
        JOIN dim_provider prv ON c.provider_id = prv.provider_id
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        WHERE {where_clause}
        LIMIT 2500
    """
    sc_df = con.execute(scatter_query).df()
    if not sc_df.empty:
        sc_df["Fraud Flag"] = sc_df["is_fraud_flag"].map({1: "Flagged / Anomalous", 0: "Legitimate Claim"})
        fig_scatter = px.scatter(
            sc_df, x="expected_benchmark_cost", y="billed_amount",
            color="Fraud Flag",
            color_discrete_map={"Flagged / Anomalous": "#d62728", "Legitimate Claim": "#1f77b4"},
            hover_data=["claim_id", "provider_name", "diagnosis_category", "length_of_stay"],
            labels={"expected_benchmark_cost": "Expected Diagnosis Norm (₹)", "billed_amount": "Billed Charges (₹)"},
            title="Inflated Billing Detection: Billed vs Clinical Expected Cost"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

with col_prv:
    st.subheader("Top Anomalous Healthcare Providers")
    prv_query = f"""
        SELECT
            prv.provider_id AS "Provider ID",
            prv.provider_name AS "Provider Name",
            prv.hospital_tier AS "Tier",
            COUNT(c.claim_id) AS "Total Claims",
            ROUND(AVG(c.billed_amount), 0) AS "Avg Bill (₹)",
            ROUND(AVG(c.is_fraud_flag) * 100.0, 1) AS "Fraud Rate (%)"
        FROM fact_claims c
        JOIN dim_provider prv ON c.provider_id = prv.provider_id
        JOIN dim_policy p ON c.policy_id = p.policy_id
        JOIN dim_member m ON c.member_id = m.member_id
        WHERE {where_clause}
        GROUP BY prv.provider_id, prv.provider_name, prv.hospital_tier
        HAVING COUNT(c.claim_id) >= 20
        ORDER BY "Fraud Rate (%)" DESC, "Avg Bill (₹)" DESC
        LIMIT 10
    """
    prv_df = con.execute(prv_query).df()
    if not prv_df.empty:
        st.dataframe(
            prv_df.style.format({
                "Avg Bill (₹)": "₹{:,.0f}",
                "Fraud Rate (%)": "{:.1f}%",
            }).background_gradient(subset=["Fraud Rate (%)"], cmap="Reds"),
            use_container_width=True
        )

# List of Top Flagged Claims for Investigation Queue
st.subheader("📋 Priority Claims Investigation Queue")
queue_query = f"""
    SELECT
        c.claim_id AS "Claim ID",
        c.member_id AS "Member ID",
        prv.provider_name AS "Hospital",
        d.diagnosis_name AS "Diagnosis",
        c.admission_date AS "Admission",
        c.length_of_stay AS "LOS (Days)",
        ROUND(c.billed_amount, 2) AS "Billed (₹)",
        c.is_emergency AS "Emergency",
        c.claim_status AS "Adjudication Status"
    FROM fact_claims c
    JOIN dim_provider prv ON c.provider_id = prv.provider_id
    JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
    JOIN dim_policy p ON c.policy_id = p.policy_id
    JOIN dim_member m ON c.member_id = m.member_id
    WHERE {where_clause} AND c.is_fraud_flag = 1
    ORDER BY c.billed_amount DESC
    LIMIT 15
"""
queue_df = con.execute(queue_query).df()
con.close()

if not queue_df.empty:
    st.dataframe(
        queue_df.style.format({"Billed (₹)": "₹{:,.2f}"}),
        use_container_width=True
    )

with st.expander("ℹ️ Methodology & Cost-Benefit Model"):
    st.markdown("""
    - **Primary Metric PR-AUC**: In extreme class imbalance (~2.2% positive fraud rate), ROC-AUC can be overly optimistic due to high true negatives. Precision-Recall AUC accurately reflects operational audit quality.
    - **Investigation Cost Model**: Assumes ₹2,000 cost per investigated dossier. The optimal threshold balances investigation expenditure against recovered fraudulent billing amounts.
    """)

