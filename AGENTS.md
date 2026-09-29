# ReportKit agent instructions

1. Read `SKILL.md` before planning a publication.
2. The CLI enforces the publication loop; follow each command's `next_step`.
3. Keep each publication project outside this engine repository.
4. Use the selection table to choose publication type, theme, and source mode before authoring.
5. Load target-specific primitives with `reportkit context --slice primitives --json`.
6. Build through `reportkit build`, then inspect the build report and rendered pages.
7. Record visual review with `reportkit review` and confirm delivery state with `reportkit status`.
