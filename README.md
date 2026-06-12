# BNPL Unit Economics, Stress Testing & Portfolio Optimization

A three-dashboard financial model analyzing the structural sustainability of Buy Now Pay Later (BNPL) unit economics across 60 borrower segments, with a constrained portfolio optimization engine built on top of the stress-tested results.

**[→ Live Portfolio Optimizer](https://bnpl-portfolio-optimizer.streamlit.app)**

---

## Dashboards

### Unit Economics & Portfolio Overview
![BNPL Portfolio Overview](Visual/Portfolio%20Overview/BNPL%20Portfolio%20Overview%20Dashboard.jpeg)

### Macro Stress Test
![Macro Stress Test](Visual/Macro%20Stress%20Test/Macro%20Stress%20Analysis%20Dashboard.png)

### Portfolio Optimizer
![Portfolio Optimizer](Visual/Portfolio%20Optimizer/Optimizer%20Result.png)

---

## What This Project Found

### 1. The portfolio makes money despite itself
Net contribution margin is 84.7% dependent on just 5 of 60 segments. The remaining 55 net to only $63M combined, with 17 actively destroying $335M in value that the top 5 must overcome. The headline $414M portfolio CM looks healthy. The composition doesn't.

### 2. The real binding constraint isn't credit risk — it's merchant structure
BNPL lenders cannot cherry-pick borrowers because merchant SLAs require volume across their full customer base. Riskier segments drive merchant GMV but compress BNPL margins. The $335M of loss-making drag isn't sloppy underwriting — it's the implicit cost of maintaining the merchant relationships that generate the profitable book. Competitive MDR compression and funding cost volatility amplify this tension structurally.

### 3. 86 basis points of MDR headroom in base — already underwater in adverse
The base portfolio breaks even at 4.14% MDR, leaving 86bps of cushion at the current 5.0%. The adverse scenario operates at a reduced MDR of 4.75% but needs 5.05% to break even — it is already 30bps underwater at its current stressed rate. The severely adverse scenario is already 160bps underwater at its stressed 4.5% MDR. The stress scenarios compound both sides simultaneously: MDR falls from 5.0% to 4.5% while funding costs rise from 9.5% to 13.0%. In an industry where merchant fee negotiations routinely move 50–200bps, the adverse book sits one renegotiation from zero.

### 4. Increasing ticket size cannot rescue Deep Subprime — but it nearly triples CM for Sub Prime
For Millennial / $50K–100K / Sub Prime, doubling the current $130 ATS almost triples CM/loan, with a profitable window between $104 and $378. Deep Subprime has no such window — its CM curve never turns positive at any ticket size, starting negative and accelerating downward regardless of loan size. The combined beta for the worst segment (Deep Subprime / <$50K) reaches 1.89, meaning default rates grow nearly twice as fast as ticket size. ECL always outpaces revenue before breakeven is reached.

### 5. A 6.3% portfolio reallocation turns a $158M stressed loss into positive CM
Touching just 1 in 16 loans, the constrained optimizer flips adverse CM from −$158M to +$0.9M, improves base CM by 52% ($414M → $630M), cuts adverse PD by 33bps, and grows GMV by $5.4B. Each additional percentage point of turnover budget in this range is worth ~$13M of adverse CM.

---

## Project Structure

```
BNPL-Unit-Economics-Model/
├── Excel/
│   └── BNPL Project.xlsx          # Three-dashboard Excel model
├── Portfolio Optimizer/
│   ├── app.py                     # Streamlit dashboard
│   ├── optimizer.py               # LP engine (scipy HiGHS)
│   ├── portfolio.py               # Portfolio metric calculations
│   ├── data_loader.py             # Excel → Python pipeline
│   ├── ui_helpers.py              # Formatters and chart builders
│   ├── frontier.py                # Efficient frontier generation
│   └── config.py                  # Constants and file paths
└── requirements.txt
```

---

## Three Dashboards

### 1. BNPL Unit Economics (Excel)
Segment-level contribution margin analysis across 60 profiles. Interactive dropdowns for generation, income bracket, and credit tier. Real-time CM vs ticket size curve with automatic detection of min/peak/max profitable ATS. Adjustable MDR and funding rate stress testing.

### 2. Macro Stress Test (Excel)
Portfolio-level P&L under Base, Adverse, and Severely Adverse macro scenarios. Each scenario applies independent multipliers to PD, EAD, ATS, and loan count at the credit tier, generation, and income bracket level simultaneously. Breakeven MDR and profitable segment count tracked across all three scenarios.

### 3. Portfolio Optimizer (Python / Streamlit)
Constrained LP optimization across all 60 segments using `scipy.optimize.linprog` with HiGHS.

**Objective:** Maximize `0.5 × Base CM + 0.3 × Adverse CM + 0.2 × Severe CM`

**Constraints:**
- Per-segment relative delta (RD): each segment weight can move at most ±RD% of its current allocation
- Global turnover budget (TO): `0.5 × Σ|wᵢ − wᵢ_cur| ≤ budget`, linearized via auxiliary variables
- Adverse PD cap: maximum weighted probability of default under stress
- GMV retention floor: minimum base-scenario GMV

**Operating Region Analysis:** 25-cell RD × TO grid showing how adverse CM, severe CM, PD, and credit tier composition shift across the full constraint space.

---

## Segmentation Framework

**60 segments: 4 Generations × 3 Income Brackets × 5 Credit Tiers**

| Dimension | Values |
|---|---|
| Generation | Gen Z, Millennial, Gen X, Baby Boomer |
| Income Bracket | <$50K, $50K–$100K, >$100K |
| Credit Tier | Deep Subprime, Sub Prime, Near Prime, Prime, Super Prime |

Each segment carries scenario-specific values for loan count, ATS, revenue per loan, ECL, funding cost, CM per loan, and PD across all three macro scenarios.

---

## Model Architecture

**PD is dynamic.** Segment-level default rates scale non-linearly with ticket size via a multiplicative beta:

```
PD(T) = PD₀ × (T / T_baseline)^β
β = Beta_Income × Beta_Credit_Tier
```

Beta ranges from **1.071** (Super Prime / >$100K) to **1.890** (Deep Subprime / <$50K). At β = 1.89, a 4× increase in ticket size produces an 18× increase in default rate.

**Macro stress applies three independent multipliers per metric:**

```
Stressed PD = Base PD × Credit_Tier_Mult × Generation_Mult × Income_Mult
Stressed ATS = Base ATS × Generation_Mult × Income_Mult
Stressed Loan Count = Base LC × Generation_Mult × Income_Mult
```

**EAD varies by credit tier**, reflecting how much of the loan is outstanding at default based on repayment timing distributions. Higher credit tiers have lower EAD because borrowers repay more before defaulting.

| Credit Tier | EAD Factor | LGD |
|---|---|---|
| Deep Subprime | 0.638 | 1.0 |
| Sub Prime | 0.563 | 1.0 |
| Near Prime | 0.518 | 1.0 |
| Prime | 0.488 | 1.0 |
| Super Prime | 0.443 | 1.0 |

---

## Scenario Assumptions

| Variable | Base | Adverse | Severely Adverse |
|---|---|---|---|
| MDR | 5.00% | 4.75% | 4.50% |
| Funding Rate | 9.50% | 11.25% | 13.00% |
| LGD | 100% | 100% | 100% |
| Fixed Cost per Loan | $3 | $3 | $3 |
| Loan Tenure | 6 weeks | 6 weeks | 6 weeks |
| Breakeven MDR | 4.14% | 5.05% | 6.10% |
| MDR Cushion / Deficit | +86 bps | −30 bps | −160 bps |

---

## Data Sources

Built from 2024 US BNPL market statistics:

- **CFPB BNPL Market Report** — 335.8M loans, ~1.82% baseline default rate, origination distribution
- **Federal Reserve SHED Report 2024** — 15% U.S. adult adoption, income bracket distributions
- **PYMNTS & Equifax 2024** — Adoption rates by generation and income
- **Affirm & Klarna public filings** — Unit economics benchmarks, funding cost references
- **Motley Fool Money / credit bureau data** — Default rates by credit category

---

## Author

**Dhruv Sandilya** — Delhi Technological University, B.Tech Computer Science & Engineering
