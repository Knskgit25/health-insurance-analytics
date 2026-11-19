"""
Master synthetic data generation orchestrator.
Generates all raw datasets deterministically and exports to data/raw/*.csv.
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.data_generation.generate_claims import generate_claims
from src.data_generation.generate_diagnoses import generate_diagnoses
from src.data_generation.generate_members import generate_members
from src.data_generation.generate_policies import generate_policies
from src.data_generation.generate_premiums import generate_premiums
from src.data_generation.generate_providers import generate_providers
from src.utils.config import get_path, load_config
from src.utils.io import save_csv


def generate_date_dimension(start_date: str = "2021-01-01", end_date: str = "2025-12-31") -> pd.DataFrame:
    """Generate calendar date dimension spanning the full analytics window."""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df = pd.DataFrame({
        "date_key": dates.date,
        "date": dates.date,
        "year": dates.year,
        "quarter": dates.quarter,
        "month": dates.month,
        "month_name": dates.strftime("%B"),
        "week": dates.isocalendar().week,
        "day_of_week": dates.dayofweek + 1,  # 1=Monday, 7=Sunday
        "is_weekend": (dates.dayofweek >= 5).astype(int),
        "policy_year": dates.year,
    })
    return df


def run_all_generation():
    """Run full synthetic generation pipeline."""
    start_time = time.time()
    config = load_config()
    seed = config["project"]["seed"]
    scale = config["scale"]
    raw_dir = get_path("raw_dir", config)
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Starting MediSure Data Generation (Seed={seed})...")
    print("=" * 60)

    # 1. Diagnoses
    print("1. Generating Diagnosis Dimension...")
    diagnoses_df = generate_diagnoses()
    save_csv(diagnoses_df, raw_dir / "diagnoses.csv")
    print(f"   Generated {len(diagnoses_df)} standard ICD-10 diagnoses.")

    # 2. Providers
    print(f"2. Generating {scale['num_providers']} Healthcare Providers...")
    providers_df = generate_providers(num_providers=scale["num_providers"], seed=seed)
    save_csv(providers_df, raw_dir / "providers.csv")
    print(f"   Generated {len(providers_df)} providers across tiers.")

    # 3. Policies & Renewals
    print(f"3. Generating {scale['num_policies']} Policies & Renewal events...")
    policies_df, renewals_df = generate_policies(num_policies=scale["num_policies"], seed=seed)
    print(f"   Generated {len(policies_df)} policies and {len(renewals_df)} renewal records.")

    # 4. Members
    print(f"4. Generating {scale['num_members']} Members and linking to policies...")
    members_df, policies_df = generate_members(
        policies_df=policies_df,
        target_members=scale["num_members"],
        seed=seed,
        inject_noise=True
    )
    save_csv(members_df, raw_dir / "members.csv")
    save_csv(policies_df, raw_dir / "policies.csv")
    save_csv(renewals_df, raw_dir / "renewals.csv")
    print(f"   Generated {len(members_df)} members across {len(policies_df)} policies.")

    # 5. Premiums
    print("5. Generating Premium Collection transactions...")
    premiums_df = generate_premiums(policies_df=policies_df, seed=seed)
    save_csv(premiums_df, raw_dir / "premiums.csv")
    print(f"   Generated {len(premiums_df)} premium transactions.")

    # 6. Claims
    print(f"6. Generating ~{scale['target_claims']} Hospitalization Claims...")
    claims_df = generate_claims(
        members_df=members_df,
        policies_df=policies_df,
        providers_df=providers_df,
        diagnoses_df=diagnoses_df,
        target_claims=scale["target_claims"],
        seed=seed,
        inject_duplicates=True
    )
    save_csv(claims_df, raw_dir / "claims.csv")
    print(f"   Generated {len(claims_df)} claim transactions (including raw injected duplicates).")

    # 7. Date Dimension
    print("7. Generating Date Dimension...")
    date_df = generate_date_dimension(
        start_date=config["project"]["date_range"]["start"],
        end_date=config["project"]["date_range"]["end"]
    )
    save_csv(date_df, raw_dir / "dates.csv")
    print(f"   Generated {len(date_df)} calendar date records.")

    # Export small sample files for quick inspection & git
    save_csv(members_df.head(100), raw_dir / "sample_members.csv")
    save_csv(claims_df.head(100), raw_dir / "sample_claims.csv")

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"Data Generation completed successfully in {elapsed:.2f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    run_all_generation()
