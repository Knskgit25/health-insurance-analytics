"""
Unit tests for data generation modules, determinism, and core invariants.
"""

import pandas as pd
import pytest

from src.data_generation.generate_claims import generate_claims
from src.data_generation.generate_diagnoses import generate_diagnoses
from src.data_generation.generate_members import generate_members
from src.data_generation.generate_policies import generate_policies
from src.data_generation.generate_premiums import generate_premiums
from src.data_generation.generate_providers import generate_providers


@pytest.fixture(scope="module")
def generated_sample_data():
    """Generate a quick fixture dataset for fast testing."""
    seed = 42
    num_policies = 1000
    target_members = 1200
    num_providers = 50
    target_claims = 2500

    providers_df = generate_providers(num_providers=num_providers, seed=seed)
    diagnoses_df = generate_diagnoses()
    policies_df, renewals_df = generate_policies(num_policies=num_policies, seed=seed)
    members_df, policies_df = generate_members(
        policies_df=policies_df, target_members=target_members, seed=seed, inject_noise=False
    )
    premiums_df = generate_premiums(policies_df=policies_df, seed=seed)
    claims_df = generate_claims(
        members_df=members_df,
        policies_df=policies_df,
        providers_df=providers_df,
        diagnoses_df=diagnoses_df,
        target_claims=target_claims,
        seed=seed,
        inject_duplicates=False
    )

    return {
        "providers": providers_df,
        "diagnoses": diagnoses_df,
        "policies": policies_df,
        "renewals": renewals_df,
        "members": members_df,
        "premiums": premiums_df,
        "claims": claims_df
    }


def test_determinism():
    """AC1: Re-generating with identical seed must yield byte-for-byte identical checksums."""
    p1 = generate_providers(num_providers=50, seed=42)
    p2 = generate_providers(num_providers=50, seed=42)
    pd.testing.assert_frame_equal(p1, p2)


def test_claim_financial_invariants(generated_sample_data):
    """AC3: approved_amount <= sum_insured and paid_amount <= approved_amount for 100% of claims."""
    claims = generated_sample_data["claims"]
    policies = generated_sample_data["policies"].set_index("policy_id")

    # Join sum_insured to claims
    merged = claims.join(policies[["sum_insured"]], on="policy_id")

    # Invariant 1: approved_amount <= sum_insured (with small float tolerance)
    assert (merged["approved_amount"] <= merged["sum_insured"] + 1e-5).all(), "approved_amount exceeded sum_insured"

    # Invariant 2: paid_amount <= approved_amount
    assert (merged["paid_amount"] <= merged["approved_amount"] + 1e-5).all(), "paid_amount exceeded approved_amount"

    # Invariant 3: patient_paid_amount >= 0
    assert (merged["patient_paid_amount"] >= -1e-5).all(), "patient_paid_amount negative"


def test_claim_date_sequence(generated_sample_data):
    """AC4: claim_settled_date >= claim_submitted_date >= discharge_date for all settled claims."""
    claims = generated_sample_data["claims"]
    settled = claims[claims["claim_status"].isin(["Approved", "Partially Approved", "Rejected"])]

    # Check discharge_date >= admission_date
    assert (settled["discharge_date"] >= settled["admission_date"]).all()

    # Check claim_submitted_date >= discharge_date
    assert (settled["claim_submitted_date"] >= settled["discharge_date"]).all()

    # Check claim_settled_date >= claim_submitted_date
    assert (settled["claim_settled_date"] >= settled["claim_submitted_date"]).all()


def test_rejection_and_fraud_rates(generated_sample_data):
    """AC5 target checks: rejection ~8-12%, fraud ~2-3%."""
    claims = generated_sample_data["claims"]
    decided = claims[claims["claim_status"] != "Pending"]
    rejection_rate = (decided["claim_status"] == "Rejected").mean()
    fraud_rate = claims["is_fraud_flag"].mean()

    assert 0.07 <= rejection_rate <= 0.14, f"Rejection rate {rejection_rate:.3f} outside expected bounds"
    assert 0.015 <= fraud_rate <= 0.045, f"Fraud rate {fraud_rate:.3f} outside expected bounds"


def test_persistency_rate(generated_sample_data):
    """AC5 target check: renewal rate ~78-88%."""
    renewals = generated_sample_data["renewals"]
    if not renewals.empty:
        persistency = renewals["renewed_flag"].mean()
        assert 0.75 <= persistency <= 0.90, f"Persistency rate {persistency:.3f} outside bounds"


def test_referential_integrity(generated_sample_data):
    """Ensure zero orphan foreign keys in generated data."""
    members = generated_sample_data["members"]
    policies = generated_sample_data["policies"]
    claims = generated_sample_data["claims"]
    providers = generated_sample_data["providers"]
    diagnoses = generated_sample_data["diagnoses"]

    policy_ids = set(policies["policy_id"])
    member_ids = set(members["member_id"])
    provider_ids = set(providers["provider_id"])
    dx_ids = set(diagnoses["diagnosis_id"])

    assert set(members["policy_id"]).issubset(policy_ids), "Orphan policy_id in members"
    assert set(claims["policy_id"]).issubset(policy_ids), "Orphan policy_id in claims"
    assert set(claims["member_id"]).issubset(member_ids), "Orphan member_id in claims"
    assert set(claims["provider_id"]).issubset(provider_ids), "Orphan provider_id in claims"
    assert set(claims["diagnosis_id"]).issubset(dx_ids), "Orphan diagnosis_id in claims"
