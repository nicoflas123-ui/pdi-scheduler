"""Clean and normalise PDI activity data.

Classifies rows as scheduled vs unscheduled and produces a canonical ``deadline``
column that downstream modules (scheduling, risk) can rely on.

Rules:
- ``Delay Level == "unknown"`` -> unscheduled (no deadline)
- ``Latest End > today + horizon_days`` -> unscheduled (placeholder far-future date)
- Everything else -> scheduled, ``deadline = Latest End``
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def clean(
    df: pd.DataFrame,
    today: datetime,
    horizon_days: int = 365,
) -> pd.DataFrame:
    """Return a cleaned copy of ``df`` with canonical scheduling columns added.

    Args:
        df: Raw activity DataFrame as produced by ``loader.load_activities``.
        today: Reference "now" used to evaluate the horizon cut-off.
        horizon_days: Any ``Latest End`` more than this many days after ``today``
            is treated as a placeholder / unscheduled marker.

    Returns:
        A new DataFrame with two added columns:

        - ``is_unscheduled`` (bool): True if the row has no meaningful deadline.
        - ``deadline`` (datetime64): The cleaned deadline, or NaT if unscheduled.

    The input ``df`` is never mutated.
    """
    out = df.copy()

    horizon_cutoff = pd.Timestamp(today) + timedelta(days=horizon_days)

    unknown = out["Delay Level"] == "unknown"
    beyond_horizon = out["Latest End"] > horizon_cutoff
    missing_deadline = out["Latest End"].isna()

    out["is_unscheduled"] = (unknown | beyond_horizon | missing_deadline).astype(bool)

    out["deadline"] = out["Latest End"]
    out.loc[out["is_unscheduled"], "deadline"] = pd.NaT

    return out