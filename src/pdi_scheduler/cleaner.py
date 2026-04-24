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

# Column name constants — centralised here so downstream modules and tests
# can refer to them by name instead of magic strings.
LATEST_END_COL = "Latest End"
DELAY_LEVEL_COL = "Delay Level"
IS_UNSCHEDULED_COL = "is_unscheduled"
DEADLINE_COL = "deadline"


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

    unknown = out[DELAY_LEVEL_COL] == "unknown"
    beyond_horizon = out[LATEST_END_COL] > horizon_cutoff
    missing_deadline = out[LATEST_END_COL].isna()

    out[IS_UNSCHEDULED_COL] = (unknown | beyond_horizon | missing_deadline).astype(bool)

    out[DEADLINE_COL] = out[LATEST_END_COL]
    out.loc[out[IS_UNSCHEDULED_COL], DEADLINE_COL] = pd.NaT

    return out
