# BNPL Unit Economics & Profitability Risk Model

A segment-level financial model analyzing the structural sustainability of Buy Now Pay Later (BNPL) unit economics under varying ticket sizes, credit tiers, demographic mix, funding costs, and Merchant Discount Rates (MDR).

This project evaluates whether BNPL profitability is structurally sustainable — and if so, under what portfolio composition.

---

## Objective

To model how:
* Ticket size elasticity
* Credit risk concentration
* Demographic mix
* Funding cost sensitivity
* Merchant pricing pressure

interact to determine BNPL contribution margin at both segment and portfolio levels.

The model identifies profitability breakpoints, optimal ticket sizes, and structural fragility thresholds.

---

## Core Hypothesis

BNPL contribution margin is not monotonic in ticket size.

Revenue scales linearly with ticket size:
```
R(T) = T × MDR
```

But expected credit loss scales non-linearly:
```
PD(T) = PD_base × (T / T_baseline)^β
```

Therefore:
```
CM(T) = T × MDR − FundingCost(T) − PD(T) × LGD × T − FixedCost
```

This produces segment-specific profitability bands:
* Minimum viable ticket size
* Peak contribution margin
* Maximum viable ticket size

Beyond a threshold, convex credit losses dominate linear revenue growth.

---

## Segmentation Framework

The portfolio is modeled across **60 user profiles**:

**4 Generations × 3 Income Brackets × 5 Credit Tiers**

Each segment includes:
* Baseline probability of default
* Average ticket size
* Beta coefficient (risk elasticity)
* Expected credit loss
* Segment-level contribution margin

This enables both:
* Micro (user-level) economics
* Macro (portfolio-level) aggregation

---

## Core Financial Assumptions

| Variable | Value |
|----------|-------|
| Merchant Discount Rate (MDR) | 5% |
| Funding Rate | 9.5% |
| Loss Given Default (LGD) | 75% |
| Fixed Cost per Loan | $3 |
| Loan Tenure | 6 weeks |

MDR and Funding Rate are adjustable within the dashboard.

---

## Key Findings

### 1. Structural Fragility

* Portfolio contribution margin: **$0.80 per loan**
* CM implies that ~98% of revenue is absorbed by funding, credit losses, and operating costs.
* ±50bps shock (funding up + MDR down) turns portfolio CM negative
* The industry operates with thin buffers and high macro sensitivity.

High merchant bargaining power and capital dependence structurally compress margins.

### 2. The Profitability Paradox

* **35% of loans profitable**
* **65% of loans loss-making**

The loss-making majority likely drives incremental merchant GMV, justifying MDR levels.

The profitable minority preserves BNPL viability but may generate less incremental merchant value.

This creates structural cross-subsidization within the portfolio.

**BNPL's sustainability depends on balancing these opposing forces.**

### 3. Non-Linear Risk Drives Breakpoints

Beta coefficients range from **1.05 (Super Prime) to 1.89 (Deep Subprime)**.
Beta coefficients for Income Brackets range from **1.05 (>100k) to 1.4 (<50k)**.

High-risk segments (β = 1.89) see defaults grow **18x** at 4x ticket size
* Low-risk segments (β = 1.05) remain stable even at 5x+ ticket size
* **This non-linearity drives segment-specific breakeven points**

### 4. Segment-Specific Profitability Windows

| Segment | Min ATS | Optimal ATS | Max ATS |
|---------|---------|-------------|---------|
| Gen Z, <$50k, Deep Subprime | Never profitable | N/A | N/A |
| Millennial, $50–100k, Near Prime | $114 | $294 | $457 |
| Gen X, >$100k, Prime | $148 | $2,068 | $4,062 |

Millennial Near Prime shows a **160%+ gap between average and optimal ticket size** — indicating controlled underwriting expansion potential.

### 5. Concentration Risk

* **45% of originations originate from Deep Subprime**
* Structurally unprofitable across ticket sizes
* Portfolio viability is highly sensitive to mix shifts.

A deterioration in low-income concentration beyond **~23%** renders the portfolio unprofitable.

**Portfolio mix is the primary strategic lever.**

### 6. Industry-Level Tension

BNPL operates in a structurally fragile equilibrium:

**Merchant Value Drivers ≠ BNPL Profit Drivers**

* Riskier segments drive merchant GMV uplift but compress BNPL margins
* Stable segments generate BNPL profit but may add less incremental merchant value

Competitive MDR compression and funding cost volatility amplify this tension.

### 7. Portfolio Mix is the Primary Control Variable

While ticket size optimization improves segment economics, long-term sustainability is primarily driven by demographic and credit mix composition.

**Growth quality matters more than growth volume**.

---

## Strategic Implications

The model suggests sustainability requires:

* Gradual expansion of Near Prime segments
* Controlled reduction in Deep Subprime concentration
* Segment-specific ticket optimization
* Revenue diversification beyond MDR-only monetization

**BNPL is not structurally doomed — but is highly sensitive to pricing, mix, and funding conditions.**

---

## Model Features

### Interactive Dashboard:
* Dynamic segment selection
* Real-time CM vs ticket size visualization
* Automatic detection of min/peak/max profitable ATS
* Adjustable MDR and funding rate stress testing
* Portfolio-level aggregation metrics

### Analytical Engine:
* 60-segment economic model
* Non-linear PD elasticity
* Portfolio-weighted aggregation
* Stress threshold detection

---

## What This Project Demonstrates

* Unit economics modeling
* Credit risk convexity analysis
* Portfolio concentration risk assessment
* Scenario-based stress testing
* Translation of micro-level risk into macro-level strategic implications
* Advanced Excel financial modeling architecture

---

## Dashboard Preview

<img width="960" height="684" alt="BNPL Unit Economics Dashboard" src="https://github.com/user-attachments/assets/d85efb2d-ca73-4d53-a804-a8628ff6835f" />

---

## Future Enhancements

* Merchant GMV lift quantification
* Monte Carlo stress simulation
* Multi-tenure product modeling
* Python-based scenario automation
* Real-world dataset integration

---

## Author

**Dhruv Sandilya**  
Delhi Technological University  
B.Tech Computer Science & Engineering

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
