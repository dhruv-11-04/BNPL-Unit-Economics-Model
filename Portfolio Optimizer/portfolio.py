# portfolio.py
"""
Portfolio-level metric calculations.
All functions are pure: (weights, scenario_df, ...) -> metrics dict.

Weighting conventions (confirmed against workbook):
  - CM, Revenue, ECL, Funding Cost, CM Per Loan  : loan-count weighted
  - ARPU                                          : user-count weighted
  - PD (optimizer constraint)                     : loan-count weighted
  - GMV                                           : sum(base_ats_i * w_i * N) / 1000 [billions]

Fixed cost note:
  The workbook Total CM column = gross CM (no fixed cost deducted).
  Fixed cost (3.0) is applied separately at the final P&L display level.
  portfolio_metrics() returns GROSS cm; callers subtract fixed_cost as needed.
"""

import numpy as np
import pandas as pd


def current_weights(base_df: pd.DataFrame) -> np.ndarray:
    """
    Derive current portfolio weights from base scenario loan counts.
    w_i = loan_count_i / total_loan_count
    Returns ndarray shape (60,), sums to 1.
    """
    lc = base_df["loan_count"].values.astype(float)
    return lc / lc.sum()


def portfolio_metrics(
    weights: np.ndarray,
    scenario_df: pd.DataFrame,
    total_loans_m: float,
    base_df: pd.DataFrame | None = None,
) -> dict:
    """
    Compute portfolio metrics for a given weight vector and scenario.

    Parameters
    ----------
    weights       : array (60,), sums to 1
    scenario_df   : base_df / adverse_df / severe_df
    total_loans_m : total portfolio loan count in millions (scalar user input)
    base_df       : supply for GMV and ARPU outputs (uses base ATS/ARPU per design)
                    if None, falls back to scenario_df

    Returns
    -------
    dict:
        cm            – gross portfolio CM (millions $), NO fixed cost deducted
        cm_per_loan   – weighted average CM per loan
        revenue       – total portfolio revenue (millions $)
        ecl           – total portfolio ECL (millions $)
        funding_cost  – total portfolio funding cost (millions $)
        arpu          – user-count weighted ARPU (base scenario)
        pd            – loan-count weighted PD
        gmv           – portfolio GMV in billions (base ATS)
        loan_count_m  – total loans in millions (= total_loans_m)
    """
    w  = np.asarray(weights, dtype=float)
    sd = scenario_df
    src = base_df if base_df is not None else scenario_df

    # ── Per-loan weighted averages (loan-count weights) ────────────
    cm_per_loan   = float(np.dot(w, sd["cm_per_loan"].values))
    rev_per_loan  = float(np.dot(w, sd["revenue_per_loan"].values))
    ecl_per_loan  = float(np.dot(w, sd["ecl"].values))
    fc_per_loan   = float(np.dot(w, sd["funding_cost"].values))
    pd_loan_wtd   = float(np.dot(w, sd["pd"].values))

    # ── Portfolio totals ───────────────────────────────────────────
    portfolio_cm      = total_loans_m * cm_per_loan   # gross, no fixed cost
    portfolio_revenue = total_loans_m * rev_per_loan
    portfolio_ecl     = total_loans_m * ecl_per_loan
    portfolio_fc      = total_loans_m * fc_per_loan

    # ── ARPU: user-count weighted from base scenario ───────────────
    u = src["user_count"].values.astype(float)
    arpu = float(np.dot(u / u.sum(), src["arpu"].values))

    # ── GMV: base ATS × optimized loan counts ─────────────────────
    base_ats  = src["ats"].values.astype(float)
    gmv_b = float(np.dot(base_ats, w) * total_loans_m / 1000.0)

    return {
        "cm":           portfolio_cm,
        "cm_per_loan":  cm_per_loan,
        "revenue":      portfolio_revenue,
        "ecl":          portfolio_ecl,
        "funding_cost": portfolio_fc,
        "arpu":         arpu,
        "pd":           pd_loan_wtd,
        "gmv":          gmv_b,
        "loan_count_m": total_loans_m,
    }


def portfolio_gmv(
    weights: np.ndarray,
    base_df: pd.DataFrame,
    total_loans_m: float,
) -> float:
    """
    GMV in billions = sum(base_ats_i * w_i * total_loans_m) / 1000
    Always uses base ATS per confirmed modelling decision.
    """
    return float(np.dot(base_df["ats"].values, weights) * total_loans_m / 1000.0)


def weighted_pd(
    weights: np.ndarray,
    scenario_df: pd.DataFrame,
) -> float:
    """
    Loan-count weighted PD for a given scenario.
    Used for optimizer PD constraint (pass adverse_df).
    """
    return float(np.dot(weights, scenario_df["pd"].values))


# ── Validation ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_stress_analysis

    base_df, adverse_df, severe_df, fixed_cost = load_stress_analysis()
    w_base = current_weights(base_df)
    w_adv  = current_weights(adverse_df)
    w_sev  = current_weights(severe_df)
    N_base = base_df["loan_count"].sum()
    N_adv  = adverse_df["loan_count"].sum()
    N_sev  = severe_df["loan_count"].sum()

    print("=" * 62)
    print("PORTFOLIO.PY VALIDATION")
    print("=" * 62)
    print(f"\nFixed cost: {fixed_cost}")
    print(f"Weights: sum={w_base.sum():.6f}, min={w_base.min():.5f}, max={w_base.max():.5f}")

    # BASE
    m = portfolio_metrics(w_base, base_df, N_base, base_df)
    print("\n── BASE (current weights, base loans) ──")
    print(f"  CM gross:     {m['cm']:>12.4f}  WB: 414.2453  {'✅' if abs(m['cm']-414.2453)<0.01 else '❌'}")
    print(f"  CM per loan:  {m['cm_per_loan']:>12.6f}  WB: 1.233131  {'✅' if abs(m['cm_per_loan']-1.233131)<1e-4 else '❌'}")
    print(f"  GMV (B):      {m['gmv']:>12.4f}  WB: 48.3372   {'✅' if abs(m['gmv']-48.3372)<0.01 else '❌'}")
    print(f"  ARPU:         {m['arpu']:>12.4f}  WB: 46.8747   {'✅' if abs(m['arpu']-46.8747)<0.01 else '❌'}")
    print(f"  PD (loan-wt): {m['pd']:>12.5f}  WB: 0.01729 (display; loan-wt = 0.02248)")

    # ADVERSE
    m = portfolio_metrics(w_adv, adverse_df, N_adv, base_df)
    print("\n── ADVERSE (current adverse weights, adverse loans) ──")
    print(f"  CM gross:     {m['cm']:>12.4f}  WB: -113.0794 {'✅' if abs(m['cm']-(-113.0794))<0.01 else '❌'}")
    print(f"  CM per loan:  {m['cm_per_loan']:>12.6f}  WB: -0.40094  {'✅' if abs(m['cm_per_loan']-(-0.40094))<1e-4 else '❌'}")
    print(f"  PD:           {m['pd']:>12.5f}  WB: 0.03397   {'✅' if abs(m['pd']-0.03397)<1e-4 else '❌'}")
    print(f"  GMV base ATS: {m['gmv']:>12.4f}  (optimizer constraint value)")

    # SEVERE
    m = portfolio_metrics(w_sev, severe_df, N_sev, base_df)
    print("\n── SEVERE (current severe weights, severe loans) ──")
    print(f"  CM gross:     {m['cm']:>12.4f}  WB: -475.5298 {'✅' if abs(m['cm']-(-475.5298))<0.01 else '❌'}")
    print(f"  CM per loan:  {m['cm_per_loan']:>12.6f}  WB: -1.910053 {'✅' if abs(m['cm_per_loan']-(-1.910053))<1e-4 else '❌'}")
    print(f"  PD:           {m['pd']:>12.5f}  WB: 0.047296  {'✅' if abs(m['pd']-0.047296)<1e-4 else '❌'}")

    # Standalone functions
    print("\n── STANDALONE FUNCTIONS ──")
    print(f"  weighted_pd(w_adv, adverse):  {weighted_pd(w_adv, adverse_df):.5f}  WB: 0.03397  {'✅' if abs(weighted_pd(w_adv, adverse_df)-0.03397)<1e-4 else '❌'}")
    print(f"  weighted_pd(w_sev, severe):   {weighted_pd(w_sev, severe_df):.5f}  WB: 0.04730  {'✅' if abs(weighted_pd(w_sev, severe_df)-0.047296)<1e-4 else '❌'}")
    print(f"  portfolio_gmv(base):           {portfolio_gmv(w_base, base_df, N_base):.4f} B  WB: 48.3372  {'✅' if abs(portfolio_gmv(w_base, base_df, N_base)-48.3372)<0.01 else '❌'}")
    print("\n" + "=" * 62)
