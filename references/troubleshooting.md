# Troubleshooting

## Reading `reportkit_doctor.py`'s output

Run it from the working directory after bootstrapping:
```bash
python3 reportkit_doctor.py
```
It always exits 0 — the report is the `MODE:` line, not the exit code.
Two modes:
- **FULL BUILD** — pdflatex/lualatex/bibtex present *and* the Libertinus
  font packages resolve via `kpsewhich`. Compiling will work.
- **SOURCE BUILD + FIGURES** — TeX engines are present but the Libertinus
  fonts are not resolvable yet. The doctor prints the fix command (install
  the portable bundle or apt-get — see `references/font-setup.md`).

Report the doctor's actual `MODE:` line rather than assuming a FULL BUILD
because "TeX is installed" — see the false-positive fix in
`references/known-fixes.md`.

## Standard task flow

1. `git clone` this repo (see `SKILL.md` for the URL/tag pattern), then
   run `shell_scripts/bootstrap.sh <cloned_dir> <work_dir>`.
2. `cd` into the work directory the bootstrap printed.
3. Run `python3 reportkit_doctor.py` and check the `MODE:` line before
   trusting a compile will succeed.
4. Build the report bundle:
   ```text
   report/
     report.tex
     references.bib      # only if citations are used
     figures/
     make_figures.py
     README.md
   ```
5. Generate analytical figures with `reportkit_viz.py`. Confirm each
   `figures/*.pdf` + `.png` pair actually exists on disk before
   referencing it in `.tex`.
6. Compile twice (required for cross-references and captions):
   ```bash
   pdflatex -interaction=nonstopmode -halt-on-error report.tex
   pdflatex -interaction=nonstopmode -halt-on-error report.tex
   ```
   If it exits nonzero, read the `.log` — don't just retry.
   `-halt-on-error` gives a clean single failure point.
7. Rasterize and visually inspect every page before delivery:
   ```bash
   pdftoppm -png -r 150 report.pdf report_page
   ```
   A nonzero-exit-code-free compile does not guarantee the diagrams
   actually look right (see `references/known-fixes.md` — that exact bug
   class compiled-looking-fine until the macros were actually invoked).

## Environment notes

- A claude.ai code-execution sandbox's filesystem resets between
  sessions — nothing persists, so re-clone and re-bootstrap each session.
- Python 3, matplotlib, numpy, and pandas are expected present alongside
  TeX Live; `biber` is not — avoid `biblatex`+`biber`, use `bibtex`/
  `natbib` if a bibliography is needed.
