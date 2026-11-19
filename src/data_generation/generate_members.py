"""
Member demographics and health profile generator.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from src.data_generation.generate_providers import INDIAN_CITIES_MASTER


def get_age_band(age: int) -> str:
    """Categorize age into standardized insurance age bands."""
    if age <= 18:
        return "0-18"
    elif age <= 35:
        return "19-35"
    elif age <= 50:
        return "36-50"
    elif age <= 65:
        return "51-65"
    else:
        return "65+"


def generate_members(
    policies_df: pd.DataFrame,
    target_members: int = 50000,
    seed: int = 42,
    inject_noise: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate members linked to policies.
    Returns:
        (members_df, updated_policies_df)
    """
    rng = np.random.default_rng(seed)
    cities_df = pd.DataFrame(
        INDIAN_CITIES_MASTER, columns=["city", "state", "region", "city_tier"]
    )

    num_policies = len(policies_df)

    # First, allocate 1 primary member ('Self') for every policy
    # The remaining members (target_members - num_policies) are distributed
    # as dependents across Family Floater and Group policies.
    remaining_slots = max(0, target_members - num_policies)

    eligible_policies = policies_df[policies_df["plan_type"].isin(["Family Floater", "Group"])].index.to_numpy()
    extra_counts = np.zeros(num_policies, dtype=int)

    if len(eligible_policies) > 0 and remaining_slots > 0:
        # Distribute remaining slots randomly among eligible policies
        chosen_indices = rng.choice(eligible_policies, size=remaining_slots, replace=True)
        unique_idx, counts = np.unique(chosen_indices, return_counts=True)
        extra_counts[unique_idx] = counts

    # Update members_covered in policies
    updated_policies_df = policies_df.copy()
    updated_policies_df["members_covered"] = 1 + extra_counts

    members_records = []
    member_id_counter = 1

    income_bands = ["<3L", "3L-7L", "7L-15L", "15L-25L", "25L+"]
    income_weights = [0.15, 0.35, 0.30, 0.15, 0.05]

    occupations = ["Salaried", "Self-Employed", "Professional", "Student", "Retired", "Homemaker"]
    occ_weights = [0.45, 0.20, 0.15, 0.05, 0.08, 0.07]

    for i in range(num_policies):
        p_row = updated_policies_df.iloc[i]
        p_id = p_row["policy_id"]
        p_start_date = pd.to_datetime(p_row["policy_start_date"]).date()
        total_in_policy = 1 + extra_counts[i]

        # Primary member location
        city_idx = rng.choice(len(cities_df))
        city_row = cities_df.iloc[city_idx]
        p_city = city_row["city"]
        p_state = city_row["state"]
        p_region = city_row["region"]
        p_tier = int(city_row["city_tier"])

        # Primary member age (22 to 68)
        self_age = int(np.clip(rng.normal(41, 11), 22, 68))
        self_dob = p_start_date - timedelta(days=int(self_age * 365.25 + rng.integers(0, 365)))
        self_gender = "Male" if rng.random() < 0.58 else "Female"

        # Generate primary member
        for m_idx in range(total_in_policy):
            m_id = f"MEM_{member_id_counter:06d}"
            member_id_counter += 1

            if m_idx == 0:
                relation = "Self"
                age = self_age
                dob = self_dob
                gender = self_gender
                income_band = rng.choice(income_bands, p=income_weights)
                occ = rng.choice(occupations, p=occ_weights)
            elif m_idx == 1:
                relation = "Spouse"
                age = int(np.clip(self_age + rng.integers(-4, 4), 21, 65))
                dob = p_start_date - timedelta(days=int(age * 365.25 + rng.integers(0, 365)))
                gender = "Female" if self_gender == "Male" else "Male"
                income_band = rng.choice(income_bands, p=income_weights)
                occ = rng.choice(["Salaried", "Homemaker", "Professional", "Self-Employed"], p=[0.35, 0.35, 0.15, 0.15])
            elif m_idx == 2 and self_age >= 30:
                relation = "Child"
                age = int(np.clip(rng.integers(1, max(2, self_age - 20)), 0, 22))
                dob = p_start_date - timedelta(days=int(age * 365.25 + rng.integers(0, 365)))
                gender = "Male" if rng.random() < 0.52 else "Female"
                income_band = "<3L"
                occ = "Student"
            else:
                relation = "Parent" if self_age <= 48 and rng.random() < 0.6 else "Child"
                if relation == "Parent":
                    age = int(np.clip(self_age + rng.integers(22, 32), 52, 85))
                    dob = p_start_date - timedelta(days=int(age * 365.25 + rng.integers(0, 365)))
                    gender = "Female" if rng.random() < 0.55 else "Male"
                    income_band = rng.choice(["<3L", "3L-7L"], p=[0.7, 0.3])
                    occ = "Retired"
                else:
                    age = int(np.clip(rng.integers(1, max(2, self_age - 20)), 0, 22))
                    dob = p_start_date - timedelta(days=int(age * 365.25 + rng.integers(0, 365)))
                    gender = "Male" if rng.random() < 0.52 else "Female"
                    income_band = "<3L"
                    occ = "Student"

            # Clinical metrics
            bmi = round(float(np.clip(rng.normal(25.2, 4.1), 16.5, 45.0)), 1)
            smoker = 1 if (age >= 18 and rng.random() < (0.24 if gender == "Male" else 0.08)) else 0

            # Chronic disease risks scale with age
            p_diab = 0.02 if age < 35 else (0.15 if age < 50 else 0.32)
            if bmi >= 28.0:
                p_diab *= 1.4
            has_diabetes = 1 if (age >= 20 and rng.random() < min(0.60, p_diab)) else 0

            p_hyp = 0.04 if age < 35 else (0.20 if age < 50 else 0.42)
            if bmi >= 28.0 or smoker == 1:
                p_hyp *= 1.3
            has_hypertension = 1 if (age >= 20 and rng.random() < min(0.70, p_hyp)) else 0

            p_card = 0.01 if age < 40 else (0.07 if age < 55 else 0.20)
            if has_diabetes and has_hypertension:
                p_card *= 1.8
            has_cardiac = 1 if (age >= 30 and rng.random() < min(0.50, p_card)) else 0

            other_chronic = 1 if (age >= 50 and rng.random() < 0.15) else 0
            pre_existing_count = has_diabetes + has_hypertension + has_cardiac + other_chronic

            members_records.append({
                "member_id": m_id,
                "policy_id": p_id,
                "relation": relation,
                "gender": gender,
                "date_of_birth": dob,
                "age_at_enrollment": age,
                "age_band": get_age_band(age),
                "city": p_city,
                "state": p_state,
                "region": p_region,
                "city_tier": p_tier,
                "occupation_category": occ,
                "income_band": income_band,
                "bmi": bmi,
                "smoker_flag": smoker,
                "pre_existing_conditions_count": pre_existing_count,
                "has_diabetes": has_diabetes,
                "has_hypertension": has_hypertension,
                "has_cardiac_history": has_cardiac,
                "enrollment_date": p_start_date,
            })

    members_df = pd.DataFrame(members_records)

    # In raw layer: inject realistic noise (Rule 14)
    if inject_noise:
        # 1.5% nulls in BMI
        bmi_null_idx = rng.choice(len(members_df), size=int(0.015 * len(members_df)), replace=False)
        members_df.loc[bmi_null_idx, "bmi"] = np.nan

        # 1.5% nulls in income_band
        inc_null_idx = rng.choice(len(members_df), size=int(0.015 * len(members_df)), replace=False)
        members_df.loc[inc_null_idx, "income_band"] = np.nan

        # Minor casing / trailing spaces in city
        noise_city_idx = rng.choice(len(members_df), size=int(0.02 * len(members_df)), replace=False)
        for idx in noise_city_idx:
            orig = members_df.loc[idx, "city"]
            if idx % 2 == 0:
                members_df.loc[idx, "city"] = f"  {orig}  "
            else:
                members_df.loc[idx, "city"] = orig.lower()

    return members_df, updated_policies_df
