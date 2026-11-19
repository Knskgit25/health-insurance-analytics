# Architectural and Implementation Decisions

This document records key decisions, assumptions, and ambiguity resolutions made during the design and implementation of the **MediSure Health Insurance Analytics Platform**, in compliance with Section 0 and Section 15 of the PRD.

---

## 1. Tooling and Runtime Environment

- **Python Version**: Python 3.12+ (Windows x64 runtime).
- **Build / Task Runner**:
  - A standard POSIX-compliant `Makefile` is provided for Linux/macOS/Git Bash users.
  - To support native Windows PowerShell where GNU `make` is typically not present, a companion `make.py` script (`python make.py <target>`) is provided with identical targets (`setup`, `data`, `warehouse`, `kpis`, `eda`, `models`, `dashboard`, `test`, `all`, `clean`).
- **Warehouse Engine**: DuckDB 1.x / 2.x embedded database. Storage file: `data/warehouse/medisure.duckdb`.
- **Gradient Boosting Engine**: XGBoost is chosen as the primary gradient boosting engine due to superior native handling of class weights, deterministic seeding, and compatibility with scikit-learn pipelines.
- **Unsupervised Anomaly Detection Baseline**: Under Windows Application Control, certain `.pyd` dynamic libraries (e.g. `sklearn.ensemble._bitset`) are restricted by system AppLocker policies. In strict adherence to PRD Section 5 ("use the closest standard alternative and log it in docs/DECISIONS.md"), an unsupervised Multivariate Standardized Z-Score Anomaly Detector is implemented as the unsupervised anomaly baseline.
- **Parquet Storage Engine**: Under Windows Application Control, pyarrow's native `_parquet.pyd` DLL is restricted. DuckDB's embedded C++ engine provides native, compliant Apache Parquet reading and writing without requiring external blocked DLLs. All parquet I/O is routed through DuckDB in `src/utils/io.py`.

---

## 2. Synthetic Data Generation and Calibration

- **Determinism**: Fully deterministic using a fixed random seed (`seed=42`) across NumPy, Faker (locale `en_IN`), and Python `random`.
- **Performance**: Vectorized generation with NumPy and Pandas to ensure all ~50,000 members, ~42,000 policies, 800 providers, and ~120,000 claims generate in under 2 minutes.
- **Realistic Signals Calibration**:
  - Target loss ratio (Incurred Claim Ratio): 70% – 95% overall, with older members (55+) on low-premium / Bronze tiers exceeding 100%.
  - Rejection rate: 8% – 12% overall, driven by waiting periods, undisclosed pre-existing conditions, incomplete documentation, and policy lapse.
  - Fraud / Anomaly share: 2% – 3% overall with injected patterns (colluding providers, excessive length-of-stay vs diagnosis norms, round-number bill amounts, high-frequency repeat claims within 90 days).
  - Renewal (persistency) rate: 78% – 88% overall, sensitive to premium hike (>15%), claim rejections, and settlement turnaround delays.
- **Raw Layer Noise**:
  - Injected realistic dirty data in raw CSVs: 1.5% nulls in `bmi` and `income_band`, occasional duplicate claim rows, whitespace and minor case inconsistencies in city names.
  - The warehouse ingestion pipeline (`build_warehouse.py`) detects, cleans, deduplicates, and logs every fix to `data/warehouse/cleaning_log.json`.

---

## 3. Warehouse Modeling and SQL Analytics

- **Schema Design**: Star schema with dimension tables (`dim_member`, `dim_policy`, `dim_provider`, `dim_diagnosis`, `dim_date`) and fact tables (`fact_claims`, `fact_premiums`, `fact_renewals`).
- **Exposure Calculation**: Member-years of exposure are computed on a pro-rated daily basis (`(LEAST(policy_end_date, period_end) - GREATEST(policy_start_date, period_start) + 1) / 365.25`) to accurately calculate Pure Premium and Claim Frequency without flat-count distortion.
- **DuckDB Dialect**: All SQL files in `sql/` use ANSI SQL compatible with DuckDB, leveraging Common Table Expressions (CTEs), window functions (`LAG`, `ROW_NUMBER`, `DENSE_RANK`), and conditional aggregation.

---

## 4. Machine Learning Methodology

- **Time-Based Splits**:
  - Claim Cost Model: Train on claims submitted 2021-01-01 through 2024-12-31; held-out test on claims submitted 2025-01-01 through 2025-12-31.
  - Fraud Detection Model: Train on 2021–2024; test on 2025. Provider historical fraud rate proxy is computed strictly on training data to prevent data leakage.
  - Lapse Prediction Model: Train on renewal dates 2021–2024; test on 2025.
- **Evaluation & Honesty**:
  - Fraud detection prioritizes PR-AUC and Net Financial Savings over misleading raw accuracy.
  - All metrics are saved to `models/metrics.json` and dynamically loaded into the README and dashboard.
