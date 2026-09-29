# Troubleshooting

## Read `reportkit doctor`

Run `reportkit doctor` from the engine clone, or through the consumer project's pinned Python environment. Read the `MODE:` line and the recommended fix.

- **FULL BUILD** means the required TeX engine and ReportKit fonts are available.
- **SOURCE BUILD + FIGURES** means TeX is available but a required font is unresolved; use the fix printed by the doctor or see [font setup](font-setup.md).
- **SOURCE BUILD** means a source bundle can be prepared, but the PDF cannot be promised.

Report the actual mode instead of treating a Python-only setup as a working TeX environment. For a fresh Debian or Ubuntu environment, run `scripts/setup_tex.sh`; use its `--check` option when dependencies are already installed. On a host without the native toolchain, follow the [Docker workflow](docker-workflow.md).

## Build and inspect a publication

From the consumer project, use the ReportKit build command. For a direct-TeX publication, set `document.source_mode: tex` and `document.main` in `publication.yaml`, then run:

```bash
reportkit build --mode combined --source-root <publication-dir> --output-root <publication-dir>/build
```

For the normal Markdown workflow, run `reportkit build --json`. Read the build report and log when the command returns diagnostics. Render and inspect the affected pages, then record whether visual review was completed:

```bash
reportkit render --pages 1 --source-root <publication-dir>
reportkit review --visual-review done --source-root <publication-dir> --json
```

If rendered pages cannot be viewed, record review as unavailable and say so in the delivery message. Keep the selected theme when its required engine is missing; repair the environment using the doctor or font-setup guidance.

## Engine developers

Raw engine commands are for class and package development or an isolated reproduction. Publication builds use `reportkit build` so its validation, diagnostics, rendering, and build manifest stay connected.

```bash
pdflatex -interaction=nonstopmode -halt-on-error report.tex
pdflatex -interaction=nonstopmode -halt-on-error report.tex
lualatex -interaction=nonstopmode -halt-on-error report.tex
lualatex -interaction=nonstopmode -halt-on-error report.tex
```

A nonzero engine exit requires reading the `.log`; a successful engine exit still needs a rendered-page review. For known macro or layout failures, see [known fixes](known-fixes.md).

## Environment notes

The Python, Matplotlib, NumPy, and pandas dependencies are pinned for reproducible builds. Use `bibtex`/`natbib` when a bibliography is needed; `biber` is not in the pinned toolchain.
