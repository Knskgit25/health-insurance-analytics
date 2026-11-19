"""
Premium collection transactions generator (fact_premiums).
"""

from datetime import timedelta

import numpy as np
import pandas as pd


def generate_premiums(policies_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate fact_premiums records for each policy term."""
    rng = np.random.default_rng(seed)

    modes = ["UPI", "Net Banking", "Credit Card", "Debit Card", "Cheque"]
    mode_weights = [0.35, 0.30, 0.20, 0.10, 0.05]

    records = []
    prem_counter = 1

    for _, row in policies_df.iterrows():
        p_id = row["policy_id"]
        annual_prem = float(row["annual_premium"])
        p_start = pd.to_datetime(row["policy_start_date"]).date()
        p_end = pd.to_datetime(row["policy_end_date"]).date()
        status = row["status"]
        lapse_d = pd.to_datetime(row["lapse_date"]).date() if pd.notna(row["lapse_date"]) else None

        # Number of policy years active
        term_start = p_start
        term_idx = 0

        while term_start < p_end:
            due_date = term_start
            term_end = min(p_end, term_start + timedelta(days=365))

            # Initial year or renewed years
            is_lapsed_term = (status == "Lapsed" and lapse_d and due_date >= lapse_d)

            p_mode = rng.choice(modes, p=mode_weights)

            if is_lapsed_term:
                # Missed payment triggered lapse
                pay_status = "Missed"
                paid_date = None
                days_late = int(rng.integers(31, 60))
            else:
                # Active term: mostly paid on time or slightly late
                if rng.random() < 0.90:
                    pay_status = "Paid"
                    days_late = 0
                    paid_date = due_date + timedelta(days=int(rng.integers(-5, 3)))
                else:
                    pay_status = "Late"
                    days_late = int(rng.integers(4, 25))
                    paid_date = due_date + timedelta(days=days_late)

            records.append({
                "premium_id": f"PRM_{prem_counter:07d}",
                "policy_id": p_id,
                "due_date": due_date,
                "paid_date": paid_date,
                "premium_amount": annual_prem if term_idx == 0 else round(annual_prem * (1.08 ** term_idx), 2),
                "payment_status": pay_status,
                "payment_mode": p_mode,
                "days_late": days_late
            })
            prem_counter += 1

            term_idx += 1
            term_start = term_end
            if term_idx >= 5:
                break

    df = pd.DataFrame(records)
    df["due_date"] = pd.to_datetime(df["due_date"])
    df["paid_date"] = pd.to_datetime(df["paid_date"])
    return df
