# Data Engineering Guide — build tooling

This directory contains the reusable renderer, validators, templates, and test
fixtures for the Data Engineering Guide. The publication manuscript, diagram
fragments, and editorial guidelines are maintained on the separate
`data-engineering-guide` branch and are intentionally not part of `main`.

The build scripts expect that source tree when they are run. Use a worktree or
checkout of `data-engineering-guide` for a complete publication build.

## Source conventions

The publication branch uses these conventions:

- `manuscript/order.txt` lists manuscript files in final build order.
- `[[REPORTKIT-VISUAL:fig:<slug>]]` markers resolve to
  `fragments/fig-<slug>.tex` files.
- Each fragment contains exactly one `diagram` environment.

## Building

Set up the locked renderer once:

```bash
bash scripts/setup.sh
python3 scripts/validate-guide.py
```

`requirements.txt` pins PyMuPDF, which rasterizes PDF pages to PNG for visual
QA. The build prints the Python, PyMuPDF, Pandoc, and TeX versions it used.
The combined build also supplies the publication front matter, generated
linked contents page, Roman-numbered preliminaries, and Arabic numbering for
the main guide.

- `bash scripts/build-section.sh manuscript/<file>.md` — build one section in
  isolation (fast QA loop for a single section's diagrams/content).
- `GUIDE_BUILD_WORKERS=2 bash scripts/build-all.sh` — build all 9 instructional
  sections (1-9) with bounded parallelism.
- `bash scripts/combine.sh` — run the canonical full-document build for every
  entry in `manuscript/order.txt`, producing
  `build/combined/data-engineering-guide.pdf`.

Every build runs two `pdflatex` passes with `-file-line-error`, checks the final
log for fatal errors, undefined references, overfull boxes, high-badness
underfull boxes, and unexpected ignored errors, then writes
`build-report.json`. Rendered pages replace the previous page directory rather
than accumulating stale PNGs; `pages/index.html` is a contact-sheet-style QA
index.

The only current log exception is the reviewed, expiry-dated upstream
longtable diagnostic in `config/build-log-allowlist.json`. Re-review it when
the pinned TeX toolchain changes; do not add broad warning suppressions.

## Known upstream bugs in `../latex_templates/*.sty`

These are ReportKit template limitations the guide's fragments work around.
The vertical `reportflow` path is covered by the core acceptance test now; the
existing direct-node fragments remain valid for dense layouts.

1. **`reportnetwork`'s default grid spacing is too tight for `rk node`'s
   rendered width on a horizontal chain, and reverses arrow direction.**
   The default grid step (3.15cm) is at or under the shared `rk node`
   style's rendered width (~31.5mm), so adjacent boxes touch/overlap by a
   fraction of a millimeter — enough to break pgf's automatic node-border
   edge-clipping math and flip the arrowhead direction. The publication branch
   carries the per-node `text width=24mm` workaround for dense fragments.
