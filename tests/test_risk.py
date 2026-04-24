"""Tests for pdi_scheduler.risk — risk band categorisation."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from pdi_scheduler.risk import categorise

NOW = datetime(2026, 4, 24, 9, 23)


def _row(
    deadline: pd.Timestamp | type(pd.NaT),
    slack: float | None,
    is_unscheduled: bool = False,
) -> dict:
    """Build a minimal row containing only the columns categorise() reads."""
    return {
        "deadline": deadline,
        "slack_minutes": slack,
        "is_unscheduled": is_unscheduled,
    }


class TestCategorise:
    """Unit tests for the categorise() function."""

    def test_adds_risk_band_column(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 1380.0)])
        result = categorise(df, now=NOW)
        assert "risk_band" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 1380.0)])
        categorise(df, now=NOW)
        assert "risk_band" not in df.columns

    def test_unscheduled_row_is_unscheduled_band(self):
        df = pd.DataFrame([_row(pd.NaT, None, is_unscheduled=True)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Unscheduled"

    def test_breached_row_is_breached_band(self):
        """Deadline in the past -> Breached, regardless of slack sign."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-23 09:23"), -1500.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Breached"

    def test_negative_slack_future_deadline_is_critical(self):
        """Deadline in future but slack negative -> Critical (not Breached)."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 10:23"), -30.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Critical"

    def test_small_positive_slack_is_at_risk(self):
        """Slack < 240 (4h) -> At Risk."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 13:23"), 60.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "At Risk"

    def test_large_positive_slack_is_comfortable(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-28 09:23"), 5660.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Comfortable"

    def test_slack_exactly_zero_is_critical(self):
        """slack == 0 is still "no time to spare" — categorise as Critical."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 10:23"), 0.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Critical"

    def test_slack_exactly_at_threshold_is_comfortable(self):
        """slack == threshold (240) is Comfortable; threshold is exclusive."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 13:23"), 240.0)])
        result = categorise(df, now=NOW, at_risk_threshold_minutes=240)
        assert result["risk_band"].iloc[0] == "Comfortable"

    def test_custom_threshold(self):
        """Configurable threshold narrows/widens the At Risk band."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 400.0)])
        result = categorise(df, now=NOW, at_risk_threshold_minutes=500)
        assert result["risk_band"].iloc[0] == "At Risk"

    def test_priority_unscheduled_wins_even_if_slack_present(self):
        """A row flagged unscheduled remains Unscheduled regardless of slack."""
        df = pd.DataFrame([_row(pd.NaT, -1000.0, is_unscheduled=True)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Unscheduled"

    def test_priority_breached_wins_over_critical(self):
        """Breached has higher priority than Critical for past deadlines."""
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-23 09:23"), -1500.0)])
        result = categorise(df, now=NOW)
        assert result["risk_band"].iloc[0] == "Breached"

    def test_mixed_batch(self):
        """Representative mix producing all 5 bands."""
        rows = [
            _row(pd.NaT, None, is_unscheduled=True),                          # Unscheduled
            _row(pd.Timestamp("2026-04-23 09:23"), -1500.0),                  # Breached
            _row(pd.Timestamp("2026-04-24 10:23"), -30.0),                    # Critical
            _row(pd.Timestamp("2026-04-24 13:23"), 60.0),                     # At Risk
            _row(pd.Timestamp("2026-04-28 09:23"), 5660.0),                   # Comfortable
        ]
        df = pd.DataFrame(rows)
        result = categorise(df, now=NOW)
        assert result["risk_band"].tolist() == [
            "Unscheduled", "Breached", "Critical", "At Risk", "Comfortable"
        ]

    def test_returns_copy(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 1380.0)])
        result = categorise(df, now=NOW)
        result.loc[0, "slack_minutes"] = 999.0
        assert df.loc[0, "slack_minutes"] == 1380.0
