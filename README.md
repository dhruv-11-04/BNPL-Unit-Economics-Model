# BNPL-Unit-Economics-&-Profitability-Risk-Model
Financial Model simulating BNPL portfolio performance across credit-tiers, ticket sizes, default rates, Merchant-Discount-Rate, and funding assumptions.

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
The model is built using the 2024 US BNPL statistics from:

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

[
CM(T) = TxMDR - CostOfFunds(T) - PD(T)xLGDxT - FixedCost
]

Where:
* At low ticket sizes → Fixed cost dominates → CM negative
* At moderate ticket sizes → CM increases
* At high ticket sizes → Probability of Default increases non-linearly → Expected Credit Loss dominates → CM decreases, eventually turning negative

Each segment therefore has:
* A minimum viable ticket size
* A peak profitability point
* A maximum viable ticket size

---

## Segmentation Framework
Users are segmented across three dimensions:
1. Generation
2. Income Bracket
3. Credit Tier (Deep Subprime → Super Prime)

This produces a 3D portfolio view enabling:
* Segment-level ARPU
* Default rate modeling
* Contribution margin analysis
* Portfolio-weighted profitability

---

## Dynamic Default Modeling
Baseline PD is derived from credit tier data.

To reflect real-world risk elasticity:
* PD(T) increases non-linearly when ticket size exceeds segment ATS
* Income stress and credit sensitivity amplify risk at higher exposures

This dynamic modeling is critical to understanding margin fragility.

---
## Key Questions

---

## Key Insights

---

## Broader Industry Conclusion
BNPL is a structurally thin-margin industry characterized by:

* High merchant bargaining power
* Capital sensitivity
* Competitive pricing pressure
* Riskier segments are value drivers for Merchants while being margin deteriorators for BNPL service providers.
* More stable segments are strategic buyers which provide lesser value but drive BNPL profitability.
* Profitability thus becomes highly fragile as these competing value drivers are navigated.

Under mild macro stress (higher funding cost or deteriorating credit mix), industry-level profitability can turn negative.

---

## Skills Demonstrated
* Credit risk modeling
* Expected Credit Loss modeling
* Unit economics analysis
* Portfolio segmentation
* Sensitivity analysis
* Strategic industry assessment
* Interactive dashboard design

---
## Dashboard Preview
<img width="960" height="685" alt="BNPL Dashboard" src="https://github.com/user-attachments/assets/3f7b99bd-5789-478e-acf9-6a65c6d02036" />

