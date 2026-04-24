"""Tests for pdi_scheduler.priority_queue — ranked work queue for schedulers."""
from __future__ import annotations

import pandas as pd

from pdi_scheduler.priority_queue import build_priority_queue


def _row(
    handling_unit: str,
    activity_type: str,
    deadline: pd.Timestamp | type(pd.NaT),
    duration: float | None,
    slack: float | None,
    risk_band: str,
    resource: str | None = "alex@example.com",
    category: str = "PDI",
    is_unscheduled: bool = False,
) -> dict:
    return {
        "Handling Unit": handling_unit,
        "Activity Type": activity_type,
        "deadline": deadline,
        "Maximal Duration": duration,
        "slack_minutes": slack,
        "risk_band": risk_band,
        "Resource": resource,
        "category": category,
        "is_unscheduled": is_unscheduled,
    }


class TestBuildPriorityQueue:
    """Unit tests for build_priority_queue()."""

    def test_returns_dataframe(self):
        rows = [_row("V1", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, 100.0, "At Risk")]
        result = build_priority_queue(pd.DataFrame(rows))
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        rows = [_row("V1", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, 100.0, "At Risk")]
        result = build_priority_queue(pd.DataFrame(rows))
        assert list(result.columns) == [
            "Handling Unit", "Activity Type", "deadline", "Maximal Duration",
            "slack_minutes", "risk_band", "Resource", "category",
        ]

    def test_sorted_by_slack_ascending(self):
        """Most urgent (lowest slack) at the top."""
        rows = [
            _row("V1", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, 500.0, "Comfortable"),
            _row("V2", "ROADTEST", pd.Timestamp("2026-04-24"), 60.0, -100.0, "Critical"),
            _row("V3", "MBPCDIAG", pd.Timestamp("2026-04-24"), 60.0, 120.0, "At Risk"),
        ]
        result = build_priority_queue(pd.DataFrame(rows))
        assert result["slack_minutes"].tolist() == [-100.0, 120.0, 500.0]

    def test_excludes_unscheduled(self):
        """Unscheduled rows have no meaningful slack and shouldn't appear."""
        rows = [
            _row("V1", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, 100.0, "At Risk"),
            _row("V2", "LTSM_TODO", pd.NaT, 60.0, None, "Unscheduled",
                 is_unscheduled=True),
        ]
        result = build_priority_queue(pd.DataFrame(rows))
        assert len(result) == 1
        assert result["Handling Unit"].iloc[0] == "V1"

    def test_top_n_respected(self):
        rows = [
            _row(f"V{i}", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, float(i * 10), "At Risk")
            for i in range(30)
        ]
        result = build_priority_queue(pd.DataFrame(rows), top_n=20)
        assert len(result) == 20

    def test_default_top_n_is_20(self):
        rows = [
            _row(f"V{i}", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, float(i * 10), "At Risk")
            for i in range(25)
        ]
        result = build_priority_queue(pd.DataFrame(rows))
        assert len(result) == 20

    def test_does_not_mutate_input(self):
        rows = [_row("V1", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, 100.0, "At Risk")]
        df = pd.DataFrame(rows)
        cols_before = list(df.columns)
        build_priority_queue(df)
        assert list(df.columns) == cols_before

    def test_fewer_rows_than_top_n_returns_all(self):
        rows = [
            _row(f"V{i}", "PDI_TODO", pd.Timestamp("2026-04-25"), 60.0, float(i * 10), "At Risk")
            for i in range(5)
        ]
        result = build_priority_queue(pd.DataFrame(rows), top_n=20)
        assert len(result) == 5

    def test_empty_input_returns_empty(self):
        df = pd.DataFrame(
            [],
            columns=[
                "Handling Unit", "Activity Type", "deadline", "Maximal Duration",
                "slack_minutes", "risk_band", "Resource", "category",
                "is_unscheduled",
            ],
        )
        result = build_priority_queue(df)
        assert len(result) == 0