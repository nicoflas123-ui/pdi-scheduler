"""Tests for pdi_scheduler.scheduling — slack-time calculation."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from pdi_scheduler.scheduling import compute_slack

# Reference "now" shared across tests
NOW = datetime(2026, 4, 24, 9, 23)


def _row(
    deadline: pd.Timestamp | type(pd.NaT),
    duration: float | None,
    is_unscheduled: bool = False,
) -> dict:
    """Build a minimal row — only the columns the slack calculator reads."""
    return {
        "deadline": deadline,
        "Maximal Duration": duration,
        "is_unscheduled": is_unscheduled,
    }


class TestComputeSlack:
    """Unit tests for compute_slack()."""

    def test_adds_slack_minutes_column(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 60.0)])
        result = compute_slack(df, now=NOW)
        assert "slack_minutes" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 60.0)])
        compute_slack(df, now=NOW)
        assert "slack_minutes" not in df.columns

    def test_positive_slack_for_comfortable_deadline(self):
        """Deadline 24h away, 60min duration -> slack = 1440 - 60 = 1380."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 60.0)])
        result = compute_slack(df, now=NOW)
        assert result["slack_minutes"].iloc[0] == 1380.0

    def test_zero_slack_when_deadline_equals_duration_ahead(self):
        """Deadline 60min away, 60min duration -> slack = 0."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 10:23"), 60.0)])
        result = compute_slack(df, now=NOW)
        assert result["slack_minutes"].iloc[0] == 0.0

    def test_negative_slack_when_duration_exceeds_time_to_deadline(self):
        """Deadline 30min away, 60min duration -> slack = -30."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 09:53"), 60.0)])
        result = compute_slack(df, now=NOW)
        assert result["slack_minutes"].iloc[0] == -30.0

    def test_breached_deadline_gives_large_negative_slack(self):
        """Deadline 2h in the past, 60min duration -> slack = -180."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 07:23"), 60.0)])
        result = compute_slack(df, now=NOW)
        assert result["slack_minutes"].iloc[0] == -180.0

    def test_nan_duration_gives_nan_slack(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), None)])
        result = compute_slack(df, now=NOW)
        assert pd.isna(result["slack_minutes"].iloc[0])

    def test_unscheduled_row_gives_nan_slack(self):
        df = pd.DataFrame([_row(pd.NaT, 60.0, is_unscheduled=True)])
        result = compute_slack(df, now=NOW)
        assert pd.isna(result["slack_minutes"].iloc[0])

    def test_mixed_rows(self):
        """Batch with mixed scheduled / unscheduled / missing-duration rows."""
        rows = [
            _row(pd.Timestamp("2026-04-25 09:23"), 60.0),                 # +1380
            _row(pd.Timestamp("2026-04-24 08:53"), 60.0),                 # -90
            _row(pd.NaT, 60.0, is_unscheduled=True),                      # NaN
            _row(pd.Timestamp("2026-04-25 09:23"), None),                 # NaN
        ]
        df = pd.DataFrame(rows)
        result = compute_slack(df, now=NOW)
        assert result["slack_minutes"].iloc[0] == 1380.0
        assert result["slack_minutes"].iloc[1] == -90.0
        assert pd.isna(result["slack_minutes"].iloc[2])
        assert pd.isna(result["slack_minutes"].iloc[3])

    def test_returns_copy(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 60.0)])
        result = compute_slack(df, now=NOW)
        result.loc[0, "Maximal Duration"] = 9999.0
        assert df.loc[0, "Maximal Duration"] == 60.0
