# frontier.py
"""
Efficient frontier: 40 optimizer runs across a range of adverse PD caps.

The frontier spans from the feasibility boundary (~0.00863) to the current
portfolio's adverse PD (~0.03464), sampling the binding zone densely and
the free zone at coarser intervals to show both the tradeoff and the plateau.

Returns a plotting-ready DataFrame:
    pd_cap          – the PD cap constraint input
    portfolio_pd    – realised weighted adverse PD at optimum
    portfolio_cm    – net portfolio CM (fixed cost deducted)
    base_cm         – gross base scenario CM
    adverse_cm      – gross adverse scenario CM
    severe_cm       – gross severe scenario CM
    gmv             – base-ATS GMV at optimum (billions)
    status          – "optimal" | "infeasible"
"""

import numpy as np
import pandas as pd
from data_loader import load_stress_analysis
from optimizer import optimize
from portfolio import current_weights, portfolio_gmv, weighted_pd
from config import FRONTIER_STEPS, FRONTIER_GMV_FLOOR, WEIGHT_MAX


def _find_feasibility_boundary(
    data: tuple,
    total_loans_m: float,
    fixed_cost: float,
    gmv_floor: float,
    relative_delta: float = 0.50,
    n_bisect: int = 30,
) -> float:
    """Binary search for the minimum feasible PD cap."""
    base_df, adverse_df, *_ = data
    n_at_max = int(round(1.0 / WEIGHT_MAX))
    pd_sorted = np.sort(adverse_df["pd"].values)
    lo = float(pd_sorted[:n_at_max].mean()) * 0.90
    hi = float(pd_sorted[:n_at_max].mean()) * 1.20

    for _ in range(n_bisect):
        mid = (lo + hi) / 2
        r = optimize(mid, gmv_floor, total_loans_m, fixed_cost,
                     relative_delta=relative_delta, _data=data)
        if r.status == "optimal":
            hi = mid
        else:
            lo = mid
    return hi


def build_frontier(
    gmv_floor: float = FRONTIER_GMV_FLOOR,
    n_steps: int = FRONTIER_STEPS,
    total_loans_m: float | None = None,
    fixed_cost: float | None = None,
    relative_delta: float = 0.50,
) -> pd.DataFrame:
    """
    Generate the efficient frontier.

    Parameters
    ----------
    gmv_floor     : GMV retention floor, fraction (default 0.90)
    n_steps       : total number of PD cap levels (default 40)
    total_loans_m : portfolio size in millions; defaults to base total
    fixed_cost    : fixed cost scalar; read from workbook if None
    relative_delta: max fractional deviation per segment (default 0.50)

    Returns
    -------
    DataFrame with columns:
        pd_cap, portfolio_pd, portfolio_cm, base_cm, adverse_cm,
        severe_cm, gmv, status
    """
    base_df, adverse_df, severe_df, fc = load_stress_analysis()
    data = (base_df, adverse_df, severe_df, fc)

    if fixed_cost is None:
        fixed_cost = fc
    if total_loans_m is None:
        total_loans_m = float(base_df["loan_count"].sum())

    w_cur = current_weights(base_df)
    cur_pd_adv = weighted_pd(w_cur, adverse_df)

    # ── Locate feasibility boundary and unconstrained optimum PD ──
    pd_boundary = _find_feasibility_boundary(data, total_loans_m, fixed_cost, gmv_floor, relative_delta)

    # Run unconstrained (high cap) to find natural optimum PD
    res_unc = optimize(cur_pd_adv, gmv_floor, total_loans_m, fixed_cost,
                       relative_delta=relative_delta, _data=data)
    pd_opt = res_unc.metrics_adverse["pd"] if res_unc.status == "optimal" else cur_pd_adv * 0.5

    # ── Build pd_cap grid ──────────────────────────────────────────
    # Dense sampling in binding zone [boundary, pd_opt + small buffer]
    # Coarse sampling from pd_opt to current portfolio PD
    n_binding = max(4, n_steps // 2)
    n_free    = n_steps - n_binding

    pd_binding = np.linspace(pd_boundary * 1.001, pd_opt * 1.01, n_binding)
    pd_free    = np.linspace(pd_opt * 1.02, cur_pd_adv, n_free)
    pd_caps    = np.concatenate([pd_binding, pd_free])

    # ── Solve ──────────────────────────────────────────────────────
    rows = []
    for pd_cap in pd_caps:
        res = optimize(
            pd_cap=float(pd_cap),
            gmv_floor=gmv_floor,
            total_loans_m=total_loans_m,
            fixed_cost=fixed_cost,
            relative_delta=relative_delta,
            _data=data,
        )
        if res.status == "optimal":
            rows.append({
                "pd_cap":       float(pd_cap),
                "portfolio_pd": res.metrics_adverse["pd"],
                "portfolio_cm": res.objective_value,
                "base_cm":      res.metrics_base["cm"],
                "adverse_cm":   res.metrics_adverse["cm"],
                "severe_cm":    res.metrics_severe["cm"],
                "gmv":          res.metrics_base["gmv"],
                "status":       "optimal",
            })
        else:
            rows.append({
                "pd_cap":       float(pd_cap),
                "portfolio_pd": np.nan,
                "portfolio_cm": np.nan,
                "base_cm":      np.nan,
                "adverse_cm":   np.nan,
                "severe_cm":    np.nan,
                "gmv":          np.nan,
                "status":       res.status,
            })

    df = pd.DataFrame(rows)
    return df


# ── Validation / demo ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("FRONTIER.PY VALIDATION")
    print("=" * 65)

    df = build_frontier(gmv_floor=FRONTIER_GMV_FLOOR, n_steps=FRONTIER_STEPS)

    optimal    = df[df["status"] == "optimal"]
    infeasible = df[df["status"] != "optimal"]

    print(f"\nTotal runs:    {len(df)}")
    print(f"Optimal:       {len(optimal)}")
    print(f"Infeasible:    {len(infeasible)}")

    if len(optimal) > 0:
        print(f"\nPortfolio PD range:  {optimal['portfolio_pd'].min():.5f} → {optimal['portfolio_pd'].max():.5f}")
        print(f"Portfolio CM range:  {optimal['portfolio_cm'].min():.2f} → {optimal['portfolio_cm'].max():.2f}")
        print(f"GMV range (B):       {optimal['gmv'].min():.4f} → {optimal['gmv'].max():.4f}")

        print(f"\n{'pd_cap':>10} {'portfolio_pd':>13} {'portfolio_cm':>13} {'gmv':>9} {'status':>11}")
        print("-" * 62)
        for _, row in df.iloc[::4].iterrows():
            pd_str  = f"{row['portfolio_pd']:.5f}" if not np.isnan(row['portfolio_pd']) else "         —"
            cm_str  = f"{row['portfolio_cm']:.2f}"  if not np.isnan(row['portfolio_cm']) else "           —"
            gmv_str = f"{row['gmv']:.4f}"           if not np.isnan(row['gmv'])          else "         —"
            print(f"{row['pd_cap']:>10.5f} {pd_str:>13} {cm_str:>13} {gmv_str:>9} {row['status']:>11}")

        # ── Quality checks ─────────────────────────────────────────
        cms  = optimal.sort_values("pd_cap")["portfolio_cm"].values
        mono = all(cms[i] <= cms[i+1] + 1.0 for i in range(len(cms)-1))
        print(f"\nMonotonicity (higher PD cap → higher or equal CM): {'✅' if mono else '⚠️'}")
        print(f"No NaN in optimal rows:  {'✅' if optimal[['portfolio_pd','portfolio_cm','gmv']].notna().all().all() else '❌'}")
        print(f"All CM values finite:    {'✅' if np.isfinite(optimal['portfolio_cm'].values).all() else '❌'}")
        print(f"Binding zone captured:   {'✅' if optimal['portfolio_pd'].nunique() > 1 else '⚠️  PD constraint never binding in range'}")

    print("\n" + "=" * 65)
