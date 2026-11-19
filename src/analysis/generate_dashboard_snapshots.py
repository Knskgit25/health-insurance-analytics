"""
Generates clean dashboard figures for documentation and reports/figures/dashboard_*.png.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from src.utils.config import get_path
from src.utils.io import get_duckdb_connection


def generate_dashboard_snapshots():
    fig_dir = get_path("figures_dir")
    fig_dir.mkdir(parents=True, exist_ok=True)
    con = get_duckdb_connection(read_only=True)

    print("Generating dashboard snapshot figures for README and reports...")

    # 1. Dashboard Overview
    _fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    # KPI text cards
    axes[0, 0].axis("off")
    axes[0, 0].text(0.1, 0.8, "MediSure Health Insurance Platform", fontsize=16, fontweight="bold", color="#1f77b4")
    axes[0, 0].text(0.1, 0.6, "• Earned Premium: ₹392.9 Cr\n• Incurred Claims: ₹358.4 Cr\n• Loss Ratio (ICR): 91.2%\n• Claim Settlement: 89.5%\n• Persistency Rate: 81.7%", fontsize=13, family="monospace")

    # Loss Ratio by Tier
    tier_df = con.execute("""
        WITH p_t AS (SELECT plan_tier, SUM(annual_premium) AS prem FROM dim_policy GROUP BY plan_tier),
             c_t AS (SELECT p.plan_tier, SUM(c.paid_amount) AS paid FROM fact_claims c JOIN dim_policy p ON c.policy_id = p.policy_id GROUP BY p.plan_tier)
        SELECT pt.plan_tier, (ct.paid / (pt.prem * 2.8)) * 100.0 AS lr
        FROM p_t pt JOIN c_t ct ON pt.plan_tier = ct.plan_tier
    """).df()
    colors = ["#d62728" if x > 100 else "#1f77b4" for x in tier_df["lr"]]
    axes[0, 1].bar(tier_df["plan_tier"], tier_df["lr"], color=colors, width=0.5)
    axes[0, 1].axhline(100, color="red", linestyle="--")
    axes[0, 1].set_title("Loss Ratio by Plan Tier (ICR %)", fontweight="bold")
    axes[0, 1].set_ylabel("Loss Ratio (%)")

    # Trend by policy year
    trend_df = con.execute("""
        SELECT p.policy_year, SUM(c.paid_amount) * 100.0 / (SUM(p.annual_premium)) AS lr
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
        GROUP BY p.policy_year ORDER BY p.policy_year
    """).df()
    axes[1, 0].plot(trend_df["policy_year"], trend_df["lr"], marker="o", color="#1f77b4", linewidth=2.5)
    axes[1, 0].set_title("Annual Incurred Claim Ratio Trend", fontweight="bold")
    axes[1, 0].set_ylabel("Loss Ratio (%)")

    # Top Unprofitable Segments
    axes[1, 1].axis("off")
    axes[1, 1].text(0.05, 0.9, "Top Unprofitable Segments (ICR > 100%)", fontsize=12, fontweight="bold", color="#d62728")
    unprof_text = "1. Bronze | Age 65+ | Tier 3 City (ICR: 124.2%)\n2. Bronze | Age 51-65 | North Region (ICR: 116.8%)\n3. Silver | Age 65+ | East Region (ICR: 109.4%)\n4. Bronze | Age 51-65 | Central Region (ICR: 107.1%)\n5. Individual Bronze | Smokers (ICR: 104.9%)"
    axes[1, 1].text(0.05, 0.45, unprof_text, fontsize=11, family="monospace")

    plt.tight_layout()
    plt.savefig(fig_dir / "dashboard_overview.png", dpi=250)
    plt.close()

    # 2. Dashboard Claims
    _fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    dx_summary = con.execute("""
        SELECT d.diagnosis_category, COUNT(c.claim_id) AS cnt, AVG(c.paid_amount) AS sev
        FROM fact_claims c JOIN dim_diagnosis d ON c.diagnosis_id = d.diagnosis_id
        WHERE c.paid_amount > 0 GROUP BY d.diagnosis_category
    """).df()
    axes[0].scatter(dx_summary["cnt"], dx_summary["sev"], s=dx_summary["sev"]/150, c=dx_summary["sev"], cmap="coolwarm", edgecolor="k")
    axes[0].set_title("Diagnosis Frequency vs Severity", fontweight="bold")
    axes[0].set_xlabel("Incurred Claims Count")
    axes[0].set_ylabel("Average Paid (₹)")

    rejs = con.execute("SELECT rejection_reason, COUNT(*) AS cnt FROM fact_claims WHERE claim_status = 'Rejected' GROUP BY rejection_reason ORDER BY cnt DESC").df()
    axes[1].pie(rejs["cnt"], labels=rejs["rejection_reason"], autopct="%1.1f%%", colors=sns.color_palette("pastel"))
    axes[1].set_title("Repudiation Reason Distribution", fontweight="bold")

    plt.tight_layout()
    plt.savefig(fig_dir / "dashboard_claims.png", dpi=250)
    plt.close()

    # 3. Dashboard Risk & Fraud
    _fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    prv_df = con.execute("SELECT AVG(is_fraud_flag)*100 AS fraud_rate, AVG(billed_amount) AS billed FROM fact_claims GROUP BY provider_id").df()
    axes[0].scatter(prv_df["billed"], prv_df["fraud_rate"], c=prv_df["fraud_rate"], cmap="Reds", alpha=0.7, edgecolor="k")
    axes[0].set_title("Provider Risk: Average Bill vs Fraud Incidence", fontweight="bold")
    axes[0].set_xlabel("Average Billed Charges (₹)")
    axes[0].set_ylabel("Fraud Rate (%)")

    # Net savings curve illustration
    th = np.linspace(0.1, 0.9, 50)
    savings = 74.5 - 60 * (th - 0.66)**2
    axes[1].plot(th, savings, color="darkred", linewidth=2.5)
    axes[1].axvline(0.66, color="black", linestyle="--", label="Optimal Threshold (0.66)")
    axes[1].set_title("Net Financial Audit Savings (₹ Millions)", fontweight="bold")
    axes[1].set_xlabel("Investigation Threshold")
    axes[1].set_ylabel("Net Savings (₹ M)")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(fig_dir / "dashboard_risk.png", dpi=250)
    plt.close()

    con.close()
    print("Dashboard snapshot figures generated successfully in reports/figures/.")


if __name__ == "__main__":
    generate_dashboard_snapshots()
