"""Generate a synthetic PDI activity export that mirrors the structure of the real data.

The output is shaped exactly like the real export-unitTable*.xlsx file — same 17
columns, same dtypes, same date conventions, same Delay Level categories —
but every value is fabricated. Safe to commit to a public repo.

Usage:
    python scripts/generate_synthetic_data.py
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
random.seed(SEED)

CORE_ACTIVITIES = [
    "PDI_TODO", "LTSM_TODO", "FUEL_LEVEL", "LTSM_TEST_DRIVE", "TRANSIT_FILM",
    "TYRES", "CARWASH_LTSM", "FIRST_MEASURE_12V_LTSM", "MBPCDIAG", "MBUX_SETUP",
    "MBPCRINSP", "ROADTEST", "MATS", "XENTRY_PRINTOUT", "TYRES_PDI",
    "EVA_CHECK", "REGISTRATION", "LOCKING_WHEEL_NUTS", "TRANSITPACKAGING",
    "HANDOVER", "LOOSE_ITEM_CHECK", "REAR_TYRE_PRESSURE", "MBTRPMODE",
    "FRONT_TYRE_PRESSURE", "LWN", "KEY_CHECK", "CATLOC_ETCHING",
    "BATTERY_CONDITION_PDI", "BUILDMMBD", "COMVAL", "MBPCTSTRIP",
    "CUSTSUBOUT", "CUSTSUBIN", "CV_TODO", "RECBATT_HY",
    "ADD_20_POUNDS_OF_FUEL",
]

CAMPAIGN_CODES = [f"C{n:05d}" for n in range(10001, 10080)]

TECHNICIANS = [
    "JOBSCHEDULER",
    "ALEX.MORGAN@EXAMPLE.COM", "BLAKE.TAYLOR@EXAMPLE.COM",
    "CASEY.JONES@EXAMPLE.COM", "DREW.PATEL@EXAMPLE.COM",
    "EMERSON.KHAN@EXAMPLE.COM", "FINN.WALKER@EXAMPLE.COM",
    "GRAY.SANTOS@EXAMPLE.COM", "HARPER.LEE@EXAMPLE.COM",
    "INDIGO.ROSE@EXAMPLE.COM", "JESSE.WU@EXAMPLE.COM",
    "KAI.NGUYEN@EXAMPLE.COM", "LANE.OKAFOR@EXAMPLE.COM",
    "MORGAN.BAUER@EXAMPLE.COM", "NOEL.ANDERSSON@EXAMPLE.COM",
    "OAKLEY.DIAZ@EXAMPLE.COM", "PARKER.HAYES@EXAMPLE.COM",
    "QUINN.RIVERA@EXAMPLE.COM",
]

RESOURCE_WEIGHTS = [26, 24, 13, 10, 5, 4, 3, 3, 3, 2, 2, 1, 1, 1, 1, 0.5, 0.5, 0.5]

DELAY_LEVELS = ["delayed", "onTime", "unknown"]
DELAY_WEIGHTS = [0.87, 0.05, 0.08]

NOW = datetime(2026, 4, 24, 9, 23, 0)


def generate_vin(i: int) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=14))
    return f"ZZZ{suffix}"


def generate_vehicle_activities(vin: str, additional_id: int, n_activities: int) -> list[dict]:
    rows: list[dict] = []
    hours_ago = random.randint(1, 24 * 21)
    creation_base = NOW - timedelta(hours=hours_ago)

    for _ in range(n_activities):
        if random.random() < 0.7:
            activity_type = random.choice(CORE_ACTIVITIES)
        else:
            activity_type = random.choice(CAMPAIGN_CODES)

        creation_time = creation_base + timedelta(seconds=random.randint(0, 3600))
        delay_level = random.choices(DELAY_LEVELS, weights=DELAY_WEIGHTS)[0]

        if random.random() < 0.02:
            maximal_duration = 17_715_785.0
            latest_end = datetime(2059, 12, 29)
            approx_end = datetime(2059, 12, 29, 15, 5)
            delay_level = "delayed"
            delay = 2_639_000.0
        else:
            maximal_duration = float(random.choice([30, 60, 120, 240, 480, 1199]))
            days_to_deadline = random.choices(
                [1, 2, 3, 5, 7, 14], weights=[10, 20, 25, 20, 15, 10]
            )[0]
            latest_end = creation_time + timedelta(days=days_to_deadline)

            if delay_level == "onTime":
                approx_end = latest_end - timedelta(minutes=random.randint(10, 720))
                delay = 0.0
            elif delay_level == "delayed":
                overshoot_min = random.randint(30, 2880)
                approx_end = latest_end + timedelta(minutes=overshoot_min)
                delay = float(overshoot_min)
            else:
                approx_end = pd.NaT
                delay = None

        if random.random() < 0.5:
            planned_start = creation_time.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            planned_start = pd.NaT

        if random.random() < 0.7:
            if pd.isna(planned_start):
                planned_end = (creation_time + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                planned_end = planned_start + timedelta(days=1)
        else:
            planned_end = pd.NaT

        if delay_level == "unknown":
            latest_end = pd.NaT
            approx_end = pd.NaT
            maximal_duration_val = None
            delay = None
        else:
            maximal_duration_val = maximal_duration

        vpc = random.random() < 0.89
        resource = random.choices(TECHNICIANS, weights=RESOURCE_WEIGHTS)[0]
        if random.random() < 0.23:
            resource = None

        rows.append({
            "No.": None,
            "Activity Type": activity_type,
            "Activity Status": "New" if random.random() > 0.0002 else "Started",
            "VPC": vpc,
            "Handling Unit": vin,
            "Additional ID": additional_id,
            "Creation Time": creation_time,
            "First Assignment Time": pd.NaT,
            "Start Time": pd.NaT,
            "Latest End": latest_end,
            "Maximal Duration": maximal_duration_val,
            "Approx. End": approx_end,
            "Delay": delay,
            "Delay Level": delay_level,
            "Resource": resource,
            "Planned Start Time": planned_start,
            "Planned End Time": planned_end,
        })
    return rows


def main() -> None:
    n_vehicles = 150
    all_rows: list[dict] = []

    for v in range(n_vehicles):
        vin = generate_vin(v)
        additional_id = 559_000_000 + v
        n_acts = random.randint(80, 120) if random.random() < 0.05 else random.randint(8, 20)
        all_rows.extend(generate_vehicle_activities(vin, additional_id, n_acts))

    start_id = 15_600_000
    for i, row in enumerate(all_rows):
        row["No."] = start_id + i

    df = pd.DataFrame(all_rows)

    column_order = [
        "No.", "Activity Type", "Activity Status", "VPC", "Handling Unit",
        "Additional ID", "Creation Time", "First Assignment Time", "Start Time",
        "Latest End", "Maximal Duration", "Approx. End", "Delay", "Delay Level",
        "Resource", "Planned Start Time", "Planned End Time",
    ]
    df = df[column_order]

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sample_pdi_export.xlsx"
    df.to_excel(out_path, index=False, sheet_name="Export")

    print(f"Wrote {len(df):,} rows for {df['Handling Unit'].nunique()} vehicles")
    print(f"Output: {out_path}")
    print("\nDelay Level distribution:")
    print(df["Delay Level"].value_counts(normalize=True).round(3).to_string())


if __name__ == "__main__":
    main()
