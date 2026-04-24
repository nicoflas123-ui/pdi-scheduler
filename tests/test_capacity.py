"""Tests for pdi_scheduler.capacity — daily workload vs capacity aggregation."""
from __future__ import annotations

from datetime import date

import pandas as pd

from pdi_scheduler.capacity import daily_load


def _row(
    deadline: pd.Timestamp | type(pd.NaT),
    duration: float | None,
    resource: str | None = "alex.morgan@example.com",
    is_unscheduled: bool = False,
) -> dict:
    """Build a minimal row containing only the columns daily_load() reads."""
    return {
        "deadline": deadline,
        "Maximal Duration": duration,
        "Resource": resource,
        "is_unscheduled": is_unscheduled,
    }


START_DATE = date(2026, 4, 24)


class TestDailyLoad:
    """Unit tests for daily_load()."""

    def test_returns_dataframe(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 15:00"), 60.0)])
        result = daily_load(df, start_date=START_DATE, days=1)
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 15:00"), 60.0)])
        result = daily_load(df, start_date=START_DATE, days=1)
        assert list(result.columns) == [
            "date", "planned_minutes", "capacity_minutes", "utilisation_pct",
        ]

    def test_returns_one_row_per_day(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 15:00"), 60.0)])
        result = daily_load(df, start_date=START_DATE, days=14)
        assert len(result) == 14

    def test_dates_are_consecutive(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 15:00"), 60.0)])
        result = daily_load(df, start_date=START_DATE, days=3)
        assert result["date"].tolist() == [
            date(2026, 4, 24),
            date(2026, 4, 25),
            date(2026, 4, 26),
        ]

    def test_planned_minutes_sums_durations_on_matching_day(self):
        rows = [
            _row(pd.Timestamp("2026-04-24 15:00"), 60.0),
            _row(pd.Timestamp("2026-04-24 09:00"), 120.0),
            _row(pd.Timestamp("2026-04-25 10:00"), 30.0),
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=2)
        assert result.loc[result["date"] == date(2026, 4, 24), "planned_minutes"].iloc[0] == 180.0
        assert result.loc[result["date"] == date(2026, 4, 25), "planned_minutes"].iloc[0] == 30.0

    def test_unscheduled_rows_excluded_from_planned(self):
        rows = [
            _row(pd.Timestamp("2026-04-24 15:00"), 60.0),
            _row(pd.NaT, 9999.0, is_unscheduled=True),  # must be excluded
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=1)
        assert result["planned_minutes"].iloc[0] == 60.0

    def test_day_with_no_activities_has_zero_planned(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-24 15:00"), 60.0)])
        result = daily_load(df, start_date=START_DATE, days=3)
        # 25th and 26th have nothing
        assert result.loc[result["date"] == date(2026, 4, 25), "planned_minutes"].iloc[0] == 0.0
        assert result.loc[result["date"] == date(2026, 4, 26), "planned_minutes"].iloc[0] == 0.0

    def test_capacity_based_on_unique_resources(self):
        """3 unique resources × 7.5h × 60 = 1350 minutes per day."""
        rows = [
            _row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource="a@example.com"),
            _row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource="b@example.com"),
            _row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource="c@example.com"),
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=1,
                            hours_per_resource_per_day=7.5)
        assert result["capacity_minutes"].iloc[0] == 3 * 7.5 * 60

    def test_capacity_ignores_null_resources(self):
        """Rows with no resource assigned don't contribute to the unique count."""
        rows = [
            _row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource="a@example.com"),
            _row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource=None),
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=1,
                            hours_per_resource_per_day=7.5)
        assert result["capacity_minutes"].iloc[0] == 1 * 7.5 * 60

    def test_utilisation_pct_calculated_correctly(self):
        rows = [
            _row(pd.Timestamp("2026-04-24 09:00"), 225.0, resource="a@example.com"),
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=1,
                            hours_per_resource_per_day=7.5)
        # capacity = 1 * 7.5 * 60 = 450, planned = 225, utilisation = 50.0
        assert result["utilisation_pct"].iloc[0] == 50.0

    def test_zero_capacity_produces_zero_utilisation_not_error(self):
        """Empty DataFrame -> 0 resources -> 0 capacity -> utilisation = 0, no crash."""
        df = pd.DataFrame(
            [], columns=["deadline", "Maximal Duration", "Resource", "is_unscheduled"]
        )
        result = daily_load(df, start_date=START_DATE, days=1)
        assert result["capacity_minutes"].iloc[0] == 0.0
        assert result["utilisation_pct"].iloc[0] == 0.0

    def test_custom_hours_per_day(self):
        """Parameter propagates to the capacity calculation."""
        rows = [_row(pd.Timestamp("2026-04-24 09:00"), 60.0, resource="a@example.com")]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=1,
                            hours_per_resource_per_day=10.0)
        assert result["capacity_minutes"].iloc[0] == 600.0

    def test_does_not_mutate_input(self):
        rows = [_row(pd.Timestamp("2026-04-24 15:00"), 60.0)]
        df = pd.DataFrame(rows)
        cols_before = list(df.columns)
        daily_load(df, start_date=START_DATE, days=1)
        assert list(df.columns) == cols_before

    def test_overlapping_day_planned_sums_all_rows(self):
        """Two activities on the same day sum; different days don't."""
        rows = [
            _row(pd.Timestamp("2026-04-24 09:00"), 30.0),
            _row(pd.Timestamp("2026-04-24 17:00"), 45.0),
            _row(pd.Timestamp("2026-04-25 09:00"), 60.0),
        ]
        df = pd.DataFrame(rows)
        result = daily_load(df, start_date=START_DATE, days=2)
        assert result.loc[result["date"] == date(2026, 4, 24), "planned_minutes"].iloc[0] == 75.0
        assert result.loc[result["date"] == date(2026, 4, 25), "planned_minutes"].iloc[0] == 60.0