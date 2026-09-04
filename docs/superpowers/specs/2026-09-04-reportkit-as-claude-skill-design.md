# ReportKit as a Claude Skill — Design

Date: 2026-09-04
Status: Approved for planning

## Problem

ReportKit is a LaTeX report toolkit (document class, style files, a matplotlib
theme, font bundle, and an execution guide) currently consumed by hand-copying
files into a Claude Project or by pasting `docs/CLAUDE_EXECUTION.md` into a
session. There is no packaged way for a Claude session — including one driven
from the Claude mobile app — to pick this toolkit up and start producing
reports, and no lightweight guardrail that catches a broken `.cls`/`.sty`
change before it ships.

## Goal

Turn this repo into a **Claude Skill**: a git-clonable package with a
`SKILL.md` entry point that a claude.ai session's code-execution sandbox
(reachable from mobile, since skills/session state are account-scoped) can
clone, bootstrap, and use to compile polished LaTeX reports — without adding
a CI/CD pipeline. Iteration should stay cheap: a maintainer changes a `.sty`
file, a local hook catches known-bad changes before commit, and the next
`git clone` in any session picks up the fix immediately.

## Non-goals

- No GitHub Actions / hosted CI. Verification is local-only (git hook).
- No new LaTeX primitives, templates, or visual redesign — the current stack
  (v1.2.1) is treated as a good baseline. The design must stay extensible so
  future `.sty`/tooling additions don't require restructuring again.
- No zip-based skill packaging or claude.ai Skills-settings upload flow —
  distribution is git clone from the public GitHub remote
  (`https://github.com/iancwm/report-kit`), not a build artifact.

## Execution model

Target environment: a claude.ai session's code-execution sandbox (the same
environment `docs/CLAUDE_EXECUTION.md` already documents — a bash tool,
persistent filesystem within a session, `TEXMFLOCAL` font installs surviving
across tool calls but not across sessions). This is reachable from the
mobile app because skills and Projects are account-scoped, not tied to a
particular client.

Bootstrap flow for a fresh session:
1. `git clone https://github.com/iancwm/report-kit.git <workdir>` (optionally
   pinned to a release tag for stability; `main` for latest).
2. `bash <workdir>/shell_scripts/bootstrap.sh <workdir> <session-workdir>`
   (existing script, unchanged in behavior).
3. Proceed per `SKILL.md`'s capability pointers and, only as needed, the
   split-out reference docs.

## Repo structure (Approach A: repo root *is* the skill)

Existing top-level directories (`latex_templates/`, `python_scripts/`,
`shell_scripts/`, `font_data/`) are kept as-is — `bootstrap.sh` and existing
docs already reference them by these names, and renaming buys nothing but
churn risk. New/changed files:

```
SKILL.md                          # new — entry point, frontmatter + quick-start
CHANGELOG.md                      # new — tag-mapped changelog
CONTRIBUTING.md                   # new — hook setup instructions
.githooks/pre-commit              # new — acceptance check wiring
scripts/acceptance_check.sh       # new — compiles smoke-test doc(s), greps for known bug signatures
docs/reference/font-setup.md      # split from CLAUDE_EXECUTION.md
docs/reference/known-fixes.md     # split from CLAUDE_EXECUTION.md
docs/reference/troubleshooting.md # split from CLAUDE_EXECUTION.md
docs/CLAUDE_EXECUTION.md          # removed after split (content redistributed)
```

### `SKILL.md`

Frontmatter carries `name`, `description` (written so claude.ai's skill
matcher triggers it on requests like "write a technical report", "make this
a PDF report"), and `version` (kept equal to `reportkit.cls`'s
`\ProvidesClass` version, so the two never silently drift).

Body: what ReportKit is, when to reach for it, the three-step bootstrap
flow above, a one-line pointer per capability (diagrams, callouts, code
blocks, viz theme, Vietnamese/lualatex support), and links into
`docs/reference/*.md` — not their content inline. This is the progressive
disclosure mechanism: `SKILL.md` loads every time the skill is invoked, a
reference file only loads when that specific problem actually comes up
(e.g. `font-setup.md` only if font resolution fails). This is what keeps a
mobile/remote session's context cheap as more tooling is added later — new
tooling adds new reference files, not weight to `SKILL.md`.

### `docs/reference/*.md`

Split of the current 219-line `CLAUDE_EXECUTION.md` by concern:
- `font-setup.md` — portable font bundle vs. apt-get fallback, `TEXMFLOCAL`
  persistence behavior.
- `known-fixes.md` — historical defect record (diagrams.sty arithmetic bug,
  engine-guard fix, etc.) — useful when debugging a similar-looking failure,
  not needed for a normal report-writing session.
- `troubleshooting.md` — `reportkit_doctor.py` output interpretation, SOURCE
  vs FULL BUILD modes.

`README.md` stays as the human-facing repo overview, pointing at `SKILL.md`
as the canonical entry point for Claude-driven use.

## Versioning & distribution

- Git tags replace zip filenames as the version boundary (e.g. `v1.2.1` for
  current state, next work tagged `v1.3.0`).
- `CHANGELOG.md` maps tags to what changed, standard Keep-a-Changelog style.
- `SKILL.md`'s clone instructions default to a pinned tag for reproducible
  sessions, with a documented one-line variant for cloning `main` when
  bleeding-edge tooling is wanted.
- No packaging script, no build artifact. A session's `git clone` *is* the
  distribution mechanism — a push to `main` plus a new tag is the entire
  "release" step.

## Verification: pre-commit acceptance hook

Goal: catch a broken `.cls`/`.sty`/`.py` change before it's committed,
without hosted CI.

- `scripts/acceptance_check.sh`: compiles
  `latex_templates/examples/primitive_acceptance_test.tex` (and, time
  permitting, the `career_guide_en` worked example) with `pdflatex`, then
  greps the compile log for known failure signatures (the arithmetic-unit
  bug class documented in `known-fixes.md`, missing-font errors, undefined
  control sequences). Exits non-zero on any hit or on a `pdflatex` failure.
- If `pdflatex` isn't found at all, the script **warns and exits 0** (allows
  the commit) rather than blocking — a machine without a LaTeX toolchain
  shouldn't be unable to commit. Real enforcement happens the next time the
  hook runs somewhere with TeX installed, or during the manual dry run
  before tagging a release.
- `.githooks/pre-commit` calls this script only when the commit touches
  `latex_templates/**` or `python_scripts/**` (via `git diff --cached
  --name-only`), so unrelated commits (docs, `SKILL.md` edits) aren't
  slowed down.
- Not auto-installed by any script — `CONTRIBUTING.md` documents running
  `git config core.hooksPath .githooks` once per clone. This keeps hook
  installation an explicit, visible repo convention rather than a script
  silently rewriting the maintainer's git config.

## Testing / verification for this sprint itself

Before tagging the new skill version:
- Run `scripts/acceptance_check.sh` directly and confirm it both passes on
  current `.cls`/`.sty` files and correctly fails against a deliberately
  reintroduced instance of the arithmetic-unit bug (regression check on the
  checker itself).
- Simulate the real mobile/remote flow end-to-end in a scratch directory:
  `git clone` the repo fresh, run `bootstrap.sh`, compile the acceptance
  test doc, confirm `reportkit_doctor.py` reports FULL BUILD. This is the
  actual acceptance criterion for "a remote Claude session on mobile can
  use this."

## Sprint backlog

1. Add `SKILL.md` (frontmatter + quick-start + capability pointers)
2. Split `docs/CLAUDE_EXECUTION.md` → `docs/reference/{font-setup,known-fixes,troubleshooting}.md`; remove the original
3. Add `CHANGELOG.md`; tag current pre-sprint state `v1.2.1` if not already tagged
4. Update clone/bootstrap instructions (`SKILL.md`, `README.md`) to reference the public GitHub URL and the pinned-tag pattern
5. Write `scripts/acceptance_check.sh`
6. Wire `.githooks/pre-commit`; write `CONTRIBUTING.md` documenting `git config core.hooksPath .githooks`
7. Dry run: fresh clone + bootstrap + acceptance check end-to-end (the mobile/remote flow), plus the checker regression check above
8. Tag `v1.3.0` once verified

## Open risks / assumptions

- Assumes the claude.ai code-execution sandbox permits outbound `git
  clone`/HTTPS to github.com within a session — consistent with existing
  `CLAUDE_EXECUTION.md` notes about the bash tool and font-bundle downloads,
  but not independently re-verified in this design pass; the dry run in
  backlog item 7 is where this gets confirmed for real.
- The pre-commit hook only runs on machines with `pdflatex` installed and
  the hook path configured; it's a courtesy net for the maintainer's own
  machine, not a hard guarantee — acceptable per the "no CI/CD" constraint.
