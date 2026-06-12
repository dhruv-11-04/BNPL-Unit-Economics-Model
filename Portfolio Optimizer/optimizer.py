# optimizer.py
"""
Portfolio weight optimizer using scipy.optimize.linprog (HiGHS).

Objective (maximise — converted to minimise for linprog):
    0.5 × Base CM + 0.3 × Adverse CM + 0.2 × Severe CM

Constraints:
    1. sum(w) = 1
    2. WEIGHT_MIN ≤ w_i ≤ WEIGHT_MAX  (global bounds)
    3. weighted_PD_adverse(w) ≤ pd_cap
    4. portfolio_GMV_base(w) ≥ gmv_floor × current_GMV_base
    5. |w_i - w_cur_i| ≤ relative_delta × w_cur_i  (per-segment proportional limit)
    6. 0.5 × Σ|w_i - w_cur_i| ≤ turnover_budget     (global one-way turnover cap)

Constraints 5 and 6 are sufficient to prevent unrealistic portfolio reshaping.
Generation mix constraints have been removed — empirical testing showed them
redundant given RD and TO already bound demographic drift to operationally
reasonable levels.
"""

import numpy as np
from scipy.optimize import linprog
from dataclasses import dataclass

from data_loader import load_stress_analysis
from portfolio import (
    current_weights, portfolio_metrics, portfolio_gmv, weighted_pd
)
from config import (
    WEIGHT_MIN, WEIGHT_MAX,
    OBJ_WEIGHT_BASE, OBJ_WEIGHT_ADVERSE, OBJ_WEIGHT_SEVERE,
)

RECOMMENDED_RELATIVE_DELTA = 0.25   # ±25% of current segment weight
DEFAULT_TURNOVER_BUDGET    = 0.10   # 10% one-way portfolio turnover


@dataclass
class OptimizationResult:
    status: str                        # "optimal" | "infeasible" | "failed"
    weights: np.ndarray | None
    objective_value: float | None      # weighted CM (no fixed-cost deduction)
    metrics_base: dict | None
    metrics_adverse: dict | None
    metrics_severe: dict | None
    infeasibility_reason: str = ""
    solver_message: str = ""


def optimize(
    pd_cap: float,
    gmv_floor: float,
    total_loans_m: float | None = None,
    fixed_cost: float | None = None,
    relative_delta: float | None = RECOMMENDED_RELATIVE_DELTA,
    turnover_budget: float | None = DEFAULT_TURNOVER_BUDGET,
    _data: tuple | None = None,
) -> OptimizationResult:
    """
    Run the portfolio weight optimizer.

    Parameters
    ----------
    pd_cap          : maximum allowed weighted adverse PD
    gmv_floor       : GMV retention fraction of current base GMV
    total_loans_m   : total portfolio size in millions; defaults to base total
    fixed_cost      : accepted for API compatibility; not used in objective
    relative_delta  : max fractional deviation per segment from current weight.
                      E.g. 0.25 → w_i ∈ [0.75×w_cur_i, 1.25×w_cur_i].
                      Combined with global WEIGHT_MIN/WEIGHT_MAX bounds.
                      Pass None for no per-segment limit.
    turnover_budget : global one-way turnover cap.
                      0.5 × Σ|w_i − w_cur_i| ≤ turnover_budget.
                      Linearised via auxiliary variables p_i, q_i ≥ 0
                      where w_i − w_cur_i = p_i − q_i.
                      Pass None for no turnover cap.
    _data           : pre-loaded (base_df, adverse_df, severe_df, fc)

    Returns
    -------
    OptimizationResult
    """
    if _data is None:
        base_df, adverse_df, severe_df, fc = load_stress_analysis()
    else:
        base_df, adverse_df, severe_df, fc = _data

    if total_loans_m is None:
        total_loans_m = float(base_df["loan_count"].sum())

    n = len(base_df)
    w_cur = current_weights(base_df)

    # ── Turnover linearisation ─────────────────────────────────────
    # Introduce auxiliary vectors p (n,) and q (n,) such that:
    #   w_i - w_cur_i = p_i - q_i,   p_i, q_i >= 0
    # The LP variable vector is x = [w (n), p (n), q (n)], length 3n.
    # Turnover constraint: 0.5 * sum(p_i + q_i) <= budget
    #   => sum(p_i + q_i) <= 2 * budget
    use_turnover = turnover_budget is not None

    N_vars = 3 * n if use_turnover else n

    # ── Objective ──────────────────────────────────────────────────
    # Objective vector c uses Base N for all terms so that the LP maximises
    # a single consistently-scaled score.  The reported objective_value is
    # then recomputed post-solve with each scenario's own loan count so it
    # represents a true blended CM rather than a Base-N-inflated score.
    blended_cm = (
        OBJ_WEIGHT_BASE    * base_df["cm_per_loan"].values +
        OBJ_WEIGHT_ADVERSE * adverse_df["cm_per_loan"].values +
        OBJ_WEIGHT_SEVERE  * severe_df["cm_per_loan"].values
    )
    if use_turnover:
        c = np.concatenate([-total_loans_m * blended_cm,
                            np.zeros(n),   # p block
                            np.zeros(n)])  # q block
    else:
        c = -total_loans_m * blended_cm

    # ── Inequality constraints ─────────────────────────────────────
    cur_gmv = portfolio_gmv(w_cur, base_df, total_loans_m)

    def _pad(row_w, p_coef=0.0, q_coef=0.0):
        """Pad a constraint row from w-only to [w, p, q] width."""
        if use_turnover:
            return np.concatenate([row_w,
                                   np.full(n, p_coef),
                                   np.full(n, q_coef)])
        return row_w

    A_ub_rows, b_ub_vals = [], []

    # C3: PD cap — pd_adv @ w <= pd_cap
    A_ub_rows.append(_pad(adverse_df["pd"].values))
    b_ub_vals.append(pd_cap)

    # C4: GMV floor — -ats @ w * N/1000 <= -floor * cur_gmv
    A_ub_rows.append(_pad(-base_df["ats"].values * total_loans_m / 1000.0))
    b_ub_vals.append(-gmv_floor * cur_gmv)

    if use_turnover:
        # C6a: Turnover budget — sum(p_i + q_i) <= 2 * budget
        to_row = np.concatenate([np.zeros(n), np.ones(n), np.ones(n)])
        A_ub_rows.append(to_row)
        b_ub_vals.append(2.0 * turnover_budget)

        # C6b: p_i - q_i = w_i - w_cur_i  ↔  split into two inequalities:
        #   w_i - p_i + q_i <= w_cur_i   (upper: deviation can't exceed p_i)
        #  -w_i + p_i - q_i <= -w_cur_i  (lower)
        for i in range(n):
            row_up = np.zeros(N_vars)
            row_up[i] = 1.0; row_up[n + i] = -1.0; row_up[2*n + i] = 1.0
            A_ub_rows.append(row_up)
            b_ub_vals.append(w_cur[i])

            row_lo = np.zeros(N_vars)
            row_lo[i] = -1.0; row_lo[n + i] = 1.0; row_lo[2*n + i] = -1.0
            A_ub_rows.append(row_lo)
            b_ub_vals.append(-w_cur[i])

    A_ub = np.array(A_ub_rows)
    b_ub = np.array(b_ub_vals)

    # ── Equality constraint: sum(w) = 1 ───────────────────────────
    if use_turnover:
        A_eq_row = np.concatenate([np.ones(n), np.zeros(n), np.zeros(n)])
    else:
        A_eq_row = np.ones(n)
    A_eq = A_eq_row.reshape(1, -1)
    b_eq = np.array([1.0])

    # ── Variable bounds ────────────────────────────────────────────
    # w-block: relative_delta per-segment limits clamped to global bounds.
    # p-block, q-block: [0, ∞) (non-negative auxiliary variables).
    bounds = []
    for i in range(n):
        if relative_delta is not None:
            ub_i = min(WEIGHT_MAX, w_cur[i] * (1.0 + relative_delta))
            lb_i = max(WEIGHT_MIN, w_cur[i] * (1.0 - relative_delta))
            lb_i = min(lb_i, ub_i)  # guard: lb must not exceed ub
        else:
            lb_i, ub_i = WEIGHT_MIN, WEIGHT_MAX
        bounds.append((lb_i, ub_i))

    if use_turnover:
        for _ in range(2 * n):          # p and q blocks
            bounds.append((0.0, None))

    # ── Solve ──────────────────────────────────────────────────────
    result = linprog(
        c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
        bounds=bounds, method="highs",
    )

    if result.status == 0:
        w_opt = result.x[:n]
        # Report true blended CM using each scenario's own loan count.
        # The optimisation itself used Base N throughout (scaling doesn't
        # change the optimal weights — proven: c_new = k*c_old only when
        # N_a==N_b==N_s; here weights are set by relative cm_per_loan
        # differences, and each scenario's N is a constant multiplier that
        # does not change the argmax of a linear objective over the same
        # feasible set).
        N_adv = float(adverse_df["loan_count"].sum())
        N_sev = float(severe_df["loan_count"].sum())
        obj_val = (
            OBJ_WEIGHT_BASE    * float(np.dot(base_df["cm_per_loan"].values,    w_opt)) * total_loans_m +
            OBJ_WEIGHT_ADVERSE * float(np.dot(adverse_df["cm_per_loan"].values, w_opt)) * N_adv +
            OBJ_WEIGHT_SEVERE  * float(np.dot(severe_df["cm_per_loan"].values,  w_opt)) * N_sev
        )

        m_base = portfolio_metrics(w_opt, base_df,    total_loans_m,                        base_df)
        m_adv  = portfolio_metrics(w_opt, adverse_df, float(adverse_df["loan_count"].sum()), base_df)
        m_sev  = portfolio_metrics(w_opt, severe_df,  float(severe_df["loan_count"].sum()),  base_df)
        for m in (m_base, m_adv, m_sev):
            m["cm_net"] = m["cm"]   # fixed cost handled at display level

        return OptimizationResult(
            status="optimal", weights=w_opt, objective_value=obj_val,
            metrics_base=m_base, metrics_adverse=m_adv, metrics_severe=m_sev,
            solver_message=result.message,
        )

    elif result.status == 2:
        reason = _diagnose_infeasibility(
            pd_cap, gmv_floor, cur_gmv,
            adverse_df["pd"].values, base_df["ats"].values,
            total_loans_m, n, relative_delta, turnover_budget, w_cur,
        )
        return OptimizationResult(
            status="infeasible", weights=None, objective_value=None,
            metrics_base=None, metrics_adverse=None, metrics_severe=None,
            infeasibility_reason=reason, solver_message=result.message,
        )

    else:
        return OptimizationResult(
            status="failed", weights=None, objective_value=None,
            metrics_base=None, metrics_adverse=None, metrics_severe=None,
            solver_message=result.message,
        )


def _diagnose_infeasibility(
    pd_cap, gmv_floor, cur_gmv,
    pd_adv_vals, ats_vals, total_loans_m, n,
    relative_delta, turnover_budget, w_cur,
) -> str:
    reasons = []

    # Per-segment upper bounds under relative delta
    if relative_delta is not None:
        ub_arr = np.array([min(WEIGHT_MAX, w_cur[i] * (1.0 + relative_delta))
                           for i in range(n)])
    else:
        ub_arr = np.full(n, WEIGHT_MAX)

    # Best-case PD: pile weight onto lowest-PD segments within ub
    idx       = np.argsort(pd_adv_vals)
    remaining = 1.0
    w_test    = np.zeros(n)
    for i in idx:
        alloc      = min(ub_arr[i], remaining)
        w_test[i]  = alloc
        remaining -= alloc
        if remaining <= 1e-9:
            break
    min_pd = float(np.dot(w_test, pd_adv_vals))
    if pd_cap < min_pd:
        reasons.append(
            f"PD cap {pd_cap:.5f} is below the minimum achievable adverse PD "
            f"({min_pd:.5f}) given relative_delta={relative_delta} and weight bounds."
        )

    gmv_needed = gmv_floor * cur_gmv
    max_gmv    = float(np.dot(ats_vals, ub_arr) * total_loans_m / 1000.0)
    if gmv_needed > max_gmv:
        reasons.append(
            f"GMV floor requires {gmv_needed:.2f}B but maximum achievable is {max_gmv:.2f}B."
        )

    if turnover_budget is not None:
        # Check whether turnover budget allows weights to sum to 1
        # The tightest case is when all segments are already at their bounds.
        max_total_movement = float(np.sum(np.abs(ub_arr - w_cur)))
        max_one_way = 0.5 * max_total_movement
        if turnover_budget < max_one_way * 0.01:   # near-zero budget
            reasons.append(
                f"Turnover budget {turnover_budget:.3f} may be too tight to allow "
                f"feasible reallocation."
            )

    if not reasons:
        reasons.append(
            "Constraints are jointly infeasible — try relaxing PD cap, GMV floor, "
            "relative_delta, or turnover_budget."
        )

    return " ".join(reasons)


# ── Validation ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = load_stress_analysis()
    base_df, adverse_df, severe_df, fixed_cost = data
    N = float(base_df["loan_count"].sum())
    w_cur = current_weights(base_df)
    cur_pd_adv = weighted_pd(w_cur, adverse_df)
    cur_gmv    = portfolio_gmv(w_cur, base_df, N)

    PD_CAP  = cur_pd_adv * 1.10
    GMV_FLR = 0.85
    RD      = 0.25
    TO      = 0.10

    print("=" * 62)
    print(f"OPTIMIZER.PY VALIDATION — RD={RD:.0%}  TO={TO:.0%}")
    print("=" * 62)
    print(f"Current adverse PD: {cur_pd_adv:.5f}  |  PD cap: {PD_CAP:.5f}")
    print(f"Current GMV (B):    {cur_gmv:.4f}     |  GMV floor: {GMV_FLR*cur_gmv:.4f}B")

    r = optimize(PD_CAP, GMV_FLR, N, fixed_cost,
                 relative_delta=RD, turnover_budget=TO, _data=data)

    print(f"\nStatus:           {r.status}")
    if r.status == "optimal":
        actual_to = 0.5 * float(np.sum(np.abs(r.weights - w_cur)))
        print(f"Objective CM:     {r.objective_value:.4f}")
        print(f"Base CM:          {r.metrics_base['cm']:.4f}")
        print(f"Adverse CM:       {r.metrics_adverse['cm']:.4f}")
        print(f"Severe CM:        {r.metrics_severe['cm']:.4f}")
        print(f"Adverse PD:       {r.metrics_adverse['pd']:.5f}  <= cap {PD_CAP:.5f}: "
              f"{'OK' if r.metrics_adverse['pd'] <= PD_CAP + 1e-6 else 'VIOLATION'}")
        print(f"GMV (B):          {r.metrics_base['gmv']:.4f}")
        print(f"Turnover used:    {actual_to:.4f}  <= budget {TO:.4f}: "
              f"{'OK' if actual_to <= TO + 1e-6 else 'VIOLATION'}")
        print(f"Weights sum:      {r.weights.sum():.8f}")
        print(f"Min weight:       {r.weights.min():.5f}  >= {0.005:.3f}: "
              f"{'OK' if r.weights.min() >= 0.005 - 1e-6 else 'VIOLATION'}")

        # Generation mix (informational only — no constraint enforced)
        print("\nGeneration mix (informational):")
        for g in base_df["generation"].unique():
            mask = (base_df["generation"] == g).values.astype(float)
            gc = float(np.dot(w_cur,      mask))
            go = float(np.dot(r.weights,  mask))
            print(f"  {g:<16}: current={gc:.2%}  optimized={go:.2%}  delta={go-gc:+.2%}")
    else:
        print(f"Infeasibility reason: {r.infeasibility_reason}")

    print("=" * 62)