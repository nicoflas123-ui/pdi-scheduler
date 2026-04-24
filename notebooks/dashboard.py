# ruff: noqa: E402
# %% [markdown]
# # PDI Scheduler Dashboard
#
# Workflow prioritisation dashboard for the PDI team. Shows at-risk activities,
# the day's priority queue, at-risk vehicles, and capacity vs demand.
#
# ## How to run
#
# **In Google Colab:** click `Runtime → Run all`. The first cell bootstraps the package.
#
# **Locally / Codespaces:** `pip install -e ".[dev]"` from the repo root, then
# open this file in Jupyter/VS Code — the `# %%` markers split it into cells.

# %% [markdown]
# ## Colab bootstrap
# No-op when running locally.

# %%
import os
import sys

IN_COLAB = "google.colab" in sys.modules

if IN_COLAB:
    import subprocess
    subprocess.run(
        ["git", "clone",
         "https://github.com/nicoflas123-ui/pdi-scheduler.git",
         "/content/pdi-scheduler"],
        check=False,
    )
    subprocess.run(["pip", "install", "-q", "-e", "/content/pdi-scheduler"], check=False)
    os.chdir("/content/pdi-scheduler")
    sys.path.insert(0, "/content/pdi-scheduler/src")

# %% [markdown]
# ## Load and process the data
# Full pipeline: load → clean → compute slack → categorise risk → classify PDI/LTSM.
#
# This cell changes the working directory to the repo root so relative paths
# like `data/sample_pdi_export.xlsx` always resolve, regardless of where the
# notebook is opened from.

# %%
from datetime import datetime
from pathlib import Path

# Walk up from wherever we are until we find the repo root (has a `data/` folder).
p = Path.cwd().resolve()
for _ in range(5):
    if (p / "data" / "sample_pdi_export.xlsx").exists():
        os.chdir(p)
        break
    p = p.parent

from pdi_scheduler.at_risk_vehicles import build_at_risk_vehicles
from pdi_scheduler.categories import classify_category
from pdi_scheduler.cleaner import clean
from pdi_scheduler.kpis import compute_kpis
from pdi_scheduler.loader import load_activities
from pdi_scheduler.priority_queue import build_priority_queue
from pdi_scheduler.risk import categorise
from pdi_scheduler.scheduling import compute_slack

DATA_PATH = Path("data") / "sample_pdi_export.xlsx"
NOW = datetime(2026, 4, 24, 9, 23)

raw = load_activities(DATA_PATH)
cleaned = clean(raw, today=NOW)
with_slack = compute_slack(cleaned, now=NOW)
with_risk = categorise(with_slack, now=NOW)
processed = classify_category(with_risk)

print(
    f"Loaded {len(processed):,} activities "
    f"across {processed['Handling Unit'].nunique()} vehicles"
)

# %% [markdown]
# ## View 1 — KPI Strip
# Headline numbers for all three user types (scheduler, team leader, ops manager).

# %%
from IPython.display import HTML

kpis = compute_kpis(processed, now=NOW)

html = f"""
<div style='display:flex;gap:12px;font-family:system-ui,sans-serif;'>
  <div style='flex:1;border-left:4px solid #2ca02c;padding:12px;background:#f8f8f8;'>
    <div style='font-size:12px;color:#666;'>On-time %</div>
    <div style='font-size:28px;font-weight:500;'>{kpis['on_time_pct']}%</div>
    <div style='font-size:12px;color:#888;'>of scheduled activities</div>
  </div>
  <div style='flex:1;border-left:4px solid #d62728;padding:12px;background:#f8f8f8;'>
    <div style='font-size:12px;color:#666;'>At-risk count</div>
    <div style='font-size:28px;font-weight:500;'>{kpis['at_risk_count']:,}</div>
    <div style='font-size:12px;color:#888;'>Breached + Critical + At Risk</div>
  </div>
  <div style='flex:1;border-left:4px solid #ff7f0e;padding:12px;background:#f8f8f8;'>
    <div style='font-size:12px;color:#666;'>Due today</div>
    <div style='font-size:28px;font-weight:500;'>{kpis['due_today']}</div>
    <div style='font-size:12px;color:#888;'>deadlines today</div>
  </div>
  <div style='flex:1;border-left:4px solid #1f77b4;padding:12px;background:#f8f8f8;'>
    <div style='font-size:12px;color:#666;'>Utilisation %</div>
    <div style='font-size:28px;font-weight:500;'>{kpis['utilisation_pct']}%</div>
    <div style='font-size:12px;color:#888;'>demand vs capacity today</div>
  </div>
</div>
"""

HTML(html)

# %% [markdown]
# ## View 2 — Priority Queue
# Top 20 activities sorted by slack (most urgent first). Non-PDI rows are muted
# because the PDI team can't act on them directly.

# %%
queue = build_priority_queue(processed, top_n=20)

RISK_COLOURS = {
    "Breached":    "background-color: #fcebeb;",
    "Critical":    "background-color: #fff3f3;",
    "At Risk":     "background-color: #fff8e1;",
    "Comfortable": "",
}


def style_row(row):
    base = RISK_COLOURS.get(row["risk_band"], "")
    if row["category"] != "PDI":
        base += " opacity: 0.55;"
    return [base] * len(row)


(queue.style
    .apply(style_row, axis=1)
    .format({"slack_minutes": "{:+.0f}m", "Maximal Duration": "{:.0f}m"})
    .hide(axis="index")
)

# %% [markdown]
# ## View 3 — At-Risk Vehicles
# Marcus the team leader's view — one row per vehicle with a worst-risk rollup.
# Only vehicles with at least one at-risk PDI activity appear.

# %%
vehicles = build_at_risk_vehicles(processed)

VEHICLE_RISK_COLOURS = {
    "Breached": "background-color: #fcebeb;",
    "Critical": "background-color: #fff3f3;",
    "At Risk":  "background-color: #fff8e1;",
}


def style_vehicle_row(row):
    return [VEHICLE_RISK_COLOURS.get(row["worst_risk"], "")] * len(row)


print(f"{len(vehicles)} vehicles flagged at risk")

(vehicles.head(20).style
    .apply(style_vehicle_row, axis=1)
    .format({
        "total_remaining_minutes": "{:.0f}m",
        "earliest_deadline": "{:%d %b %H:%M}",
    })
    .hide(axis="index")
)