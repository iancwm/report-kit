---
name: reportkit
description: Compile polished, professionally-designed technical/analytical PDF reports using LaTeX — a matching diagram and callout system, and a synced matplotlib chart theme. Use when asked to write, create, or format a technical report, PDF report, analytical report, evaluation, or brief as a finished document deliverable.
version: 1.2.1
---

# ReportKit

> The `version` field in this file's frontmatter tracks the LaTeX
> document class version (`reportkit.cls`'s `\ProvidesClass` version), not
> the skill-packaging release — that's versioned separately via git tags
> (see `CHANGELOG.md`). `version: 1.2.1` here alongside a `v1.3.0` git tag
> is expected, not a mismatch.

ReportKit is a LaTeX document class (`reportkit.cls`) plus supporting style
files, a matplotlib chart theme, and a font bundle, for producing
professionally designed technical reports as PDFs — narrative-first
documents with semantic callouts (`principle`, `redflag`,
`deliverablenote`, ...), native diagram primitives (matrices, swimlanes,
networks, layered architectures, evidence stacks, cycles, funnels), and
analytical charts using a shared color palette.

Use this skill whenever a request calls for a polished technical or
analytical report as a finished PDF deliverable — not for quick
throwaway output or plain prose.

## Quick start

```bash
git clone https://github.com/iancwm/report-kit.git <workdir>
# Or pin to a specific release (see CHANGELOG.md for tags):
#   git clone --branch v1.3.0 https://github.com/iancwm/report-kit.git <workdir>

bash <workdir>/shell_scripts/bootstrap.sh <workdir> <session-workdir>
cd <session-workdir>
python3 reportkit_doctor.py   # confirm MODE: FULL BUILD before trusting a compile
```

`<session-workdir>` holds only the flat core files (`reportkit.cls`,
`reportkit-boxes.sty`, `reportkit-code.sty`, `reportkit-diagrams.sty`,
`reportkit_doctor.py`, `reportkit_viz.py`) plus `figures/` — enough to
compile a report — while examples (`latex_templates/examples/`), the
report template (`latex_templates/REPORT_TEMPLATE.tex`), and reference
docs (`references/*.md`) remain only in `<workdir>`, the cloned repo.

`main` always has the latest tooling; a release tag is the reproducible
choice when stability matters more than newest features. See
`CHANGELOG.md` for what changed between tags.

## Capabilities

- **Document class** (`latex_templates/reportkit.cls`) — title page,
  headers/footers, section styling. See
  `latex_templates/REPORT_TEMPLATE.tex` for a minimal skeleton.
- **Semantic callouts** (`reportkit-boxes.sty`) — `principle`, `redflag`,
  `deliverablenote`, `execsummary`, and others; use these instead of ad
  hoc bold text for anything the reader should treat as a distinct claim.
- **Code blocks** (`reportkit-code.sty`) — styled, syntax-aware code
  listings.
- **Native diagrams** (`reportkit-diagrams.sty`) — matrices, swimlanes,
  networks, layered architectures, evidence stacks (`RKStack`), cycles
  (`RKCycle`), funnels (`RKFunnel`). See
  `latex_templates/examples/primitive_acceptance_test.tex` for worked
  syntax of every primitive.
- **Analytical charts** (`python_scripts/reportkit_viz.py`) — a
  matplotlib theme with a palette synced to the document class, for any
  chart generated from real data rather than expressed as a native
  diagram.
- **Worked examples** — `latex_templates/examples/career_guide_en/`
  (7-page pdflatex) and `career_guide_vi/` (4-page lualatex, Vietnamese
  content — see the Unicode content section of `references/font-setup.md`).

## When something goes wrong

Don't paste in error output blind — check the specific reference file for
the problem you're hitting first:

- Fonts not resolving, or setting up Unicode/lualatex content →
  `references/font-setup.md`
- A compile error that looks like it should just work (arithmetic/unit
  errors in diagrams, `\times` rendering wrong under lualatex, a doctor
  false positive) → `references/known-fixes.md` — it may already be fixed
  and documented, or be the same class of bug as something that was.
- Interpreting `reportkit_doctor.py`'s output, or the standard
  build-and-inspect task flow → `references/troubleshooting.md`

## Non-negotiables

- Always run `reportkit_doctor.py` and report its actual `MODE:` line
  rather than assuming a build will succeed because TeX is installed.
- Compile twice (cross-references and captions need a second pass).
- Rasterize and visually inspect every page (`pdftoppm -png -r 150`)
  before calling a report done — a clean exit code does not mean the
  diagrams actually render correctly.
