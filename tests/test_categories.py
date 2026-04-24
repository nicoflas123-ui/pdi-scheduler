"""Tests for pdi_scheduler.categories — PDI vs non-PDI classification."""
from __future__ import annotations

import pandas as pd

from pdi_scheduler.categories import classify_category


class TestClassifyCategory:
    """Unit tests for classify_category()."""

    def test_adds_category_column(self):
        df = pd.DataFrame({"Activity Type": ["PDI_TODO"]})
        result = classify_category(df)
        assert "category" in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"Activity Type": ["PDI_TODO"]})
        classify_category(df)
        assert "category" not in df.columns

    def test_pdi_todo_is_pdi(self):
        df = pd.DataFrame({"Activity Type": ["PDI_TODO"]})
        result = classify_category(df)
        assert result["category"].iloc[0] == "PDI"

    def test_explicit_pdi_activities_are_pdi(self):
        """Core PDI activity types from the Op10-Op80 workflow."""
        pdi_types = [
            "PDI_TODO", "ROADTEST", "MBPCDIAG", "MBUX_SETUP", "MBPCRINSP",
            "TYRES_PDI", "EVA_CHECK", "HANDOVER", "LOCKING_WHEEL_NUTS",
            "BATTERY_CONDITION_PDI", "REGISTRATION", "XENTRY_PRINTOUT",
        ]
        df = pd.DataFrame({"Activity Type": pdi_types})
        result = classify_category(df)
        assert (result["category"] == "PDI").all()

    def test_ltsm_activities_are_ltsm(self):
        ltsm_types = ["LTSM_TODO", "LTSM_TEST_DRIVE", "CARWASH_LTSM",
                      "FIRST_MEASURE_12V_LTSM"]
        df = pd.DataFrame({"Activity Type": ltsm_types})
        result = classify_category(df)
        assert (result["category"] == "LTSM").all()

    def test_campaign_codes_are_campaign(self):
        """Codes starting with N##### or C##### are service campaigns."""
        df = pd.DataFrame({"Activity Type": ["N12345", "C10001", "C99999"]})
        result = classify_category(df)
        assert (result["category"] == "Campaign").all()

    def test_unknown_activity_is_other(self):
        df = pd.DataFrame({"Activity Type": ["SOMETHING_NOVEL"]})
        result = classify_category(df)
        assert result["category"].iloc[0] == "Other"

    def test_mixed_batch(self):
        df = pd.DataFrame({
            "Activity Type": [
                "PDI_TODO", "LTSM_TODO", "C10001", "SOMETHING_ELSE", "ROADTEST",
            ]
        })
        result = classify_category(df)
        assert result["category"].tolist() == [
            "PDI", "LTSM", "Campaign", "Other", "PDI",
        ]
