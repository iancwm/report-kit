# Changelog

All notable changes to ReportKit are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions are git
tags on this repository, not a published package registry.

## [Unreleased]

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
