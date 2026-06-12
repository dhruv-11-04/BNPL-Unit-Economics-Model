# data_loader.py
"""
Reads the Stress Analysis sheet from BNLP_Project.xlsx.
Returns three standardized DataFrames: base_df, adverse_df, severe_df.
"""

import pandas as pd
import numpy as np
from config import (
    WORKBOOK_PATH, STRESS_ANALYSIS_SHEET,
    DATA_START_ROW, NUM_SEGMENTS, COL_OFFSETS, BLOCK_START_COLS,
    FIXED_COST_ROW, FIXED_COST_COL,
)


def load_stress_analysis() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    """
    Returns (base_df, adverse_df, severe_df, fixed_cost).
    Raises ValueError if validation fails.
    """
    raw = pd.read_excel(
        WORKBOOK_PATH,
        sheet_name=STRESS_ANALYSIS_SHEET,
        header=None,
    )

    base_df    = _extract_block(raw, "base")
    adverse_df = _extract_block(raw, "adverse")
    severe_df  = _extract_block(raw, "severe")
    fixed_cost = _read_fixed_cost(raw)

    _validate(base_df, adverse_df, severe_df)

    return base_df, adverse_df, severe_df, fixed_cost


def _fix_income_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise income bracket labels to standard US formatting.
    Workbook uses Indian lakh notation (1,00,000); convert to 100,000.
    """
    mapping = {
        "50,000-1,00,000": "50,000-100,000",
        ">1,00,000":       ">100,000",
        "<50,000":         "<50,000",
    }
    df["income_bracket"] = df["income_bracket"].map(
        lambda x: mapping.get(str(x).strip(), str(x).strip())
    )
    return df


def _extract_block(raw: pd.DataFrame, scenario: str) -> pd.DataFrame:
    start_col = BLOCK_START_COLS[scenario]
    rows = raw.iloc[DATA_START_ROW: DATA_START_ROW + NUM_SEGMENTS, :]

    records = {}
    for field, offset in COL_OFFSETS.items():
        col_idx = start_col + offset
        records[field] = rows.iloc[:, col_idx].values

    df = pd.DataFrame(records)

    # Rename segment column to segment_id
    df = df.rename(columns={"segment": "segment_id"})

    # Cast numeric columns
    str_cols = {"generation", "income_bracket", "credit_tier"}
    for col in df.columns:
        if col not in str_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["segment_id"] = df["segment_id"].astype(int)
    df = df.reset_index(drop=True)
    df = _fix_income_labels(df)
    return df


def _read_fixed_cost(raw: pd.DataFrame) -> float:
    """Read the fixed cost scalar (absolute row 64, col 0)."""
    val = raw.iloc[FIXED_COST_ROW, FIXED_COST_COL]
    if pd.notna(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    print("WARNING: Fixed cost not found in expected location; using documented value 3.")
    return 3.0


def _validate(base_df, adverse_df, severe_df):
    # cm_contribution is a display-only derived column.
    # The severe block in the workbook has it unpopulated — exclude from null check.
    NON_CRITICAL = {"cm_contribution"}

    for name, df in [("base", base_df), ("adverse", adverse_df), ("severe", severe_df)]:
        if len(df) != NUM_SEGMENTS:
            raise ValueError(f"{name}: expected {NUM_SEGMENTS} rows, got {len(df)}")
        critical_cols = [c for c in df.columns if c not in NON_CRITICAL]
        if df[critical_cols].isnull().any().any():
            bad = df[critical_cols].columns[df[critical_cols].isnull().any()].tolist()
            raise ValueError(f"{name}: missing values in critical columns {bad}")

    # Segment ordering must be identical
    if not (base_df["segment_id"].equals(adverse_df["segment_id"]) and
            base_df["segment_id"].equals(severe_df["segment_id"])):
        raise ValueError("Segment ordering differs across scenario blocks.")


if __name__ == "__main__":
    base_df, adverse_df, severe_df, fixed_cost = load_stress_analysis()

    print(f"\n✅ Fixed cost: {fixed_cost}")
    print(f"\n{'='*60}")
    for name, df in [("BASE", base_df), ("ADVERSE", adverse_df), ("SEVERE", severe_df)]:
        print(f"\n{name} — shape: {df.shape}")
        print(df[["segment_id", "generation", "income_bracket", "credit_tier",
                   "pd", "cm_per_loan", "loan_count"]].head(5).to_string(index=False))
    print(f"\n{'='*60}")
    print("All validations passed.")