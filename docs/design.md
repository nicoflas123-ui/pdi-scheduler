# Design Notes

Five views were lo-fi prototyped before coding. Visual mockups are described in the README's User Guide section; rationale is captured per-view below.

## Personas
- **Sofia (Scheduler)** — needs a ranked work queue. Doesn't want to filter or sort. Picks from the top.
- **Marcus (Team Leader)** — walks the floor. Thinks in vehicles, not activities.
- **Priya (Ops Manager)** — plans the next two weeks. Cares about totals and bottlenecks, not individual jobs.

## View → Persona → Question

| View | Persona | Question |
|---|---|---|
| 1. KPI strip | All three | "How are we doing right now?" |
| 2. Priority queue | Sofia | "What should I hand out next?" |
| 3. At-risk vehicles | Marcus | "Which cars do I walk to first?" |
| 4. Capacity vs demand | Priya | "Which days are overloaded?" |
| 5. Activity-type bottleneck | Priya | "Which type of work is the bottleneck?" |

## Design principles applied (Module 3)

- **Lo-fi over polish.** Each view was sketched as plain SVG rectangles with no decorative styling, focusing on layout and information hierarchy.
- **One question per view.** No view answers two questions; if it would, it gets split.
- **Colour means risk only.** Red/amber/green encode risk band consistently across all views — once the user has learned the system in View 1, every other view re-uses the same code.
- **Show stress states.** Mockups deliberately included overloaded days and breached rows so the design copes with the unhappy path, not just the green-state demo.