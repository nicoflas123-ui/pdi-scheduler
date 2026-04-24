# Sprint Retrospectives

A running log of sprint retrospectives, in keeping with Scrum ceremonies (Module 1 L10). Each entry covers what went well, what didn't, and concrete actions for the next sprint.

---

## Sprint 1 — Core Scheduling Logic (Retro)

**Sprint goal:** Deliver five modules of tested business logic (`loader`, `cleaner`, `scheduling`, `risk`, `capacity`) ready for the dashboard views in Sprint 2.

**Outcome:** ✅ All 5 tickets (#16, #17, #18, #19, #20) merged to `main` across 5 PRs. 58 unit tests, 100% line coverage on every module.

### What went well

- **TDD rhythm locked in from ticket #16 onwards.** Red → Green → Refactor is now muscle memory. Commit messages tag each phase, so the commit log is its own process documentation.
- **Type-strong contracts between modules.** Column-name constants (e.g. `DEADLINE_COL`) live in the module that owns them and are re-used downstream. Refactors in `cleaner` didn't break `scheduling` because the tests held the line.
- **Ruff caught real bugs, not just style issues.** The F811 duplicate-import in PR #32 and the F401 unused import in PR #34 would have shipped otherwise.
- **Edge cases are tested, not assumed.** Boundary conditions like "slack exactly zero" and "placeholder 2059 dates" have dedicated tests. Real-world data surprises should hit familiar guardrails.

### What didn't go well

- **PR #32 shipped pre-lint code.** `ruff check . --fix` was run locally but the changes weren't staged before `git push`. Required a cleanup PR (#33) to restore a clean `main`. Embarrassing but educational — lesson applied from PR #34 onwards and no repeats since.
- **Scope creep attempt on Ticket #20.** Domain input on agency staffing triggered a tempting redesign. Caught ourselves, chose Option A (stay on original scope), noted the real staffing problem in Next Steps. A good reminder that MVP scope discipline is a deliverable, not an afterthought.
- **Skipped refactor on two tickets (#19, #20).** Intentional — green code was already clean — but had to explicitly document the decision to avoid looking like I forgot the step. Future sprints should state upfront whether each ticket will have a refactor phase.

### Actions for Sprint 2

1. **Always commit ruff fixes before pushing.** This is now a pre-push checklist item; if a CI pipeline lands this sprint it becomes enforced automatically.
2. **State the refactor plan at the start of each ticket.** Either "will refactor X" or "skipping, code already clean" — decide upfront, not retroactively.
3. **Scope freeze for Sprint 2.** Any new domain insight goes straight into a new ticket for Sprint 3 or "Next Steps" — no mid-sprint redesigns.

### By the numbers

| Metric | Value |
|---|---|
| Tickets closed | 5 (#16, #17, #18, #19, #20) |
| Pull requests merged | 6 (5 feature + 1 cleanup) |
| Commits on `main` | 25+ |
| Unit tests added | 58 |
| Line coverage | 100% on all 5 modules |
| Lint status | Clean |