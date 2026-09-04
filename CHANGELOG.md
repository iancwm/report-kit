# Changelog

All notable changes to ReportKit are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions are git
tags on this repository, not a published package registry.

## [Unreleased]

## [1.4.0] - 2026-09-04
### Added
- Semantic visual grammar over the existing native TikZ primitives:
  qualitative and point matrices, risk heatmaps, flows, swimlanes,
  architectures, roadmaps, capability maps, pillars, maturity models,
  continuums, trees, networks, causal loops, evidence stacks, cycles, and
  conceptual funnels. The low-level v1.2 APIs remain supported.
- `VISUAL_GRAMMAR_SPEC.md` — product contract for choosing, implementing,
  validating, documenting, and visually QA'ing the reporting-system visual
  grammar.
- Analytical treemap, waterfall, tornado, bubble-matrix, and timeline helpers
  in `reportkit_viz.py`, all using the existing ReportKit theme and vector
  export conventions.

### Changed
- `bootstrap.sh` now copies all semantic diagram modules into a report work
  directory, preserving the one-command setup path.

## [1.3.0] - 2026-09-04
### Added
- `SKILL.md` — Claude Skill entry point (frontmatter, quick start,
  capability pointers, non-negotiables) enabling this repo to be
  git-cloned directly into a Claude session (including from the Claude
  mobile app, via any claude.ai session with code execution) and used
  with no manual file copying.
- `references/{font-setup,known-fixes,troubleshooting}.md` — split from
  the former `docs/CLAUDE_EXECUTION.md`, loaded on demand rather than up
  front (progressive disclosure).
- `scripts/acceptance_check.sh` + `.githooks/pre-commit` — local, no-CI
  verification that compiles the primitive acceptance test and checks for
  known failure signatures before a commit touching `latex_templates/**`
  or `python_scripts/**`. See `CONTRIBUTING.md`.
- This `CHANGELOG.md`.
- `latex_templates/examples/primitive_acceptance_test.tex`: matrix and
  layered-architecture sections exercising `\RKMatrixCell` and `\RKLayer`
  (including the `accent` cell variant). The acceptance test previously
  only exercised the newer v1.2 primitives, so `scripts/acceptance_check.sh`
  could not have caught a regression of the v1.2.0 arithmetic bug (see
  `references/known-fixes.md`) even though guarding exactly that class of
  defect is the acceptance hook's purpose.

### Fixed
- `shell_scripts/bootstrap.sh`: core-file and font-bundle lookup paths
  corrected to match this repo's actual layout (`latex_templates/`,
  `python_scripts/`, `font_data/`) instead of assuming everything sits
  flat at the project directory's root. The script could not previously
  succeed against a real checkout of this repo.

### Changed
- Distribution model: this repo is cloned directly
  (`https://github.com/iancwm/report-kit`) rather than uploaded as Project
  files or a packaged zip.

## [1.2.1] - 2026-09-04
### Fixed
- `reportkit.cls`: legacy `libertinust1math` package load is now guarded
  behind `\ifPDFTeX`. Under lualatex it previously clobbered `\times`'s
  glyph mapping (silently rendered as `∝`); pdflatex output is unaffected
  (verified byte-identical).

## [1.2.0] - 2026-09-04
### Added
- `reportkit-diagrams.sty`: three new diagram primitives — `RKStack`
  (evidence/rigor tiers), `RKCycle` (non-terminating feedback loops),
  `RKFunnel` (staged conversion/narrowing) — plus the `deliverablenote`
  callout in `reportkit-boxes.sty`. See
  `latex_templates/examples/primitive_acceptance_test.tex` for usage.

### Fixed
- `reportkit-diagrams.sty`: 15 sites wrote a decimal coefficient directly
  against a length macro with no operator between them, e.g.
  `0.25\rk@matrixw`. pgfmath parsed the concatenated text as an invalid
  number ("Illegal unit of measure"). Any diagram using `RKMatrixCell` or
  `RKLayer` failed to compile. Fixed by inserting `*` (coordinate
  expressions) or precomputing via `\pgfmathsetlengthmacro` (`text width=`
  node keys, which don't auto-evaluate arithmetic).

## [1.1.0] and earlier
Pre-dates this changelog. See `latex_templates/reportkit-code.sty`'s
`\ProvidesPackage` line (`v1.1.0`) for the last version stamped before
tracking began here.
