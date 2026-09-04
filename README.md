# ReportKit — complete bundle

Everything needed to set up and use ReportKit in a fresh Claude Project session,
organized into four categories.

## 1. latex_templates/
- `reportkit.cls` (v1.2.1), `reportkit-boxes.sty`, `reportkit-code.sty`,
  `reportkit-diagrams.sty` — the core document class and style files, including the
  v1.2 diagram primitives (`RKStack`, `RKCycle`, `RKFunnel`), the `deliverablenote`
  callout, and the v1.2.1 lualatex/pdflatex engine-guard fix.
- `REPORT_TEMPLATE.tex` — minimal report skeleton.
- `examples/primitive_acceptance_test.tex` — exercises all v1.2 primitives; useful
  as a smoke test after any core-file change.
- `examples/career_guide_en/` — full 7-page worked example (pdflatex).
- `examples/career_guide_vi/` — full 4-page worked example with Vietnamese content
  (lualatex; see docs/CLAUDE_EXECUTION.md §2.2 for the extra setup this needs).

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
  runs the doctor. Covers the pdflatex path; see docs for the lualatex additions.

## docs/
- `CLAUDE_EXECUTION.md` — the full execution guide, including every bug found and
  fixed this session (diagram arithmetic bug, `RKCycle` arrow direction, float
  drift, font setup cost, the lualatex `\times` bug) with verification notes for
  each, not just the fixes themselves.

## Setup (fresh session)
```bash
# 1. Core pdflatex path
bash shell_scripts/bootstrap.sh <project_dir> <work_dir>

# 2. If compiling Vietnamese or other Unicode content, additionally:
apt-get install -y --no-install-recommends texlive-luatex
mkdir -p /usr/local/share/texmf/fonts/opentype/public/libertine-stub
cp font_data/LinBiolinum_K.otf /usr/local/share/texmf/fonts/opentype/public/libertine-stub/
mktexlsr /usr/local/share/texmf
```

To use this bundle as the project's source of truth going forward, upload its
contents to the Claude Project files (or a connected GitHub repo — see the earlier
discussion on splitting core-library maintenance into Claude Code vs. day-to-day
report generation in this chat interface).
