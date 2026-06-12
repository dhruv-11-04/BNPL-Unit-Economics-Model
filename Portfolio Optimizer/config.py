# config.py
# Central configuration for the BNLP Portfolio Optimizer

# ── File paths ────────────────────────────────────────────────────────────────
WORKBOOK_PATH = "../Excel/BNPL Project.xlsx"

# ── Sheet names ───────────────────────────────────────────────────────────────
STRESS_ANALYSIS_SHEET = "Stress Analysis"
PORTFOLIO_METRICS_SHEET = "Stressed Portfolio Metrics"

# ── Stress Analysis layout constants ─────────────────────────────────────────
# Data starts at row 3 (0-indexed), 60 segment rows
DATA_START_ROW = 2
NUM_SEGMENTS = 60

# Column offsets within each scenario block (0-indexed relative to block start)
COL_OFFSETS = {
    "segment":           0,
    "generation":        1,
    "income_bracket":    2,
    "credit_tier":       3,
    "pd":                4,
    "ead":               5,
    "ats":               6,
    "revenue_per_loan":  7,
    "funding_cost":      8,
    "ecl":               9,
    "cm_per_loan":       10,
    "user_count":        11,
    "loan_count":        12,
    "avg_loan_per_user": 13,
    "arpu":              14,
    "cm_per_user":       15,
    "cm_per_segment":    16,
    "cm_contribution":   17,
}

# Absolute starting columns (0-indexed) for each scenario block
BLOCK_START_COLS = {
    "base":    0,
    "adverse": 20,
    "severe":  39,
}

# Fixed cost row location (absolute row index in the raw sheet)
FIXED_COST_ROW = 64     # row 64 contains the value 3
FIXED_COST_COL = 0      # column 0

# ── Column dtypes for standardized DataFrames ─────────────────────────────────
SEGMENT_DTYPES = {
    "segment_id":        int,
    "generation":        str,
    "income_bracket":    str,
    "credit_tier":       str,
    "pd":                float,
    "ead":               float,
    "ats":               float,
    "revenue_per_loan":  float,
    "funding_cost":      float,
    "ecl":               float,
    "cm_per_loan":       float,
    "user_count":        float,
    "loan_count":        float,
    "avg_loan_per_user": float,
    "arpu":              float,
    "cm_per_user":       float,
    "cm_per_segment":    float,
    "cm_contribution":   float,
}

# ── Optimizer parameters ──────────────────────────────────────────────────────
WEIGHT_MIN = 0.0
WEIGHT_MAX = 0.20

# Objective weights (Base, Adverse, Severe)
OBJ_WEIGHT_BASE    = 0.5
OBJ_WEIGHT_ADVERSE = 0.3
OBJ_WEIGHT_SEVERE  = 0.2

# ── Efficient frontier ────────────────────────────────────────────────────────
FRONTIER_STEPS = 40          # number of PD cap levels to evaluate
FRONTIER_GMV_FLOOR = 0.90    # default GMV retention floor for frontier runs

# ── Canonical credit tier ordering (Deep → Super Prime) ──────────────────────
CREDIT_TIER_ORDER = [
    "Deep Subprime",
    "Sub Prime",
    "Near Prime",
    "Prime",
    "Super Prime",
]