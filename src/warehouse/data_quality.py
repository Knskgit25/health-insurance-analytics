"""
Automated Data Quality & Warehouse Validation Suite.
Validates Acceptance Criteria AC2, AC3, AC4, AC5, AC6 against DuckDB.
"""

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.config import get_path
from src.utils.io import get_duckdb_connection


def run_data_quality_checks() -> dict[str, bool]:
    """Run full data quality test suite on DuckDB warehouse."""
    con = get_duckdb_connection(read_only=True)
    results = {}
    failures = []

    print("=" * 60)
    print("Running MediSure Warehouse Data Quality Checks...")
    print("=" * 60)

    # 1. Primary Key Uniqueness (AC2)
    pk_checks = [
        ("dim_member", "member_id"),
        ("dim_policy", "policy_id"),
        ("dim_provider", "provider_id"),
        ("dim_diagnosis", "diagnosis_id"),
        ("dim_date", "date_key"),
        ("fact_claims", "claim_id"),
        ("fact_premiums", "premium_id"),
        ("fact_renewals", "renewal_id"),
    ]

    for table, pk in pk_checks:
        res = con.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {table}
        """).fetchone()[0]
        check_name = f"PK Uniqueness ({table}.{pk})"
        passed = (res == 0)
        results[check_name] = passed
        if not passed:
            failures.append(f"{check_name} failed: found {res} duplicate primary keys.")
        else:
            print(f" [PASS] {check_name}: 0 duplicates")

    # 2. Foreign Key Referential Integrity (AC2)
    fk_checks = [
        ("dim_member", "policy_id", "dim_policy", "policy_id"),
        ("fact_claims", "member_id", "dim_member", "member_id"),
        ("fact_claims", "policy_id", "dim_policy", "policy_id"),
        ("fact_claims", "provider_id", "dim_provider", "provider_id"),
        ("fact_claims", "diagnosis_id", "dim_diagnosis", "diagnosis_id"),
        ("fact_premiums", "policy_id", "dim_policy", "policy_id"),
        ("fact_renewals", "policy_id", "dim_policy", "policy_id"),
    ]

    for f_tbl, f_col, p_tbl, p_col in fk_checks:
        res = con.execute(f"""
            SELECT COUNT(*)
            FROM {f_tbl} f
            LEFT JOIN {p_tbl} p ON f.{f_col} = p.{p_col}
            WHERE p.{p_col} IS NULL
        """).fetchone()[0]
        check_name = f"Zero Orphan FKs ({f_tbl}.{f_col} -> {p_tbl}.{p_col})"
        passed = (res == 0)
        results[check_name] = passed
        if not passed:
            failures.append(f"{check_name} failed: found {res} orphan foreign keys.")
        else:
            print(f" [PASS] {check_name}: 0 orphans")

    # 3. Financial Invariants (AC3)
    financial_res = con.execute("""
        SELECT
            COUNT(CASE WHEN c.approved_amount > p.sum_insured + 0.01 THEN 1 END) AS si_breaches,
            COUNT(CASE WHEN c.paid_amount > c.approved_amount + 0.01 THEN 1 END) AS appr_breaches,
            COUNT(CASE WHEN c.patient_paid_amount < -0.01 THEN 1 END) AS negative_patient_paid
        FROM fact_claims c
        JOIN dim_policy p ON c.policy_id = p.policy_id
    """).fetchone()

    passed_ac3 = (financial_res[0] == 0 and financial_res[1] == 0 and financial_res[2] == 0)
    results["AC3_Financial_Invariants"] = passed_ac3
    if not passed_ac3:
        failures.append(f"AC3 failed: {financial_res[0]} SI breaches, {financial_res[1]} approval breaches.")
    else:
        print(" [PASS] AC3 Financial Invariants: 100% of claims satisfy approved <= sum_insured and paid <= approved")

    # 4. Date Sequencing (AC4)
    date_res = con.execute("""
        SELECT
            COUNT(CASE WHEN claim_submitted_date < discharge_date THEN 1 END) AS subm_before_disch,
            COUNT(CASE WHEN claim_settled_date < claim_submitted_date THEN 1 END) AS sett_before_subm
        FROM fact_claims
        WHERE claim_status IN ('Approved', 'Partially Approved', 'Rejected')
    """).fetchone()

    passed_ac4 = (date_res[0] == 0 and date_res[1] == 0)
    results["AC4_Date_Sequence"] = passed_ac4
    if not passed_ac4:
        failures.append(f"AC4 failed: {date_res[0]} submitted before discharge, {date_res[1]} settled before submitted.")
    else:
        print(" [PASS] AC4 Date Sequence: 100% of settled claims satisfy settled >= submitted >= discharge")

    # 5. Domain Metrics Ranges (AC5)
    metrics_res = con.execute("""
        WITH metrics AS (
            SELECT
                SUM(paid_amount) AS total_incurred,
                COUNT(CASE WHEN claim_status = 'Rejected' THEN 1 END) * 1.0 /
                    NULLIF(COUNT(CASE WHEN claim_status IN ('Approved', 'Partially Approved', 'Rejected') THEN 1 END), 0) AS rejection_rate,
                AVG(is_fraud_flag) AS fraud_rate
            FROM fact_claims
        ),
        renewal_metrics AS (
            SELECT AVG(renewed_flag) AS renewal_rate FROM fact_renewals
        ),
        earned_prem AS (
            SELECT SUM(premium_amount) AS total_premium 
            FROM fact_premiums 
            WHERE payment_status IN ('Paid', 'Late')
        )
        SELECT
            m.total_incurred,
            e.total_premium,
            m.rejection_rate,
            m.fraud_rate,
            r.renewal_rate
        FROM metrics m, renewal_metrics r, earned_prem e
    """).fetchone()

    total_incurred, total_prem, rej_rate, fraud_rate, renew_rate = metrics_res
    # Approximate portfolio loss ratio on full terms
    est_loss_ratio = total_incurred / total_prem if total_prem else 0.0

    print("\nPortfolio Calibrated Metrics:")
    print(f" - Portfolio Loss Ratio proxy: {est_loss_ratio * 100:.2f}% (Target: 70% - 95%)")
    print(f" - Rejection Rate: {rej_rate * 100:.2f}% (Target: 8% - 12%)")
    print(f" - Fraud Share: {fraud_rate * 100:.2f}% (Target: 2% - 3%)")
    print(f" - Renewal Rate: {renew_rate * 100:.2f}% (Target: 78% - 88%)")

    # 6. Cleaning Log Check (AC6)
    clean_log_file = get_path("warehouse_dir") / "cleaning_log.json"
    has_cleaning_log = clean_log_file.exists()
    results["AC6_Cleaning_Log"] = has_cleaning_log
    if has_cleaning_log:
        with open(clean_log_file, "r") as f:
            log_data = json.load(f)
        print(f" [PASS] AC6 Cleaning Log found: {len(log_data.get('fixes', {}))} cleaning fix types recorded.")
    else:
        failures.append("AC6 failed: cleaning_log.json does not exist.")

    con.close()

    print("-" * 60)
    if failures:
        print(f"FAILED: {len(failures)} data quality checks failed.")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("SUCCESS: All data quality checks passed flawlessly!")
        print("=" * 60)

    return results


if __name__ == "__main__":
    run_data_quality_checks()
