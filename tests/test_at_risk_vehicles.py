"""Tests for pdi_scheduler.at_risk_vehicles — vehicle-level rollup view."""
from __future__ import annotations

import pandas as pd

from pdi_scheduler.at_risk_vehicles import build_at_risk_vehicles


def _row(
    handling_unit: str,
    deadline: pd.Timestamp | type(pd.NaT),
    duration: float | None,
    risk_band: str,
    category: str = "PDI",
    is_unscheduled: bool = False,
) -> dict:
    return {
        "Handling Unit": handling_unit,
        "deadline": deadline,
        "Maximal Duration": duration,
        "risk_band": risk_band,
        "category": category,
        "is_unscheduled": is_unscheduled,
    }


class TestBuildAtRiskVehicles:
    """Unit tests for build_at_risk_vehicles()."""

    def test_returns_dataframe(self):
        rows = [_row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached")]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        rows = [_row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached")]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert list(result.columns) == [
            "Handling Unit", "activity_count", "earliest_deadline",
            "worst_risk", "total_remaining_minutes",
        ]

    def test_one_row_per_vehicle(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached"),
            _row("V1", pd.Timestamp("2026-04-26"), 30.0, "Critical"),
            _row("V2", pd.Timestamp("2026-04-27"), 60.0, "At Risk"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert len(result) == 2
        assert set(result["Handling Unit"]) == {"V1", "V2"}

    def test_activity_count_sums_at_risk_activities(self):
        """Count includes any at-risk activities on the vehicle (PDI or not)."""
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached"),
            _row("V1", pd.Timestamp("2026-04-26"), 30.0, "Critical"),
            _row("V1", pd.Timestamp("2026-04-27"), 30.0, "At Risk"),
            _row("V1", pd.Timestamp("2026-05-01"), 30.0, "Comfortable"),  # excluded
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert result["activity_count"].iloc[0] == 3

    def test_earliest_deadline_is_the_minimum(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-25 14:00"), 60.0, "Critical"),
            _row("V1", pd.Timestamp("2026-04-24 09:00"), 30.0, "Breached"),
            _row("V1", pd.Timestamp("2026-04-27 10:00"), 60.0, "At Risk"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert result["earliest_deadline"].iloc[0] == pd.Timestamp("2026-04-24 09:00")

    def test_worst_risk_is_most_severe(self):
        """Worst risk prefers Breached > Critical > At Risk."""
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "At Risk"),
            _row("V1", pd.Timestamp("2026-04-26"), 60.0, "Critical"),
            _row("V1", pd.Timestamp("2026-04-27"), 60.0, "Breached"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert result["worst_risk"].iloc[0] == "Breached"

    def test_worst_risk_only_critical_when_no_breached(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "At Risk"),
            _row("V1", pd.Timestamp("2026-04-26"), 60.0, "Critical"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert result["worst_risk"].iloc[0] == "Critical"

    def test_total_remaining_sums_durations(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached"),
            _row("V1", pd.Timestamp("2026-04-26"), 30.0, "Critical"),
            _row("V1", pd.Timestamp("2026-04-27"), 15.0, "At Risk"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert result["total_remaining_minutes"].iloc[0] == 105.0

    def test_vehicles_with_only_comfortable_are_excluded(self):
        """Vehicle with no at-risk activities doesn't appear."""
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached"),
            _row("V2", pd.Timestamp("2026-05-01"), 60.0, "Comfortable"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert list(result["Handling Unit"]) == ["V1"]

    def test_vehicles_with_only_unscheduled_are_excluded(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached"),
            _row("V2", pd.NaT, 60.0, "Unscheduled", is_unscheduled=True),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert list(result["Handling Unit"]) == ["V1"]

    def test_vehicle_with_only_non_pdi_at_risk_is_excluded(self):
        """PDI team can't act on LTSM/Campaign-only vehicles — exclude them."""
        rows = [
            _row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached", category="LTSM"),
            _row("V2", pd.Timestamp("2026-04-25"), 60.0, "Breached", category="PDI"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert list(result["Handling Unit"]) == ["V2"]

    def test_vehicle_with_mixed_pdi_and_ltsm_included_counts_all(self):
        """If a vehicle has PDI at-risk activity, include it; count totals all at-risk."""
        rows = [
            _row("V1", pd.Timestamp("2026-04-24"), 60.0, "Critical", category="PDI"),
            _row("V1", pd.Timestamp("2026-04-25"), 30.0, "Breached", category="LTSM"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert len(result) == 1
        # Worst risk should still reflect the Breached LTSM (team leader needs to know)
        assert result["worst_risk"].iloc[0] == "Breached"
        assert result["activity_count"].iloc[0] == 2
        assert result["total_remaining_minutes"].iloc[0] == 90.0

    def test_sorted_by_earliest_deadline_ascending(self):
        rows = [
            _row("V1", pd.Timestamp("2026-04-26"), 60.0, "Breached"),
            _row("V2", pd.Timestamp("2026-04-24"), 60.0, "Critical"),
            _row("V3", pd.Timestamp("2026-04-25"), 60.0, "At Risk"),
        ]
        result = build_at_risk_vehicles(pd.DataFrame(rows))
        assert list(result["Handling Unit"]) == ["V2", "V3", "V1"]

    def test_does_not_mutate_input(self):
        rows = [_row("V1", pd.Timestamp("2026-04-25"), 60.0, "Breached")]
        df = pd.DataFrame(rows)
        cols_before = list(df.columns)
        build_at_risk_vehicles(df)
        assert list(df.columns) == cols_before

    def test_empty_input_returns_empty(self):
        df = pd.DataFrame(
            [],
            columns=[
                "Handling Unit", "deadline", "Maximal Duration",
                "risk_band", "category", "is_unscheduled",
            ],
        )
        result = build_at_risk_vehicles(df)
        assert len(result) == 0
        assert list(result.columns) == [
            "Handling Unit", "activity_count", "earliest_deadline",
            "worst_risk", "total_remaining_minutes",
        ]