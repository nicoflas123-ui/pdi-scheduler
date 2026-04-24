"""Aggregate planned work minutes vs available resource minutes per day.

This module answers the question the Capacity vs Demand chart (View 4) needs:
"For each of the next N days, how much work is scheduled to finish that day,
and how much capacity do we have?"

The capacity model is deliberately simple:
    capacity_minutes_per_day = unique_resources * hours_per_resource_per_day * 60

This is *illustrative* — it assumes every resource is available every day at
full working hours. The real staffing picture (CLdN fixed staff + agency
labour + job-rotation) is out of scope for the MVP; see README → Next Steps.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

DEADLINE_COL = "deadline"
DURATION_COL = "Maximal Duration"
RESOURCE_COL = "Resource"
IS_UNSCHEDULED_COL = "is_unscheduled"


def daily_load(
    df: pd.DataFrame,
    start_date: date,
    days: int,
    hours_per_resource_per_day: float = 7.5,
) -> pd.DataFrame:
    """Aggregate planned work vs capacity over a window of ``days`` days.

    Args:
        df: DataFrame produced by ``cleaner.clean`` (must have ``deadline``,
            ``Maximal Duration``, ``Resource``, ``is_unscheduled``).
        start_date: First day of the window (inclusive).
        days: Number of consecutive days to report on.
        hours_per_resource_per_day: Assumed daily working hours per resource.

    Returns:
        DataFrame with one row per day and columns:
            - ``date`` (date)
            - ``planned_minutes`` (float)  — sum of durations whose deadline
              falls on that day (excluding unscheduled rows)
            - ``capacity_minutes`` (float) — unique non-null resources ×
              ``hours_per_resource_per_day`` × 60
            - ``utilisation_pct`` (float)  — planned / capacity × 100
              (0 when capacity is 0, no divide-by-zero error)
    """
    scheduled = df.loc[~df[IS_UNSCHEDULED_COL]].copy() if len(df) else df.copy()

    # Unique resources across the whole input — capacity is constant across
    # the window for this simple model.
    n_resources = scheduled[RESOURCE_COL].dropna().nunique() if len(scheduled) else 0
    capacity_minutes = n_resources * hours_per_resource_per_day * 60

    # Map deadlines to their date component for grouping
    if len(scheduled):
        scheduled["_deadline_date"] = scheduled[DEADLINE_COL].dt.date
        by_day = scheduled.groupby("_deadline_date")[DURATION_COL].sum()
    else:
        by_day = pd.Series(dtype=float)

    rows = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        planned = float(by_day.get(day, 0.0))
        util = (planned / capacity_minutes * 100) if capacity_minutes > 0 else 0.0
        rows.append({
            "date": day,
            "planned_minutes": planned,
            "capacity_minutes": float(capacity_minutes),
            "utilisation_pct": util,
        })

    return pd.DataFrame(rows)
