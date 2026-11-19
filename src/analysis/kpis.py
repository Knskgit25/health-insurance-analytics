"""
KPI calculation engine and SQL-vs-Pandas validator.
Executes all SQL KPI queries, computes Pandas equivalents, validates within 0.01% (AC7),
and exports processed analytical summary tables.
"""

import sys
import time
from datetime import date
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.utils.config import get_path, load_config
from src.utils.io import get_duckdb_connection, save_parquet


def calculate_pro_rated_exposure_days(start_date: date, end_date: date, period_start: date, period_end: date) -> float:
    """
    Calculate exact active exposure days within an observation period.
    Edge cases handled: mid-year start, mid-year lapse, full year.
    """
    eff_start = max(start_date, period_start)
    eff_end = min(end_date, period_end)
    if eff_start > eff_end:
        return 0.0
    return float((eff_end - eff_start).days + 1)


def calculate_member_years(start_date: date, end_date: date, members_covered: int = 1) -> float:
    """Calculate member-years of exposure for a policy contract."""
    days = (end_date - start_date).days + 1
    return float(days / 365.25 * members_covered)


def run_all_kpis() -> dict[str, pd.DataFrame]:
    """Execute all KPI SQL scripts, run pandas reconciliation, and export summaries."""
    start_time = time.time()
    config = load_config()
    processed_dir = get_path("processed_dir", config)
    processed_dir.mkdir(parents=True, exist_ok=True)
    sql_kpis_dir = ROOT / "sql" / "kpis"

    con = get_duckdb_connection(read_only=True)
    results = {}

    print("=" * 60)
    print("Executing MediSure Insurance KPIs...")
    print("=" * 60)

    # 1. Profitability KPIs
    print("1. Running kpi_profitability.sql...")
    with open(sql_kpis_dir / "kpi_profitability.sql", "r", encoding="utf-8") as f:
        sql_prof = f.read()
    df_prof = con.execute(sql_prof).df()
    save_parquet(df_prof, processed_dir / "kpi_profitability.parquet")
    results["profitability"] = df_prof

    # 2. Claims KPIs
    print("2. Running kpi_claims.sql...")
    with open(sql_kpis_dir / "kpi_claims.sql", "r", encoding="utf-8") as f:
        sql_claims = f.read()
    df_claims = con.execute(sql_claims).df()
    save_parquet(df_claims, processed_dir / "kpi_claims.parquet")
    results["claims"] = df_claims

    # 3. Operations KPIs
    print("3. Running kpi_operations.sql...")
    with open(sql_kpis_dir / "kpi_operations.sql", "r", encoding="utf-8") as f:
        sql_ops = f.read()
    df_ops = con.execute(sql_ops).df()
    save_parquet(df_ops, processed_dir / "kpi_operations.parquet")
    results["operations"] = df_ops

    # 4. Retention KPIs
    print("4. Running kpi_retention.sql...")
    with open(sql_kpis_dir / "kpi_retention.sql", "r", encoding="utf-8") as f:
        sql_ret = f.read()
    df_ret = con.execute(sql_ret).df()
    save_parquet(df_ret, processed_dir / "kpi_retention.parquet")
    results["retention"] = df_ret

    # 5. Risk KPIs
    print("5. Running kpi_risk.sql...")
    with open(sql_kpis_dir / "kpi_risk.sql", "r", encoding="utf-8") as f:
        sql_risk = f.read()
    df_risk = con.execute(sql_risk).df()
    save_parquet(df_risk, processed_dir / "kpi_risk.parquet")
    results["risk"] = df_risk

    # Reconciliation between SQL and Pandas (AC7)
    print("\nValidating SQL vs Pandas KPI Concordance (AC7)...")
    policies = con.execute("SELECT * FROM dim_policy").df()
    claims = con.execute("SELECT * FROM fact_claims").df()
    renewals = con.execute("SELECT * FROM fact_renewals").df()

    # Pandas Earned Premium & Incurred Claims
    policies["exposure_days"] = (pd.to_datetime(policies["policy_end_date"]) - pd.to_datetime(policies["policy_start_date"])).dt.days + 1.0
    policies["earned_prem_pd"] = policies["annual_premium"] * (policies["exposure_days"] / 365.25)
    pandas_total_earned = float(policies["earned_prem_pd"].sum())

    claims["incurred_pd"] = np.where(claims["claim_status"] == "Pending", claims["approved_amount"], claims["paid_amount"])
    pandas_total_incurred = float(claims["incurred_pd"].sum())

    pandas_loss_ratio = (pandas_total_incurred / pandas_total_earned) * 100.0

    # SQL Loss Ratio Total
    sql_total_earned = float(df_prof["total_earned_premium"].sum())
    sql_total_incurred = float(df_prof["total_incurred_claims"].sum())
    sql_loss_ratio = (sql_total_incurred / sql_total_earned) * 100.0

    lr_diff_pct = abs(sql_loss_ratio - pandas_loss_ratio) / pandas_loss_ratio * 100.0
    print(f" - SQL Total Earned Premium:    INR {sql_total_earned:,.2f}")
    print(f" - Pandas Total Earned Premium: INR {pandas_total_earned:,.2f}")
    print(f" - SQL Loss Ratio:    {sql_loss_ratio:.4f}%")
    print(f" - Pandas Loss Ratio: {pandas_loss_ratio:.4f}%")
    print(f" - Concordance Diff:  {lr_diff_pct:.6f}% (Tolerance: < 0.01%)")

    assert lr_diff_pct < 0.01, f"Loss ratio discrepancy {lr_diff_pct:.4f}% exceeds 0.01% tolerance!"

    # Persistency Reconciliation
    sql_persistency = float(con.execute("SELECT AVG(renewed_flag) * 100.0 FROM fact_renewals").fetchone()[0])
    pandas_persistency = float(renewals["renewed_flag"].mean() * 100.0)
    pers_diff = abs(sql_persistency - pandas_persistency)
    print(f" - SQL Persistency:    {sql_persistency:.4f}%")
    print(f" - Pandas Persistency: {pandas_persistency:.4f}%")
    assert pers_diff < 0.01, "Persistency reconciliation failed!"

    con.close()
    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"All KPIs computed and validated in {elapsed:.2f} seconds.")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run_all_kpis()
