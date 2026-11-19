"""
Diagnosis taxonomy generator based on ICD-10 standard categories.
Calibrated for realistic Indian health insurance claims portfolio.
"""

import pandas as pd

DIAGNOSIS_CATALOG = [
    # Cardiac
    ("DX_1001", "I21.9", "Acute Myocardial Infarction", "Cardiac", 5, 5, 42000.0, 98000.0),
    ("DX_1002", "I20.0", "Unstable Angina Pectoris", "Cardiac", 4, 3, 18000.0, 42000.0),
    ("DX_1003", "I50.9", "Congestive Heart Failure", "Cardiac", 4, 5, 22000.0, 52000.0),
    ("DX_1004", "I10.0", "Hypertensive Heart Disease / Crisis", "Cardiac", 3, 3, 10000.0, 24000.0),
    # Oncology
    ("DX_2001", "C34.9", "Malignant Neoplasm of Bronchus/Lung", "Oncology", 5, 6, 48000.0, 115000.0),
    ("DX_2002", "C50.9", "Malignant Neoplasm of Breast", "Oncology", 4, 4, 38000.0, 88000.0),
    ("DX_2003", "Z51.1", "Inpatient Chemotherapy & Targeted Therapy", "Oncology", 3, 2, 14000.0, 32000.0),
    # Orthopedic
    ("DX_3001", "M16.9", "Total Knee / Hip Arthroplasty", "Orthopedic", 4, 5, 48000.0, 96000.0),
    ("DX_3002", "S72.0", "Fracture of Femur / Major Trauma Surgery", "Orthopedic", 4, 5, 28000.0, 65000.0),
    ("DX_3003", "M54.5", "Lumbar Spine Disc Herniation / Decompression", "Orthopedic", 3, 4, 22000.0, 52000.0),
    ("DX_3004", "S82.0", "Lower Limb Fracture Reduction & Fixation", "Orthopedic", 2, 3, 12000.0, 28000.0),
    # Maternity
    ("DX_4001", "O80.0", "Single Spontaneous Delivery (Normal)", "Maternity", 2, 3, 11000.0, 26000.0),
    ("DX_4002", "O82.0", "Caesarean Section Delivery", "Maternity", 3, 4, 18000.0, 42000.0),
    ("DX_4003", "O14.9", "Pre-eclampsia with Inpatient Monitoring", "Maternity", 3, 4, 14000.0, 32000.0),
    # Respiratory
    ("DX_5001", "J18.9", "Bacterial / Viral Pneumonia", "Respiratory", 3, 4, 12000.0, 28000.0),
    ("DX_5002", "J44.1", "Chronic Obstructive Pulmonary Disease (COPD)", "Respiratory", 4, 4, 15000.0, 36000.0),
    ("DX_5003", "J45.9", "Severe Acute Asthma Exacerbation", "Respiratory", 2, 2, 8000.0, 18000.0),
    # Gastro
    ("DX_6001", "K35.8", "Acute Appendicitis with Appendectomy", "Gastro", 3, 3, 15000.0, 34000.0),
    ("DX_6002", "K80.2", "Calculus of Gallbladder (Laparoscopic)", "Gastro", 3, 3, 18000.0, 40000.0),
    ("DX_6003", "K26.9", "Acute Duodenal Ulcer with Hemorrhage", "Gastro", 4, 3, 14000.0, 32000.0),
    # Infectious
    ("DX_7001", "A90.0", "Dengue Fever with Thrombocytopenia", "Infectious", 2, 3, 9000.0, 22000.0),
    ("DX_7002", "A01.0", "Typhoid Fever with Complications", "Infectious", 2, 3, 8000.0, 20000.0),
    ("DX_7003", "U07.1", "Acute Respiratory Viral Infection / COVID-19", "Infectious", 4, 5, 18000.0, 48000.0),
    # Renal
    ("DX_8001", "N18.9", "Chronic Kidney Disease Stage 5 / Dialysis", "Renal", 4, 3, 14000.0, 36000.0),
    ("DX_8002", "N20.1", "Ureteric Calculus with Laser Lithotripsy", "Renal", 2, 2, 12000.0, 28000.0),
    # Neuro
    ("DX_9001", "I63.9", "Cerebral Infarction / Ischemic Stroke", "Neuro", 5, 6, 45000.0, 110000.0),
    ("DX_9002", "G40.9", "Status Epilepticus / Intractable Seizures", "Neuro", 3, 3, 14000.0, 32000.0),
    # Other
    ("DX_0001", "H26.9", "Senile Cataract with Phacoemulsification", "Other", 1, 1, 9000.0, 20000.0),
    ("DX_0002", "L03.9", "Severe Cellulitis & Soft Tissue Infection", "Other", 2, 3, 10000.0, 22000.0),
]


def generate_diagnoses() -> pd.DataFrame:
    """Generate the standardized ICD-10 diagnosis dimension dataframe."""
    columns = [
        "diagnosis_id", "diagnosis_code", "diagnosis_name", "diagnosis_category",
        "severity_level", "typical_los_days", "typical_cost_min", "typical_cost_max"
    ]
    return pd.DataFrame(DIAGNOSIS_CATALOG, columns=columns)
