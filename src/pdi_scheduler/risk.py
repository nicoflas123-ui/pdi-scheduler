"""Map activities into risk bands based on deadline and slack.

Bands (evaluated in order — first match wins):

1. **Unscheduled** — row was flagged by the cleaner (no meaningful deadline).
2. **Breached** — deadline is already in the past.
3. **Critical** — deadline is in the future but slack is <= 0; we'd miss it
   even if we started the work immediately.
4. **At Risk** — slack is positive but below the configurable threshold.
5. **Comfortable** — slack is above the threshold.

The rules are order-sensitive on purpose. A breached row mathematically also
has negative slack, but we want the UI to say "Breached" (the stronger
statement), not "Critical".
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

DEADLINE_COL = "deadline"
SLACK_COL = "slack_minutes"
IS_UNSCHEDULED_COL = "is_unscheduled"
RISK_BAND_COL = "risk_band"

BAND_UNSCHEDULED = "Unscheduled"
BAND_BREACHED = "Breached"
BAND_CRITICAL = "Critical"
BAND_AT_RISK = "At Risk"
BAND_COMFORTABLE = "Comfortable"


def categorise(
    df: pd.DataFrame,
    now: datetime,
    at_risk_threshold_minutes: int = 240,
) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``risk_band`` column added.

    Args:
        df: DataFrame produced by ``scheduling.compute_slack`` — must contain
            ``deadline``, ``slack_minutes`` and ``is_unscheduled`` columns.
        now: Reference "now" used to evaluate the breached rule.
        at_risk_threshold_minutes: Slack below this (and > 0) is At Risk.
            Anything at or above is Comfortable. Default 240 minutes (4 hours).

    Returns:
        A new DataFrame with ``risk_band`` column populated with one of the
        five band names.
    """
    out = df.copy()
    now_ts = pd.Timestamp(now)

    # Default everyone to Comfortable, then override in priority order.
    bands = pd.Series(BAND_COMFORTABLE, index=out.index, dtype=object)

    # At Risk: positive slack but below threshold
    bands = bands.mask(
        out[SLACK_COL] < at_risk_threshold_minutes,
        BAND_AT_RISK,
    )

    # Critical: slack <= 0
    bands = bands.mask(out[SLACK_COL] <= 0, BAND_CRITICAL)

    # Breached: deadline already passed (higher priority than Critical)
    bands = bands.mask(out[DEADLINE_COL] < now_ts, BAND_BREACHED)

    # Unscheduled: highest priority — overrides everything
    bands = bands.mask(out[IS_UNSCHEDULED_COL], BAND_UNSCHEDULED)

    out[RISK_BAND_COL] = bands
    return out