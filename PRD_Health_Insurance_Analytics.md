# PRD: Health Insurance Analytics Platform (End-to-End Data Analytics Project)

**Document owner:** Project author (portfolio project)
**Intended executor:** Antigravity agent (autonomous build)
**Status:** Ready for build
**Version:** 1.0

---

## 0. How the Agent Should Use This Document

1. Read the entire PRD before writing any code.
2. Build in the order of the milestones in Section 12. Do not skip ahead.
3. After each milestone, run its acceptance checks (Section 13) and fix failures before moving on.
4. Where this PRD is ambiguous, choose the simplest option that satisfies the acceptance criteria, and record the decision in `docs/DECISIONS.md`.
5. Do not use paid services or external APIs. Everything must run locally on a laptop with `pip install -r requirements.txt`.
6. Do not leave placeholder code, `TODO`s, or fake numbers in the final deliverable. Every number shown in the dashboard and README must be computed from the data.
7. Make the project reproducible: one command regenerates everything from scratch (`make all`).

---

## 1. Project Summary

Build a complete, portfolio-grade analytics project for a **health insurance company**. The project covers the full data lifecycle: synthetic data generation, a warehouse with a clean schema, SQL analytics, exploratory analysis, three machine learning models, and an interactive dashboard, plus a written insights report.

The goal is to demonstrate the skills a data analyst or analytics engineer needs in the insurance domain: data modeling, SQL, KPI definition, statistical analysis, predictive modeling, visualization, and business storytelling.

## 2. Goals and Non-Goals

### Goals
- G1. Produce a realistic, internally consistent synthetic health insurance dataset (members, policies, providers, claims, premiums).
- G2. Build a relational warehouse (star-schema style) in DuckDB with documented tables.
- G3. Compute standard insurance KPIs through reusable SQL.
- G4. Deliver exploratory analysis that surfaces real, defensible business insights.
- G5. Train and evaluate three models: claim cost prediction, claim fraud/anomaly detection, and policy lapse (churn) prediction.
- G6. Ship an interactive multi-page Streamlit dashboard.
- G7. Produce a polished README and an executive insights report that a recruiter can skim in 3 minutes.

### Non-Goals
- No real personal health data. No PII. All data is synthetic.
- No production deployment, authentication, or cloud infrastructure.
- No deep learning. Classical ML only (scikit-learn, gradient boosting).
- No claims of regulatory (IRDAI/HIPAA) compliance.

## 3. Target Audience

| Audience | What they need |
|---|---|
| Recruiters / hiring managers | A clear README, screenshots, headline insights, clean code |
| Technical interviewers | Sound schema, correct SQL, honest model evaluation, tests |
| The project author | Something they fully understand and can explain in an interview |

## 4. Business Context and Questions

The fictional company is **"MediSure Health Insurance"**, selling individual, family-floater, and group health policies in India. All monetary values are in **INR (₹)**.

The analytics must answer these business questions:

**Profitability**
- BQ1. What is the overall loss ratio, and how does it vary by plan type, age band, region, and policy year?
- BQ2. Which segments are unprofitable (loss ratio above 100%)?

**Claims**
- BQ3. What are claim frequency and severity by diagnosis category, age band, and hospital tier?
- BQ4. How long does claim settlement take, and what drives delays?
- BQ5. What is the claim rejection rate and the main rejection reasons?

**Risk and fraud**
- BQ6. Which providers or claims look anomalous (billing patterns, repeated high-value claims)?
- BQ7. Can we predict the cost of a claim or a member's annual claim cost at policy-issue time?

**Retention**
- BQ8. What is the renewal (persistency) rate, and which members are likely to lapse?
- BQ9. Does a claim experience (rejection, slow settlement) affect renewal?

**Operations**
- BQ10. How do cashless vs reimbursement claims differ in cost, turnaround, and rejection?

## 5. Technology Stack (Fixed)

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Data generation | numpy, pandas, faker (locale `en_IN`), seeded RNG |
| Warehouse | DuckDB (single file `data/warehouse/medisure.duckdb`) |
| SQL | DuckDB SQL, stored as `.sql` files in `sql/` |
| Analysis | pandas, scipy, statsmodels |
| ML | scikit-learn, xgboost or lightgbm (pick one, document why), shap (optional) |
| Visualization | plotly (dashboard), matplotlib/seaborn (static report figures) |
| Dashboard | Streamlit (multi-page) |
| Testing | pytest, plus data quality checks |
| Task runner | Makefile |
| Style | ruff + black, type hints on public functions |

If a package is unavailable in the build environment, use the closest standard alternative and log it in `docs/DECISIONS.md`.

## 6. Repository Structure

```
medisure-health-insurance-analytics/
├── README.md
├── Makefile
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── config/
│   └── config.yaml                # seeds, row counts, date range, paths
├── data/
│   ├── raw/                       # generated CSVs (gitignored except small sample)
│   ├── processed/                 # cleaned/feature tables (parquet)
│   └── warehouse/                 # medisure.duckdb
├── src/
│   ├── data_generation/
│   │   ├── generate_members.py
│   │   ├── generate_policies.py
│   │   ├── generate_providers.py
│   │   ├── generate_claims.py
│   │   ├── generate_premiums.py
│   │   └── run_generation.py
│   ├── warehouse/
│   │   ├── build_warehouse.py
│   │   └── data_quality.py
│   ├── analysis/
│   │   ├── kpis.py
│   │   └── eda.py
│   ├── ml/
│   │   ├── features.py
│   │   ├── claim_cost_model.py
│   │   ├── fraud_model.py
│   │   ├── lapse_model.py
│   │   └── evaluate.py
│   └── utils/
│       ├── config.py
│       └── io.py
├── sql/
│   ├── schema.sql
│   ├── kpis/                      # one file per KPI group
│   └── analysis/                  # one file per business question
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_kpi_deep_dive.ipynb
│   └── 03_modeling.ipynb
├── dashboard/
│   ├── app.py
│   ├── pages/
│   │   ├── 1_Executive_Overview.py
│   │   ├── 2_Claims_Analysis.py
│   │   ├── 3_Risk_and_Fraud.py
│   │   ├── 4_Retention.py
│   │   └── 5_Member_Explorer.py
│   └── components/
├── models/                        # saved model artifacts (.joblib) + metrics.json
├── reports/
│   ├── figures/
│   └── executive_insights.md
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── KPI_DEFINITIONS.md
│   ├── ER_DIAGRAM.md              # mermaid diagram
│   └── DECISIONS.md
└── tests/
    ├── test_generation.py
    ├── test_warehouse.py
    ├── test_kpis.py
    └── test_models.py
```

## 7. Data Specification

### 7.1 Scale and Time Range

Configurable in `config/config.yaml`. Defaults:

| Item | Default |
|---|---|
| Members | 50,000 |
| Policies | ~42,000 |
| Providers (hospitals) | 800 |
| Claims | ~120,000 |
| Time range | 2021-01-01 to 2025-12-31 (5 policy years) |
| Random seed | 42 |

Generation must complete in under 5 minutes on a normal laptop and be fully deterministic given the seed.

### 7.2 Tables (Warehouse Schema)

Use a star-schema style with fact and dimension tables.

**dim_member**
`member_id (PK), policy_id (FK), relation (self/spouse/child/parent), gender, date_of_birth, age_at_enrollment, age_band, city, state, region (North/South/East/West/Central), city_tier (1/2/3), occupation_category, income_band, bmi, smoker_flag, pre_existing_conditions_count, has_diabetes, has_hypertension, has_cardiac_history, enrollment_date`

**dim_policy**
`policy_id (PK), plan_type (Individual/Family Floater/Group), plan_tier (Bronze/Silver/Gold/Platinum), sum_insured, annual_premium, deductible, co_pay_pct, policy_start_date, policy_end_date, policy_year, sales_channel (Agent/Online/Broker/Bancassurance), renewal_count, status (Active/Lapsed/Cancelled), lapse_date, members_covered`

**dim_provider**
`provider_id (PK), provider_name, city, state, region, hospital_tier (Tier1/Tier2/Tier3), network_status (Network/Non-Network), bed_count, specialty_focus, avg_rating, accreditation (NABH/None)`

**dim_diagnosis**
`diagnosis_id (PK), diagnosis_code (ICD-10-like), diagnosis_name, diagnosis_category (Cardiac, Oncology, Orthopedic, Maternity, Respiratory, Gastro, Infectious, Renal, Neuro, Other), severity_level (1-5), typical_los_days, typical_cost_min, typical_cost_max`

**dim_date**
`date_key, date, year, quarter, month, month_name, week, day_of_week, is_weekend, policy_year`

**fact_claims**
`claim_id (PK), member_id, policy_id, provider_id, diagnosis_id, claim_type (Cashless/Reimbursement), admission_date, discharge_date, length_of_stay, claim_submitted_date, claim_settled_date, settlement_tat_days, billed_amount, approved_amount, paid_amount, patient_paid_amount, claim_status (Approved/Partially Approved/Rejected/Pending), rejection_reason (nullable), is_emergency, is_planned, icu_days, num_procedures, is_fraud_flag (hidden ground-truth label used only for fraud model validation)`

**fact_premiums**
`premium_id (PK), policy_id, due_date, paid_date, premium_amount, payment_status (Paid/Late/Missed), payment_mode, days_late`

**fact_renewals**
`renewal_id (PK), policy_id, renewal_due_date, renewed_flag, renewal_premium, premium_change_pct, lapse_reason (nullable)`

Create appropriate primary keys, foreign keys, and indexes. Every foreign key must resolve (no orphans). Write the DDL in `sql/schema.sql`.

### 7.3 Realism Rules (Embedded Signals)

The synthetic data must contain real, discoverable relationships so the analysis and models are meaningful. Implement at least the following, and document each in `docs/DATA_DICTIONARY.md`:

1. **Age drives risk.** Claim frequency and severity increase with age, with sharply higher cardiac, oncology, and renal rates above 50.
2. **Pre-existing conditions.** Members with diabetes, hypertension, or cardiac history have 1.5x to 3x higher claim probability for related diagnoses.
3. **Smoking and BMI** raise respiratory and cardiac claim probability.
4. **Maternity claims** occur mainly for female members aged 22 to 38 and only on plans with maternity cover (Gold/Platinum), subject to a waiting period.
5. **Hospital tier.** Tier 1 (metro) hospitals have higher billed amounts for the same diagnosis (roughly 1.4x to 2x versus Tier 3).
6. **Sum insured cap.** `approved_amount` never exceeds `sum_insured`. Co-pay and deductible are applied correctly.
7. **Seasonality.** Respiratory and infectious claims peak in winter and monsoon months.
8. **Claim cost distribution** is right-skewed (log-normal-like) with a long tail of catastrophic claims.
9. **Settlement TAT.** Cashless claims settle faster (mean around 3 to 5 days) than reimbursement (mean around 12 to 20 days). Non-network hospitals and complex claims take longer.
10. **Rejections.** Overall rejection rate roughly 8 to 12%. Reasons include: waiting period violation, pre-existing disease not disclosed, documentation incomplete, treatment not covered, policy lapsed at admission. Rejection is more likely for reimbursement claims and online-channel policies with incomplete documentation.
11. **Fraud.** Inject about 2 to 3% fraudulent claims (ground-truth `is_fraud_flag`) with patterns such as: inflated billed amounts versus diagnosis norm, repeated claims from the same member within a short window, unusually short length of stay with very high bills, a small set of colluding providers (about 15 providers with elevated fraud share), admissions on weekends with round-number bills. Fraud must be detectable but not trivially so (overlap with legitimate behavior).
12. **Lapse and renewal.** Renewal probability falls with: premium increase above 15%, a rejected claim, slow settlement (above 20 days), late premium payments, younger age with no claims (low perceived value), and online channel. Renewal rises with Platinum tier and a recent approved claim with fast settlement. Overall annual renewal rate roughly 78 to 88%.
13. **Premium adequacy.** Create a mix of profitable and unprofitable segments. The overall loss ratio should land between 70% and 95%, with some segments (for example older members on low-premium plans in specific regions) above 100%.
14. **Missing data and noise.** Introduce a small realistic amount of messiness in the **raw** layer only (for example 1 to 2% nulls in `bmi` and `income_band`, a few inconsistent city name spellings, some duplicate claim rows). The warehouse build must clean these and log what was fixed.

### 7.4 Data Layers

- **Raw** (`data/raw/*.csv`): as generated, including the injected messiness.
- **Warehouse** (DuckDB): cleaned, typed, constrained, and deduplicated.
- **Processed** (`data/processed/*.parquet`): feature tables for ML.

## 8. KPI Definitions

Document every KPI precisely in `docs/KPI_DEFINITIONS.md` and implement each as parameterized SQL in `sql/kpis/`. Every KPI must be sliceable by plan type, plan tier, age band, region, city tier, sales channel, and policy year where meaningful.

| KPI | Definition |
|---|---|
| Earned premium | Premium attributable to the elapsed portion of the policy in the period |
| Incurred claims | Paid + approved-pending claim amounts in the period |
| Loss ratio (Incurred Claim Ratio) | Incurred claims / Earned premium |
| Claim frequency | Number of claims / Member-years of exposure |
| Claim severity | Average paid amount per claim |
| Pure premium | Incurred claims / Member-years |
| Claim settlement ratio | Approved (including partial) claims / Total decided claims |
| Rejection rate | Rejected claims / Total decided claims |
| Avg settlement TAT | Mean days from submission to settlement |
| Cashless share | Cashless claims / Total claims |
| Persistency (renewal rate) | Renewed policies / Policies due for renewal |
| Lapse rate | 1 - Persistency |
| Avg premium per member | Annual premium / Members covered |
| Provider concentration | Share of total claim cost from the top 10 providers |
| High-value claim share | Share of claims above the 95th percentile of billed amount |

Handle exposure correctly: partial-year policies must use pro-rated member-years, not a flat count. This is a common source of mistakes, so write a unit test for it.

## 9. Analysis Requirements

### 9.1 SQL Analytics (`sql/analysis/`)
Write at least 15 well-commented queries that answer BQ1 to BQ10. Must collectively demonstrate: CTEs, window functions (ranking, running totals, LAG for year-over-year), conditional aggregation, cohort analysis (policy-year renewal cohorts), percentile calculations, and a self-join or anti-join (for example members with repeat claims within 90 days).

### 9.2 Exploratory Data Analysis (`notebooks/01_eda.ipynb`, `src/analysis/eda.py`)
- Data profiling: shapes, dtypes, null rates, duplicates, and the cleaning log.
- Univariate and bivariate analysis of key variables.
- Claim cost distribution, log transform, outlier treatment, with justification.
- Correlation analysis and categorical association (for example Cramér's V).
- Statistical tests with interpretation: for example a t-test or Mann-Whitney U on cashless vs reimbursement TAT, chi-square on rejection by channel, ANOVA/Kruskal-Wallis on severity by hospital tier. Report effect sizes, not only p-values.
- At least 12 publication-quality static figures saved to `reports/figures/`.

### 9.3 KPI Deep Dive (`notebooks/02_kpi_deep_dive.ipynb`)
- Loss ratio waterfall by segment.
- Year-over-year trend with the drivers of change.
- Identification of the top 5 unprofitable segments with a recommended action for each (repricing, underwriting rule, network action).

## 10. Machine Learning Requirements

For every model: define the target, build leakage-free features, use a proper split, compare against a baseline, tune lightly, evaluate honestly, and save the artifact plus metrics.

### 10.1 Model A: Claim Cost Prediction (Regression)
- **Target:** `log1p(paid_amount)` at claim level. Report metrics back-transformed to ₹.
- **Features:** member demographics and health attributes, plan and policy attributes, diagnosis category, hospital tier, claim type, emergency flag, planned flag. **Exclude** anything only known after the claim (settlement date, approved amount, discharge-derived fields if unknown at prediction time). Document the prediction time assumption.
- **Baselines:** global mean and a diagnosis-category mean.
- **Models:** Ridge regression and a gradient boosted model.
- **Metrics:** MAE, RMSE, R², MAPE or sMAPE, and a calibration plot (predicted vs actual by decile).
- **Split:** time-based (train on 2021 to 2024, test on 2025).
- **Explainability:** feature importance and SHAP summary if shap is available.

### 10.2 Model B: Fraud / Anomaly Detection (Classification)
- **Target:** `is_fraud_flag`. Heavily imbalanced (about 2 to 3%).
- **Features:** billed amount relative to the diagnosis norm (z-score or ratio), length of stay vs expected, claim count by the member in the trailing 90 days, provider fraud-rate proxy computed **only from training data**, weekend admission, round-number flag, ICU days relative to LOS.
- **Approach:** supervised gradient boosting with class weighting, plus an unsupervised Isolation Forest as a comparison.
- **Metrics:** PR-AUC (primary), ROC-AUC, precision and recall at a chosen operating threshold, a confusion matrix, and a **cost-based threshold analysis** (assume investigating a claim costs ₹2,000 and a missed fraud costs its billed amount; show the net savings curve).
- **Do not** report accuracy as a headline metric. Explain why.

### 10.3 Model C: Policy Lapse Prediction (Classification)
- **Target:** `renewed_flag == 0` at renewal.
- **Features:** premium change %, claims count and rejection history, average settlement TAT experienced, late payment count, tenure, plan tier, channel, age band, city tier.
- **Split:** by renewal date (time-based).
- **Metrics:** ROC-AUC, PR-AUC, lift/gain chart, calibration, and a retention-targeting simulation (if we contact the top 20% highest-risk members, what share of lapses do we reach).
- **Output:** a scored table `data/processed/lapse_scores.parquet` consumed by the dashboard.

### 10.4 General ML Rules
- Fix all random seeds. Use scikit-learn `Pipeline` and `ColumnTransformer` so preprocessing is inside the CV loop.
- No target leakage. Add a `tests/test_models.py` check that excluded columns are absent from the feature matrix.
- Save `models/metrics.json` containing the metrics of all models, and `models/*.joblib`.
- Write a short "Model card" section per model in the README (purpose, data, metrics, limitations).

## 11. Dashboard Requirements (Streamlit)

Multi-page app launched with `streamlit run dashboard/app.py`. Reads from DuckDB and the processed parquet files. Must be fast (cache queries with `st.cache_data`).

**Global:** sidebar filters for policy year, plan type, region, and sales channel, applied across pages. Consistent color theme. Every chart has a title, axis labels with units (₹), and tooltips.

| Page | Contents |
|---|---|
| 1. Executive Overview | KPI cards (premium, incurred claims, loss ratio, settlement ratio, persistency) with YoY delta; loss ratio trend; loss ratio by plan tier; top 5 unprofitable segments table |
| 2. Claims Analysis | Frequency and severity by diagnosis category; claim cost distribution; TAT by claim type; rejection reasons breakdown; seasonality heatmap (month × diagnosis category) |
| 3. Risk and Fraud | Provider risk ranking; scatter of billed vs expected cost with flagged claims; fraud model score distribution; threshold slider showing precision/recall/net savings; list of top suspicious claims |
| 4. Retention | Renewal cohort heatmap; lapse drivers; lapse risk score distribution; table of top at-risk policies with a download button (CSV) |
| 5. Member Explorer | Select a member or policy ID to see profile, claim history timeline, predicted risk, and predicted lapse probability |

Include an "About / Methodology" expander on each page explaining the metric definitions in plain language. Export a screenshot of each page to `reports/figures/dashboard_*.png` (document the manual step if automated capture is not possible).

## 12. Milestones (Build Order)

| # | Milestone | Deliverables |
|---|---|---|
| M0 | Scaffold | Repo structure, `requirements.txt`, `Makefile`, config, lint setup, `.gitignore` |
| M1 | Data generation | All generators, `run_generation.py`, raw CSVs, `DATA_DICTIONARY.md`, generation tests |
| M2 | Warehouse | `schema.sql`, `build_warehouse.py`, cleaning log, `data_quality.py`, `ER_DIAGRAM.md`, warehouse tests |
| M3 | KPIs and SQL | KPI SQL files, `KPI_DEFINITIONS.md`, 15+ analysis queries, KPI tests |
| M4 | EDA | `eda.py`, EDA notebook, 12+ figures, statistical tests |
| M5 | ML | Feature pipelines, three models, metrics, saved artifacts, lapse scores, model tests |
| M6 | Dashboard | Five-page Streamlit app wired to real data |
| M7 | Reporting | `executive_insights.md`, final README with screenshots, `DECISIONS.md`, cleanup |

## 13. Acceptance Criteria

### Data and Warehouse
- AC1. `make data` regenerates all raw data deterministically (running twice with the same seed gives identical checksums).
- AC2. Zero orphan foreign keys in the warehouse. Zero duplicate primary keys.
- AC3. `approved_amount <= sum_insured` and `paid_amount <= approved_amount` for 100% of claims.
- AC4. `claim_settled_date >= claim_submitted_date >= discharge_date` for all settled claims.
- AC5. Overall loss ratio is between 70% and 95%, rejection rate between 8% and 12%, fraud share between 2% and 3%, renewal rate between 78% and 88%.
- AC6. The data cleaning log lists every correction with counts.

### Analytics
- AC7. All KPIs in Section 8 are implemented in SQL and match a pandas re-computation within a tolerance of 0.01%.
- AC8. Pro-rated exposure is tested with at least three edge cases (mid-year start, mid-year lapse, full year).
- AC9. At least 15 SQL analysis queries run without error and each has a header comment stating the business question.
- AC10. The executive report states at least 8 insights, each with a number, a chart reference, and a recommended action.

### ML
- AC11. All three models beat their baselines on the held-out time-based test set. If a model does not, document why honestly rather than hiding it.
- AC12. The fraud model reports PR-AUC and the cost-based threshold analysis.
- AC13. No leakage test passes. Time-based splits are used where specified.
- AC14. `models/metrics.json` exists and the README table is generated from it, not typed by hand.

### Dashboard
- AC15. `streamlit run dashboard/app.py` starts with no errors and all five pages render with the sidebar filters affecting the charts.
- AC16. Initial page load under 5 seconds on the default dataset (using caching).

### Engineering
- AC17. `make all` runs: generate data, build the warehouse, compute KPIs, run EDA, train the models, and run the tests, with exit code 0.
- AC18. `pytest` passes. `ruff check` is clean.
- AC19. README contains: project overview, business problem, architecture diagram, how to run in under 5 commands, key insights with screenshots, model cards, tech stack, project structure, limitations, and future work.

## 14. Makefile Targets

```
make setup       # create venv, install requirements
make data        # generate raw data
make warehouse   # build and validate DuckDB warehouse
make kpis        # run KPI SQL and export summary tables
make eda         # run EDA scripts and save figures
make models      # train and evaluate all models
make dashboard   # launch Streamlit
make test        # pytest + ruff
make all         # data -> warehouse -> kpis -> eda -> models -> test
make clean       # remove generated artifacts
```

## 15. Documentation Requirements

- `README.md` written for a recruiter: lead with the problem and the top 3 insights, then the architecture, then how to run.
- `docs/DATA_DICTIONARY.md`: every table and column, type, description, and the embedded realism rules.
- `docs/KPI_DEFINITIONS.md`: formula, SQL file reference, and interpretation for each KPI.
- `docs/ER_DIAGRAM.md`: a Mermaid ER diagram of the warehouse.
- `docs/DECISIONS.md`: a log of every assumption and ambiguity resolution.
- `reports/executive_insights.md`: a 2 to 3 page business-style summary with figures, written for a non-technical insurance executive.

## 16. Quality and Honesty Standards

- Never fabricate results. All numbers in the README, report, and dashboard come from executed code.
- State clearly in the README that the data is **synthetic** and that findings reflect the simulation's design, not real-world facts. Frame the project as demonstrating method and capability.
- Where a model performs unrealistically well, because the synthetic signal is clean, note this under limitations.
- Keep code readable: small functions, docstrings, type hints, no dead code.
- Keep notebooks clean: executed top to bottom, with markdown commentary between cells explaining the why.

## 17. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Synthetic data too clean, so the models look unrealistically good | Inject noise, overlapping distributions, and missing values; discuss in limitations |
| Time leakage in features | Time-based splits; compute aggregates using only prior data; leakage test |
| Wrong exposure maths inflates or deflates frequency | Pro-rated member-years plus unit tests |
| Dashboard is slow | DuckDB plus `st.cache_data`; pre-aggregated summary tables |
| Scope creep | Follow milestones strictly; log extras in "Future Work" |

## 18. Future Work (Do Not Build Now)

- Time-series forecasting of monthly claims and reserves.
- Customer segmentation (clustering) for product design.
- Pricing model (GLM frequency-severity) for premium adequacy.
- Orchestration with Airflow or Prefect, and dbt for the transformation layer.
- Deployment to Streamlit Community Cloud.

## 19. Definition of Done

The project is done when a stranger can clone the repository, run `make setup && make all && make dashboard`, and within 10 minutes see a working dashboard, read an executive report with real insights, and verify that the tests pass, with every claim in the README traceable to code in the repo.
