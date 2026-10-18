# ReportKit agent instructions

For every PDF publication, read [SKILL.md](SKILL.md) before selecting a target or drafting.
Follow the loop one step per session: run the single command `next_step` names, record the result, then STOP; `reportkit status` recovers saved state after a reset.
Keep publication projects and their artifacts outside this engine checkout.
Use the skill's format table to choose structure, look, source mode, and reference.
On fresh Debian/Ubuntu hosts, run `scripts/setup_tex.sh` before drafting/building; use `--check` when installed.
On Windows or without a native toolchain, use `scripts/reportkit_container.py` with a pinned image digest ([workflow](references/docker-workflow.md)).
Initialize a separate project and install its Python environment as described in SKILL.md.
Run the consumer project's `reportkit doctor --require full-build` before promising a PDF.
Build the selected target and render the pages. Inspect `build-report.json` selection, or `container-build.json` selection for container builds.
Report when visual review is unavailable; never claim it was completed.

## Session discipline

Run the loop one step per session; `next_step` is the handoff to the next session, not an invitation to run the whole loop in one conversation. Subagents write their output to files and return only a path + short summary. The consumer project's own `CLAUDE.md`/`AGENTS.md` sets the packet, handoff, and fan-out contract — follow it over these engine defaults.
