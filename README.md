# ReportKit

A LaTeX toolkit for producing polished, professionally designed technical
reports as PDFs, packaged as a Claude Skill.

**`SKILL.md` is the Claude-driven entry point** — a claude.ai session
clones this repo and follows it directly. This file is the human-facing
overview.

## Repository boundary

This repository is a reusable **publication engine** — LaTeX classes/styles,
Python tooling, shell scripts, docs, and small generic examples. It does not
contain any actual publication. A publication's manuscript, figures, assets,
`publication.yaml`, build output, QA logs, and final PDF live in a **separate
consumer project**, built against a clone of this repo.

| report-kit (this repo) | Consumer publication project |
|---|---|
| `latex_templates/`, `python_scripts/`, `publication_pipeline/` | `manuscript/`, `fragments/`, `assets/`, `figures/` |
| `shell_scripts/`, `scripts/`, `references/` | `publication.yaml`, `build/`, `output/`, `reportkit.lock` |

Full guardrails and the recommended consumer project structure are in
[`references/repository-boundary.md`](references/repository-boundary.md).
Migrating an existing content branch out of this repo is covered in
[`references/migrating-content-branches.md`](references/migrating-content-branches.md).

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
- `publication_config.py` — reads a consumer project's `publication.yaml`;
  `license_metadata.py` — reads this repo's own `metadata/licenses.yml`.
- `career_guide_en_make_figures.py` — example figure generator using `reportkit_viz`.

## 3. publication_pipeline/
Reusable build/validate/inspect harness for a consumer publication project —
Pandoc → LaTeX compilation, the strict diagnostic gate, page rendering, and
PDF inspection. Takes no fixed publication as input: point it at any project
with `--source-root`/`--output-root`. `example_publication/` is a small
generic fixture used only by this repo's own tests, not a real publication.
See [`publication_pipeline/README.md`](publication_pipeline/README.md).

## 4. font_data/
- `reportkit-libertinus-fonts.tar.gz` — the ~26MB Libertinus font subset harvested
  from `texlive-fonts-extra` (a 1.7GB package), for fast `bootstrap.sh` setup.
- `LinBiolinum_K.otf` + `LinBiolinum_K_stub_README.md` — stub font and explanation
  for the lualatex-only upstream packaging gap in `libertinus-otf.sty`.

## 5. shell_scripts/
- `bootstrap.sh` — one-command session setup: copies core files, installs fonts to
  `TEXMFLOCAL` (persists across tool calls, no env var needed), scaffolds a
  consumer publication project (`manuscript/`, `fragments/`, `assets/`,
  `figures/`, `build/`, `output/`, `publication.yaml`), and runs the doctor.
  Refuses to run if the target directory is inside this clone. Covers the
  pdflatex path; see `references/font-setup.md` for the lualatex additions.

## 6. references/
- `repository-boundary.md`, `migrating-content-branches.md` — the engine/
  publication boundary and how to move existing content out of this repo.
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
requirements are documented in `references/licensing.md`.

## 7. scripts/ and .githooks/
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
[`SKILL.md`](SKILL.md#visual-grammar).
