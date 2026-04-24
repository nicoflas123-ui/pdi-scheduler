"""Tests for pdi_scheduler.loader — the Excel data loader."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pdi_scheduler.loader import (
    DATETIME_COLUMNS,
    EXPECTED_COLUMNS,
    load_activities,
)

# Path to the committed synthetic dataset. Tests assume it has been generated.
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_pdi_export.xlsx"


class TestLoadActivities:
    """Tests for the load_activities function."""

    def test_returns_dataframe(self):
        """Happy path: loading a valid Excel returns a DataFrame."""
        df = load_activities(SAMPLE_PATH)
        assert isinstance(df, pd.DataFrame)

    def test_has_all_expected_columns(self):
        """Loader preserves all 17 columns from the export."""
        df = load_activities(SAMPLE_PATH)
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_has_expected_row_count(self):
        """Loader reads every row of the synthetic file."""
        df = load_activities(SAMPLE_PATH)
        # Synthetic data: 150 vehicles, ~2,500 activities
        assert len(df) > 2_000
        assert len(df) < 5_000

    def test_datetime_columns_are_parsed(self):
        """Date columns come back as pandas datetime64, not strings."""
        df = load_activities(SAMPLE_PATH)
        for col in DATETIME_COLUMNS:
            assert pd.api.types.is_datetime64_any_dtype(df[col]), (
                f"Column {col!r} is not datetime; got {df[col].dtype}"
            )

    def test_vpc_column_is_boolean(self):
        """VPC column is parsed as bool, not string or int."""
        df = load_activities(SAMPLE_PATH)
        assert pd.api.types.is_bool_dtype(df["VPC"])

    def test_raises_file_not_found(self, tmp_path):
        """Non-existent path raises FileNotFoundError with a helpful message."""
        missing = tmp_path / "does_not_exist.xlsx"
        with pytest.raises(FileNotFoundError, match="does_not_exist.xlsx"):
            load_activities(missing)

    def test_raises_value_error_on_missing_columns(self, tmp_path):
        """An Excel file missing required columns raises ValueError."""
        bad_path = tmp_path / "bad.xlsx"
        # Create an Excel with the wrong shape
        pd.DataFrame({"some": [1], "other": [2], "columns": [3]}).to_excel(
            bad_path, index=False, sheet_name="Export"
        )
        with pytest.raises(ValueError, match="missing expected columns"):
            load_activities(bad_path)
