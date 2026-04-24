"""Headline metrics for the dashboard KPI strip.

The ``compute_kpis`` function returns the four numbers shown at the top of
every dashboard view:

- ``on_time_pct``      — % of scheduled activities with risk_band Comfortable
- ``at_risk_count``    — count of Breached + Critical + At Risk activities
- ``due_today``        — count of scheduled activities whose deadline is today
- ``utilisation_pct``  — today's planned minutes / today's capacity minutes

All calculations exclude unscheduled rows so placeholder / unknown deadlines
don't distort the headline numbers.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

DEADLINE_COL = "deadline"
DURATION_COL = "Maximal Duration"
RISK_BAND_COL = "risk_band"
RESOURCE_COL = "Resource"
IS_UNSCHEDULED_COL = "is_unscheduled"

AT_RISK_BANDS = {"Breached", "Critical", "At Risk"}
ON_TIME_BAND = "Comfortable"


def compute_kpis(
    df: pd.DataFrame,
    now: datetime,
    hours_per_resource_per_day: float = 7.5,
) -> dict[str, float]:
    """Return a dict of the four headline KPIs.

    Args:
        df: DataFrame produced by the full pipeline (loader → cleaner →
            compute_slack → categorise). Must include ``risk_band``,
            ``deadline``, ``Maximal Duration``, ``Resource``,
            ``is_unscheduled``.
        now: Reference "now" — used to identify "today's" activities.
        hours_per_resource_per_day: Used for the utilisation calculation.

    Returns:
        ``{"on_time_pct": float, "at_risk_count": int, "due_today": int,
        "utilisation_pct": float}``
    """
    if len(df) == 0:
        return {
            "on_time_pct": 0.0,
            "at_risk_count": 0,
            "due_today": 0,
            "utilisation_pct": 0.0,
        }

    scheduled = df.loc[~df[IS_UNSCHEDULED_COL]]
    today = pd.Timestamp(now).date()

    # On-time %: proportion of scheduled rows that are Comfortable
    n_scheduled = len(scheduled)
    if n_scheduled == 0:
        on_time_pct = 0.0
    else:
        n_comfortable = (scheduled[RISK_BAND_COL] == ON_TIME_BAND).sum()
        on_time_pct = float(n_comfortable / n_scheduled * 100)

    # At-risk count: rows in any of the three risk bands
    at_risk_count = int(df[RISK_BAND_COL].isin(AT_RISK_BANDS).sum())

    # Due today: scheduled rows whose deadline falls on today's date
    due_today = int((scheduled[DEADLINE_COL].dt.date == today).sum())

    # Utilisation: today's planned / today's capacity
    n_resources = df[RESOURCE_COL].dropna().nunique()
    capacity_minutes = n_resources * hours_per_resource_per_day * 60
    if capacity_minutes == 0:
        utilisation_pct = 0.0
    else:
        planned_today = float(
            scheduled.loc[scheduled[DEADLINE_COL].dt.date == today, DURATION_COL].sum()
        )
        utilisation_pct = planned_today / capacity_minutes * 100

    return {
        "on_time_pct": round(on_time_pct, 1),
        "at_risk_count": at_risk_count,
        "due_today": due_today,
        "utilisation_pct": round(utilisation_pct, 1),
    }
