[![CI](https://github.com/nicoflas123-ui/pdi-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/nicoflas123-ui/pdi-scheduler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# PDI Scheduler

A workflow prioritisation dashboard for Pre-Delivery Inspection (PDI) operations. Ingests an Excel export of in-flight PDI activities and surfaces what's at risk, what's next in the queue, which vehicles need attention, and how the next two weeks of demand compare to capacity.

**Python version:** 3.11+ (developed on 3.12.1).

---

## 1. Overview

PDI is the final stage of preparing a vehicle before it leaves a compound for a dealer or end customer — safety checks, road tests, electronic setup, valet, etc. (see `docs/PDI_Process_Flow.pdf` for the full Op10–Op80 workflow). At any one time a real PDI operation has thousands of activities in flight across hundreds of vehicles, with deadlines driven by customer requested handover dates.

This tool ingests the daily activity export and produces a five-view dashboard that answers a different question for each user:

| User | Question |
|---|---|
| Scheduler (Sofia) | "What should I hand out next?" |
| Team Leader (Marcus) | "Which cars do I need to walk over to right now?" |
| Ops Manager (Priya) | "Which days next fortnight will be overloaded? Which activity types are bottlenecking us?" |

---

## 2. Problem & Users

The real-world data we sanitised showed **86.7% of activities flagged as delayed** out of nearly 18,000. There was no single view ranking them. Schedulers, team leaders and ops managers all had to mentally re-sort the same Excel file with different filters.

PDI Scheduler replaces that with a single dashboard that sorts once (by slack time) and surfaces the three perspectives each user actually needs.

---

## 3. Design

The five dashboard views were prototyped in low-fidelity before any code was written, following Module 3 (Design Thinking, Empathy, Lo-Fi prototyping). Three personas (Sofia / Marcus / Priya) drove the empathy stage; each view was designed to answer one specific question for one specific persona, with no overlap. The design artefacts and rationale are in `docs/design.md`.

---

## 4. Project Management

The project followed an Agile / Kanban approach (Module 1 L8–L11) with sprint-based delivery and a GitHub Projects board as the Jira-equivalent.

**Board:** [PDI Scheduler Delivery Board](https://github.com/users/nicoflas123-ui/projects/1)

**Sprint structure:**
- **Sprint 0** — setup (scaffolding, synthetic data, Figma prototype, README skeleton)
- **Sprint 1** — five business-logic modules built test-first (loader, cleaner, scheduling, risk, capacity)
- **Sprint 2** — dashboard views (KPI strip, priority queue, at-risk vehicles, capacity vs demand, bottleneck)
- **Sprint 3** — CI/CD, documentation, evaluation, bug-ticket workflow demo

**Tooling:**
- **GitHub Issues** — captured all 19 requirements as tickets before any code was written. Two issue templates (`feature_request.md` and `bug_report.md`) enforce different documentation for features vs bugs (subtask 9).
- **GitHub Projects** — Kanban board with columns `Backlog → Sprint Ready → In Progress → In Review → Done`.
- **GitHub Pull Requests** — every feature ticket = one branch = one PR closing that issue. Self-review comments record per-PR sign-off.
- **Labels** — sprint, priority, and type labels on every ticket for at-a-glance triage.
- **Sprint retrospectives** — `docs/sprint_retrospectives.md` captures lessons after each sprint (Module 1 L10 — Scrum Ceremonies).

---

## 5. Build Process

The MVP was built incrementally, one feature per branch per PR. Highlights:

**Test-Driven Development (Module 5).** All five Sprint 1 modules were built test-first. Every ticket has a Red → Green → Refactor commit trail visible in `git log`. For example, PR #32 (data loader): commits 2476ac2 (Red — failing tests), 9a21a62 (Green — minimum implementation), b821c30 (Refactor — extracted shared constants).

**Architecture (Module 6).** Logic lives in `src/pdi_scheduler/` as a proper Python package with one module per single responsibility:

```
loader      → read Excel into typed DataFrame
cleaner     → flag unscheduled rows, normalise deadline column
scheduling  → compute slack time
risk        → categorise into Breached / Critical / At Risk / Comfortable / Unscheduled
capacity    → aggregate planned vs available minutes per day
categories  → classify activities as PDI / LTSM / Campaign / Other
kpis        → headline dashboard metrics
priority_queue → top-N actionable activities for the queue view
at_risk_vehicles → vehicle-level rollup for the team-leader view
```

The notebook (`notebooks/dashboard.ipynb`) is a thin presentation layer over those modules — pure rendering, no business logic. This separation (Module 6 L5) means the logic is unit-testable without a running notebook.

**Honest engineering trail.** PRs #33 and #40 are housekeeping/cleanup PRs that fixed lint issues missed in earlier PRs. Kept honest in the commit history rather than rewritten.

---

## 6. Testing & CI/CD

- **102 unit tests**, 100% line coverage on every business-logic module
- **`pytest`** for the test runner with **`pytest-cov`** for coverage
- **`ruff`** for linting and static analysis
- **GitHub Actions** runs `ruff check` + `pytest --cov` on every push to `main` and every PR. Coverage reports uploaded as artifacts.

A red CI blocks merging until fixed — see `.github/workflows/ci.yml`.

---

## 7. User Guide

### Quickest path — Google Colab

1. Open [`notebooks/dashboard.ipynb`](notebooks/dashboard.ipynb) in Colab (`File → Open notebook → GitHub` and paste the repo URL)
2. `Runtime → Run all`
3. The first cell auto-clones and installs the package (~30 seconds), then the dashboard renders below

### Local

```bash
git clone https://github.com/nicoflas123-ui/pdi-scheduler.git
cd pdi-scheduler
pip install -e ".[dev]"
jupyter lab notebooks/dashboard.ipynb
```

### Reading The Dashboard

| View | What it shows | Best for |
|---|---|---|
| **KPI strip** | On-time %, at-risk count, due today, utilisation | Quick health check |
| **Priority queue** | Top 20 activities ranked by slack ascending | Picking the next job |
| **At-risk vehicles** | One row per vehicle, worst risk + remaining work | Shop-floor walkaround |
| **Capacity vs demand** | 14-day bar chart, overloaded days in red | Planning agency staffing |
| **Activity-type bottleneck** | Top 10 PDI types by at-risk minutes, segmented by risk band | Skill-mix decisions |

### Risk Bands

- **Breached** — deadline already past
- **Critical** — slack ≤ 0 (won't make deadline if started now)
- **At Risk** — slack < 4 hours
- **Comfortable** — slack ≥ 4 hours
- **Unscheduled** — placeholder/unknown deadline; excluded from headline metrics

### Using your own data

Replace `data/sample_pdi_export.xlsx` with your real PDI activity export (must have the same 17 columns — see `pdi_scheduler.loader.EXPECTED_COLUMNS`).

---

## 8. Technical Documentation

### Repo structure

```
pdi-scheduler/
├── .github/
│   ├── workflows/ci.yml       GitHub Actions pipeline
│   └── ISSUE_TEMPLATE/        feature + bug templates
├── src/pdi_scheduler/         business-logic package (9 modules)
├── tests/                     102 unit tests, 100% coverage
├── notebooks/
│   ├── dashboard.py           cell-marked Python source (clean diffs)
│   └── dashboard.ipynb        Colab-ready notebook (jupytext-paired)
├── data/sample_pdi_export.xlsx  synthetic dataset, 2,551 rows / 150 vehicles
├── scripts/generate_synthetic_data.py  reproducible data generator
├── docs/                      design, retrospectives, this file
├── pyproject.toml             package + dev deps
└── requirements.txt
```

### Pipeline

```
load_activities → clean → compute_slack → categorise → classify_category
                                          ↓
                          (KPIs / queue / vehicles / capacity / bottleneck)
```

Each function is pure (no I/O, no mutation), takes a DataFrame, returns a DataFrame. Easy to test, easy to compose.

### Run tests locally

```bash
pytest -v                              # full suite
pytest --cov=src/pdi_scheduler         # with coverage
ruff check .                           # lint
```

### How CI works

`.github/workflows/ci.yml` runs on push to `main` and every PR:

1. Checkout repo
2. Set up Python 3.11
3. `pip install -e ".[dev]"`
4. `ruff check .`
5. `pytest --cov`
6. Upload coverage report as artifact

Failures block merge.

---

## 9. Evaluation

### What works well

- **TDD discipline produced robust, isolated logic.** All 9 business-logic modules have 100% unit-test coverage; refactors during development never broke anything because the tests held the line. Real bugs (e.g. F811 duplicate import in PR #32) were caught by `ruff` before merge.
- **Clean separation of logic and presentation.** The package contains zero rendering code; the notebook contains zero business logic. Either can change independently.
- **Honest engineering history.** The git log tells the truth — including PRs #33 and #40 which fixed lint issues missed in earlier PRs. A team reviewer can see exactly what happened.
- **Reproducible synthetic data.** Anyone cloning the public repo can regenerate the dataset deterministically with `python scripts/generate_synthetic_data.py`. No real PDI data is exposed.

### Limitations

- **Capacity model is illustrative, not operational.** The current `daily_load` function treats capacity as `unique_resources × 7.5h × 60`. Real PDI staffing involves CLdN fixed staff plus flexible agency labour with multi-day booking lead times — see Next Steps.
- **No persistence.** Each run loads the Excel file from scratch. A real deployment would want incremental updates and run-over-run comparisons.
- **DST handling is naive.** The slack calculator does straightforward `(deadline − now)` arithmetic, which is off by 60 minutes across BST↔GMT changes (this is exactly the bug captured in Issue #30).
- **Lo-fi visual design.** Charts are functional, not polished. Production-grade design would need a UX pass.

### What I would do differently

- **Set up the CI workflow in Sprint 0, not Sprint 3.** The recurring "lint fixes missed before push" issue (PRs #33, #40) would have been caught automatically if CI had been live from the start.
- **Disable VS Code format-on-save earlier.** Same root cause as above — silent file edits between commit and push are now disabled, but only after losing time to two cleanup PRs.
- **Decide refactor strategy upfront per ticket.** Multiple Sprint 1 tickets had no meaningful refactor step because the green code was already clean. I documented the decision retroactively, which works but reads as a justification rather than a plan. Future projects: state "no refactor" upfront in the ticket if applicable.

### Next Steps (if this were a v1.1)

1. **Real staffing model.** Inputs for CLdN fixed headcount + booked agency staff per day. Output: gap analysis showing how many additional agency bookings are needed for the coming week.
2. **Job rotation suggestions.** When PDI is quiet, recommend redeploying technicians to LTSM/repair sections. When PDI is busy, recommend pulling them back.
3. **Streamlit deployment.** The notebook works for analysts; a hosted Streamlit version would let non-technical users see the dashboard via a URL.
4. **Pre-commit hook.** `ruff` + `pytest` as a Git pre-commit hook to enforce locally what CI enforces remotely.
5. **DST-safe slack calculation** (Issue #30) — switch to timezone-aware arithmetic.

### Reflection on SDLC choices

A Kanban-style flow with three short sprints suited a solo project. The single biggest discipline-payoff was TDD: writing tests before code forced me to make API decisions before implementation decisions, which produced cleaner module boundaries than I would have got from "implement first, test later." If I had chosen Waterfall (Module 1 L4), I would have spent longer on upfront design and got less feedback from running code; iterative sprints with a working notebook from Sprint 2 onwards meant I could see the design decisions playing out in real outputs and adjust scope (e.g. the Resource-column rethink mid-Sprint 2).

---

## 10. Acknowledgements

Synthetic data generated to mirror the structure of a real PDI activity export (Mercedes-Benz UK / CLdN) — all VINs, names, and emails are fabricated. Real export not committed to this repo.

Course modules referenced throughout: M1 (SDLC, Agile, Scrum, Kanban), M2 (GitHub Projects, Issues, Markdown, PRs), M3 (Design Thinking, Empathy, Lo-Fi, Figma), M5 (TDD, Unit Testing, Static Analysis), M6 (Architecture, SOLID, Modularity, Software Engineering for Data Science).