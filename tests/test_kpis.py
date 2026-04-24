"""Tests for pdi_scheduler.kpis — headline dashboard metrics."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from pdi_scheduler.kpis import compute_kpis

NOW = datetime(2026, 4, 24, 9, 23)


def _row(
    deadline: pd.Timestamp | type(pd.NaT),
    duration: float | None,
    risk_band: str,
    resource: str | None = "alex@example.com",
    is_unscheduled: bool = False,
) -> dict:
    """Minimal row containing only the columns compute_kpis() reads."""
    return {
        "deadline": deadline,
        "Maximal Duration": duration,
        "risk_band": risk_band,
        "Resource": resource,
        "is_unscheduled": is_unscheduled,
    }


class TestComputeKpis:
    """Unit tests for compute_kpis()."""

    def test_returns_dict_with_four_keys(self):
        df = pd.DataFrame([_row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable")])
        result = compute_kpis(df, now=NOW)
        assert set(result.keys()) == {
            "on_time_pct", "at_risk_count", "due_today", "utilisation_pct",
        }

    def test_on_time_pct_all_comfortable(self):
        rows = [_row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable") for _ in range(4)]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["on_time_pct"] == 100.0

    def test_on_time_pct_half_comfortable(self):
        rows = [
            _row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable"),
            _row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable"),
            _row(pd.Timestamp("2026-04-24 08:00"), 60.0, "Breached"),
            _row(pd.Timestamp("2026-04-24 10:00"), 60.0, "Critical"),
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["on_time_pct"] == 50.0

    def test_on_time_pct_excludes_unscheduled_from_denominator(self):
        """Unscheduled rows don't count against the on-time ratio."""
        rows = [
            _row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable"),
            _row(pd.NaT, 60.0, "Unscheduled", is_unscheduled=True),
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["on_time_pct"] == 100.0

    def test_on_time_pct_zero_scheduled_returns_zero(self):
        """No scheduled rows -> 0.0 rather than divide-by-zero."""
        df = pd.DataFrame([_row(pd.NaT, 60.0, "Unscheduled", is_unscheduled=True)])
        result = compute_kpis(df, now=NOW)
        assert result["on_time_pct"] == 0.0

    def test_at_risk_count_sums_breached_critical_at_risk(self):
        rows = [
            _row(pd.Timestamp("2026-04-23 09:23"), 60.0, "Breached"),
            _row(pd.Timestamp("2026-04-24 10:23"), 60.0, "Critical"),
            _row(pd.Timestamp("2026-04-24 13:23"), 60.0, "At Risk"),
            _row(pd.Timestamp("2026-04-28 09:23"), 60.0, "Comfortable"),
            _row(pd.NaT, 60.0, "Unscheduled", is_unscheduled=True),
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["at_risk_count"] == 3

    def test_at_risk_count_zero_when_all_comfortable(self):
        rows = [_row(pd.Timestamp("2026-04-28 09:23"), 60.0, "Comfortable") for _ in range(5)]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["at_risk_count"] == 0

    def test_due_today_counts_activities_with_deadline_today(self):
        rows = [
            _row(pd.Timestamp("2026-04-24 15:00"), 60.0, "At Risk"),   # today
            _row(pd.Timestamp("2026-04-24 23:59"), 60.0, "Comfortable"),  # today
            _row(pd.Timestamp("2026-04-25 09:00"), 60.0, "Comfortable"),  # tomorrow
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["due_today"] == 2

    def test_due_today_ignores_unscheduled(self):
        rows = [
            _row(pd.Timestamp("2026-04-24 15:00"), 60.0, "At Risk"),
            _row(pd.NaT, 60.0, "Unscheduled", is_unscheduled=True),
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW)
        assert result["due_today"] == 1

    def test_utilisation_pct_is_today_planned_over_capacity(self):
        """1 resource × 7.5h × 60 = 450min capacity. 225min planned today = 50%."""
        rows = [
            _row(pd.Timestamp("2026-04-24 15:00"), 225.0, "At Risk"),
        ]
        df = pd.DataFrame(rows)
        result = compute_kpis(df, now=NOW, hours_per_resource_per_day=7.5)
        assert result["utilisation_pct"] == 50.0

    def test_utilisation_zero_capacity_returns_zero(self):
        """No resources -> 0 capacity -> 0% utilisation, no divide-by-zero."""
        df = pd.DataFrame(
            [],
            columns=["deadline", "Maximal Duration", "risk_band", "Resource", "is_unscheduled"],
        )
        result = compute_kpis(df, now=NOW)
        assert result["utilisation_pct"] == 0.0

    def test_does_not_mutate_input(self):
        rows = [_row(pd.Timestamp("2026-04-25 09:23"), 60.0, "Comfortable")]
        df = pd.DataFrame(rows)
        cols_before = list(df.columns)
        compute_kpis(df, now=NOW)
        assert list(df.columns) == cols_before