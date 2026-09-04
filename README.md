# ReportKit

A LaTeX toolkit for producing polished, professionally designed technical
reports as PDFs, packaged as a Claude Skill.

**`SKILL.md` is the Claude-driven entry point** — a claude.ai session
clones this repo and follows it directly. This file is the human-facing
overview.

## 1. latex_templates/
- `reportkit.cls` (v1.2.1), `reportkit-boxes.sty`, `reportkit-code.sty`,
  `reportkit-diagrams.sty` — the core document class and style files, including the
  v1.2 diagram primitives (`RKStack`, `RKCycle`, `RKFunnel`), the `deliverablenote`
  callout, and the v1.2.1 lualatex/pdflatex engine-guard fix.
- `REPORT_TEMPLATE.tex` — minimal report skeleton.
- `examples/primitive_acceptance_test.tex` — exercises all v1.2 primitives; useful
  as a smoke test after any core-file change (see `scripts/acceptance_check.sh`).
- `examples/career_guide_en/` — full 7-page worked example (pdflatex).
- `examples/career_guide_vi/` — full 4-page worked example with Vietnamese content
  (lualatex; see `references/font-setup.md` for the extra setup this needs).

## 2. python_scripts/
- `reportkit_viz.py` — Matplotlib analytical chart theme (palette synced with
  `reportkit.cls`, includes the `Deliverable` color).
- `reportkit_doctor.py` — environment check (FULL BUILD / SOURCE BUILD detection).
- `career_guide_en_make_figures.py` — example figure generator using `reportkit_viz`.

## 3. font_data/
- `reportkit-libertinus-fonts.tar.gz` — the ~26MB Libertinus font subset harvested
  from `texlive-fonts-extra` (a 1.7GB package), for fast `bootstrap.sh` setup.
- `LinBiolinum_K.otf` + `LinBiolinum_K_stub_README.md` — stub font and explanation
  for the lualatex-only upstream packaging gap in `libertinus-otf.sty`.

## 4. shell_scripts/
- `bootstrap.sh` — one-command session setup: copies core files, installs fonts to
  `TEXMFLOCAL` (persists across tool calls, no env var needed), creates `figures/`,
  runs the doctor. Covers the pdflatex path; see `references/font-setup.md` for the
  lualatex additions.

## 5. references/
- `font-setup.md`, `known-fixes.md`, `troubleshooting.md` — split from the
  former execution guide, and linked from `SKILL.md` on demand rather than
  loaded up front, so a session's context only grows with the specific
  problem it's actually hitting.

## 6. scripts/ and .githooks/
- `scripts/acceptance_check.sh` — compiles the primitive acceptance test and
  checks for known failure signatures; run by hand, or automatically via
  `.githooks/pre-commit` once enabled (see `CONTRIBUTING.md`). No hosted CI.

## Setup

See `SKILL.md`'s Quick start section — the commands are the same whether
you're a person cloning this locally or a Claude session bootstrapping it.

## Versioning

Releases are git tags (e.g. `v1.2.1`, `v1.3.0`) on this repo, not a zip or
package registry. See `CHANGELOG.md`.
