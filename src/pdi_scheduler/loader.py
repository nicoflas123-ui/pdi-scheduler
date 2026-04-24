"""Load PDI activity data from the Excel export.

The export has a fixed 17-column schema. This module reads the file, validates
the columns, and returns a typed pandas DataFrame.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "No.", "Activity Type", "Activity Status", "VPC", "Handling Unit",
    "Additional ID", "Creation Time", "First Assignment Time", "Start Time",
    "Latest End", "Maximal Duration", "Approx. End", "Delay", "Delay Level",
    "Resource", "Planned Start Time", "Planned End Time",
]

DATETIME_COLUMNS = [
    "Creation Time", "First Assignment Time", "Start Time",
    "Latest End", "Approx. End", "Planned Start Time", "Planned End Time",
]


def load_activities(path: str | Path) -> pd.DataFrame:
    """Read a PDI activity export and return a typed DataFrame.

    Args:
        path: Path to the .xlsx export file.

    Returns:
        DataFrame with all 17 expected columns, dates parsed as datetime64,
        and VPC parsed as bool.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file is missing any of the 17 expected columns.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDI export not found: {path}")

    df = pd.read_excel(path, sheet_name="Export")

    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Export is missing expected columns: {sorted(missing)}"
        )

    # Coerce date columns to datetime — openpyxl usually gets this right,
    # but we force it to guarantee the contract with downstream modules.
    for col in DATETIME_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # VPC should always be boolean
    df["VPC"] = df["VPC"].astype(bool)

    # Preserve canonical column order
    return df[EXPECTED_COLUMNS]