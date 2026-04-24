"""Build the vehicle-level at-risk rollup shown in dashboard View 3.

View 3 is the team leader's view — vehicle-first rather than activity-first.
One row per vehicle, showing the worst risk band, earliest deadline, count of
at-risk activities, and total remaining minutes of work.

A vehicle is only included if at least one of its at-risk activities is a PDI
activity — the PDI team can't directly act on LTSM, repair, or campaign work,
so showing those vehicles would be noise.
"""
from __future__ import annotations

import pandas as pd

HANDLING_UNIT_COL = "Handling Unit"
DEADLINE_COL = "deadline"
DURATION_COL = "Maximal Duration"
RISK_BAND_COL = "risk_band"
CATEGORY_COL = "category"
IS_UNSCHEDULED_COL = "is_unscheduled"

# Risk bands that count as "needs attention" for this view.
AT_RISK_BANDS = ("Breached", "Critical", "At Risk")

# Ordered worst -> best so idxmax on the rank picks the worst.
RISK_RANK = {"Breached": 3, "Critical": 2, "At Risk": 1, "Comfortable": 0}

OUTPUT_COLUMNS = [
    "Handling Unit", "activity_count", "earliest_deadline",
    "worst_risk", "total_remaining_minutes",
]


def build_at_risk_vehicles(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate at-risk activities into one row per vehicle.

    Args:
        df: Fully processed DataFrame (loader → cleaner → compute_slack →
            categorise → classify_category).

    Returns:
        DataFrame with one row per eligible vehicle, sorted by
        ``earliest_deadline`` ascending. Eligible means: at least one at-risk
        activity AND at least one of those at-risk activities is category PDI.
    """
    if len(df) == 0:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # Rows that count as "at risk" — exclude unscheduled and Comfortable.
    at_risk = df.loc[
        (~df[IS_UNSCHEDULED_COL]) & (df[RISK_BAND_COL].isin(AT_RISK_BANDS))
    ].copy()

    if len(at_risk) == 0:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # A vehicle qualifies only if ≥1 of its at-risk activities is PDI.
    pdi_vehicles = (
        at_risk.loc[at_risk[CATEGORY_COL] == "PDI", HANDLING_UNIT_COL].unique()
    )
    qualified = at_risk.loc[at_risk[HANDLING_UNIT_COL].isin(pdi_vehicles)].copy()

    if len(qualified) == 0:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    qualified["_risk_rank"] = qualified[RISK_BAND_COL].map(RISK_RANK)

    grouped = qualified.groupby(HANDLING_UNIT_COL, as_index=False).agg(
        activity_count=(HANDLING_UNIT_COL, "size"),
        earliest_deadline=(DEADLINE_COL, "min"),
        _worst_rank=("_risk_rank", "max"),
        total_remaining_minutes=(DURATION_COL, "sum"),
    )

    rank_to_band = {v: k for k, v in RISK_RANK.items()}
    grouped["worst_risk"] = grouped["_worst_rank"].map(rank_to_band)

    grouped = grouped[OUTPUT_COLUMNS].sort_values(
        "earliest_deadline", ascending=True,
    ).reset_index(drop=True)

    return grouped
