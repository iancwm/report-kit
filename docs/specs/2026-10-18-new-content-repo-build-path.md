# Spec — fix the new-content-repo build path

- **Date:** 2026-10-18
- **Branch:** (proposed — none assigned yet)
- **Area:** `publication_pipeline/scripts/publication_build.py`, `python_scripts/reportkit/{cli,target,loop,doctor}.py`, `SKILL.md`, `references/repository-boundary.md`, `references/troubleshooting.md`
- **Status:** proposed

## Summary

Starting a **new** content repo with ReportKit and building it end-to-end is
frictionful in ways that push workarounds into the consumer. A consumer
(`computer-zero-to-hero`) had to write its own `CLAUDE.md` rules to (a) rename
the built PDF from the title slug to a stable filename, and (b) guard against
a failed build leaving a stray PDF behind. Those are engine concerns, not
consumer concerns. This spec defines the fix so a new content repo builds and
packages end-to-end without consumer-side rename or cleanup logic.

## Current behaviour (verified against `main` @ `a370bee`)

- `reportkit build` writes exactly one PDF, named `<slug>.pdf` (the slug is
  derived from `publication.yaml`'s title), into `<project>/build/combined/`.
  `reportkit package` copies that single PDF and its QA manifest into
  `<project>/output/`. (`SKILL.md`, `references/repository-boundary.md`.)
- `reportkit init <dir>` scaffolds the recommended consumer structure and
  refuses a directory inside the engine clone. (`references/repository-boundary.md`.)
- The loop is documented as a table in `SKILL.md` (select → lock → scaffold →
  preflight → author → materialize → check → build → diagnose → review →
  deliver). There is no single "start a new content repo" runnable that ties
  these together for a cold start, including the toolchain decision.
- A consumer worked around the slug filename and the failed-build cleanup in
  its own `CLAUDE.md` (rename slug → `publication.pdf`; on gate failure delete
  the slug PDF and do not touch `output/`).

## Gaps

| # | Gap | Effect |
|---|-----|--------|
| G1 | Output filename is the title slug (`<slug>.pdf`), not a stable, predictable name | Every consumer must slugify its title to locate the artifact, or rename it. Consumers write their own rename step. |
| G2 | No single cold-start runnable for a new content repo | An agent must assemble the loop from several docs and decide native vs container toolchain by itself; wrong first steps burn turns. |
| G3 | Failed-build cleanup (stale slug PDF, untouched `output/`) is documented in prose, not enforced or reported | A failed build can leave a PDF that looks like a deliverable. |
| G4 | Cold-start toolchain diagnosis does not clearly route to the two supported paths (`setup_tex.sh` vs pinned container digest) | A fresh host fails the first build and the remediation is not obvious. |

## Work items

### W1 — Stable, predictable output filename (G1)

Make the delivered filename a first-class, documented contract rather than an
implicit slug.

- **Decision (choose one):**
  1. Emit a stable filename `publication.pdf` (the TeX compiler's intermediate
     name already exists) and record the slug in `build-report.json`; or
  2. Keep `<slug>.pdf` but expose the resolved filename in the `build` result
     payload (`{"pdf": "<path>", "slug": "...", ...}`) so consumers never
     re-derive it.
- **Acceptance:** a consumer can run `reportkit build --source-root <p> --json`
  and read the exact output PDF path from the result without slugifying the
  title; `reportkit package` copies that same path into `output/`.

### W2 — Single cold-start runnable (G2)

Add a documented, runnable cold-start path that an agent can follow from an
empty directory to a packaged PDF.

- **Content:** target set → init → materialize → doctor → check → build →
  package, in one sequence, with the toolchain decision made explicit at the
  `doctor` step.
- **Location:** a new `references/quickstart-new-repo.md` (or fold into
  `SKILL.md`), and route `reportkit status` / `next_step` to it on an
  undeclared target.
- **Acceptance:** a fresh agent, following only that reference, reaches a
  packaged PDF without consulting other docs.

### W3 — Enforce and report the single-PDF + cleanup contract (G3)

Make the "exactly one PDF in `build/combined/`" invariant an executable check
rather than prose.

- **Content:** after `build`, assert exactly one `.pdf` in `build/combined/`
  and surface it in the result. On a failed gate, remove the stray slug PDF and
  leave `output/` untouched, reporting that explicitly.
- **Acceptance:** a failed build reports `{"passed": false, "pdf_left": false,
  "output_touched": false}` (or equivalent) and leaves no `.pdf` in
  `build/combined/`.

### W4 — Cold-start toolchain routing (G4)

Make `reportkit doctor --require full-build` state, in one place, which
supported toolchain path to take and the exact next command.

- **Content:** doctor output names the missing dependency and the remediation
  (`bash scripts/setup_tex.sh` for native, or the pinned image digest command
  from `references/docker-workflow.md` for container), instead of only a
  downgraded `MODE:` line.
- **Acceptance:** on a host with no TeX, `doctor` returns a remediation that,
  run as-is, produces a passing `doctor --require full-build`.

## Out of scope

- Changing the pinned toolchain image or ICU 76.1 pinning (separate release
  gate).
- `reportkit materialize` / single-PDF-build integration (tracked in
  `2026-10-05-materialize-consumer-context-integration.md`).
- Consumer-project naming conventions beyond the filename contract in W1.

## Acceptance summary

A new content repo, started by an agent from an empty directory, reaches a
packaged PDF by following one documented path, reads its exact output path from
the build result, and never has to write rename or cleanup logic of its own.
