"""
BNPL Portfolio Optimizer — Streamlit Dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data_loader import load_stress_analysis
from portfolio import current_weights, portfolio_metrics, portfolio_gmv, weighted_pd
from optimizer import optimize
from config import (
    WEIGHT_MIN, WEIGHT_MAX,
    OBJ_WEIGHT_BASE, OBJ_WEIGHT_ADVERSE, OBJ_WEIGHT_SEVERE,
)
from ui_helpers import (
    compute_baseline_metrics,
    build_allocation_tables,
    build_generation_mix,
    build_credit_tier_mix,
    fmt_cm,
    fmt_cm_delta,
    fmt_pd,
    fmt_pd_pct,
    fmt_pd_delta_bps,
    fmt_gmv,
    fmt_pct,
    delta_color,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BNPL Portfolio Optimizer",
    page_icon="📊",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    .metric-card {
        background: #181825;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 18px 20px 14px 20px;
        height: 100%;
    }
    .metric-label {
        font-size: 11px;
        color: #6c7086;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
        font-weight: 600;
    }
    .metric-current {
        font-size: 13px;
        color: #7f849c;
        margin-bottom: 4px;
    }
    .metric-current span { color: #bac2de; font-weight: 600; }
    .metric-opt {
        font-size: 20px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 6px;
    }
    .metric-delta { font-size: 12px; opacity: 0.85; }
    .metric-divider {
        border: none;
        border-top: 1px solid #313244;
        margin: 8px 0;
    }
    .pos { color: #a6e3a1; }
    .neg { color: #f38ba8; }
    .neu { color: #585b70; font-style: italic; font-size: 13px; }

    .section-header {
        font-size: 15px;
        font-weight: 700;
        color: #cdd6f4;
        letter-spacing: 0.02em;
        border-bottom: 1px solid #313244;
        padding-bottom: 10px;
        margin-bottom: 20px;
        margin-top: 8px;
    }

    /* Objective function pill */
    .obj-banner {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 12px 20px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .obj-label {
        font-size: 11px;
        color: #6c7086;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        white-space: nowrap;
    }
    .obj-formula {
        font-size: 13px;
        color: #cdd6f4;
        font-family: monospace;
        letter-spacing: 0.02em;
    }
    .obj-w-base    { color: #89b4fa; font-weight: 700; }
    .obj-w-adverse { color: #f9e2af; font-weight: 700; }
    .obj-w-severe  { color: #f38ba8; font-weight: 700; }

    [data-testid="stSidebar"] { background: #11111b; }
    [data-testid="stSidebar"] .stSlider > label { font-size: 13px; }

    .alloc-header {
        font-size: 13px;
        font-weight: 600;
        color: #a6adc8;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ── Data loading (cached) ─────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading workbook…")
def load_data():
    base_df, adverse_df, severe_df, fixed_cost = load_stress_analysis()
    return base_df, adverse_df, severe_df, fixed_cost

base_df, adverse_df, severe_df, fixed_cost = load_data()
N_default  = float(base_df["loan_count"].sum())
w_cur      = current_weights(base_df)
cur_pd_adv = weighted_pd(w_cur, adverse_df)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Optimizer Settings")
    st.markdown("---")

    total_loans_m = st.number_input(
        "Total Portfolio Size (M loans)",
        min_value=50.0,
        max_value=2000.0,
        value=float(round(N_default, 1)),
        step=10.0,
        help="Total number of loans in millions. Changes GMV and all revenue totals proportionally.",
    )

    # Risk constraints — hardcoded to values that are permissive enough
    # to never interfere with RD / TO optimisation.
    # PD cap: 1.10× current adverse PD (10% headroom above current portfolio).
    # GMV floor: 85% retention — generous enough to not bind under normal RD ranges.
    pd_cap    = cur_pd_adv * 1.10
    gmv_floor = 0.85

    st.markdown("**Rebalancing Flexibility**")

    _rd_options = ["20%", "25%", "30%", "40%", "50%"]
    _rd_str = st.select_slider(
        "Per-Segment Rebalancing Limit",
        options=_rd_options,
        value="25%",
        help="Maximum fractional change per segment weight. 30% means each segment can move ±30% of its current allocation.",
    )
    relative_delta = float(_rd_str.strip("%")) / 100
    st.caption("Controls how aggressively the optimizer can shift segment allocations.")

    turnover_budget = st.slider(
        "Portfolio Reallocation Budget (Turnover Cap)",
        min_value=0.01,
        max_value=0.30,
        value=0.10,
        step=0.01,
        format="%.2f",
        help=(
            "Global one-way turnover cap: 0.5 × Σ|w_i − w_cur_i| ≤ this value. "
            "At 10% no more than 10% of the total portfolio weight can be "
            "redistributed in aggregate."
        ),
    )
    st.caption(f"Max one-way reallocation: **{turnover_budget:.0%}** of total portfolio weight.")

    st.markdown("---")
    run_btn = st.button("🚀 Optimize Portfolio", use_container_width=True, type="primary")

# ── Session state ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "run_params" not in st.session_state:
    st.session_state.run_params = {}
if "operating_grid" not in st.session_state:
    st.session_state.operating_grid = None

if run_btn:
    _data = (base_df, adverse_df, severe_df, fixed_cost)

    with st.spinner("Running optimizer…"):
        result = optimize(
            pd_cap=pd_cap,
            gmv_floor=gmv_floor,
            total_loans_m=total_loans_m,
            fixed_cost=fixed_cost,
            relative_delta=relative_delta,
            turnover_budget=turnover_budget,
            _data=_data,
        )

    _RD_GRID = [0.20, 0.25, 0.30, 0.40, 0.50]
    _TO_GRID = [0.05, 0.075, 0.10, 0.15, 0.20]

    with st.spinner(f"Computing operating region ({len(_RD_GRID) * len(_TO_GRID)} grid cells)…"):
        operating_grid = {}
        for _rd in _RD_GRID:
            for _to in _TO_GRID:
                _r = optimize(
                    pd_cap=pd_cap,
                    gmv_floor=gmv_floor,
                    total_loans_m=total_loans_m,
                    fixed_cost=fixed_cost,
                    relative_delta=_rd,
                    turnover_budget=_to,
                    _data=_data,
                )
                if _r.status == "optimal":
                    _w = _r.weights
                    _w_cur_local = current_weights(base_df)
                    _deep_sub = float(sum(
                        _w[_i] for _i in range(len(_w))
                        if base_df.iloc[_i]["credit_tier"] == "Deep Subprime"
                    ))
                    _prime_sp = float(sum(
                        _w[_i] for _i in range(len(_w))
                        if base_df.iloc[_i]["credit_tier"] in ("Prime", "Super Prime")
                    ))
                    _to_used = 0.5 * float(np.sum(np.abs(_w - _w_cur_local)))
                    operating_grid[(_rd, _to)] = {
                        "status":   "optimal",
                        "adv_cm":   _r.metrics_adverse["cm"],
                        "sev_cm":   _r.metrics_severe["cm"],
                        "adv_pd":   _r.metrics_adverse["pd"],
                        "deep_sub": _deep_sub,
                        "prime_sp": _prime_sp,
                        "to_used":  _to_used,
                    }
                else:
                    operating_grid[(_rd, _to)] = {
                        "status": _r.status,
                    }

    st.session_state.result        = result
    st.session_state.operating_grid = operating_grid
    st.session_state.run_params    = dict(
        pd_cap=pd_cap, gmv_floor=gmv_floor,
        total_loans_m=total_loans_m, relative_delta=relative_delta,
        turnover_budget=turnover_budget,
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# BNPL Portfolio Optimizer")
st.markdown(
    "<p style='color:#7f849c; font-size:15px; margin-top:-8px; margin-bottom:20px;'>"
    "Stress-adjusted origination mix optimizer across 60 Generation × Income × Credit segments."
    "</p>",
    unsafe_allow_html=True,
)

result = st.session_state.result

if result is None:
    st.info("👈  Configure parameters in the sidebar and click **Optimize Portfolio** to run.")
elif result.status != "optimal":
    st.error(f"**Optimizer returned: {result.status}**  \n{result.infeasibility_reason}")

# ── Baseline ──────────────────────────────────────────────────────────────────
baseline = compute_baseline_metrics(
    base_df, adverse_df, severe_df, fixed_cost, total_loans_m, w_cur
)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — KPI COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">① Portfolio KPI Comparison</div>', unsafe_allow_html=True)

# ── Objective function banner ─────────────────────────────────────────────────
st.markdown(
    f"""
<div class="obj-banner">
  <span class="obj-label">Maximizing</span>
  <span class="obj-formula">
    <span class="obj-w-base">{OBJ_WEIGHT_BASE:.0%} × Base CM</span>
    &nbsp;+&nbsp;
    <span class="obj-w-adverse">{OBJ_WEIGHT_ADVERSE:.0%} × Adverse CM</span>
    &nbsp;+&nbsp;
    <span class="obj-w-severe">{OBJ_WEIGHT_SEVERE:.0%} × Severe CM</span>
  </span>
</div>
""",
    unsafe_allow_html=True,
)

# ── 5 KPI cards (Objective CM removed) ───────────────────────────────────────
kpis = [
    ("Base CM",    "base_cm", fmt_cm,  True,  "Contribution margin under base (no-stress) scenario"),
    ("Adverse CM", "adv_cm",  fmt_cm,  True,  "CM under adverse macro stress"),
    ("Severe CM",  "sev_cm",  fmt_cm,  True,  "CM under severely adverse macro stress"),
    ("Adverse PD", "adv_pd",  fmt_pd,  False, "Loan-count weighted probability of default (adverse scenario)"),
    ("GMV",        "gmv",     fmt_gmv, True,  "Gross Merchandise Value at base-scenario ATS (billions)"),
]

cols = st.columns(len(kpis))
for col, (label, key, fmt, higher_is_better, tooltip) in zip(cols, kpis):
    cur_val = baseline[key]
    opt_val = None
    if result is not None and result.status == "optimal":
        opt_map = {
            "base_cm": result.metrics_base["cm"],
            "adv_cm":  result.metrics_adverse["cm"],
            "sev_cm":  result.metrics_severe["cm"],
            "adv_pd":  result.metrics_adverse["pd"],
            "gmv":     result.metrics_base["gmv"],
        }
        opt_val = opt_map[key]

    with col:
        if opt_val is not None:
            improved = (opt_val > cur_val) if higher_is_better else (opt_val < cur_val)
            css_cls  = "pos" if improved else "neg"

            if key == "adv_pd":
                cur_display = fmt_pd_pct(cur_val)
                opt_display = fmt_pd_pct(opt_val)
                delta_str   = fmt_pd_delta_bps(cur_val, opt_val)
            else:
                delta       = opt_val - cur_val
                pct         = (delta / abs(cur_val) * 100) if cur_val != 0 else 0
                sign        = "+" if delta >= 0 else "-"
                cur_display = fmt(cur_val)
                opt_display = fmt(opt_val)
                delta_str   = f"{sign}{fmt_cm_delta(delta)} ({sign}{abs(pct):.1f}%)"

            st.markdown(f"""
<div class="metric-card" title="{tooltip}">
  <div class="metric-label">{label}</div>
  <div class="metric-current">Current: <span>{cur_display}</span></div>
  <hr class="metric-divider">
  <div class="metric-opt {css_cls}">{opt_display}</div>
  <div class="metric-delta {css_cls}">{delta_str}</div>
</div>""", unsafe_allow_html=True)
        else:
            cur_display = fmt_pd_pct(cur_val) if key == "adv_pd" else fmt(cur_val)
            st.markdown(f"""
<div class="metric-card" title="{tooltip}">
  <div class="metric-label">{label}</div>
  <div class="metric-current"><span>{cur_display}</span></div>
  <hr class="metric-divider">
  <div class="neu">Run optimizer →</div>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ALLOCATION CHANGES
# ═══════════════════════════════════════════════════════════════════════════════
if result is not None and result.status == "optimal":
    st.markdown("---")
    st.markdown('<div class="section-header">② Allocation Changes</div>', unsafe_allow_html=True)

    increases_df, reductions_df = build_allocation_tables(base_df, w_cur, result.weights, top_n=6)

    col_inc, col_red = st.columns(2)
    with col_inc:
        st.markdown(
            "<div class='alloc-header'>"
            "<span style='color:#a6e3a1; font-size:16px;'>▲</span> Top Increases"
            "</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            increases_df.style
                .format({"Current Weight": "{:.2%}", "Optimized Weight": "{:.2%}", "Change": "{:+.2%}"})
                .map(lambda v: "color: #a6e3a1; font-weight:600" if isinstance(v, float) and v > 0 else "",
                     subset=["Change"]),
            use_container_width=True,
            hide_index=True,
        )
    with col_red:
        st.markdown(
            "<div class='alloc-header'>"
            "<span style='color:#f38ba8; font-size:16px;'>▼</span> Top Reductions"
            "</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            reductions_df.style
                .format({"Current Weight": "{:.2%}", "Optimized Weight": "{:.2%}", "Change": "{:+.2%}"})
                .map(lambda v: "color: #f38ba8; font-weight:600" if isinstance(v, float) and v < 0 else "",
                     subset=["Change"]),
            use_container_width=True,
            hide_index=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PORTFOLIO MIX COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">③ Portfolio Mix Comparison</div>', unsafe_allow_html=True)

if result is None or result.status != "optimal":
    st.caption("Run the optimizer to see the optimized segment mix alongside the current portfolio.")

w_opt_for_mix = result.weights if (result is not None and result.status == "optimal") else None

CHART_BGCOLOR   = "#181825"
CHART_PAPER     = "#181825"
CHART_FONT      = "#cdd6f4"
GRID_COLOR      = "#313244"
COLOR_CURRENT   = "#89b4fa"
COLOR_OPTIMIZED = "#a6e3a1"

col_gen, col_credit = st.columns(2)

with col_gen:
    gen_df = build_generation_mix(base_df, w_cur, w_opt_for_mix)
    fig_gen = go.Figure()
    fig_gen.add_trace(go.Bar(
        name="Current",
        x=gen_df["Generation"],
        y=gen_df["Current"],
        marker_color=COLOR_CURRENT,
        marker_opacity=0.85,
        text=[f"{v:.1%}" for v in gen_df["Current"]],
        textposition="outside",
        textfont=dict(size=11),
    ))
    if w_opt_for_mix is not None:
        fig_gen.add_trace(go.Bar(
            name="Optimized",
            x=gen_df["Generation"],
            y=gen_df["Optimized"],
            marker_color=COLOR_OPTIMIZED,
            marker_opacity=0.85,
            text=[f"{v:.1%}" for v in gen_df["Optimized"]],
            textposition="outside",
            textfont=dict(size=11),
        ))
    fig_gen.update_layout(
        title=dict(text="Generation Mix", font=dict(size=14), x=0),
        barmode="group", bargap=0.25, bargroupgap=0.08,
        yaxis=dict(tickformat=".0%", title="Portfolio Weight", gridcolor=GRID_COLOR, showgrid=True),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=12)),
        plot_bgcolor=CHART_BGCOLOR, paper_bgcolor=CHART_PAPER,
        font=dict(color=CHART_FONT, size=12),
        margin=dict(t=40, b=10, l=10, r=10), height=300,
    )
    st.plotly_chart(fig_gen, use_container_width=True, config={"displayModeBar": False})

with col_credit:
    credit_df = build_credit_tier_mix(base_df, w_cur, w_opt_for_mix)
    fig_credit = go.Figure()
    fig_credit.add_trace(go.Bar(
        name="Current",
        x=credit_df["Credit Tier"],
        y=credit_df["Current"],
        marker_color=COLOR_CURRENT,
        marker_opacity=0.85,
        text=[f"{v:.1%}" for v in credit_df["Current"]],
        textposition="outside",
        textfont=dict(size=11),
    ))
    if w_opt_for_mix is not None:
        fig_credit.add_trace(go.Bar(
            name="Optimized",
            x=credit_df["Credit Tier"],
            y=credit_df["Optimized"],
            marker_color=COLOR_OPTIMIZED,
            marker_opacity=0.85,
            text=[f"{v:.1%}" for v in credit_df["Optimized"]],
            textposition="outside",
            textfont=dict(size=11),
        ))
    fig_credit.update_layout(
        title=dict(text="Credit Tier Mix", font=dict(size=14), x=0),
        barmode="group", bargap=0.25, bargroupgap=0.08,
        yaxis=dict(tickformat=".0%", title="Portfolio Weight", gridcolor=GRID_COLOR, showgrid=True),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=12)),
        plot_bgcolor=CHART_BGCOLOR, paper_bgcolor=CHART_PAPER,
        font=dict(color=CHART_FONT, size=12),
        margin=dict(t=40, b=10, l=10, r=10), height=300,
    )
    st.plotly_chart(fig_credit, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — PORTFOLIO OPERATING REGION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="section-header">④ Portfolio Operating Region Analysis</div>', unsafe_allow_html=True)

operating_grid = st.session_state.get("operating_grid", None)

if operating_grid is None:
    st.caption(
        "Run the optimizer to generate the RD × TO operating region analysis. "
        "The grid computes 25 optimizer runs across all Per-Segment Limit × Turnover combinations."
    )
else:
    _RD_VALS = [0.20, 0.25, 0.30, 0.40, 0.50]
    _TO_VALS = [0.05, 0.075, 0.10, 0.15, 0.20]

    # ── Supporting table ──────────────────────────────────────────
    with st.expander("Operating region data table", expanded=True):
        rp = st.session_state.run_params
        st.caption(
            f"PD cap: **{rp.get('pd_cap', 0):.4f}** ({rp.get('pd_cap', 0)*100:.3f}%)  ·  "
            f"GMV floor: **{rp.get('gmv_floor', 0):.0%}**  ·  "
            f"Portfolio size: **{rp.get('total_loans_m', 0):.1f}M loans**"
        )

        table_rows = []
        for rd in _RD_VALS:
            for to in _TO_VALS:
                cell = operating_grid.get((rd, to), {})
                is_rec = (rd == 0.25 and to == 0.10)
                if cell.get("status") == "optimal":
                    table_rows.append({
                        "Seg Limit":   f"{'★ ' if is_rec else ''}{rd:.0%}",
                        "TO":          f"{to:.1%}",
                        "Adv CM ($M)": cell["adv_cm"],
                        "Sev CM ($M)": cell["sev_cm"],
                        "Adv PD":      cell["adv_pd"],
                        "Deep Sub %":  cell["deep_sub"],
                        "Prime+SP %":  cell["prime_sp"],
                        "TO Used %":   cell["to_used"],
                    })
                else:
                    table_rows.append({
                        "Seg Limit":   f"{rd:.0%}",
                        "TO":          f"{to:.1%}",
                        "Adv CM ($M)": None,
                        "Sev CM ($M)": None,
                        "Adv PD":      None,
                        "Deep Sub %":  None,
                        "Prime+SP %":  None,
                        "TO Used %":   None,
                    })

        table_df = pd.DataFrame(table_rows)

        def _fmt_cm_cell(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return "—"
            sign = "+" if v >= 0 else "-"
            return f"{sign}${abs(v):,.1f}M"

        def _fmt_pct_cell(v):
            return "—" if v is None else f"{v:.2%}"

        def _fmt_pd_cell(v):
            return "—" if v is None else f"{v*100:.3f}%"

        def _color_adv_cm(v):
            if not isinstance(v, str) or v == "—":
                return ""
            # Strip star and parse
            clean = v.replace("★ ", "").replace("+", "").replace("$", "").replace("M", "").replace(",", "")
            try:
                num = float(clean)
                return "color: #a6e3a1; font-weight:600" if num >= 0 else "color: #f38ba8"
            except Exception:
                return ""

        styled = table_df.style.format({
            "Adv CM ($M)": _fmt_cm_cell,
            "Sev CM ($M)": _fmt_cm_cell,
            "Adv PD":      _fmt_pd_cell,
            "Deep Sub %":  _fmt_pct_cell,
            "Prime+SP %":  _fmt_pct_cell,
            "TO Used %":   _fmt_pct_cell,
        }).map(
            lambda v: "color: #a6e3a1; font-weight:600" if isinstance(v, float) and v >= 0
                      else ("color: #f38ba8" if isinstance(v, float) and v < 0 else ""),
            subset=["Adv CM ($M)", "Sev CM ($M)"],
        )

        st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Objective: {OBJ_WEIGHT_BASE:.0%} × Base CM  +  {OBJ_WEIGHT_ADVERSE:.0%} × Adverse CM  +  "
    f"{OBJ_WEIGHT_SEVERE:.0%} × Severe CM  ·  "
    f"Segment bounds: [{WEIGHT_MIN:.1%}, {WEIGHT_MAX:.0%}]  ·  "
    "All values in USD"
)