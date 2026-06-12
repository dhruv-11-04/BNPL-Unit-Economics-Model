"""
ui_helpers.py
Helper functions for the Streamlit dashboard.
No optimization logic lives here — only data transformation and formatting.
"""

import numpy as np
import pandas as pd
from portfolio import current_weights, portfolio_metrics, portfolio_gmv, weighted_pd
from config import OBJ_WEIGHT_BASE, OBJ_WEIGHT_ADVERSE, OBJ_WEIGHT_SEVERE, CREDIT_TIER_ORDER


# ── Formatters ────────────────────────────────────────────────────────────────

def fmt_cm(val: float) -> str:
    """Format a CM value in $M with sign (for absolute values)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if val >= 0:
        return f"+${val:,.1f}M"
    return f"-${abs(val):,.1f}M"


def fmt_cm_delta(val: float) -> str:
    """
    Format a CM delta in $M WITHOUT a leading sign character.
    The call site prepends sign='+' or '-' to avoid double-sign (++$84.4M).
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"${abs(val):,.1f}M"


def fmt_pd(val: float) -> str:
    """Format a PD value as a raw decimal string (e.g. '0.0346')."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.4f}"


def fmt_pd_pct(val: float) -> str:
    """Format a PD value as a display percentage string (e.g. '3.46%')."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val * 100:.2f}%"


def fmt_pd_delta_bps(cur_val: float, opt_val: float) -> str:
    """
    Format a PD delta in basis points.
    Returns e.g. '↓111 bps' or '↑5 bps'.
    """
    bps = round((opt_val - cur_val) * 10_000)
    arrow = "↓" if bps < 0 else "↑"
    return f"{arrow}{abs(bps)} bps"


def fmt_gmv(val: float) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"${val:.2f}B"


def fmt_pct(val: float) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.2%}"


def delta_color(val: float, higher_is_better: bool = True) -> str:
    if val is None:
        return "neu"
    improved = (val > 0) if higher_is_better else (val < 0)
    return "pos" if improved else "neg"


# ── Baseline metrics ──────────────────────────────────────────────────────────

def compute_baseline_metrics(
    base_df, adverse_df, severe_df, fixed_cost, total_loans_m, w_cur
) -> dict:
    """
    Compute current portfolio metrics for the KPI comparison section.
    Uses the caller-supplied total_loans_m so baseline and optimized metrics
    are always computed at the same portfolio scale.

    NOTE: fixed_cost parameter is accepted for API compatibility but NOT deducted here.
    cm_per_loan already embeds the $3/loan fixed cost in the workbook formula:
        CM Per Loan = Revenue - Funding Cost - ECL - Fixed_Cost
    portfolio_metrics() gross CM therefore already matches the workbook Total CM exactly.
    """
    blended = (OBJ_WEIGHT_BASE    * base_df["cm_per_loan"].values +
               OBJ_WEIGHT_ADVERSE * adverse_df["cm_per_loan"].values +
               OBJ_WEIGHT_SEVERE  * severe_df["cm_per_loan"].values)
    obj_cur = float(np.dot(blended, w_cur) * total_loans_m)

    # Each scenario uses its own loan-count-derived weights and loan count total.
    # Base weights (w_cur) derive from base loan counts and apply only to the base
    # scenario. Adverse and severe have different per-segment loan counts (stress
    # contracts volume unevenly), so they require their own weight vectors.
    lc_adv = adverse_df["loan_count"].values.astype(float)
    lc_sev = severe_df["loan_count"].values.astype(float)
    w_adv  = lc_adv / lc_adv.sum()
    w_sev  = lc_sev / lc_sev.sum()
    N_adv  = float(lc_adv.sum())
    N_sev  = float(lc_sev.sum())

    m_b = portfolio_metrics(w_cur, base_df,    total_loans_m, base_df)
    m_a = portfolio_metrics(w_adv, adverse_df, N_adv,         base_df)
    m_s = portfolio_metrics(w_sev, severe_df,  N_sev,         base_df)

    return {
        "obj_cm":  obj_cur,
        "base_cm": m_b["cm"],
        "adv_cm":  m_a["cm"],
        "sev_cm":  m_s["cm"],
        "adv_pd":  m_a["pd"],
        "gmv":     m_b["gmv"],
    }


# ── Allocation tables ─────────────────────────────────────────────────────────

def build_allocation_tables(
    base_df,
    w_cur: np.ndarray,
    w_opt: np.ndarray,
    top_n: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (increases_df, reductions_df) — top_n rows each, sorted by |change|.
    """
    changes = w_opt - w_cur

    def _label(i):
        row = base_df.iloc[i]
        return f"{row['generation']} / {row['income_bracket']} / {row['credit_tier']}"

    records = [
        {
            "Segment": _label(i),
            "Current Weight": w_cur[i],
            "Optimized Weight": w_opt[i],
            "Change": changes[i],
        }
        for i in range(len(w_cur))
    ]
    df = pd.DataFrame(records)

    increases  = (df[df["Change"] > 1e-6]
                    .sort_values("Change", ascending=False)
                    .head(top_n)
                    .reset_index(drop=True))
    reductions = (df[df["Change"] < -1e-6]
                    .sort_values("Change", ascending=True)
                    .head(top_n)
                    .reset_index(drop=True))

    return increases, reductions


# ── Mix builders ──────────────────────────────────────────────────────────────

def build_generation_mix(
    base_df,
    w_cur: np.ndarray,
    w_opt: np.ndarray | None,
) -> pd.DataFrame:
    """Return DataFrame with columns [Generation, Current, Optimized]."""
    gens = base_df["generation"].unique()
    rows = []
    for g in gens:
        mask = (base_df["generation"] == g).values.astype(float)
        row = {
            "Generation": g,
            "Current": float(np.dot(w_cur, mask)),
        }
        if w_opt is not None:
            row["Optimized"] = float(np.dot(w_opt, mask))
        else:
            row["Optimized"] = None
        rows.append(row)
    return pd.DataFrame(rows)


def build_credit_tier_mix(
    base_df,
    w_cur: np.ndarray,
    w_opt: np.ndarray | None,
) -> pd.DataFrame:
    """
    Return DataFrame with columns [Credit Tier, Current, Optimized].
    Ordered by CREDIT_TIER_ORDER (Deep Subprime → Super Prime).
    """
    present = set(base_df["credit_tier"].unique())
    ordered = [t for t in CREDIT_TIER_ORDER if t in present]
    remainder = [t for t in present if t not in CREDIT_TIER_ORDER]
    tiers = ordered + remainder

    rows = []
    for t in tiers:
        mask = (base_df["credit_tier"] == t).values.astype(float)
        row = {
            "Credit Tier": t,
            "Current": float(np.dot(w_cur, mask)),
        }
        if w_opt is not None:
            row["Optimized"] = float(np.dot(w_opt, mask))
        else:
            row["Optimized"] = None
        rows.append(row)
    return pd.DataFrame(rows)