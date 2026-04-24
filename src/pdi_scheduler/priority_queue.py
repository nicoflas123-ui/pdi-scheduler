"""Build the ranked work queue shown in dashboard View 2.

The priority queue is the scheduler's main working surface: the top-N
activities sorted by ascending slack (most urgent first). Unscheduled rows
are excluded — they have no actionable deadline.
"""
from __future__ import annotations

import pandas as pd

SLACK_COL = "slack_minutes"
IS_UNSCHEDULED_COL = "is_unscheduled"

QUEUE_COLUMNS = [
    "Handling Unit", "Activity Type", "deadline", "Maximal Duration",
    "slack_minutes", "risk_band", "Resource", "category",
]


def build_priority_queue(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Return the top-N actionable activities sorted by slack ascending.

    Args:
        df: Fully processed DataFrame (loader → cleaner → compute_slack →
            categorise → classify_category).
        top_n: Maximum number of rows to return. Default 20.

    Returns:
        A DataFrame with the eight display columns, sorted by ``slack_minutes``
        ascending, with unscheduled rows removed and capped at ``top_n``.
    """
    if len(df) == 0:
        return pd.DataFrame(columns=QUEUE_COLUMNS)

    actionable = df.loc[~df[IS_UNSCHEDULED_COL]].copy()
    ranked = actionable.sort_values(SLACK_COL, ascending=True).head(top_n)
    return ranked[QUEUE_COLUMNS].reset_index(drop=True)