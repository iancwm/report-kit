# Editorial visual baseline

These six PNGs are the reviewed A4 render of `../report.tex` at 150 DPI. The
manifest records the pinned toolchain, PDF hash, fonts, page sizes and pixel
comparison settings. `scripts/visual_qa_editorial.py` regenerates the three
vector figures in the same pinned environment before compiling the article.

To compare against this baseline from the repository root:

```bash
docker build -f toolchain/Dockerfile -t reportkit-pinned .
docker run --rm --entrypoint /bin/sh reportkit-pinned \
  -c 'python scripts/visual_qa_editorial.py'
```

To refresh after an intentional visual change, mount only this directory and
run with `--update-expected`. Review all six PNGs against the script's manual
checklist before committing them.

```bash
docker run --rm --entrypoint /bin/sh \
  -v "$PWD/latex_templates/examples/editorial-feature/expected:/opt/reportkit/latex_templates/examples/editorial-feature/expected" \
  reportkit-pinned -c 'python scripts/visual_qa_editorial.py --update-expected'
```

Reviewed 2026-09-26: headline and drop cap, column rhythm, two pull quotes,
sidebar, three exhibits, diagram, credits, notes and sources. Page 4 has
open space after the full-width chart and diagram; it preserves exhibit
order without splitting either figure. Page 6 is a short concluding page.
The three chart PDFs embed Libertinus Sans. No clipped content, collisions,
blank pages, or blocking TeX diagnostics were found.
