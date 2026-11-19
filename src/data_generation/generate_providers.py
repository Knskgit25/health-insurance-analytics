"""
Provider (Hospital) data generator.
"""

import numpy as np
import pandas as pd
from faker import Faker

# 15 designated fraud-prone provider IDs for Rule 11
FRAUD_PROVIDER_INDICES = {12, 45, 88, 103, 154, 219, 287, 342, 405, 477, 512, 590, 644, 715, 782}

INDIAN_CITIES_MASTER = [
    # Metro / Tier 1
    ("Mumbai", "Maharashtra", "West", 1),
    ("Delhi", "Delhi", "North", 1),
    ("Bengaluru", "Karnataka", "South", 1),
    ("Chennai", "Tamil Nadu", "South", 1),
    ("Hyderabad", "Telangana", "South", 1),
    ("Kolkata", "West Bengal", "East", 1),
    ("Pune", "Maharashtra", "West", 1),
    ("Ahmedabad", "Gujarat", "West", 1),
    # Tier 2
    ("Jaipur", "Rajasthan", "North", 2),
    ("Lucknow", "Uttar Pradesh", "North", 2),
    ("Chandigarh", "Punjab", "North", 2),
    ("Indore", "Madhya Pradesh", "Central", 2),
    ("Bhopal", "Madhya Pradesh", "Central", 2),
    ("Kochi", "Kerala", "South", 2),
    ("Coimbatore", "Tamil Nadu", "South", 2),
    ("Visakhapatnam", "Andhra Pradesh", "South", 2),
    ("Nagpur", "Maharashtra", "West", 2),
    ("Surat", "Gujarat", "West", 2),
    ("Patna", "Bihar", "East", 2),
    ("Bhubaneswar", "Odisha", "East", 2),
    ("Guwahati", "Assam", "East", 2),
    # Tier 3
    ("Varanasi", "Uttar Pradesh", "North", 3),
    ("Agra", "Uttar Pradesh", "North", 3),
    ("Dehradun", "Uttarakhand", "North", 3),
    ("Jabalpur", "Madhya Pradesh", "Central", 3),
    ("Gwalior", "Madhya Pradesh", "Central", 3),
    ("Madurai", "Tamil Nadu", "South", 3),
    ("Mangalore", "Karnataka", "South", 3),
    ("Nashik", "Maharashtra", "West", 3),
    ("Rajkot", "Gujarat", "West", 3),
    ("Ranchi", "Jharkhand", "East", 3),
    ("Siliguri", "West Bengal", "East", 3),
    ("Raipur", "Chhattisgarh", "Central", 3),
]

HOSPITAL_PREFIXES = [
    "Apollo", "Fortis", "Max Super Specialty", "Manipal", "Narayana Health",
    "Care", "Medanta", "KIMS", "Aster Medcity", "Columbia Asia", "Ruby Hall",
    "Lilavati", "Kokilaben Dhirubhai Ambani", "Hinduja", "Sir Ganga Ram",
    "Sanjeevani", "LifeLine", "Apex", "City Care", "Sunrise", "Grace",
    "Lotus", "Sterling", "Sahyadri", "Sunshine", "Metro Heart", "Sparsh"
]


def generate_providers(num_providers: int = 800, seed: int = 42) -> pd.DataFrame:
    """Generate hospital providers dataset."""
    rng = np.random.default_rng(seed)
    faker = Faker("en_IN")
    faker.seed_instance(seed)

    cities_df = pd.DataFrame(
        INDIAN_CITIES_MASTER, columns=["city", "state", "region", "city_tier"]
    )

    provider_ids = [f"PRV_{i+1:06d}" for i in range(num_providers)]
    provider_names = []
    cities, states, regions, hospital_tiers = [], [], [], []
    network_statuses, bed_counts, specialty_focuses = [], [], []
    avg_ratings, accreditations = [], []
    is_fraud_prone = []

    specialties = [
        "Multi-Specialty", "Cardiac Sciences", "Oncology & Cancer Care",
        "Orthopedics & Joint Replacement", "Neurosciences", "Gastroenterology",
        "Nephrology & Urology", "General Medicine & Surgery"
    ]
    specialty_probs = [0.45, 0.12, 0.10, 0.10, 0.08, 0.05, 0.05, 0.05]

    for i in range(num_providers):
        # City selection weighted by tier
        tier_weights = [0.45, 0.35, 0.20]
        chosen_tier = rng.choice([1, 2, 3], p=tier_weights)
        eligible_cities = cities_df[cities_df["city_tier"] == chosen_tier]
        city_row = eligible_cities.iloc[rng.integers(0, len(eligible_cities))]

        city = city_row["city"]
        state = city_row["state"]
        region = city_row["region"]

        # Hospital tier correlates with city tier
        if chosen_tier == 1:
            h_tier = rng.choice(["Tier1", "Tier2", "Tier3"], p=[0.60, 0.30, 0.10])
        elif chosen_tier == 2:
            h_tier = rng.choice(["Tier1", "Tier2", "Tier3"], p=[0.20, 0.55, 0.25])
        else:
            h_tier = rng.choice(["Tier1", "Tier2", "Tier3"], p=[0.05, 0.35, 0.60])

        prefix = HOSPITAL_PREFIXES[i % len(HOSPITAL_PREFIXES)]
        suffix = rng.choice(["Hospital", "Medical Center", "Institute of Medical Sciences", "Healthcare"])
        provider_name = f"{prefix} {suffix}, {city}"

        # Network status: 85% network, 15% non-network
        net_status = "Network" if rng.random() < 0.85 else "Non-Network"

        # Beds
        if h_tier == "Tier1":
            beds = int(rng.integers(250, 1200))
            nabh = "NABH" if rng.random() < 0.75 else "None"
            rating = round(float(rng.uniform(3.8, 4.9)), 1)
        elif h_tier == "Tier2":
            beds = int(rng.integers(100, 450))
            nabh = "NABH" if rng.random() < 0.40 else "None"
            rating = round(float(rng.uniform(3.2, 4.4)), 1)
        else:
            beds = int(rng.integers(30, 180))
            nabh = "NABH" if rng.random() < 0.15 else "None"
            rating = round(float(rng.uniform(2.5, 3.9)), 1)

        specialty = rng.choice(specialties, p=specialty_probs)
        fraud_prone = 1 if i in FRAUD_PROVIDER_INDICES else 0

        provider_names.append(provider_name)
        cities.append(city)
        states.append(state)
        regions.append(region)
        hospital_tiers.append(h_tier)
        network_statuses.append(net_status)
        bed_counts.append(beds)
        specialty_focuses.append(specialty)
        avg_ratings.append(rating)
        accreditations.append(nabh)
        is_fraud_prone.append(fraud_prone)

    df = pd.DataFrame({
        "provider_id": provider_ids,
        "provider_name": provider_names,
        "city": cities,
        "state": states,
        "region": regions,
        "hospital_tier": hospital_tiers,
        "network_status": network_statuses,
        "bed_count": bed_counts,
        "specialty_focus": specialty_focuses,
        "avg_rating": avg_ratings,
        "accreditation": accreditations,
        "is_fraud_prone": is_fraud_prone,  # internal helper for fraud injection
    })

    return df
