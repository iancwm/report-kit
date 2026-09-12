# ReportKit

A LaTeX toolkit for producing polished, professionally designed technical
reports as PDFs, with a versioned host-neutral CLI contract and a Claude Skill
adapter.

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
| `scripts/`, `references/` | `publication.yaml`, `build/`, `output/`, `reportkit.lock` |

Full guardrails and the recommended consumer project structure are in
[`references/repository-boundary.md`](references/repository-boundary.md).
Migrating an existing content branch out of this repo is covered in
[`references/migrating-content-branches.md`](references/migrating-content-branches.md).

## 1. latex_templates/
- `reportkit.cls` (v1.9.3), `reportkit-core.sty`, `reportkit-boxes.sty`,
  `reportkit-code.sty`, `reportkit-diagrams.sty`, `reportkit-grammar.sty`,
  `reportkit-pandoc.sty`, and `reportkit-longform.sty` — the core document
  class and style files. The public diagram DSL covers positioning, risk,
  process, architecture, hierarchy, planning, strategy, state, comparison,
  and timeline visuals; existing low-level primitives remain available for
  custom composition.
- `themes/` — visual identity (typography, geometry, palette, running
  furniture), selected via `\documentclass[theme=<name>]{reportkit}`.
  `reportkit-theme-default.sty` reproduces ReportKit's original design
  exactly. `reportkit-theme-institutional-research.sty`
  (`theme=institutional-research`, requires `lualatex`) is a Letter-geometry,
  Google-Sans institutional research theme.
- `publication_types/` — structural primitives layered on top of a theme,
  selected via `\documentclass[publication-type=<name>]{reportkit}`.
  `reportkit-equity-research.sty` (`publication-type=equity-research`,
  currently requires `theme=institutional-research`) adds a research front
  page, rating strip, sidebar blocks, an exhibit system, table grammar, a
  dense financial-model mode, and risk/reward primitives; see
  `docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md`
  for the architecture and the visualization-integration/fixtures work still
  in progress on top of it.
- `REPORT_TEMPLATE.tex` — minimal report skeleton.
- `examples/{primitive_acceptance_test,visual_grammar_acceptance_test}.tex` —
  compile the legacy and v1.4 public APIs respectively; use the acceptance
  check after any core-file change.
- `examples/institutional_equity_acceptance_test.tex` — compact LuaLaTeX
  coverage for the institutional-research/equity-research pair; the acceptance
  check stages the licensed Google Sans fixtures from `font_data/`.
- `examples/career_guide_en/` — full 7-page worked example (pdflatex).
- `examples/career_guide_vi/` — full 4-page worked example with Vietnamese content
  (lualatex; see `references/font-setup.md` for the extra setup this needs).

## 2. python_scripts/
- `reportkit` (from the repository root) — stdlib CLI facade for init, doctor,
  context, check, build, diagnose, inspect, docs, analyse-history, and package; its importable
  implementation lives under `python_scripts/reportkit/`, including
  `reportkit/themes/` — per-theme Python tokens (`default`,
  `institutional-research`) plus the `technical` compatibility alias for
  `default` that `reportkit_viz.py` and the publication context resolve by name.
- `reportkit_viz.py` — Matplotlib analytical chart theme, switchable at
  runtime via `apply_theme(name)` (palette/geometry/fonts synced with the
  matching `latex_templates/themes/*.sty` file; `check-theme --theme <name>`
  verifies the sync), including treemap, waterfall, tornado, bubble-matrix,
  risk/reward, and dated timeline figures alongside standard analytical
  charts.
- `reportkit_doctor.py` — environment check (FULL BUILD / SOURCE BUILD detection).
- `publication_config.py` — compatibility import for the nested or legacy
  consumer `publication.yaml` loader;
  `license_metadata.py` — reads this repo's own `metadata/licenses.yml`.
- `career_guide_en_make_figures.py` — example figure generator using `reportkit_viz`.

## 3. publication_pipeline/
Reusable build/validate/inspect harness for a consumer publication project —
Pandoc → LaTeX compilation, the strict diagnostic gate, page rendering, and
PDF inspection. Takes no fixed publication as input: point it at any project
  with `--source-root`/`--output-root`. Use `./reportkit` as the stable command
  interface; `example_publication/` is a small generic fixture used only by
  this repo's own tests, not a real publication.
See [`publication_pipeline/README.md`](publication_pipeline/README.md).

## 4. font_data/
- `reportkit-libertinus-fonts.tar.gz` — the ~26MB Libertinus font subset harvested
  from `texlive-fonts-extra` (a 1.7GB package), for fast `reportkit init --install-fonts`
  setup.
- `GoogleSans-{Regular,Medium,Bold}.ttf` — licensed fixtures for the
  institutional-research theme's local `font_path` and acceptance smoke test;
  see `GOOGLE_SANS_LICENSE.md`.
- `LinBiolinum_K.otf` + `LinBiolinum_K_stub_README.md` — stub font and explanation
  for the lualatex-only upstream packaging gap in `libertinus-otf.sty`.

## 5. references/
- [`repository-boundary.md`](references/repository-boundary.md),
  [`migrating-content-branches.md`](references/migrating-content-branches.md) —
  the engine/publication boundary and how to move existing content out of this
  repo.
- [`font-setup.md`](references/font-setup.md),
  [`known-fixes.md`](references/known-fixes.md),
  [`troubleshooting.md`](references/troubleshooting.md),
  [`accessibility-tagging.md`](references/accessibility-tagging.md), and
  [`licensing.md`](references/licensing.md) — operational, accessibility, and
  licensing guidance, linked from `SKILL.md` or the relevant entry points on
  demand.
- [`agent-contract.md`](references/agent-contract.md) — the v1.9 contract
  versioning policy, diagnostic exits, pinned toolchain, and security/trust
  boundary.

## Licensing scope

| Scope | Default licence |
|---|---|
| Source code and build tooling | GPL-3.0-or-later (`LICENSE`) |
| Original publication prose and diagrams | CC BY 4.0 ([`CONTENT-LICENSE.md`](CONTENT-LICENSE.md)) |
| Code examples and third-party assets | Separately licensed; see [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) |

The machine-readable defaults are in `metadata/licenses.yml`; contributor
requirements are documented in [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`references/licensing.md`](references/licensing.md).

## 6. scripts/ and .githooks/
- `scripts/acceptance_check.sh` — compiles the legacy and visual-grammar
  acceptance tests and checks for known failure signatures; run by hand, or
  automatically via `.githooks/pre-commit` once enabled (see
  [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Setup

Initialize a consumer project and install the pinned Python build environment:

```bash
<skill-directory>/reportkit init <report-directory> --install-fonts
python3 -m venv <report-directory>/build/.venv
<report-directory>/build/.venv/bin/python -m pip install --require-hashes \
  -r <skill-directory>/toolchain/requirements.lock
```

The test-only additions for repository contributors are in
`tests/requirements.txt`; see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Versioning

Releases are git tags (for example `v1.9.3`) on this repo, not a zip or package
registry. The ReportKit release version and machine-contract version are
independent; see [`references/agent-contract.md`](references/agent-contract.md)
and `CHANGELOG.md`.

## Visual grammar

Use a native semantic diagram for qualitative reasoning (such as a strategy
matrix, risk heatmap, process, architecture, roadmap, or capability map). Use
`reportkit_viz.py` for figures whose geometry represents measured values. The
full interfaces, constraints, and acceptance requirements are in
[`SKILL.md`](SKILL.md#visual-grammar).
