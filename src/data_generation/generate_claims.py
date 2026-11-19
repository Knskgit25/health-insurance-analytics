"""
Granular claim transaction generator with realistic insurance physics (fact_claims).
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

# Fraud pattern constants
FRAUD_PROVIDERS = {
    "PRV_000013", "PRV_000046", "PRV_000089", "PRV_000104", "PRV_000155",
    "PRV_000220", "PRV_000288", "PRV_000343", "PRV_000406", "PRV_000478",
    "PRV_000513", "PRV_000591", "PRV_000645", "PRV_000716", "PRV_000783"
}

REJECTION_REASONS = [
    "Waiting Period Not Completed",
    "Pre-Existing Condition Not Disclosed",
    "Treatment Not Covered Under Policy",
    "Incomplete Documentation",
    "Policy Inactive or Lapsed at Admission"
]


def generate_claims(
    members_df: pd.DataFrame,
    policies_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    diagnoses_df: pd.DataFrame,
    target_claims: int = 120000,
    seed: int = 42,
    inject_duplicates: bool = True
) -> pd.DataFrame:
    """Generate realistic health insurance claims dataframe."""
    rng = np.random.default_rng(seed)

    # Pre-build lookup dictionaries for fast vectorized generation
    policy_dict = policies_df.set_index("policy_id").to_dict("index")
    providers_df.set_index("provider_id").to_dict("index")
    provider_ids = providers_df["provider_id"].to_numpy()
    provider_tiers = providers_df["hospital_tier"].to_numpy()
    provider_networks = providers_df["network_status"].to_numpy()
    diagnosis_records = diagnoses_df.to_dict("records")
    dx_ids_by_cat = {}
    for d in diagnosis_records:
        dx_ids_by_cat.setdefault(d["diagnosis_category"], []).append(d)

    # Step 1: Member claim weight calculation based on clinical & demographic risk
    ages = members_df["age_at_enrollment"].to_numpy()
    diabetes = members_df["has_diabetes"].to_numpy()
    hypertension = members_df["has_hypertension"].to_numpy()
    cardiac = members_df["has_cardiac_history"].to_numpy()
    smoker = members_df["smoker_flag"].to_numpy()
    bmi = members_df["bmi"].fillna(25.0).to_numpy()

    # Risk weights: exponential curve for age + chronic conditions
    age_factor = np.exp((ages - 35) / 28.0)
    clinical_risk = 1.0 + 1.2 * diabetes + 1.0 * hypertension + 1.8 * cardiac + 0.4 * smoker + 0.3 * (bmi > 30)
    member_weights = age_factor * clinical_risk
    member_probs = member_weights / member_weights.sum()

    # Sample member indices for the target claims
    sampled_member_indices = rng.choice(len(members_df), size=target_claims, p=member_probs)

    # Prepare claim attributes
    claim_records = []
    claim_counter = 1

    # Keep track of recent claim admissions per member for repeat claim injection

    for idx in sampled_member_indices:
        m_row = members_df.iloc[idx]
        m_id = m_row["member_id"]
        p_id = m_row["policy_id"]
        p_info = policy_dict[p_id]
        gender = m_row["gender"]
        age = m_row["age_at_enrollment"]
        m_diab = m_row["has_diabetes"]
        m_hyp = m_row["has_hypertension"]
        m_card = m_row["has_cardiac_history"]
        m_smk = m_row["smoker_flag"]
        p_tier = p_info["plan_tier"]
        p_start = pd.to_datetime(p_info["policy_start_date"]).date()
        p_end = pd.to_datetime(p_info["policy_end_date"]).date()
        si = float(p_info["sum_insured"])
        deductible = float(p_info["deductible"])
        copay_pct = float(p_info["co_pay_pct"])

        # Determine diagnosis category based on member profile (Rule 1, 2, 3, 4)
        cat_choices = [
            "Cardiac", "Oncology", "Orthopedic", "Maternity", "Respiratory",
            "Gastro", "Infectious", "Renal", "Neuro", "Other"
        ]
        cat_weights = [0.12, 0.08, 0.12, 0.05, 0.14, 0.12, 0.16, 0.07, 0.06, 0.08]

        # Shift weights according to member profile
        if m_card or (age > 50 and m_hyp):
            cat_weights[0] += 0.25  # Cardiac
        if m_diab or age > 55:
            cat_weights[7] += 0.15  # Renal
        if m_smk or m_row["region"] in ["North", "East"]:
            cat_weights[4] += 0.15  # Respiratory
        if age > 55:
            cat_weights[1] += 0.15  # Oncology
            cat_weights[8] += 0.10  # Neuro
            cat_weights[2] += 0.12  # Orthopedic

        # Rule 4: Maternity only for females 22-38 on Gold/Platinum after 9-month waiting period
        is_maternity_eligible = (
            gender == "Female" and (22 <= age <= 38) and
            (p_tier in ["Gold", "Platinum"]) and
            (p_end - p_start).days >= 300
        )
        if not is_maternity_eligible:
            cat_weights[3] = 0.0  # Zero maternity probability
        else:
            cat_weights[3] = 0.22

        # Normalize weights
        sum_w = sum(cat_weights)
        norm_weights = [w / sum_w for w in cat_weights]
        chosen_cat = rng.choice(cat_choices, p=norm_weights)

        # Pick a diagnosis in this category
        dx_candidate = rng.choice(dx_ids_by_cat[chosen_cat])
        dx_id = dx_candidate["diagnosis_id"]
        sev_lvl = int(dx_candidate["severity_level"])
        typ_los = int(dx_candidate["typical_los_days"])
        c_min = float(dx_candidate["typical_cost_min"])
        c_max = float(dx_candidate["typical_cost_max"])

        # Admission date between policy_start and policy_end
        # Seasonality (Rule 7): Respiratory/Infectious peak in Q3 (July-Sep) & Q4 (Oct-Dec)
        pol_days = (p_end - p_start).days
        if pol_days <= 10:
            offset_days = rng.integers(0, max(1, pol_days))
        else:
            if chosen_cat in ["Respiratory", "Infectious"] and rng.random() < 0.65:
                # Target monsoon / winter months
                # Select a year within active term
                cand_year = rng.integers(p_start.year, p_end.year + 1)
                cand_month = rng.choice([7, 8, 9, 10, 11, 12])
                cand_day = rng.integers(1, 28)
                adm_cand = date(cand_year, cand_month, cand_day)
                if p_start <= adm_cand <= p_end:
                    offset_days = (adm_cand - p_start).days
                else:
                    offset_days = rng.integers(0, pol_days)
            else:
                offset_days = rng.integers(0, pol_days)

        admission_date = p_start + timedelta(days=int(offset_days))

        # Check for maternity waiting period: 270 days
        if chosen_cat == "Maternity" and (admission_date - p_start).days < 270 and (p_end - p_start).days > 280:
            admission_date = p_start + timedelta(days=int(rng.integers(275, pol_days)))

        # Provider selection
        prv_idx = rng.integers(0, len(provider_ids))
        prv_id = provider_ids[prv_idx]
        h_tier = provider_tiers[prv_idx]
        h_network = provider_networks[prv_idx]

        # Length of stay
        los = max(1, int(np.clip(rng.poisson(typ_los), 1, 30)))
        discharge_date = admission_date + timedelta(days=los)

        # Claim type: 65% Cashless for Network, Reimbursement for Non-Network
        if h_network == "Network":
            claim_type = "Cashless" if rng.random() < 0.82 else "Reimbursement"
        else:
            claim_type = "Reimbursement"

        # Emergency flag
        is_emergency = 1 if (sev_lvl >= 4 and rng.random() < 0.60) or rng.random() < 0.18 else 0
        is_planned = 1 - is_emergency
        icu_days = max(0, min(los, int(rng.integers(1, los + 1)))) if (sev_lvl >= 4 and rng.random() < 0.55) else 0
        num_procedures = max(1, int(rng.choice([1, 2, 3, 4], p=[0.60, 0.25, 0.10, 0.05])))

        # Fraud determination (Rule 11) - calibrated to land in 2.0% - 3.0%
        is_fraud = 0
        is_fraud_provider = prv_id in FRAUD_PROVIDERS
        if is_fraud_provider and rng.random() < 0.25 or rng.random() < 0.018:
            is_fraud = 1

        # Pricing calculation (Rule 5 & 8) - calibrated for portfolio loss ratio 70% - 95%
        tier_mult = 1.75 if h_tier == "Tier1" else (1.30 if h_tier == "Tier2" else 1.0)
        base_center = (c_min + c_max) / 2.0
        cost_scale = rng.lognormal(mean=np.log(base_center), sigma=0.25)
        raw_billed = cost_scale * tier_mult * (1.0 + 0.15 * (sev_lvl - 3)) * (1.0 + 0.12 * icu_days) * 0.79

        if is_fraud:
            # Inflate billed amount, or round number, or extreme LOS discrepancy
            if rng.random() < 0.50:
                raw_billed *= rng.uniform(2.2, 4.0)
            if rng.random() < 0.60:
                # Round number billing (e.g. 150000, 200000, 350000)
                raw_billed = round(raw_billed / 10000.0) * 10000.0
            if los > 3 and rng.random() < 0.40:
                los = 1
                discharge_date = admission_date + timedelta(days=1)

        billed_amount = round(float(np.clip(raw_billed, 8000.0, 1800000.0)), 2)

        # Adjudication & Rejection (Rule 10) - Target ~9.5% rejection rate
        # Rejection factors
        p_reject = 0.08
        if claim_type == "Reimbursement":
            p_reject += 0.04
        if p_info["sales_channel"] == "Online":
            p_reject += 0.02
        if is_fraud and rng.random() < 0.45:
            p_reject += 0.30
        if (admission_date - p_start).days < 30 and sev_lvl < 4:
            p_reject += 0.18  # 30-day initial waiting period

        # Final status
        r_val = rng.random()
        if r_val < p_reject:
            claim_status = "Rejected"
            if (admission_date - p_start).days < 30:
                rej_reason = "Waiting Period Not Completed"
            elif m_card and chosen_cat == "Cardiac" and rng.random() < 0.4:
                rej_reason = "Pre-Existing Condition Not Disclosed"
            else:
                rej_reason = rng.choice(REJECTION_REASONS, p=[0.25, 0.25, 0.20, 0.20, 0.10])
        elif r_val < p_reject + 0.025:
            claim_status = "Pending"
            rej_reason = None
        elif r_val < p_reject + 0.13:
            claim_status = "Partially Approved"
            rej_reason = None
        else:
            claim_status = "Approved"
            rej_reason = None

        # Turnaround Time (TAT) and dates (Rule 9 & AC4)
        if claim_type == "Cashless":
            claim_submitted_date = discharge_date
            tat = max(1, int(np.clip(rng.normal(3.8, 1.8), 1, 14)))
        else:
            claim_submitted_date = discharge_date + timedelta(days=int(rng.integers(1, 15)))
            tat_base = 15.6 if h_network == "Network" else 20.4
            tat = max(3, int(np.clip(rng.normal(tat_base, 4.5), 3, 45)))

        if claim_status == "Pending":
            claim_settled_date = None
            settlement_tat_days = None
        else:
            claim_settled_date = claim_submitted_date + timedelta(days=tat)
            settlement_tat_days = tat

        # Financial waterfall (AC3 strict invariants)
        if claim_status == "Rejected":
            approved_amount = 0.0
            paid_amount = 0.0
            patient_paid_amount = billed_amount
        elif claim_status == "Pending":
            # For pending claims, approved amount estimate under sum insured
            approved_amount = min(si, round(billed_amount * 0.85, 2))
            paid_amount = 0.0
            patient_paid_amount = 0.0
        else:
            # Approved or Partially Approved
            approval_ratio = rng.uniform(0.90, 0.98) if claim_status == "Approved" else rng.uniform(0.65, 0.82)
            eligible_amount = billed_amount * approval_ratio
            # Apply deductible
            after_ded = max(0.0, eligible_amount - deductible)
            # Apply co-pay
            after_copay = after_ded * (1.0 - copay_pct)
            # Cap strictly at sum_insured
            appr = min(si, round(after_copay, 2))
            approved_amount = appr
            paid_amount = appr
            patient_paid_amount = round(billed_amount - paid_amount, 2)

        c_id = f"CLM_{claim_counter:07d}"
        claim_counter += 1

        claim_records.append({
            "claim_id": c_id,
            "member_id": m_id,
            "policy_id": p_id,
            "provider_id": prv_id,
            "diagnosis_id": dx_id,
            "claim_type": claim_type,
            "admission_date": admission_date,
            "discharge_date": discharge_date,
            "length_of_stay": los,
            "claim_submitted_date": claim_submitted_date,
            "claim_settled_date": claim_settled_date,
            "settlement_tat_days": settlement_tat_days,
            "billed_amount": billed_amount,
            "approved_amount": approved_amount,
            "paid_amount": paid_amount,
            "patient_paid_amount": patient_paid_amount,
            "claim_status": claim_status,
            "rejection_reason": rej_reason,
            "is_emergency": is_emergency,
            "is_planned": is_planned,
            "icu_days": icu_days,
            "num_procedures": num_procedures,
            "is_fraud_flag": is_fraud
        })

    claims_df = pd.DataFrame(claim_records)
    claims_df["admission_date"] = pd.to_datetime(claims_df["admission_date"])
    claims_df["discharge_date"] = pd.to_datetime(claims_df["discharge_date"])
    claims_df["claim_submitted_date"] = pd.to_datetime(claims_df["claim_submitted_date"])
    claims_df["claim_settled_date"] = pd.to_datetime(claims_df["claim_settled_date"])

    # Raw layer noise: duplicate rows (Rule 14)
    if inject_duplicates:
        dup_indices = rng.choice(len(claims_df), size=int(0.002 * len(claims_df)), replace=False)
        dup_rows = claims_df.iloc[dup_indices].copy()
        claims_df = pd.concat([claims_df, dup_rows], ignore_index=True)

    return claims_df
