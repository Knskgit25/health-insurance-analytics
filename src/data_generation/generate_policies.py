"""
Policy contract generator for MediSure Health Insurance.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd

PLAN_TIER_CONFIG = {
    "Bronze": {"sum_insured": 250000.0, "deductible": 15000.0, "co_pay_pct": 0.20, "base_prem": 10500.0},
    "Silver": {"sum_insured": 500000.0, "deductible": 5000.0, "co_pay_pct": 0.10, "base_prem": 17500.0},
    "Gold": {"sum_insured": 1000000.0, "deductible": 2500.0, "co_pay_pct": 0.05, "base_prem": 29000.0},
    "Platinum": {"sum_insured": 2000000.0, "deductible": 0.0, "co_pay_pct": 0.00, "base_prem": 52000.0},
}


def generate_policies(num_policies: int = 42000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate dim_policy and fact_renewals.
    Returns:
        (policies_df, renewals_df)
    """
    rng = np.random.default_rng(seed)

    policy_ids = [f"POL_{i+1:06d}" for i in range(num_policies)]

    # Plan type distribution
    plan_types = rng.choice(
        ["Individual", "Family Floater", "Group"],
        size=num_policies,
        p=[0.50, 0.35, 0.15]
    )

    # Plan tier distribution
    plan_tiers = rng.choice(
        ["Bronze", "Silver", "Gold", "Platinum"],
        size=num_policies,
        p=[0.25, 0.35, 0.25, 0.15]
    )

    # Sales channel distribution
    channels = rng.choice(
        ["Agent", "Online", "Broker", "Bancassurance"],
        size=num_policies,
        p=[0.40, 0.25, 0.20, 0.15]
    )

    # Start dates staggered from 2021-01-01 to 2024-12-31
    base_date = date(2021, 1, 1)
    max_start_days = (date(2024, 12, 1) - base_date).days
    start_day_offsets = rng.integers(0, max_start_days, size=num_policies)

    # Calculate members covered
    members_covered_list = []
    for pt in plan_types:
        if pt == "Individual":
            members_covered_list.append(1)
        elif pt == "Family Floater":
            members_covered_list.append(int(rng.choice([2, 3, 4], p=[0.4, 0.4, 0.2])))
        else:  # Group
            members_covered_list.append(int(rng.choice([1, 2, 3, 4, 5], p=[0.2, 0.3, 0.3, 0.1, 0.1])))

    # Lists for policy rows
    sums_insured = []
    annual_premiums = []
    deductibles = []
    co_pays = []
    start_dates = []
    end_dates = []
    policy_years = []
    renewal_counts = []
    statuses = []
    lapse_dates = []

    # Lists for renewals
    renewals_data = []
    renewal_id_counter = 1

    for i in range(num_policies):
        tier = plan_tiers[i]
        pt = plan_types[i]
        ch = channels[i]
        cov_count = members_covered_list[i]
        p_cfg = PLAN_TIER_CONFIG[tier]

        # Financial parameters
        si = p_cfg["sum_insured"]
        ded = p_cfg["deductible"]
        copay = p_cfg["co_pay_pct"]

        # Base annual premium with realistic variance
        base_prem = p_cfg["base_prem"]
        if pt == "Family Floater":
            prem_mult = 1.0 + 0.35 * (cov_count - 1)
        elif pt == "Group":
            prem_mult = 0.85 * cov_count
        else:
            prem_mult = 1.0

        noise_factor = rng.uniform(0.92, 1.08)
        annual_prem = round(base_prem * prem_mult * noise_factor, 2)

        p_start = base_date + timedelta(days=int(start_day_offsets[i]))
        current_year = p_start.year
        policy_years.append(current_year)

        # Renewal simulation over 5-year timeline up to end of 2025
        p_end = p_start + timedelta(days=365)
        cur_status = "Active"
        cur_lapse_date = None
        cur_renewal_count = 0
        cur_premium = annual_prem

        term_start = p_start
        term_end = p_end

        # Multi-year renewal loop
        while term_end <= date(2025, 12, 31):
            # Renewal event
            renewal_due = term_end
            if renewal_due > date(2025, 12, 31):
                break

            # Premium change % (-5% to +25%)
            prem_change = round(float(rng.normal(0.08, 0.06)), 3)
            # Bound realistic change
            prem_change = max(-0.05, min(0.30, prem_change))
            new_premium = round(cur_premium * (1.0 + prem_change), 2)

            # Renewal probability baseline ~ 83%
            p_renew = 0.83
            if prem_change > 0.15:
                p_renew -= 0.18
            if ch == "Online":
                p_renew -= 0.06
            elif ch == "Agent":
                p_renew += 0.05
            if tier == "Platinum":
                p_renew += 0.07
            elif tier == "Bronze":
                p_renew -= 0.04

            is_renewed = 1 if rng.random() < p_renew else 0

            lapse_reason = None
            if is_renewed == 0:
                lapse_reasons = [
                    "High Premium Increase",
                    "Dissatisfaction with Claim Processing",
                    "Switched to Competitor",
                    "Cost Cutting / Affordability",
                    "Low Perceived Need"
                ]
                reason_probs = [0.35, 0.25, 0.20, 0.10, 0.10]
                lapse_reason = rng.choice(lapse_reasons, p=reason_probs)

                renewals_data.append({
                    "renewal_id": f"RNW_{renewal_id_counter:07d}",
                    "policy_id": policy_ids[i],
                    "renewal_due_date": renewal_due,
                    "renewed_flag": 0,
                    "renewal_premium": new_premium,
                    "premium_change_pct": prem_change,
                    "lapse_reason": lapse_reason
                })
                renewal_id_counter += 1

                cur_status = "Lapsed"
                cur_lapse_date = renewal_due
                break
            else:
                renewals_data.append({
                    "renewal_id": f"RNW_{renewal_id_counter:07d}",
                    "policy_id": policy_ids[i],
                    "renewal_due_date": renewal_due,
                    "renewed_flag": 1,
                    "renewal_premium": new_premium,
                    "premium_change_pct": prem_change,
                    "lapse_reason": None
                })
                renewal_id_counter += 1

                cur_renewal_count += 1
                cur_premium = new_premium
                term_start = term_end
                term_end = term_start + timedelta(days=365)
                p_end = term_end

        sums_insured.append(si)
        annual_premiums.append(annual_prem)
        deductibles.append(ded)
        co_pays.append(copay)
        start_dates.append(p_start)
        end_dates.append(p_end)
        renewal_counts.append(cur_renewal_count)
        statuses.append(cur_status)
        lapse_dates.append(cur_lapse_date)

    policies_df = pd.DataFrame({
        "policy_id": policy_ids,
        "plan_type": plan_types,
        "plan_tier": plan_tiers,
        "sum_insured": sums_insured,
        "annual_premium": annual_premiums,
        "deductible": deductibles,
        "co_pay_pct": co_pays,
        "policy_start_date": pd.to_datetime(start_dates),
        "policy_end_date": pd.to_datetime(end_dates),
        "policy_year": policy_years,
        "sales_channel": channels,
        "renewal_count": renewal_counts,
        "status": statuses,
        "lapse_date": pd.to_datetime(lapse_dates),
        "members_covered": members_covered_list
    })

    renewals_df = pd.DataFrame(renewals_data)
    if not renewals_df.empty:
        renewals_df["renewal_due_date"] = pd.to_datetime(renewals_df["renewal_due_date"])

    return policies_df, renewals_df
