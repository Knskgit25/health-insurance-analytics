"""
Unit tests for KPIs, SQL queries, and pro-rated exposure calculations.
Validates Acceptance Criteria AC7, AC8, and AC9.
"""

from datetime import date

import numpy as np
import pandas as pd

from src.analysis.kpis import calculate_member_years, calculate_pro_rated_exposure_days
from src.utils.config import ROOT_DIR
from src.utils.io import get_duckdb_connection


def test_pro_rated_exposure_edge_cases():
    """AC8: Test pro-rated exposure calculation with at least three distinct edge cases."""
    period_start = date(2023, 1, 1)
    period_end = date(2023, 12, 31)

    # Edge Case 1: Full Year Policy (2023-01-01 to 2023-12-31)
    days_full = calculate_pro_rated_exposure_days(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        period_start=period_start,
        period_end=period_end
    )
    assert days_full == 365.0, f"Full year days expected 365, got {days_full}"
    my_full = calculate_member_years(date(2023, 1, 1), date(2023, 12, 31), members_covered=1)
    assert abs(my_full - (365.0 / 365.25)) < 1e-4

    # Edge Case 2: Mid-Year Start Policy (Starts 2023-07-01 to 2024-06-30)
    # Inside 2023 period: July 1 to Dec 31 = 184 days
    days_mid_start = calculate_pro_rated_exposure_days(
        start_date=date(2023, 7, 1),
        end_date=date(2024, 6, 30),
        period_start=period_start,
        period_end=period_end
    )
    assert days_mid_start == 184.0, f"Mid-year start days expected 184, got {days_mid_start}"

    # Edge Case 3: Mid-Year Lapse (Starts 2023-01-01, lapses on 2023-04-30)
    # Inside 2023 period: Jan 1 to April 30 = 120 days
    days_mid_lapse = calculate_pro_rated_exposure_days(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 4, 30),
        period_start=period_start,
        period_end=period_end
    )
    assert days_mid_lapse == 120.0, f"Mid-year lapse days expected 120, got {days_mid_lapse}"

    # Edge Case 4: Policy entirely outside period
    days_outside = calculate_pro_rated_exposure_days(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        period_start=period_start,
        period_end=period_end
    )
    assert days_outside == 0.0


def test_sql_vs_pandas_kpi_concordance():
    """AC7: All KPIs in Section 8 match a pandas re-computation within a tolerance of 0.01%."""
    con = get_duckdb_connection(read_only=True)

    policies = con.execute("SELECT * FROM dim_policy").df()
    claims = con.execute("SELECT * FROM fact_claims").df()
    renewals = con.execute("SELECT * FROM fact_renewals").df()

    # Incurred Claims
    sql_incurred = float(con.execute("""
        SELECT SUM(paid_amount + CASE WHEN claim_status = 'Pending' THEN approved_amount ELSE 0.0 END)
        FROM fact_claims
    """).fetchone()[0])
    claims["incurred"] = np.where(claims["claim_status"] == "Pending", claims["approved_amount"], claims["paid_amount"])
    pandas_incurred = float(claims["incurred"].sum())
    assert abs(sql_incurred - pandas_incurred) / pandas_incurred < 0.0001, "Incurred claims tolerance exceeded"

    # Earned Premium
    sql_earned = float(con.execute("""
        SELECT SUM(annual_premium * ((DATE_DIFF('day', policy_start_date, policy_end_date) + 1.0) / 365.25))
        FROM dim_policy
    """).fetchone()[0])
    policies["exposure_days"] = (pd.to_datetime(policies["policy_end_date"]) - pd.to_datetime(policies["policy_start_date"])).dt.days + 1.0
    pandas_earned = float((policies["annual_premium"] * (policies["exposure_days"] / 365.25)).sum())
    assert abs(sql_earned - pandas_earned) / pandas_earned < 0.0001, "Earned premium tolerance exceeded"

    # Loss Ratio
    sql_loss_ratio = (sql_incurred / sql_earned) * 100.0
    pandas_loss_ratio = (pandas_incurred / pandas_earned) * 100.0
    assert abs(sql_loss_ratio - pandas_loss_ratio) / pandas_loss_ratio < 0.0001, "Loss ratio tolerance exceeded"

    # Settlement TAT
    sql_tat = float(con.execute("""
        SELECT AVG(settlement_tat_days)
        FROM fact_claims
        WHERE claim_status IN ('Approved', 'Partially Approved', 'Rejected')
    """).fetchone()[0])
    settled_claims = claims[claims["claim_status"].isin(["Approved", "Partially Approved", "Rejected"])]
    pandas_tat = float(settled_claims["settlement_tat_days"].mean())
    assert abs(sql_tat - pandas_tat) / pandas_tat < 0.0001, "Settlement TAT tolerance exceeded"

    # Persistency
    sql_persistency = float(con.execute("SELECT AVG(renewed_flag) FROM fact_renewals").fetchone()[0])
    pandas_persistency = float(renewals["renewed_flag"].mean())
    assert abs(sql_persistency - pandas_persistency) < 0.0001, "Persistency tolerance exceeded"

    con.close()


def test_analysis_queries_execution_and_headers():
    """AC9: At least 15 SQL analysis queries run without error and each has a header comment stating the business question."""
    con = get_duckdb_connection(read_only=True)
    sql_analysis_dir = ROOT_DIR / "sql" / "analysis"
    query_files = list(sql_analysis_dir.glob("*.sql"))

    assert len(query_files) >= 15, f"Expected at least 15 analysis queries, found {len(query_files)}"

    for sql_file in query_files:
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for header comment with Business Question
        assert "-- Business Question:" in content or "-- BQ" in content, (
            f"Query file {sql_file.name} lacks required Business Question header comment."
        )

        # Execute query against DuckDB
        df = con.execute(content).df()
        assert df is not None, f"Query {sql_file.name} returned None"
        assert len(df) > 0, f"Query {sql_file.name} returned empty result"

    con.close()
