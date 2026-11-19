# MediSure Health Insurance Analytics - KPI Definitions

This document details the definition, mathematical formulation, SQL implementation, and business interpretation of every standard insurance KPI implemented in the MediSure Health Insurance Analytics platform.

---

## 1. Profitability & Underwriting KPIs

### 1.1 Earned Premium
- **Definition**: The portion of the written annual premium attributable to the elapsed coverage time within the measurement period.
- **Formula**:
  $$\text{Earned Premium} = \sum_{\text{policies}} \text{Annual Premium} \times \frac{\text{Exposure Days in Period}}{\text{Policy Term Days (365.25)}}$$
- **SQL File**: `sql/kpis/kpi_profitability.sql`
- **Interpretation**: True revenue recognized for the accounting period under accrual accounting standards.

### 1.2 Incurred Claims
- **Definition**: The total cost of claims occurring during the measurement period, including paid claims and approved pending settlements.
- **Formula**:
  $$\text{Incurred Claims} = \sum \text{Paid Amount} + \sum \text{Approved Amount of Pending Claims}$$
- **SQL File**: `sql/kpis/kpi_profitability.sql`
- **Interpretation**: The total claim liability generated during the policy period.

### 1.3 Loss Ratio (Incurred Claim Ratio - ICR)
- **Definition**: The percentage of earned premium paid or payable in claims.
- **Formula**:
  $$\text{Loss Ratio} = \frac{\text{Incurred Claims}}{\text{Earned Premium}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_profitability.sql`
- **Target Benchmark**: Healthy range between 70% and 95%. Above 100% indicates underwriting losses.

### 1.4 Pure Premium
- **Definition**: The average claim cost per unit of exposure (member-year).
- **Formula**:
  $$\text{Pure Premium} = \frac{\text{Incurred Claims}}{\text{Member-Years of Exposure}}$$
- **SQL File**: `sql/kpis/kpi_profitability.sql`
- **Interpretation**: The baseline premium required solely to cover claims risk, excluding operational overhead and profit margin.

---

## 2. Claims Operational KPIs

### 2.1 Claim Frequency
- **Definition**: Number of incurred claims per member-year of exposure.
- **Formula**:
  $$\text{Claim Frequency} = \frac{\text{Count of Incurred Claims}}{\text{Member-Years of Exposure}}$$
- **SQL File**: `sql/kpis/kpi_claims.sql`
- **Interpretation**: Measures the incidence rate of hospitalization across demographic cohorts and plan types.

### 2.2 Claim Severity
- **Definition**: The average paid amount per approved/settled claim.
- **Formula**:
  $$\text{Claim Severity} = \frac{\sum \text{Paid Amount}}{\text{Count of Paid Claims}}$$
- **SQL File**: `sql/kpis/kpi_claims.sql`
- **Interpretation**: Measures the financial magnitude of each hospitalization event.

### 2.3 Claim Settlement Ratio (CSR)
- **Definition**: The percentage of decided claims that were approved (fully or partially).
- **Formula**:
  $$\text{CSR} = \frac{\text{Count of Approved Claims} + \text{Count of Partially Approved Claims}}{\text{Total Decided Claims (Approved + Partially Approved + Rejected)}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_claims.sql`
- **Interpretation**: A critical customer-facing metric reflecting policyholder trust and operational reliability.

### 2.4 Rejection Rate
- **Definition**: The proportion of decided claims that were formally repudiated/rejected.
- **Formula**:
  $$\text{Rejection Rate} = \frac{\text{Count of Rejected Claims}}{\text{Total Decided Claims}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_claims.sql`
- **Interpretation**: High rejection rates indicate poor onboarding disclosure, strict underwriting, or operational friction.

### 2.5 Average Settlement Turnaround Time (TAT)
- **Definition**: The average elapsed days between claim submission and final settlement.
- **Formula**:
  $$\text{Avg TAT} = \frac{\sum (\text{Settled Date} - \text{Submitted Date})}{\text{Count of Settled Claims}}$$
- **SQL File**: `sql/kpis/kpi_operations.sql`
- **Interpretation**: Operational efficiency measure. Cashless claims typically achieve <5 days, while reimbursement claims average 12–20 days.

### 2.6 Cashless Share
- **Definition**: Percentage of total claims processed through network cashless authorization.
- **Formula**:
  $$\text{Cashless Share} = \frac{\text{Count of Cashless Claims}}{\text{Total Claims}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_operations.sql`
- **Interpretation**: Reflects network penetration and customer convenience.

---

## 3. Retention & Policyholder KPIs

### 3.1 Persistency Rate (Renewal Rate)
- **Definition**: The percentage of policies due for renewal that are successfully renewed.
- **Formula**:
  $$\text{Persistency} = \frac{\text{Count of Renewed Policies}}{\text{Count of Policies Due for Renewal}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_retention.sql`
- **Benchmark**: Target range between 78% and 88%.

### 3.2 Lapse Rate
- **Definition**: The complement of the persistency rate.
- **Formula**:
  $$\text{Lapse Rate} = 100\% - \text{Persistency Rate}$$
- **SQL File**: `sql/kpis/kpi_retention.sql`
- **Interpretation**: Direct driver of customer lifetime value erosion.

### 3.3 Average Premium per Member
- **Definition**: Total annual premium divided by the total count of members covered.
- **Formula**:
  $$\text{Avg Premium per Member} = \frac{\sum \text{Annual Premium}}{\sum \text{Members Covered}}$$
- **SQL File**: `sql/kpis/kpi_profitability.sql`

---

## 4. Risk & Concentration KPIs

### 4.1 Provider Concentration
- **Definition**: The proportion of total paid claim costs accounted for by the top 10 healthcare providers.
- **Formula**:
  $$\text{Provider Concentration} = \frac{\sum_{i=1}^{10} \text{Paid Amount}_{\text{provider}_i}}{\sum_{\text{all}} \text{Paid Amount}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_risk.sql`
- **Interpretation**: High concentration exposes the insurer to provider fee negotiations and fraud vulnerabilities.

### 4.2 High-Value Claim Share
- **Definition**: The percentage of total claims exceeding the 95th percentile of billed amounts.
- **Formula**:
  $$\text{High-Value Claim Share} = \frac{\sum_{\text{claims} \ge P95} \text{Paid Amount}}{\sum_{\text{all}} \text{Paid Amount}} \times 100\%$$
- **SQL File**: `sql/kpis/kpi_risk.sql`
- **Interpretation**: Catastrophic tail risk quantification.

