"""Classify activity types into PDI vs LTSM vs Campaign vs Other.

This drives the visual distinction in the Priority Queue and other views —
non-PDI activities are shown muted because the PDI team can't act on them
directly (LTSM is a separate operation; campaigns are scheduled centrally).
"""
from __future__ import annotations

import re

import pandas as pd

ACTIVITY_TYPE_COL = "Activity Type"
CATEGORY_COL = "category"

# Core PDI activity types — based on the Op10-Op80 workflow in the PDI process flow.
PDI_TYPES = frozenset({
    "PDI_TODO", "ROADTEST", "MBPCDIAG", "MBUX_SETUP", "MBPCRINSP",
    "TYRES", "TYRES_PDI", "EVA_CHECK", "HANDOVER", "LOCKING_WHEEL_NUTS",
    "BATTERY_CONDITION_PDI", "REGISTRATION", "XENTRY_PRINTOUT", "MATS",
    "TRANSITPACKAGING", "LOOSE_ITEM_CHECK", "REAR_TYRE_PRESSURE",
    "FRONT_TYRE_PRESSURE", "MBTRPMODE", "LWN", "KEY_CHECK",
    "CATLOC_ETCHING", "BUILDMMBD", "COMVAL", "MBPCTSTRIP",
    "CUSTSUBOUT", "CUSTSUBIN", "CV_TODO",
})

# Campaign codes look like N##### or C##### (5-digit suffix)
CAMPAIGN_PATTERN = re.compile(r"^[NC]\d{5}$")


def _classify_one(activity_type: str) -> str:
    if activity_type in PDI_TYPES:
        return "PDI"
    if "LTSM" in activity_type:
        return "LTSM"
    if CAMPAIGN_PATTERN.match(activity_type):
        return "Campaign"
    return "Other"


def classify_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``category`` column.

    Categories:
        - ``"PDI"`` — core PDI activities (Op10-Op80 workflow)
        - ``"LTSM"`` — long-term storage maintenance activities
        - ``"Campaign"`` — service campaigns (N##### / C##### codes)
        - ``"Other"`` — anything unrecognised
    """
    out = df.copy()
    out[CATEGORY_COL] = out[ACTIVITY_TYPE_COL].apply(_classify_one)
    return out