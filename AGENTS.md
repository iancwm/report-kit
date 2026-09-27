# ReportKit agent instructions

When creating a PDF with this repository, read `SKILL.md` before drafting or
building. This checkout is the publication engine. Put each publication in a
separate directory outside this clone.

## First run

1. Read the user's requested format, template, theme, and design guidelines.
   Record the chosen `document.publication_type` and `document.theme` in the
   consumer project's `publication.yaml` before writing the manuscript. Use
   the selection table and matching authoring reference in `SKILL.md`. If the
   request is ambiguous, clarify the choice before drafting.
2. In a fresh Debian/Ubuntu environment, run `scripts/setup_tex.sh` before
   building. It installs TeX and fonts, then compiles editorial and
   institutional LuaLaTeX smoke documents. Run `scripts/setup_tex.sh --check`
   when dependencies are already installed.
3. Initialize the separate project with `./reportkit init <project-dir>` and
   install the Python environment as shown in `SKILL.md`. Run
   `<project-dir>/build/.venv/bin/python ./reportkit doctor --require full-build`
   before promising a PDF.
4. Build using the selected target, inspect `build-report.json`'s `selection`,
   and visually review the rendered pages against the user's design guidelines.

Do not copy `latex_templates/REPORT_TEMPLATE.tex` for a requested article,
brief, book, equity report, or presentation. It is only the generic technical
report starter. Do not silently replace an unavailable requested target with
the default theme; report the specific build failure and fix the setup.
