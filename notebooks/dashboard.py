# ruff: noqa: E402
# %% [markdown]
# # PDI Scheduler Dashboard
#
# Workflow prioritisation dashboard for the PDI team. Shows at-risk activities,
# the day's priority queue, at-risk vehicles, capacity vs demand, and the
# activity-type bottleneck.
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

# %%
from datetime import datetime, timedelta
from pathlib import Path

# Walk up until we find the repo root (has a `data/` folder).
p = Path.cwd().resolve()
for _ in range(5):
    if (p / "data" / "sample_pdi_export.xlsx").exists():
        os.chdir(p)
        break
    p = p.parent

from pdi_scheduler.at_risk_vehicles import build_at_risk_vehicles
from pdi_scheduler.capacity import daily_load
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

# %% [markdown]
# ## View 4 — Capacity vs Demand (next 14 days)
# Priya the ops manager's forward-looking view. Blue bars = planned work minutes,
# dashed line = capacity. Bars crossing the line highlight overloaded days.

# %%
import plotly.graph_objects as go

load_df = daily_load(
    processed,
    start_date=NOW.date(),
    days=14,
    hours_per_resource_per_day=7.5,
)

capacity_line = load_df["capacity_minutes"].iloc[0] if len(load_df) else 0
bar_colours = [
    "#e24b4a" if planned > capacity_line else "#378add"
    for planned in load_df["planned_minutes"]
]

fig_capacity = go.Figure()
fig_capacity.add_trace(go.Bar(
    x=load_df["date"],
    y=load_df["planned_minutes"],
    marker_color=bar_colours,
    name="Planned minutes",
    hovertemplate="<b>%{x|%a %d %b}</b><br>Planned: %{y:,.0f}m<extra></extra>",
))
fig_capacity.add_hline(
    y=capacity_line,
    line=dict(color="black", width=1.5, dash="dash"),
    annotation_text=f"Capacity ({capacity_line:,.0f}m)",
    annotation_position="top right",
)
fig_capacity.update_layout(
    title="Capacity vs demand — next 14 days",
    xaxis_title="Deadline date",
    yaxis_title="Minutes",
    height=380,
    margin=dict(l=40, r=40, t=60, b=40),
    showlegend=False,
    plot_bgcolor="white",
)
fig_capacity.update_xaxes(showgrid=False)
fig_capacity.update_yaxes(gridcolor="#eee")
fig_capacity.show()

# %% [markdown]
# ## View 5 — Activity-Type Bottleneck
# Which PDI activity types are driving the backlog? Horizontal bars segmented
# by risk band, sorted by total at-risk minutes.

# %%
pdi_at_risk = processed.loc[
    (processed["category"] == "PDI")
    & (~processed["is_unscheduled"])
    & (processed["risk_band"].isin(["Breached", "Critical", "At Risk"]))
].copy()

# Cap unrealistic durations (placeholder 1199m ROADTEST values in real data).
pdi_at_risk["_capped_duration"] = pdi_at_risk["Maximal Duration"].clip(upper=480)

agg = (pdi_at_risk
    .groupby(["Activity Type", "risk_band"], as_index=False)
    .agg(minutes=("_capped_duration", "sum"), jobs=("_capped_duration", "size"))
)

totals = agg.groupby("Activity Type", as_index=False)["minutes"].sum()
top10 = totals.sort_values("minutes", ascending=False).head(10)["Activity Type"]
agg = agg.loc[agg["Activity Type"].isin(top10)]

BAND_COLOURS = {"Breached": "#e24b4a", "Critical": "#a32d2d", "At Risk": "#ef9f27"}

fig_bottleneck = go.Figure()
for band in ["Breached", "Critical", "At Risk"]:
    sub = agg.loc[agg["risk_band"] == band]
    fig_bottleneck.add_trace(go.Bar(
        y=sub["Activity Type"],
        x=sub["minutes"],
        name=band,
        orientation="h",
        marker_color=BAND_COLOURS[band],
        hovertemplate="<b>%{y}</b><br>" + band + ": %{x:,.0f}m<extra></extra>",
    ))

fig_bottleneck.update_layout(
    title="Activity-type bottleneck — top 10 PDI types by at-risk minutes",
    barmode="stack",
    xaxis_title="At-risk minutes (durations capped at 480m)",
    yaxis=dict(categoryorder="total ascending"),
    height=460,
    margin=dict(l=160, r=40, t=60, b=40),
    plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig_bottleneck.update_xaxes(gridcolor="#eee")
fig_bottleneck.show()