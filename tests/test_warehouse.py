"""
Integration and data quality tests for the DuckDB warehouse layer.
Validates AC2, AC3, AC4, AC5, AC6.
"""

import json

import pytest

from src.utils.config import get_path
from src.utils.io import get_duckdb_connection


@pytest.fixture(scope="module")
def duckdb_con():
    """Yield read-only connection to populated warehouse DuckDB instance."""
    con = get_duckdb_connection(read_only=True)
    yield con
    con.close()


def test_primary_key_uniqueness(duckdb_con):
    """AC2: Zero duplicate primary keys across all dimension and fact tables."""
    tables_pks = [
        ("dim_member", "member_id"),
        ("dim_policy", "policy_id"),
        ("dim_provider", "provider_id"),
        ("dim_diagnosis", "diagnosis_id"),
        ("dim_date", "date_key"),
        ("fact_claims", "claim_id"),
        ("fact_premiums", "premium_id"),
        ("fact_renewals", "renewal_id"),
    ]
    for table, pk in tables_pks:
        dup_count = duckdb_con.execute(
            f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {table}"
        ).fetchone()[0]
        assert dup_count == 0, f"Table {table} has {dup_count} duplicate {pk} primary keys."


def test_referential_integrity(duckdb_con):
    """AC2: Zero orphan foreign keys in the warehouse."""
    foreign_keys = [
        ("dim_member", "policy_id", "dim_policy", "policy_id"),
        ("fact_claims", "member_id", "dim_member", "member_id"),
        ("fact_claims", "policy_id", "dim_policy", "policy_id"),
        ("fact_claims", "provider_id", "dim_provider", "provider_id"),
        ("fact_claims", "diagnosis_id", "dim_diagnosis", "diagnosis_id"),
        ("fact_premiums", "policy_id", "dim_policy", "policy_id"),
        ("fact_renewals", "policy_id", "dim_policy", "policy_id"),
    ]
    for f_tbl, f_col, p_tbl, p_col in foreign_keys:
        orphans = duckdb_con.execute(f"""
            SELECT COUNT(*)
            FROM {f_tbl} f
            LEFT JOIN {p_tbl} p ON f.{f_col} = p.{p_col}
            WHERE p.{p_col} IS NULL
        """).fetchone()[0]
        assert orphans == 0, f"Found {orphans} orphan records in {f_tbl}.{f_col} referencing {p_tbl}.{p_col}"


def test_financial_waterfall_invariants(duckdb_con):
    """AC3: approved_amount <= sum_insured and paid_amount <= approved_amount for 100% of claims."""
    breaches = duckdb_con.execute("""
        SELECT
            COUNT(CASE WHEN c.approved_amount > p.sum_insured + 0.01 THEN 1 END),
            COUNT(CASE WHEN c.paid_amount > c.approved_amount + 0.01 THEN 1 END),
            COUNT(CASE WHEN c.patient_paid_amount < -0.01 THEN 1 END)
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
    """).fetchone()

    assert breaches[0] == 0, f"{breaches[0]} claims violated sum_insured cap"
    assert breaches[1] == 0, f"{breaches[1]} claims violated approved_amount cap"
    assert breaches[2] == 0, f"{breaches[2]} claims had negative patient_paid_amount"


def test_settlement_date_sequencing(duckdb_con):
    """AC4: claim_settled_date >= claim_submitted_date >= discharge_date for all settled claims."""
    date_violations = duckdb_con.execute("""
        SELECT
            COUNT(CASE WHEN claim_submitted_date < discharge_date THEN 1 END),
            COUNT(CASE WHEN claim_settled_date < claim_submitted_date THEN 1 END)
        FROM fact_claims
        WHERE claim_status IN ('Approved', 'Partially Approved', 'Rejected')
    """).fetchone()

    assert date_violations[0] == 0, f"{date_violations[0]} claims submitted before discharge"
    assert date_violations[1] == 0, f"{date_violations[1]} claims settled before submission"


def test_portfolio_benchmarks(duckdb_con):
    """AC5: Calibrated loss ratio (70-95%), rejection rate (8-12%), fraud share (2-3%), renewal rate (78-88%)."""
    res = duckdb_con.execute("""
        WITH claims_agg AS (
            SELECT
                SUM(paid_amount) AS total_paid,
                COUNT(CASE WHEN claim_status = 'Rejected' THEN 1 END) * 1.0 /
                    NULLIF(COUNT(CASE WHEN claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END), 0) AS rej_rate,
                AVG(is_fraud_flag) AS fraud_rate
            FROM fact_claims
        ),
        prem_agg AS (
            SELECT SUM(premium_amount) AS total_prem FROM fact_premiums WHERE payment_status IN ('Paid', 'Late')
        ),
        renewal_agg AS (
            SELECT AVG(renewed_flag) AS renewal_rate FROM fact_renewals
        )
        SELECT
            c.total_paid / p.total_prem AS loss_ratio,
            c.rej_rate,
            c.fraud_rate,
            r.renewal_rate
        FROM claims_agg c, prem_agg p, renewal_agg r
    """).fetchone()

    loss_ratio, rej_rate, fraud_rate, renewal_rate = res

    assert 0.70 <= loss_ratio <= 0.95, f"Loss ratio {loss_ratio:.3f} outside [0.70, 0.95]"
    assert 0.08 <= rej_rate <= 0.12, f"Rejection rate {rej_rate:.3f} outside [0.08, 0.12]"
    assert 0.02 <= fraud_rate <= 0.03, f"Fraud share {fraud_rate:.3f} outside [0.02, 0.03]"
    assert 0.78 <= renewal_rate <= 0.88, f"Renewal rate {renewal_rate:.3f} outside [0.78, 0.88]"


def test_cleaning_log_exists_and_accurate():
    """AC6: Cleaning log exists and records all cleaning operations."""
    log_path = get_path("warehouse_dir") / "cleaning_log.json"
    assert log_path.exists(), "cleaning_log.json does not exist"
    with open(log_path, "r", encoding="utf-8") as f:
        log = json.load(f)
    fixes = log.get("fixes", {})
    assert "member_bmi_nulls_imputed_count" in fixes
    assert "member_income_nulls_imputed_count" in fixes
    assert "claims_duplicates_dropped" in fixes
    assert fixes["claims_duplicates_dropped"] > 0
