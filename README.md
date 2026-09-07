# ReportKit

A LaTeX toolkit for producing polished, professionally designed technical
reports as PDFs, packaged as a Claude Skill.

**`SKILL.md` is the Claude-driven entry point** — a claude.ai session
clones this repo and follows it directly. This file is the human-facing
overview.

## 1. latex_templates/
- `reportkit.cls` (v1.5.0), `reportkit-boxes.sty`, `reportkit-code.sty`,
  `reportkit-diagrams.sty`, `reportkit-grammar.sty`, `reportkit-pandoc.sty`,
  and `reportkit-longform.sty` — the core document class and style files. The
  public diagram DSL covers positioning, risk, process, architecture,
  hierarchy, planning, strategy, state, comparison, and timeline visuals;
  existing low-level primitives remain available for custom composition.
- `REPORT_TEMPLATE.tex` — minimal report skeleton.
- `examples/{primitive_acceptance_test,visual_grammar_acceptance_test}.tex` —
  compile the legacy and v1.4 public APIs respectively; use the acceptance
  check after any core-file change.
- `examples/career_guide_en/` — full 7-page worked example (pdflatex).
- `examples/career_guide_vi/` — full 4-page worked example with Vietnamese content
  (lualatex; see `references/font-setup.md` for the extra setup this needs).

## 2. python_scripts/
- `reportkit_viz.py` — Matplotlib analytical chart theme (palette synced with
  `reportkit.cls`, including treemap, waterfall, tornado, bubble-matrix, and
  dated timeline figures alongside standard analytical charts).
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

## Licensing scope

| Scope | Default licence |
|---|---|
| Source code and build tooling | GPL-3.0-or-later (`LICENSE`) |
| Original publication prose and diagrams | CC BY 4.0 (`CONTENT-LICENSE.md`) |
| Code examples and third-party assets | Separately licensed; see `THIRD-PARTY-NOTICES.md` |

The machine-readable defaults are in `metadata/licenses.yml`; contributor
requirements are documented in `documentation/licensing.md`.

## 6. scripts/ and .githooks/
- `scripts/acceptance_check.sh` — compiles the legacy and visual-grammar
  acceptance tests and checks for known failure signatures; run by hand, or
  automatically via `.githooks/pre-commit` once enabled (see
  `CONTRIBUTING.md`).

## Setup

See `SKILL.md`'s Quick start section — the commands are the same whether
you're a person cloning this locally or a Claude session bootstrapping it.

## Versioning

Releases are git tags (e.g. `v1.2.1`, `v1.3.0`) on this repo, not a zip or
package registry. See `CHANGELOG.md`.

## Visual grammar

Use a native semantic diagram for qualitative reasoning (such as a strategy
matrix, risk heatmap, process, architecture, roadmap, or capability map). Use
`reportkit_viz.py` for figures whose geometry represents measured values. The
full interfaces, constraints, and acceptance requirements are in
[`VISUAL_GRAMMAR_SPEC.md`](VISUAL_GRAMMAR_SPEC.md).
