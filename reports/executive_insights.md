# Executive Insights Report: MediSure Health Insurance Analytics

**Prepared for:** Executive Leadership & Underwriting Committee, MediSure Health Insurance  
**Evaluation Period:** 2021-01-01 to 2025-12-31 (5 Policy Years)  
**Data Portfolio:** 50,000 Insured Members | 42,000 Policies | 800 Network Providers | 120,000 Claims  
**Author:** MediSure Analytics Engineering & Actuarial Data Science Team  

---

## Executive Summary

Over the 5-year observation period, MediSure collected **₹392.9 Crore** in earned premiums and incurred **₹358.4 Crore** across 120,000 hospitalization claims, resulting in an overall portfolio **Incurred Claim Ratio (Loss Ratio) of 91.2%**. While the overall portfolio remains operationally stable, granular segment analytics reveal critical cross-subsidies: **Bronze plan tiers and older demographic cohorts (age 51+) operate at substantial underwriting deficits (loss ratios exceeding 110%)**, which are masked by healthy margins in Platinum corporate and young individual policies (69.1% loss ratio).

This report outlines **8 actionable strategic insights** across Underwriting, Claims Operations, Network Management, and Retention.

---

## 8 Key Business Insights & Recommended Actions

### Insight 1: Bronze Tier Structural Underwriting Deficit (108.4% Loss Ratio)
- **Data Finding**: Bronze plan policies generated ₹82.4 Crore in earned premium but accumulated ₹89.3 Crore in incurred claims, yielding an unprofitable **Incurred Claim Ratio (ICR) of 108.4%**, compared to 69.1% for Platinum and 78.5% for Gold.
- **Root Cause**: Inadequate initial base pricing for high-risk older applicants coupled with minimal deductible barriers (₹15,000) that fail to offset metro hospital inflation.
- **Chart Reference**: `reports/figures/02_loss_ratio_by_tier.png` and `reports/figures/dashboard_overview.png`
- **Recommended Action**: Implement an immediate **age-rated premium loading (+22% for policyholders age 50+)** on Bronze renewals and mandate a **15% co-pay for Tier 1 metro hospitalizations**.

---

### Insight 2: Severe Price Elasticity Trigger Point at 15% Premium Increase
- **Data Finding**: While standard renewal persistency averages **81.7%**, renewal probability drops sharply from **86.4%** (under 5% premium hikes) down to **58.2%** when renewal quotes increase by more than 15%.
- **Root Cause**: High sensitivity among younger, claim-free policyholders who perceive poor value in double-digit price increases and switch to retail competitors.
- **Chart Reference**: `reports/figures/10_retention_vs_premium_hike.png`
- **Recommended Action**: Cap standard inflation indexation at **12.5% annually**. For required actuarial increases exceeding 15%, offer multi-year lock-in discounts or voluntary deductible step-ups (e.g. ₹10k deductible for a 10% premium discount) to preserve retention.

---

### Insight 3: Reimbursement Operational Lag (17.6 vs 3.4 Days) Drives Customer Dissatisfaction
- **Data Finding**: Reimbursement claims take an average of **17.6 days** to settle compared to **3.4 days** for cashless network authorizations—a statistically significant delay (**Mann-Whitney U: $p < 10^{-10}$, Cohen's $d = 4.48$**). Furthermore, policyholders experiencing settlement turnaround times (TAT) > 20 days suffer a **14.3% lower renewal rate**.
- **Root Cause**: Physical dossier transit, manual medical audit of paper discharge summaries, and fragmented non-network billing verification.
- **Chart Reference**: `reports/figures/05_settlement_tat_comparison.png` and `reports/figures/13_cashless_vs_reimbursement_ops.png`
- **Recommended Action**: Deploy an **instant digital reimbursement OCR upload app** with automated pre-auth for bills under ₹50,000, targeting an average reimbursement TAT reduction to **< 7 days**.

---

### Insight 4: Hospital Tier 1 Metro Pricing Disparity (1.91x Multiplier vs Tier 3)
- **Data Finding**: For identical clinical diagnoses, Tier 1 metro facilities bill an average of **₹37,141** per admission versus **₹19,391** in Tier 3 facilities (**Kruskal-Wallis: $H = 4217.4, p < 10^{-10}$**), despite comparable clinical recovery length of stay (4.2 vs 3.8 days).
- **Root Cause**: Inflated room rent markups, unbundled procedure pricing, and premium diagnostics at unaccredited corporate hospitals.
- **Chart Reference**: `reports/figures/08_hospital_tier_cost_disparity.png`
- **Recommended Action**: Institute standardized **Procedure Package Rates (PPR)** across the Preferred Provider Network (PPN) and cap room rent reimbursement at 1.0% of Sum Insured per day.

---

### Insight 5: Machine Learning Fraud Detection Unlocks ₹7.46 Crore in Net Audit Savings
- **Data Finding**: Supervised gradient boosting (XGBoost) achieved a **PR-AUC of 0.7994** on held-out 2025 claims, outperforming unsupervised anomaly baselines (0.4779). At an optimal financial operating threshold of **0.66**, the model achieves **63.5% Precision and 78.1% Recall**.
- **Financial Impact**: Net financial savings of **₹74,588,133 (₹7.46 Crore)** after factoring in ₹2,000 investigation audit costs per flagged claim.
- **Chart Reference**: `reports/figures/09_provider_fraud_dispersion.png` and `reports/figures/dashboard_risk.png`
- **Recommended Action**: Embed the XGBoost fraud scoring engine directly into the claims pre-authorization adjudication workflow, automatically routing claims scored $\ge 0.66$ to the Special Investigation Unit (SIU) prior to payment disbursement.

---

### Insight 6: Concentration of Risk in Colluding Network Hospitals (15 Providers)
- **Data Finding**: A cluster of **15 specific healthcare providers** accounted for over **32% of all flagged fraudulent claims**, characterized by weekend admissions with round-number billing (e.g. exactly ₹1,50,000) and abnormally short stays ($\le 1$ day) for major surgical diagnoses.
- **Root Cause**: Collusion between corrupt billing desks and brokers submitting fabricated hospitalization dossiers.
- **Chart Reference**: `reports/figures/09_provider_fraud_dispersion.png`
- **Recommended Action**: Blacklist the top 5 offending facilities, suspend cashless empanelment for the remaining 10 pending full forensic audit, and mandate biometric patient verification upon hospital admission.

---

### Insight 7: Epidemiological Seasonality Demands Dynamic Claim Reserves (Q3/Q4 Surges)
- **Data Finding**: Inpatient admissions for respiratory and infectious diseases (Dengue, Typhoid, Viral Pneumonia) surge by **68% between July and November** (monsoon and post-monsoon quarters), creating intense seasonal cash outflow peaks in North and East regions.
- **Root Cause**: Vector-borne epidemic peaks following monsoon rains and elevated PM2.5 winter air pollution in northern urban clusters.
- **Chart Reference**: `reports/figures/07_seasonality_heatmap.png`
- **Recommended Action**: Dynamically adjust **Outstanding Claims Reserves (IBNR)** by +40% entering Q3 and pre-allocate temporary claims adjudication staff to prevent settlement backlogs.

---

### Insight 8: Pre-Existing Metabolic Conditions Drive Catastrophic Claim Costs
- **Data Finding**: Insured members with diagnosed Diabetes and Hypertension experience an annual hospitalization incidence of **31.4%** (compared to 8.2% for healthy cohorts) and an average annual claim cost of **₹42,850** (3.4x higher than the healthy baseline of ₹12,600).
- **Root Cause**: Accelerated microvascular complications leading to secondary renal failure and cardiovascular events.
- **Chart Reference**: `reports/figures/12_clinical_financial_correlation.png` and `reports/figures/04_frequency_severity_diagnosis_matrix.png`
- **Recommended Action**: Launch an active **Chronic Disease Management & Wellness Program** (subsidized HbA1c checks, digital glucometers, annual tele-consultation) incentivized with a 10% renewal premium rebate for members maintaining controlled biometric targets.

---

## Financial Summary Table

| Initiative | Target Segment | Projected Annual Impact | Timeframe |
|---|---|---|---|
| **Bronze Tier Age Repricing** | Policyholders Age 50+ on Bronze | +₹14.2 Crore Earned Premium | Q1 Next Fiscal |
| **PPR Package Caps (Tier 1)** | Metro Inpatient Procedures | -₹18.5 Crore Incurred Claims | Immediate |
| **ML Fraud Pre-auth Scoring** | Incurred Claims $\ge 0.66$ Score | +₹7.46 Crore Net Fraud Recovery | Immediate |
| **Digital Fast-Track Reimbursement** | Non-network Reimbursement Claims | +3.5% Retention (+₹8.2 Cr) | Q2 Next Fiscal |
| **Total Projected Net Profitability Impact** | **Portfolio Wide** | **+₹48.36 Crore Annual Improvement** | **12 Months** |

