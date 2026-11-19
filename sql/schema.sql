-- MediSure Health Insurance Analytics - Warehouse DDL
-- Target Engine: DuckDB 1.x / 2.x

-- 1. Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR NOT NULL,
    week INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL,
    policy_year INTEGER NOT NULL
);

-- 2. Healthcare Provider Dimension
CREATE TABLE IF NOT EXISTS dim_provider (
    provider_id VARCHAR PRIMARY KEY,
    provider_name VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    hospital_tier VARCHAR NOT NULL,
    network_status VARCHAR NOT NULL,
    bed_count INTEGER NOT NULL,
    specialty_focus VARCHAR NOT NULL,
    avg_rating DOUBLE NOT NULL,
    accreditation VARCHAR NOT NULL
);

-- 3. Clinical Diagnosis Dimension
CREATE TABLE IF NOT EXISTS dim_diagnosis (
    diagnosis_id VARCHAR PRIMARY KEY,
    diagnosis_code VARCHAR NOT NULL,
    diagnosis_name VARCHAR NOT NULL,
    diagnosis_category VARCHAR NOT NULL,
    severity_level INTEGER NOT NULL,
    typical_los_days INTEGER NOT NULL,
    typical_cost_min DOUBLE NOT NULL,
    typical_cost_max DOUBLE NOT NULL
);

-- 4. Policy Contract Dimension
CREATE TABLE IF NOT EXISTS dim_policy (
    policy_id VARCHAR PRIMARY KEY,
    plan_type VARCHAR NOT NULL,
    plan_tier VARCHAR NOT NULL,
    sum_insured DOUBLE NOT NULL,
    annual_premium DOUBLE NOT NULL,
    deductible DOUBLE NOT NULL,
    co_pay_pct DOUBLE NOT NULL,
    policy_start_date DATE NOT NULL,
    policy_end_date DATE NOT NULL,
    policy_year INTEGER NOT NULL,
    sales_channel VARCHAR NOT NULL,
    renewal_count INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    lapse_date DATE,
    members_covered INTEGER NOT NULL
);

-- 5. Member Dimension
CREATE TABLE IF NOT EXISTS dim_member (
    member_id VARCHAR PRIMARY KEY,
    policy_id VARCHAR NOT NULL REFERENCES dim_policy(policy_id),
    relation VARCHAR NOT NULL,
    gender VARCHAR NOT NULL,
    date_of_birth DATE NOT NULL,
    age_at_enrollment INTEGER NOT NULL,
    age_band VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    city_tier INTEGER NOT NULL,
    occupation_category VARCHAR NOT NULL,
    income_band VARCHAR NOT NULL,
    bmi DOUBLE NOT NULL,
    smoker_flag INTEGER NOT NULL,
    pre_existing_conditions_count INTEGER NOT NULL,
    has_diabetes INTEGER NOT NULL,
    has_hypertension INTEGER NOT NULL,
    has_cardiac_history INTEGER NOT NULL,
    enrollment_date DATE NOT NULL
);

-- 6. Claim Transactions Fact
CREATE TABLE IF NOT EXISTS fact_claims (
    claim_id VARCHAR PRIMARY KEY,
    member_id VARCHAR NOT NULL REFERENCES dim_member(member_id),
    policy_id VARCHAR NOT NULL REFERENCES dim_policy(policy_id),
    provider_id VARCHAR NOT NULL REFERENCES dim_provider(provider_id),
    diagnosis_id VARCHAR NOT NULL REFERENCES dim_diagnosis(diagnosis_id),
    claim_type VARCHAR NOT NULL,
    admission_date DATE NOT NULL,
    discharge_date DATE NOT NULL,
    length_of_stay INTEGER NOT NULL,
    claim_submitted_date DATE NOT NULL,
    claim_settled_date DATE,
    settlement_tat_days INTEGER,
    billed_amount DOUBLE NOT NULL,
    approved_amount DOUBLE NOT NULL,
    paid_amount DOUBLE NOT NULL,
    patient_paid_amount DOUBLE NOT NULL,
    claim_status VARCHAR NOT NULL,
    rejection_reason VARCHAR,
    is_emergency INTEGER NOT NULL,
    is_planned INTEGER NOT NULL,
    icu_days INTEGER NOT NULL,
    num_procedures INTEGER NOT NULL,
    is_fraud_flag INTEGER NOT NULL
);

-- 7. Premium Transactions Fact
CREATE TABLE IF NOT EXISTS fact_premiums (
    premium_id VARCHAR PRIMARY KEY,
    policy_id VARCHAR NOT NULL REFERENCES dim_policy(policy_id),
    due_date DATE NOT NULL,
    paid_date DATE,
    premium_amount DOUBLE NOT NULL,
    payment_status VARCHAR NOT NULL,
    payment_mode VARCHAR NOT NULL,
    days_late INTEGER NOT NULL
);

-- 8. Policy Renewal Fact
CREATE TABLE IF NOT EXISTS fact_renewals (
    renewal_id VARCHAR PRIMARY KEY,
    policy_id VARCHAR NOT NULL REFERENCES dim_policy(policy_id),
    renewal_due_date DATE NOT NULL,
    renewed_flag INTEGER NOT NULL,
    renewal_premium DOUBLE NOT NULL,
    premium_change_pct DOUBLE NOT NULL,
    lapse_reason VARCHAR
);

-- Analytical Indexes
CREATE INDEX IF NOT EXISTS idx_claims_member ON fact_claims(member_id);
CREATE INDEX IF NOT EXISTS idx_claims_policy ON fact_claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_provider ON fact_claims(provider_id);
CREATE INDEX IF NOT EXISTS idx_claims_diagnosis ON fact_claims(diagnosis_id);
CREATE INDEX IF NOT EXISTS idx_claims_admission ON fact_claims(admission_date);
CREATE INDEX IF NOT EXISTS idx_claims_status ON fact_claims(claim_status);
CREATE INDEX IF NOT EXISTS idx_premiums_policy ON fact_premiums(policy_id);
CREATE INDEX IF NOT EXISTS idx_renewals_policy ON fact_renewals(policy_id);
CREATE INDEX IF NOT EXISTS idx_member_policy ON dim_member(policy_id);

