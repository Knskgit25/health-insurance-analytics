"""
Warehouse Ingestion & Data Cleaning Pipeline.
Ingests raw CSV data, performs data quality cleaning, logs fixes,
and populates the DuckDB warehouse according to sql/schema.sql.
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.data_generation.generate_providers import INDIAN_CITIES_MASTER
from src.utils.config import get_path, load_config
from src.utils.io import get_duckdb_connection, read_csv


def build_warehouse() -> dict:
    """Build and populate the DuckDB warehouse from raw CSVs."""
    start_time = time.time()
    config = load_config()
    raw_dir = get_path("raw_dir", config)
    warehouse_dir = get_path("warehouse_dir", config)
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    db_file = get_path("duckdb_file", config)

    # Remove existing database file if present to guarantee a fresh rebuild
    if db_file.exists():
        try:
            db_file.unlink()
        except OSError:
            pass

    cleaning_log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fixes": {}
    }

    print("=" * 60)
    print("Building MediSure DuckDB Warehouse...")
    print("=" * 60)

    # 1. Initialize schema in DuckDB
    schema_sql_path = ROOT / "sql" / "schema.sql"
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    con = get_duckdb_connection()
    con.execute(schema_sql)
    print("1. Applied DDL schema and indexes to DuckDB.")

    # Canonical city lookup
    canonical_cities = {c[0].lower(): c[0] for c in INDIAN_CITIES_MASTER}

    # 2. Clean and load dim_date
    print("2. Ingesting dim_date...")
    dates_df = read_csv(raw_dir / "dates.csv")
    dates_df["date_key"] = pd.to_datetime(dates_df["date_key"]).dt.date
    dates_df["date"] = pd.to_datetime(dates_df["date"]).dt.date
    con.register("tmp_dates", dates_df)
    con.execute("INSERT OR REPLACE INTO dim_date SELECT * FROM tmp_dates")
    con.unregister("tmp_dates")

    # 3. Clean and load dim_provider
    print("3. Ingesting dim_provider...")
    providers_df = read_csv(raw_dir / "providers.csv")
    # Drop internal helper columns if present
    if "is_fraud_prone" in providers_df.columns:
        providers_clean = providers_df.drop(columns=["is_fraud_prone"]).copy()
    else:
        providers_clean = providers_df.copy()
    providers_clean["accreditation"] = providers_clean["accreditation"].fillna("None")
    con.register("tmp_providers", providers_clean)
    con.execute("INSERT OR REPLACE INTO dim_provider SELECT * FROM tmp_providers")
    con.unregister("tmp_providers")

    # 4. Clean and load dim_diagnosis
    print("4. Ingesting dim_diagnosis...")
    diagnoses_df = read_csv(raw_dir / "diagnoses.csv")
    con.register("tmp_diagnoses", diagnoses_df)
    con.execute("INSERT OR REPLACE INTO dim_diagnosis SELECT * FROM tmp_diagnoses")
    con.unregister("tmp_diagnoses")

    # 5. Clean and load dim_policy
    print("5. Ingesting dim_policy...")
    policies_df = read_csv(raw_dir / "policies.csv")
    policies_df["policy_start_date"] = pd.to_datetime(policies_df["policy_start_date"]).dt.date
    policies_df["policy_end_date"] = pd.to_datetime(policies_df["policy_end_date"]).dt.date
    policies_df["lapse_date"] = pd.to_datetime(policies_df["lapse_date"]).dt.date
    con.register("tmp_policies", policies_df)
    con.execute("INSERT OR REPLACE INTO dim_policy SELECT * FROM tmp_policies")
    con.unregister("tmp_policies")

    # 6. Clean and load dim_member (Rule 14 cleaning)
    print("6. Cleaning and ingesting dim_member...")
    members_df = read_csv(raw_dir / "members.csv")

    # Log & clean city casing/whitespace
    city_raw = members_df["city"].astype(str)
    city_stripped = city_raw.str.strip()
    city_canonical = city_stripped.str.lower().map(canonical_cities).fillna(city_stripped)
    city_fixed_count = int((city_raw != city_canonical).sum())
    members_df["city"] = city_canonical
    cleaning_log["fixes"]["member_city_standardization_count"] = city_fixed_count

    # Log & impute missing BMI
    null_bmi_count = int(members_df["bmi"].isna().sum())
    median_bmi = float(members_df["bmi"].median())
    members_df["bmi"] = members_df["bmi"].fillna(round(median_bmi, 1))
    cleaning_log["fixes"]["member_bmi_nulls_imputed_count"] = null_bmi_count

    # Log & impute missing income_band
    null_inc_count = int(members_df["income_band"].isna().sum())
    mode_inc = members_df["income_band"].mode()[0] if not members_df["income_band"].dropna().empty else "3L-7L"
    members_df["income_band"] = members_df["income_band"].fillna(mode_inc)
    cleaning_log["fixes"]["member_income_nulls_imputed_count"] = null_inc_count

    # Deduplicate member_id if any
    init_mem_count = len(members_df)
    members_df = members_df.drop_duplicates(subset=["member_id"])
    mem_dups_dropped = init_mem_count - len(members_df)
    cleaning_log["fixes"]["member_duplicates_dropped"] = mem_dups_dropped

    members_df["date_of_birth"] = pd.to_datetime(members_df["date_of_birth"]).dt.date
    members_df["enrollment_date"] = pd.to_datetime(members_df["enrollment_date"]).dt.date

    con.register("tmp_members", members_df)
    con.execute("INSERT OR REPLACE INTO dim_member SELECT * FROM tmp_members")
    con.unregister("tmp_members")

    # 7. Clean and load fact_claims (Rule 14 deduplication & cleaning)
    print("7. Cleaning and ingesting fact_claims...")
    claims_df = read_csv(raw_dir / "claims.csv")
    init_claims_count = len(claims_df)
    claims_clean = claims_df.drop_duplicates(subset=["claim_id"]).copy()
    claims_dups_dropped = init_claims_count - len(claims_clean)
    cleaning_log["fixes"]["claims_duplicates_dropped"] = claims_dups_dropped

    # Date parsing
    claims_clean["admission_date"] = pd.to_datetime(claims_clean["admission_date"]).dt.date
    claims_clean["discharge_date"] = pd.to_datetime(claims_clean["discharge_date"]).dt.date
    claims_clean["claim_submitted_date"] = pd.to_datetime(claims_clean["claim_submitted_date"]).dt.date
    claims_clean["claim_settled_date"] = pd.to_datetime(claims_clean["claim_settled_date"]).dt.date

    con.register("tmp_claims", claims_clean)
    con.execute("INSERT OR REPLACE INTO fact_claims SELECT * FROM tmp_claims")
    con.unregister("tmp_claims")

    # 8. Clean and load fact_premiums
    print("8. Ingesting fact_premiums...")
    premiums_df = read_csv(raw_dir / "premiums.csv")
    premiums_df["due_date"] = pd.to_datetime(premiums_df["due_date"]).dt.date
    premiums_df["paid_date"] = pd.to_datetime(premiums_df["paid_date"]).dt.date
    con.register("tmp_premiums", premiums_df)
    con.execute("INSERT OR REPLACE INTO fact_premiums SELECT * FROM tmp_premiums")
    con.unregister("tmp_premiums")

    # 9. Clean and load fact_renewals
    print("9. Ingesting fact_renewals...")
    renewals_df = read_csv(raw_dir / "renewals.csv")
    renewals_df["renewal_due_date"] = pd.to_datetime(renewals_df["renewal_due_date"]).dt.date
    con.register("tmp_renewals", renewals_df)
    con.execute("INSERT OR REPLACE INTO fact_renewals SELECT * FROM tmp_renewals")
    con.unregister("tmp_renewals")

    # Save cleaning log to warehouse directory
    cleaning_log_path = warehouse_dir / "cleaning_log.json"
    with open(cleaning_log_path, "w", encoding="utf-8") as f:
        json.dump(cleaning_log, f, indent=2)

    # Verification counts
    counts = {}
    for tbl in ["dim_date", "dim_provider", "dim_diagnosis", "dim_policy", "dim_member", "fact_claims", "fact_premiums", "fact_renewals"]:
        cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        counts[tbl] = cnt
        print(f"   Table '{tbl}': {cnt:,} rows")

    con.close()
    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"Warehouse built successfully in {elapsed:.2f} seconds.")
    print(f"Cleaning log saved to {cleaning_log_path}")
    print("=" * 60)

    return {"counts": counts, "cleaning_log": cleaning_log}


if __name__ == "__main__":
    build_warehouse()
