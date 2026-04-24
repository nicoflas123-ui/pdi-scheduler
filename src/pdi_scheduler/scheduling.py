"""Slack-time calculation for PDI activities.

Slack is the "breathing room" an activity has before its deadline, given its
estimated duration. Formula:

    slack_minutes = (deadline - now) in minutes  -  maximal_duration

Rows that are unscheduled (``is_unscheduled == True``) or have no
``Maximal Duration`` receive ``slack_minutes = NaN`` because slack is undefined
without both a real deadline and a duration estimate.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

DEADLINE_COL = "deadline"
DURATION_COL = "Maximal Duration"
IS_UNSCHEDULED_COL = "is_unscheduled"
SLACK_COL = "slack_minutes"


def compute_slack(df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``slack_minutes`` column added.

    Args:
        df: DataFrame produced by ``cleaner.clean`` — must contain
            ``deadline``, ``Maximal Duration`` and ``is_unscheduled`` columns.
        now: Reference "now" used to compute time-to-deadline.

    Returns:
        A new DataFrame with ``slack_minutes`` column. NaN for unscheduled rows
        or rows with missing duration.
    """
    out = df.copy()

    time_to_deadline = (out[DEADLINE_COL] - pd.Timestamp(now)).dt.total_seconds() / 60
    slack = time_to_deadline - out[DURATION_COL]

    # Rows where slack is undefined -> NaN
    slack = slack.where(~out[IS_UNSCHEDULED_COL], other=np.nan)

    out[SLACK_COL] = slack
    return out