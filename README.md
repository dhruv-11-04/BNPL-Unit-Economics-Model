# BNPL Unit Economics & Profitability Risk Model
Financial model simulating BNPL portfolio performance across credit tiers, ticket sizes, default rates, Merchant Discount Rate, and funding assumptions.

---

## Overview
This project models the **unit economics, credit risk dynamics, and portfolio-level profitability** of a Buy Now Pay Later (BNPL) Pay-in-4 provider using 2024–2025 industry benchmarks.

The objective is to evaluate:
* Whether BNPL margins are structurally sustainable
* How profitability varies across user segments
* The viable ticket size range for different risk profiles
* The trade-off between merchant GMV lift and BNPL profitability

This model integrates **credit segmentation, demographic distribution, expected credit loss modeling, and dynamic contribution margin analysis** into an interactive dashboard.

---

## Industry Context
BNPL providers offer short-duration installment credit (typically 4 installments over 6 weeks) at 0% interest to consumers and monetize primarily through Merchant Discount Rates (MDR).

### Structural Industry Characteristics
* High merchant bargaining power → MDR compression
* Capital dependence → Cost of funds sensitivity
* Credit risk concentration in specific segments
* Thin margins amplified by portfolio mix volatility

---

## Data Sources
The model is built using 2024 US BNPL statistics from:

* Federal Reserve (SHED Report 2024) — 15% U.S. adult adoption
* CFPB BNPL Market Report — 335.8M loans, ~1.82–1.83% default rate
* PYMNTS & Equifax (2024) — Adoption by generation & income
* Public filings from providers such as Affirm and Klarna
* Motley Fool Money research — Default rates by credit category
* CFPB risk distribution profiles

---

## Core Financial Assumptions

| Variable                     | Value   |
| ---------------------------- | ------- |
| Merchant Discount Rate (MDR) | 5%      |
| Cost of Funds                | 9.5%    |
| Loan Tenure                  | 6 weeks |
| Loss Given Default (LGD)     | 75%     |
| Fixed Cost per Loan          | $3      |

---

## Core Hypothesis
Contribution Margin (CM) remains positive only within a **specific ticket size band**, which varies by user segment.
```
CM(T) = T × MDR - CostOfFunds(T) - PD(T) × LGD × T - FixedCost
```

Where:
* **At low ticket sizes** → Fixed cost dominates → CM negative
* **At moderate ticket sizes** → CM increases
* **At high ticket sizes** → Probability of Default increases non-linearly → Expected Credit Loss dominates → CM decreases, eventually turning negative

Each segment therefore has:
* A minimum viable ticket size
* A peak profitability point
* A maximum viable ticket size

---

## Segmentation Framework
Users are segmented across three dimensions:
1. **Generation** (Gen Z, Millennial, Gen X, Baby Boomer)
2. **Income Bracket** (<$50k, $50k-$100k, >$100k)
3. **Credit Tier** (Deep Subprime → Super Prime)

This produces **60 distinct user profiles** (4 × 3 × 5) enabling:
* Segment-level ARPU calculation
* Granular default rate modeling
* Contribution margin analysis by profile
* Portfolio-weighted profitability assessment

---

## Dynamic Default Modeling
Baseline probability of default (PD) is derived from credit tier data.

To reflect real-world risk elasticity:
* **PD(T) scales non-linearly** when ticket size increases beyond segment baseline
* Risk sensitivity modeled as: `PD(T) = PD_base × (T / T_baseline)^β`
* **Beta coefficients** vary by segment: β = 1.05 (Super Prime) to 1.89 (Deep Subprime)
* Income stress and credit sensitivity amplify risk at higher exposures

This dynamic modeling is critical to understanding margin fragility at scale.

---

## Key Questions Addressed

1. **Is BNPL structurally profitable?**
   - Portfolio-level CM: $0.80/user — razor-thin margins
   - 35% of loans are unprofitable
   - Business is viable but fragile

2. **Which segments drive value vs destroy it?**
   - Gen Z low-income: -$33/user (9.8% of portfolio, 19.8% of loans)
   - Gen X high-income: +$45/user (3% of portfolio, disproportionate profit)
   - Middle-income Millennials: Sweet spot at $0.27-$4/user

3. **What are optimal ticket size limits by segment?**
   - Deep Subprime Gen Z: Never profitable (recommend decline)
   - Middle-income Millennial (Prime): $99-$219 (peak at ~$140)
   - High-income Gen X (Super Prime): No meaningful upper limit

---

## Key Insights

### 1. Structural Fragility
* **Portfolio CM of $0.80/user** — 98% of revenue consumed by costs
* **35% loan-level unprofitability** — requires cross-subsidization from profitable segments
* **Concentration risk threshold: 23%** — Portfolio breaks if low-income share exceeds this

### 2. Non-Linear Default Risk
* Default probability scales with beta coefficients ranging **1.05 to 1.89**
* High-risk segments (β = 1.89) see defaults grow **18x** at 4x ticket size
* Low-risk segments (β = 1.05) remain stable even at 5x+ ticket size
* **This non-linearity drives segment-specific breakeven points**

### 3. Segment-Specific Profitability Windows

| Segment | Min Viable ATS | Max Viable ATS | Peak CM ATS | Peak CM Value |
|---------|----------------|----------------|-------------|---------------|
| Gen Z, <$50k, Deep Sub | Never | Never | N/A | -$33/user |
| Millennial, $50-100k, Prime | $99 | $219 | ~$140 | $0.72 |
| Gen X, >$100k, Super Prime | Baseline | No limit | $800-1000 | $42+ |

### 5. Industry-Level Implications
* **Merchant value vs BNPL profitability trade-off:**
  - Risky segments drive merchant GMV but destroy BNPL margins
  - Stable segments generate BNPL profit but lower merchant conversion lift
* **Competitive dynamics:** Race to the bottom on MDR compresses already-thin margins
* **Macro sensitivity:** +100bps funding cost could render industry unprofitable
* **Regulatory risk:** Default rate disclosure or fee caps could eliminate marginal segments

---

## Broader Industry Conclusion
BNPL is a **structurally thin-margin industry** characterized by:

* High merchant bargaining power → MDR compression
* Capital sensitivity → Funding cost vulnerability
* Competitive pricing pressure → Limited differentiation
* Riskier segments are value drivers for merchants while being margin deteriorators for BNPL providers
* Stable segments are strategic buyers which provide lesser merchant value but drive BNPL profitability
* **Profitability is highly fragile** as these competing value drivers are navigated

Under mild macro stress (higher funding cost, deteriorating credit mix, or regulatory intervention), **industry-level profitability can turn negative**.

**Strategic imperative:** Selective growth with dynamic, risk-based approval limits.

---

## Model Features

### Interactive Dashboard
* **Dynamic user profile selection** across generation, income, credit tier
* **Real-time contribution margin curves** showing profitability vs ticket size
* **Scenario analysis** via adjustable MDR and funding rate parameters
* **Portfolio statistics** including default rate, average CM, loan composition
* **Optimization metrics** (min/max/peak profitable ticket sizes per segment)

### Analytical Capabilities
* 60-cell economic model with segment-specific parameters
* Non-linear default probability functions with beta coefficients
* Portfolio-weighted aggregation and sensitivity analysis
* Revenue validation against industry benchmarks

---

## Skills Demonstrated
* **Financial modeling:** Unit economics, contribution margin analysis
* **Credit risk modeling:** Expected credit loss, PD/LGD framework, non-linear risk scaling
* **Data triangulation:** Multi-source integration (census, industry reports, public filings)
* **Portfolio analysis:** Segmentation, concentration risk, mix sensitivity
* **Strategic reasoning:** Growth prioritization, risk-based decision framework
* **Data visualization:** Interactive dashboard design, scenario analysis interface
* **Model validation:** Industry benchmarking, sanity checking

---

## Dashboard Preview
<img width="960" height="685" alt="BNPL Dashboard" src="https://github.com/user-attachments/assets/3f7b99bd-5789-478e-acf9-6a65c6d02036" />

---

## How to Use

1. **Download** the Excel file from this repository
3. **Navigate to "Dashboard" tab**
4. **Select user profile** using dropdowns:
   - Generation (Gen Z, Millennial, Gen X, Baby Boomer)
   - Income Bracket (<$50k, $50k-$100k, >$100k)
   - Credit Category (Deep Subprime → Super Prime)
5. **View results:**
   - Contribution margin curve shows profitability across ticket size range
   - Metrics panel displays segment-specific statistics
   - Optimization thresholds show min/max/peak profitable ticket sizes
6. **Run scenarios:**
   - Adjust MDR (Merchant Discount Rate) to model pricing changes
   - Adjust Funding Rate to assess capital cost sensitivity
   - Dashboard updates dynamically
  
---

## Future Enhancements
* Add merchant GMV lift modeling to quantify merchant-side value
* Incorporate seasonality effects on default rates
* Model multi-installment plans (Pay-in-6, Pay-in-12)
* Add Monte Carlo simulation for portfolio stress testing
* Integrate with Python for automated scenario generation

---

## Author
**Dhruv Sandilya**  
Delhi Technological University | B.Tech Computer Science & Engineering  
dhruvsandilya1104@gmail.com

---

## Acknowledgments
Data sources include Federal Reserve, CFPB, PYMNTS, Equifax, and public filings from BNPL providers. This project was developed independently as part of a self-directed learning initiative in financial modeling and credit risk analysis.
