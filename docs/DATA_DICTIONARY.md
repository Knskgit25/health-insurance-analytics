# MediSure Health Insurance Analytics - Data Dictionary

This document details the schema of all raw and warehouse tables, their columns, data types, definitions, and the embedded realism rules implemented in the synthetic data generator.

---

## 1. Warehouse Tables & Column Definitions

### 1.1 `dim_member`
Stores demographic, socioeconomic, and baseline clinical attributes of insured members.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `member_id` | VARCHAR (PK) | No | Unique identifier for the member (`MEM_XXXXXX`) |
| `policy_id` | VARCHAR (FK) | No | Policy under which the member is covered (`POL_XXXXXX`) |
| `relation` | VARCHAR | No | Relation to primary policyholder (`Self`, `Spouse`, `Child`, `Parent`) |
| `gender` | VARCHAR | No | Member gender (`Male`, `Female`, `Other`) |
| `date_of_birth` | DATE | No | Date of birth |
| `age_at_enrollment`| INTEGER | No | Age in years at initial policy enrollment |
| `age_band` | VARCHAR | No | Age bracket (`0-18`, `19-35`, `36-50`, `51-65`, `65+`) |
| `city` | VARCHAR | No | Residential city (cleaned to standard casing) |
| `state` | VARCHAR | No | Indian State / UT |
| `region` | VARCHAR | No | Geographic zone (`North`, `South`, `East`, `West`, `Central`) |
| `city_tier` | INTEGER | No | Urbanization tier (`1`, `2`, `3`) |
| `occupation_category`| VARCHAR | No | Employment type (`Salaried`, `Self-Employed`, `Professional`, `Student`, `Retired`, `Homemaker`) |
| `income_band` | VARCHAR | Yes (in raw) | Annual household income bracket (`<3L`, `3L-7L`, `7L-15L`, `15L-25L`, `25L+`) |
| `bmi` | DOUBLE | Yes (in raw) | Body Mass Index (kg/m²) |
| `smoker_flag` | INTEGER | No | Smoking status (`1` = Current/Regular Smoker, `0` = Non-Smoker) |
| `pre_existing_conditions_count` | INTEGER | No | Total count of pre-existing chronic conditions |
| `has_diabetes` | INTEGER | No | Indicator for pre-existing Type 1/2 Diabetes (`1`/`0`) |
| `has_hypertension` | INTEGER | No | Indicator for pre-existing Hypertension (`1`/`0`) |
| `has_cardiac_history` | INTEGER | No | Indicator for pre-existing cardiovascular condition (`1`/`0`) |
| `enrollment_date` | DATE | No | Date member was first enrolled |

---

### 1.2 `dim_policy`
Stores policy contracts, coverage terms, and underwriting parameters.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `policy_id` | VARCHAR (PK) | No | Unique identifier for policy contract (`POL_XXXXXX`) |
| `plan_type` | VARCHAR | No | Product structure (`Individual`, `Family Floater`, `Group`) |
| `plan_tier` | VARCHAR | No | Coverage tier (`Bronze`, `Silver`, `Gold`, `Platinum`) |
| `sum_insured` | DOUBLE | No | Maximum annual coverage liability in INR (₹) |
| `annual_premium` | DOUBLE | No | Annual policy premium charged in INR (₹) |
| `deductible` | DOUBLE | No | Annual deductible amount before insurance coverage applies |
| `co_pay_pct` | DOUBLE | No | Policyholder co-payment percentage (e.g., 0.10 for 10%) |
| `policy_start_date`| DATE | No | Start date of initial coverage |
| `policy_end_date` | DATE | No | Expiration / renewal date of policy term |
| `policy_year` | INTEGER | No | Policy year cohort (2021 to 2025) |
| `sales_channel` | VARCHAR | No | Acquisition channel (`Agent`, `Online`, `Broker`, `Bancassurance`) |
| `renewal_count` | INTEGER | No | Cumulative number of times policy has renewed |
| `status` | VARCHAR | No | Policy contract status (`Active`, `Lapsed`, `Cancelled`) |
| `lapse_date` | DATE | Yes | Date policy lapsed or was cancelled |
| `members_covered` | INTEGER | No | Number of active members covered under policy |

---

### 1.3 `dim_provider`
Healthcare network hospitals and healthcare facilities.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `provider_id` | VARCHAR (PK) | No | Unique hospital identifier (`PRV_XXXXXX`) |
| `provider_name` | VARCHAR | No | Registered hospital name |
| `city` | VARCHAR | No | City of facility |
| `state` | VARCHAR | No | State of facility |
| `region` | VARCHAR | No | Geographic zone |
| `hospital_tier` | VARCHAR | No | Facility tier (`Tier1`, `Tier2`, `Tier3`) |
| `network_status` | VARCHAR | No | Contracting status (`Network`, `Non-Network`) |
| `bed_count` | INTEGER | No | Total inpatient hospital beds |
| `specialty_focus`| VARCHAR | No | Primary medical center specialty |
| `avg_rating` | DOUBLE | No | Quality audit / patient rating (1.0 to 5.0) |
| `accreditation` | VARCHAR | No | Accreditation status (`NABH`, `None`) |

---

### 1.4 `dim_diagnosis`
Standard clinical diagnosis taxonomy and reference norms.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `diagnosis_id` | VARCHAR (PK) | No | Diagnosis code identifier (`DX_XXXX`) |
| `diagnosis_code` | VARCHAR | No | ICD-10 compatible code (e.g. `I21.9`, `C34.9`) |
| `diagnosis_name` | VARCHAR | No | Clinical clinical diagnosis description |
| `diagnosis_category`| VARCHAR | No | Broad medical category (`Cardiac`, `Oncology`, `Orthopedic`, `Maternity`, `Respiratory`, `Gastro`, `Infectious`, `Renal`, `Neuro`, `Other`) |
| `severity_level` | INTEGER | No | Severity index (1 = minor, 5 = critical) |
| `typical_los_days` | INTEGER | No | Benchmark expected length of stay in days |
| `typical_cost_min` | DOUBLE | No | Expected lower bound cost benchmark (₹) |
| `typical_cost_max` | DOUBLE | No | Expected upper bound cost benchmark (₹) |

---

### 1.5 `dim_date`
Enterprise date dimension covering 2021-01-01 to 2025-12-31.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `date_key` | DATE (PK) | No | Calendar date |
| `date` | DATE | No | Date |
| `year` | INTEGER | No | Calendar year |
| `quarter` | INTEGER | No | Calendar quarter (1-4) |
| `month` | INTEGER | No | Month number (1-12) |
| `month_name` | VARCHAR | No | Full month name (`January`..`December`) |
| `week` | INTEGER | No | ISO week number (1-53) |
| `day_of_week` | INTEGER | No | Day of week (1=Monday, 7=Sunday) |
| `is_weekend` | INTEGER | No | Weekend indicator (`1` if Saturday/Sunday, `0` otherwise) |
| `policy_year` | INTEGER | No | Corresponding policy cycle year |

---

### 1.6 `fact_claims`
Granular claim transaction table.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `claim_id` | VARCHAR (PK) | No | Unique claim transaction ID (`CLM_XXXXXXX`) |
| `member_id` | VARCHAR (FK) | No | Patient member ID |
| `policy_id` | VARCHAR (FK) | No | Insuring policy ID |
| `provider_id` | VARCHAR (FK) | No | Hospital facility ID |
| `diagnosis_id` | VARCHAR (FK) | No | Primary admitting diagnosis ID |
| `claim_type` | VARCHAR | No | Settlement mechanism (`Cashless`, `Reimbursement`) |
| `admission_date` | DATE | No | Hospital admission date |
| `discharge_date` | DATE | No | Hospital discharge date |
| `length_of_stay` | INTEGER | No | Duration of inpatient stay in days |
| `claim_submitted_date` | DATE | No | Date claim dossier submitted |
| `claim_settled_date` | DATE | Yes | Date claim was adjudicated/settled |
| `settlement_tat_days` | INTEGER | Yes | Elapsed turnaround days |
| `billed_amount` | DOUBLE | No | Gross billed charges by provider in INR |
| `approved_amount`| DOUBLE | No | Underwriting approved amount in INR |
| `paid_amount` | DOUBLE | No | Final insurer payout in INR |
| `patient_paid_amount` | DOUBLE | No | Out-of-pocket payment (co-pay + deductible + disallowed) |
| `claim_status` | VARCHAR | No | Final adjudication (`Approved`, `Partially Approved`, `Rejected`, `Pending`) |
| `rejection_reason`| VARCHAR | Yes | Specific rejection classification if rejected |
| `is_emergency` | INTEGER | No | Emergency admission flag (`1`/`0`) |
| `is_planned` | INTEGER | No | Planned elective procedure flag (`1`/`0`) |
| `icu_days` | INTEGER | No | Days spent in Intensive Care Unit |
| `num_procedures` | INTEGER | No | Count of surgical/medical procedures performed |
| `is_fraud_flag` | INTEGER | No | Ground-truth fraudulent claim indicator (`1`/`0`) |

---

### 1.7 `fact_premiums`
Monthly/annual premium billing and collection transactions.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `premium_id` | VARCHAR (PK) | No | Unique billing transaction ID (`PRM_XXXXXXX`) |
| `policy_id` | VARCHAR (FK) | No | Policy contract ID |
| `due_date` | DATE | No | Scheduled premium payment due date |
| `paid_date` | DATE | Yes | Actual receipt date of premium |
| `premium_amount` | DOUBLE | No | Scheduled premium installment amount in INR |
| `payment_status` | VARCHAR | No | Status (`Paid`, `Late`, `Missed`) |
| `payment_mode` | VARCHAR | No | Payment method (`Net Banking`, `UPI`, `Credit Card`, `Debit Card`, `Cheque`) |
| `days_late` | INTEGER | No | Number of days delayed past due date |

---

### 1.8 `fact_renewals`
Annual policy renewal and persistency events.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `renewal_id` | VARCHAR (PK) | No | Unique renewal event ID (`RNW_XXXXXXX`) |
| `policy_id` | VARCHAR (FK) | No | Policy contract ID |
| `renewal_due_date` | DATE | No | Date policy was eligible for renewal |
| `renewed_flag` | INTEGER | No | Renewal outcome indicator (`1` = Renewed, `0` = Lapsed) |
| `renewal_premium` | DOUBLE | No | Premium quote for renewed policy year |
| `premium_change_pct` | DOUBLE | No | Percentage change in premium vs preceding year |
| `lapse_reason` | VARCHAR | Yes | Root cause rationale if policy lapsed |

---

## 2. Embedded Realism Signals (Synthetic Data Physics)

The data generation engine embeds 14 deterministic business rules specified in PRD Section 7.3:

1. **Age Risk Curve**: Claim probability scales with age via logistic hazard function; members over 50 exhibit 3.5x higher cardiac, oncology, and renal incidence rates.
2. **Pre-Existing Disease Multipliers**: Members with diagnosed diabetes, hypertension, or cardiac history experience a 2.2x to 3.0x multiplier on cardiovascular and renal hospitalization incidence.
3. **Lifestyle Modifiers**: Smokers and members with BMI > 30 experience an elevated hazard ratio (1.8x) for respiratory and cardiac conditions.
4. **Maternity Rules**: Maternity claims are restricted strictly to female policyholders aged 22–38 holding Gold or Platinum tiers, respecting a mandatory 9-month waiting period from initial enrollment.
5. **Hospital Tier Multipliers**: Billed charges for identical diagnoses at Tier 1 (metro) facilities scale 1.6x – 2.0x higher than Tier 3 facilities.
6. **Financial Waterfall Consistency**: Strict invariant enforcement:
   $$\text{approved\_amount} \le \text{sum\_insured}$$
   $$\text{paid\_amount} \le \text{approved\_amount}$$
   $$\text{patient\_paid\_amount} = \text{billed\_amount} - \text{paid\_amount}$$
   Co-pays and deductibles are subtracted strictly from approved claims.
7. **Epidemiological Seasonality**: Respiratory and infectious disease claims surge in Q3 (monsoon) and Q4 (winter) in North and East regions.
8. **Log-Normal Skewed Claim Severity**: Claim billed amounts follow a calibrated log-normal distribution with fat tails, generating realistic catastrophic claims up to policy limits.
9. **Turnaround Time (TAT) Dynamics**:
   - Cashless claims: Mean TAT 3.8 days ($\sigma = 1.8$).
   - Reimbursement claims: Mean TAT 15.6 days ($\sigma = 4.5$). Non-network hospitals incur an additional 4–7 day delay.
10. **Claim Repudiation Mechanics**: Target 8%–12% rejection rate driven by waiting period non-compliance, non-disclosure of pre-existing conditions, unlisted procedures, and policy lapses.
11. **Fraud / Anomaly Patterns**: Injected at 2.4% rate, characterized by:
    - Billed amount z-score > 3.0 relative to diagnosis mean.
    - Abnormally short LOS (<= 1 day) with extreme billed amounts.
    - Provider collusion: 15 specific network hospitals with 30%+ fraud incidence.
    - Weekend admission dates paired with round-number bills (e.g., ₹1,50,000 exactly).
    - Repeat claims from the same member within 90 days.
12. **Renewal & Persistency Physics**: Policy renewal probability responds dynamically to:
    - Premium hikes > 15% (-22% renewal odds).
    - Recent claim repudiation (-35% renewal odds).
    - Settlement TAT > 20 days (-18% renewal odds).
    - Late premium payment history (-15% renewal odds).
    - Baseline renewal rate lands between 78% and 88%.
13. **Segment Profitability**: Overall portfolio loss ratio calibrated between 70% and 95%. Older cohorts on low-premium Bronze plans in specific Tier 2/3 clusters intentionally exceed 100% loss ratio.
14. **Raw Data Messiness & Ingestion Cleaning**:
    - Raw CSVs contain ~1.5% missing BMI/income band values, slight casing/whitespace variations in city names, and 0.2% injected duplicate claim rows.
    - The warehouse build cleans, standardizes, imputes median values, deduplicates, and logs all cleaning actions.

