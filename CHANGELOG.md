# Changelog

All notable changes to ReportKit are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions are git
tags on this repository, not a published package registry.

## [Unreleased]

### Added
- `reportkit init` now scaffolds a consumer publication project outside the
  engine clone, with optional bundled Libertinus font installation.
- The repository now includes the GPL-3.0-or-later license text.
- Dependabot, Ruff, and an advisory pip-audit gate now signal dependency and
  code-quality drift in CI.

### Changed
- The CLI contract is versioned at 1.1.0, and LaTeX text escaping is shared
  across publication and authoring generators.
- The setup documentation now explains the pinned Python environment needed
  for full publication builds.
- Consumer output configuration is honored, pipeline scripts use the
  consumer project's build environment, and direct script execution uses the
  shared ReportKit package bootstrap.
- Analytical visualization helpers now live under `reportkit.viz`, while the
  legacy `reportkit_viz.py` import remains compatible.
- Failed build stages now produce one consistent structured report shape, and
  the doctor includes actionable Python dependency remediation.

### Removed
- The obsolete file-copying `shell_scripts/bootstrap.sh` workflow is retired
  in favor of `reportkit init` and `--source-root`.
- Obsolete shell wrappers and the duplicate career-guide figure generator are
  retired in favor of the Python CLI and shared pipeline entry points.

## [1.9.3] - 2026-09-11

### Added
- Hand-written LaTeX documents now use a generated publication registry and
  shared class-option parser, so unknown themes, unknown publication types,
  unsupported theme/publication pairs, and renderer mismatches fail with a
  class error instead of producing a plausible document under the wrong target.

### Changed
- Publication template staging and acceptance checks now include generated
  registry/parser inputs and the licensed Google Sans fixtures used by the
  institutional-research smoke test.

### For contributors
- Registry drift and compile coverage exercise the `technical` alias, supported
  publication pairs, and invalid selections.

## [1.9.2] - 2026-09-11

### Added
- Publication authors can now resolve the current paged publication matrix
  into one immutable build target, including the renderer, class, template,
  writer, engine, geometry, accessibility, and package choices.
- `reportkit context`, `check`, and `build` now share registry-backed target
  validation, including the `technical` compatibility alias, engine checks,
  candidate suggestions, and structured configuration diagnostics.

## [1.9.1] - 2026-09-10

### Fixed
- Dated roadmap milestone arrows follow wrapped period labels, diagram label
  validation ignores edge labels, and Pandoc figures preserve their aspect
  ratio.
- Publication builds stage project figures/assets with hashes, support
  per-project licensing and classification, and escape configured URLs safely
  in generated LaTeX.
- Visualization helpers now support pre-2.2 pandas month-end aliases and use
  marker shapes as a second encoding for grouped bubble matrices.

### For contributors
- Test collection now exposes scientific-stack import incompatibilities instead
  of hiding them behind an unrelated optional-package skip.

## [1.9.0] - 2026-09-10

### Added
- ReportKit v1.9.0 agent-contract foundations: capability and diagnostic schema
  1.0.0, balanced LaTeX/Python signature extraction with adjacent metadata,
  filtered `context` catalogs for the two current paged publication matrices,
  deterministic contract-derived documentation, `docs --write/--check`,
  contract-version negotiation on `check`/`build`, shared diagnostics and
  stable exit classes, JSON build output, pinned-toolchain doctor checks,
  build-report schema v3, a digest/snapshot/version/hash-pinned OCI toolchain,
  fingerprinted visual baselines, and pinned GitHub Actions gates. Existing
  flat context fields and raw LaTeX authoring remain supported through v1.x.
- Build security controls for converter/TeX time and address-space limits,
  restrictive TeX file access, disabled shell escape, source-path confinement,
  escaped Markdown content, and explicit trusted fragment/direct-TeX escape
  hatches. See `references/agent-contract.md`.
- Institutional-research theme fixtures, QA, and skill guidance: a
  fictional four-page equity-research example
  (`latex_templates/examples/equity-research/`, front page, analysis
  exhibits, risk/reward, financial model) built from only public
  ReportKit primitives, its financial figures reconciled to one
  internally-consistent model; a compact
  `institutional_equity_acceptance_test.tex` smoke fixture compiled by a
  new `lualatex` block in `scripts/acceptance_check.sh`;
  `scripts/visual_qa_equity_research.py` (compile, run
  `reportkit.diagnostics` log checks, render every page to PNG, and
  pixel-diff against a checked-in baseline); and a new
  `references/institutional-research-theme.md`, linked from `SKILL.md`,
  documenting the primitive reference, the `researchmain`/
  `researchsidebar` minipage-adjacency requirement, the `exhibitgrid`
  column-count limit, and `rkv.apply_theme`/`rkv.risk_reward_chart` usage.
  Fixed a `risk_reward_chart()` label-overlap bug found by actually
  rendering the new fixture's chart. Fifth and final step of the
  institutional-research theme + equity-research publication-type work;
  see
  `docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md`.
- Theme-aware visualization layer: `reportkit_viz.apply_theme(name)` now
  actually switches theme at runtime (colors, `TEXT_WIDTH_IN`,
  `FIGURE_SIZES`, fonts, mathtext) via a new `reportkit.themes` Python
  package (`default`/`institutional-research`, mirroring the LaTeX theme
  names); `check-theme --theme institutional-research` is now genuinely
  synchronized instead of honestly failing against the wrong palette; new
  `risk_reward_chart()` for the bear/base/bull exhibit
  (`reportkit-equity-research.sty`'s `\bullcase`/`\basecase`/`\bearcase`
  expect its output). `FIGURE_SIZES` gains `dominant` (alias of `wide`,
  which stays) and `half` (sized for a half-width exhibit pane) for both
  themes. Fourth step of the institutional-research theme + equity-research
  publication-type work; see
  `docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md`.
- Equity-research publication type (v1.8.0):
  `publication-type=equity-research`
  (`latex_templates/publication_types/reportkit-equity-research.sty`) adds
  the research front page (`researchfrontpage`/`researchkicker`/
  `researchheadline`/`researchdeck`), a rating strip, sidebar blocks
  (`analystblock`/`marketdatablock`/`estimatesblock`), a `whatschanged`
  primitive, the `exhibit` system with `fullwidthexhibit`/`exhibitgrid`/
  `exhibitpair` compositions, an institutional `financialtable` grammar, a
  dense `financialmodelpage` mode, and `\bullcase`/`\basecase`/`\bearcase`
  risk-reward primitives. Currently requires
  `theme=institutional-research` (checked at load time with a clear error).
  Third step of the institutional-research theme + equity-research
  publication-type work; see
  `docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md`.
- Institutional-research theme (v1.7.0): `theme=institutional-research`
  (`latex_templates/themes/reportkit-theme-institutional-research.sty`) adds
  US Letter geometry, Google Sans resolution via `fontspec`
  (`theme.font_family`/`font_path`/`font_policy: strict`/`fallback` in
  `publication.yaml`, with an Inter → Noto Sans → TeX Gyre Heros fallback
  chain), the spec's full type scale, and quieter semantic callouts
  (`reportkit-boxes.sty` now themes its callout chrome). Requires
  `lualatex`; `reportkit check`/`build` and the theme file itself both
  refuse to build it under any other engine. Second step of the
  institutional-research theme + equity-research publication-type work; see
  `docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md`.
- Theme architecture (v1.6.0): typography, geometry, palette, and running
  furniture moved out of `reportkit.cls` into a selected theme file under
  `latex_templates/themes/`. `\documentclass{reportkit}` (or
  `theme=default`) reproduces the pre-v1.6 design unchanged. `publication.yaml`'s
  `document` section gains `theme`, `publication_type`, and `paper`;
  `reportkit context`/`reportkit check`/`reportkit build` all resolve and
  validate them, refusing to build a theme against an engine that can't
  render it. First step of the institutional-research theme + equity-research
  publication-type work; see
  `docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md`.
- PDF inspection now reports bookmarks, font metadata, page dimensions,
  blank pages, and near-margin content.
- Publications can validate optional source/manuscript and link registries;
  named links render through `\RKLink{key}` in generated documents.
- `reportkit analyse-history` summarizes recurring diagnostics and repeated
  allowlist entries from build history.
- `\rkcode{...}` for rendering identifier-like technical tokens, such as
  `event_date`, safely in direct semantic-diagram labels.
- Width-aware swimlanes: `columns=`, `node width=`, `column spacing=`, and
  `label gutter=` keep opted-in process nodes inside their declared width.
- Explicit state and flow branch layouts via `\stateat`, `\terminalstateat`,
  and `\stepat`, with straight, bent, and orthogonal routed edges plus label
  placement controls.
- `reportarchitecture` annotations at the top or bottom of the measured
  diagram, and positioned, width-constrained timeline watermark labels.

### Fixed
- The ReportKit acceptance fixture now exercises vertical `reportflow`
  layout.

## [1.5.0] - 2026-09-08

### Added
- `reportkit` now provides one stdlib command interface for environment
  checks, publication context, validation, builds, diagnostics, PDF inspection,
  and release packaging.
- Publication projects can use nested `publication.yaml` sections and named
  profiles while retaining the legacy flat format.
- Build diagnostics now report typed, severity-aware issues with ownership and
  authored-fragment locations, including wrapped TeX messages.
- Passing builds emit schema-v2 manifests with PDF hashes, provenance,
  figure/table counts, and unique history records.

### Changed
- The publication test suite is part of the acceptance gate, and the
  compatibility shell wrappers route through the CLI facade.
- Capability inventories are generated from the LaTeX primitives and checked
  against the documented visual and callout lists.

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
