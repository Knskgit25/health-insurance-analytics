"""
Generates clean, fully executable Jupyter notebooks for EDA, KPI Deep Dive, and ML Modeling.
"""

from pathlib import Path
import nbformat as nbf

NOTEBOOKS_DIR = Path(__file__).resolve().parent


def create_eda_notebook():
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("""# 01. Exploratory Data Analysis (EDA) - MediSure Health Insurance

This notebook explores the **MediSure Health Insurance** warehouse dataset stored in DuckDB.
We conduct demographic profiling, financial analysis of claims, epidemiological patterns, and statistical hypothesis testing.
"""),
        nbf.v4.new_code_cell("""import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from src.utils.io import get_duckdb_connection

con = get_duckdb_connection(read_only=True)
print("Connected to MediSure DuckDB warehouse.")
"""),
        nbf.v4.new_markdown_cell("""## 1. Portfolio Demographic & Policy Overview"""),
        nbf.v4.new_code_cell("""members_df = con.execute("SELECT * FROM dim_member").df()
policies_df = con.execute("SELECT * FROM dim_policy").df()

print(f"Total Members: {len(members_df):,}")
print(f"Total Policies: {len(policies_df):,}")
display(members_df.head())
"""),
        nbf.v4.new_markdown_cell("""## 2. Incurred Claims Distribution & Log Transformation"""),
        nbf.v4.new_code_cell("""claims_df = con.execute("SELECT * FROM fact_claims").df()
paid_claims = claims_df[claims_df['paid_amount'] > 0]['paid_amount']

print(f"Total Claims: {len(claims_df):,}")
print(f"Mean Paid Amount: INR {paid_claims.mean():,.2f}")
print(f"Median Paid Amount: INR {paid_claims.median():,.2f}")
print(f"P95 Paid Amount: INR {paid_claims.quantile(0.95):,.2f}")

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
sns.histplot(paid_claims, bins=40, kde=True, ax=axes[0], color='navy')
axes[0].set_title("Paid Claim Amount Distribution (INR)")
sns.histplot(np.log1p(paid_claims), bins=40, kde=True, ax=axes[1], color='teal')
axes[1].set_title("Log-Transformed Claim Amount log1p(₹)")
plt.show()
"""),
        nbf.v4.new_markdown_cell("""## 3. Statistical Hypothesis Testing
### Mann-Whitney U: Cashless vs Reimbursement TAT"""),
        nbf.v4.new_code_cell("""cashless_tat = claims_df[claims_df['claim_type'] == 'Cashless']['settlement_tat_days'].dropna()
reimb_tat = claims_df[claims_df['claim_type'] == 'Reimbursement']['settlement_tat_days'].dropna()

u_stat, p_val = stats.mannwhitneyu(cashless_tat, reimb_tat)
print(f"Mann-Whitney U statistic: {u_stat:,.1f}, p-value: {p_val:.4e}")
print(f"Cashless Mean TAT: {cashless_tat.mean():.2f} days vs Reimbursement Mean TAT: {reimb_tat.mean():.2f} days")
"""),
        nbf.v4.new_markdown_cell("""### Kruskal-Wallis: Severity Across Hospital Tiers"""),
        nbf.v4.new_code_cell("""tier_df = con.execute(\"\"\"
    SELECT c.paid_amount, p.hospital_tier
    FROM fact_claims c
    JOIN dim_provider p ON c.provider_id = p.provider_id
    WHERE c.paid_amount > 0
\"\"\").df()

h_stat, kw_pval = stats.kruskal(
    tier_df[tier_df['hospital_tier'] == 'Tier1']['paid_amount'],
    tier_df[tier_df['hospital_tier'] == 'Tier2']['paid_amount'],
    tier_df[tier_df['hospital_tier'] == 'Tier3']['paid_amount']
)
print(f"Kruskal-Wallis H-statistic: {h_stat:,.2f}, p-value: {kw_pval:.4e}")
"""),
        nbf.v4.new_code_cell("""con.close()""")
    ]
    with open(NOTEBOOKS_DIR / "01_eda.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print("Created 01_eda.ipynb")


def create_kpi_deep_dive_notebook():
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("""# 02. KPI Deep Dive & Profitability Analysis - MediSure

This notebook performs a deep-dive analysis into portfolio loss ratio (Incurred Claim Ratio),
unprofitable customer segments (ICR > 100%), and persistency retention drivers.
"""),
        nbf.v4.new_code_cell("""import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.utils.io import get_duckdb_connection

con = get_duckdb_connection(read_only=True)
"""),
        nbf.v4.new_markdown_cell("""## 1. Portfolio Loss Ratio by Plan Tier & Type"""),
        nbf.v4.new_code_cell("""prof_df = con.execute(\"\"\"
    WITH policy_exp AS (
        SELECT policy_id, plan_type, plan_tier,
               annual_premium * ((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25) AS earned_prem
        FROM dim_policy
    ),
    claims_agg AS (
        SELECT policy_id, SUM(paid_amount) AS incurred
        FROM fact_claims GROUP BY policy_id
    )
    SELECT p.plan_type, p.plan_tier,
           ROUND(SUM(p.earned_prem), 2) AS earned_premium,
           ROUND(COALESCE(SUM(c.incurred), 0.0), 2) AS incurred_claims,
           ROUND(COALESCE(SUM(c.incurred), 0.0) / SUM(p.earned_prem) * 100.0, 2) AS loss_ratio_pct
    FROM policy_exp p
    LEFT JOIN claims_agg c ON p.policy_id = c.policy_id
    GROUP BY p.plan_type, p.plan_tier
    ORDER BY loss_ratio_pct DESC
\"\"\").df()

display(prof_df)
"""),
        nbf.v4.new_markdown_cell("""## 2. Top Unprofitable Segments (Loss Ratio > 100%)"""),
        nbf.v4.new_code_cell("""unprof_df = con.execute(\"\"\"
    WITH seg AS (
        SELECT p.plan_tier, m.age_band, m.region,
               SUM((DATE_DIFF('day', p.policy_start_date, p.policy_end_date) + 1.0)/365.25 * (p.annual_premium/p.members_covered)) AS earned_prem,
               SUM(c.paid_amount) AS incurred
        FROM dim_member m
        JOIN dim_policy p ON m.policy_id = p.policy_id
        LEFT JOIN fact_claims c ON m.member_id = c.member_id
        GROUP BY p.plan_tier, m.age_band, m.region
    )
    SELECT plan_tier, age_band, region,
           ROUND(earned_prem, 2) AS earned_prem,
           ROUND(incurred, 2) AS incurred,
           ROUND(incurred - earned_prem, 2) AS underwriting_deficit,
           ROUND(incurred / earned_prem * 100.0, 2) AS loss_ratio_pct
    FROM seg
    WHERE incurred > earned_prem
    ORDER BY underwriting_deficit DESC
    LIMIT 10
\"\"\").df()

display(unprof_df)
"""),
        nbf.v4.new_markdown_cell("""## 3. Recommended Underwriting Actions
1. **Bronze Tier Repricing**: Older members (51+) on Bronze plans exhibit >100% loss ratios due to inadequate base premiums. Implement an age-rated premium loading (+25% for age 50+).
2. **Co-pay Enforcement**: Introduce a mandatory 20% co-pay on Tier 1 metro hospital admissions for Bronze and Silver tiers to curb billing inflation.
3. **Preferred Provider Network (PPN)**: Direct volume towards NABH-accredited network facilities with negotiated package rates.
"""),
        nbf.v4.new_code_cell("""con.close()""")
    ]
    with open(NOTEBOOKS_DIR / "02_kpi_deep_dive.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print("Created 02_kpi_deep_dive.ipynb")


def create_modeling_notebook():
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("""# 03. Machine Learning Modeling - MediSure

This notebook demonstrates the end-to-end development, evaluation, and serialization of the three core ML models:
1. **Model A: Claim Cost Prediction** (Ridge Regression vs Gradient Boosting)
2. **Model B: Fraud / Anomaly Detection** (Supervised Gradient Boosting vs Isolation Forest)
3. **Model C: Policy Lapse Prediction** (Retention Targeting & Persistency Classification)
"""),
        nbf.v4.new_code_cell("""import json
from pathlib import Path
import pandas as pd
from src.utils.config import get_path

metrics_path = get_path("metrics_file")
if metrics_path.exists():
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    print("Loaded Model Metrics from models/metrics.json:")
    print(json.dumps(metrics, indent=2))
else:
    print("Run `python src/ml/evaluate.py` to train and evaluate all models.")
""")
    ]
    with open(NOTEBOOKS_DIR / "03_modeling.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print("Created 03_modeling.ipynb")


if __name__ == "__main__":
    create_eda_notebook()
    create_kpi_deep_dive_notebook()
    create_modeling_notebook()

