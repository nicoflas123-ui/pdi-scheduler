"""Tests for pdi_scheduler.cleaner — DataFrame cleaning rules."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from pdi_scheduler.cleaner import clean


def _make_row(**overrides) -> dict:
    """Build a minimal row dict with sensible defaults for cleaner tests."""
    base = {
        "No.": 1,
        "Activity Type": "PDI_TODO",
        "Activity Status": "New",
        "VPC": True,
        "Handling Unit": "ZZZTEST0000000001",
        "Additional ID": 559_000_001,
        "Creation Time": pd.Timestamp("2026-04-20 08:00"),
        "First Assignment Time": pd.NaT,
        "Start Time": pd.NaT,
        "Latest End": pd.Timestamp("2026-04-25 17:00"),
        "Maximal Duration": 120.0,
        "Approx. End": pd.Timestamp("2026-04-25 16:30"),
        "Delay": 0.0,
        "Delay Level": "onTime",
        "Resource": "alex.morgan@example.com",
        "Planned Start Time": pd.NaT,
        "Planned End Time": pd.NaT,
    }
    base.update(overrides)
    return base


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


TODAY = datetime(2026, 4, 24, 9, 23)


class TestClean:
    """Unit tests for the clean() function."""

    def test_returns_dataframe(self):
        df = _make_df([_make_row()])
        result = clean(df, today=TODAY)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_mutate_input(self):
        df = _make_df([_make_row()])
        original_columns = list(df.columns)
        clean(df, today=TODAY)
        assert list(df.columns) == original_columns
        assert "is_unscheduled" not in df.columns
        assert "deadline" not in df.columns

    def test_adds_is_unscheduled_column(self):
        df = _make_df([_make_row()])
        result = clean(df, today=TODAY)
        assert "is_unscheduled" in result.columns
        assert result["is_unscheduled"].dtype == bool

    def test_adds_deadline_column(self):
        df = _make_df([_make_row()])
        result = clean(df, today=TODAY)
        assert "deadline" in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result["deadline"])

    def test_normal_row_is_scheduled(self):
        """A normal in-horizon row is NOT unscheduled."""
        df = _make_df([_make_row()])
        result = clean(df, today=TODAY)
        assert result["is_unscheduled"].iloc[0] is False or \
               result["is_unscheduled"].iloc[0] == False  # noqa: E712

    def test_placeholder_far_future_date_is_unscheduled(self):
        """A row with Latest End beyond horizon is unscheduled."""
        row = _make_row(**{"Latest End": pd.Timestamp("2059-12-29")})
        df = _make_df([row])
        result = clean(df, today=TODAY, horizon_days=365)
        assert result["is_unscheduled"].iloc[0] == True  # noqa: E712

    def test_unknown_delay_level_is_unscheduled(self):
        """Delay Level == 'unknown' marks the row as unscheduled."""
        row = _make_row(**{"Delay Level": "unknown", "Latest End": pd.NaT})
        df = _make_df([row])
        result = clean(df, today=TODAY)
        assert result["is_unscheduled"].iloc[0] == True  # noqa: E712

    def test_unscheduled_rows_have_nat_deadline(self):
        row = _make_row(**{"Latest End": pd.Timestamp("2059-12-29")})
        df = _make_df([row])
        result = clean(df, today=TODAY, horizon_days=365)
        assert pd.isna(result["deadline"].iloc[0])

    def test_scheduled_rows_deadline_matches_latest_end(self):
        latest_end = pd.Timestamp("2026-04-25 17:00")
        row = _make_row(**{"Latest End": latest_end})
        df = _make_df([row])
        result = clean(df, today=TODAY)
        assert result["deadline"].iloc[0] == latest_end

    def test_horizon_boundary_exactly_at_horizon(self):
        """Row exactly at horizon (365 days out) is treated as scheduled."""
        horizon = pd.Timestamp("2027-04-24 09:23")  # exactly 365 days from TODAY
        row = _make_row(**{"Latest End": horizon})
        df = _make_df([row])
        result = clean(df, today=TODAY, horizon_days=365)
        assert result["is_unscheduled"].iloc[0] == False  # noqa: E712

    def test_row_just_beyond_horizon_is_unscheduled(self):
        """Row 366 days out is unscheduled."""
        beyond = pd.Timestamp("2027-04-26 09:23")
        row = _make_row(**{"Latest End": beyond})
        df = _make_df([row])
        result = clean(df, today=TODAY, horizon_days=365)
        assert result["is_unscheduled"].iloc[0] == True  # noqa: E712

    def test_mixed_dataframe(self):
        """A realistic mixed batch — some scheduled, some not."""
        rows = [
            _make_row(**{"Latest End": pd.Timestamp("2026-04-25 17:00")}),  # scheduled
            _make_row(**{"Latest End": pd.Timestamp("2059-12-29")}),         # placeholder
            _make_row(**{"Delay Level": "unknown", "Latest End": pd.NaT}),   # unknown
        ]
        df = _make_df(rows)
        result = clean(df, today=TODAY)
        assert result["is_unscheduled"].tolist() == [False, True, True]

    def test_returns_copy_not_view(self):
        """Mutating the result must not affect the original."""
        df = _make_df([_make_row()])
        result = clean(df, today=TODAY)
        result.loc[0, "Activity Type"] = "CHANGED"
        assert df.loc[0, "Activity Type"] == "PDI_TODO"
