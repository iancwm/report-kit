# Data Engineering Guide — build quick reference

This is a quick reference for maintaining the Data Engineering Guide manuscript
and its ReportKit-native diagrams. It is not a full spec — see
`publication-guidelines.md` for the editorial/production design spec this
project was built from.

## Adding a diagram to a manuscript section

Insert a line of the exact form, on its own line with blank lines around it,
at the point in the manuscript where the diagram should appear:

```
[[REPORTKIT-VISUAL:fig:<slug>]]
```

`<slug>` must match a fragment file named `fragments/fig-<slug>.tex`. For
example, `[[REPORTKIT-VISUAL:fig:sec02-ingestion-semantics]]` pulls in
`fragments/fig-sec02-ingestion-semantics.tex`.

## Fragment convention

Each file in `fragments/` is named `fig-<slug>.tex` and contains exactly one
`\begin{diagram}[...] ... \end{diagram}` block (type, label, caption, source,
and description are set in the `[...]` options; the diagram body follows).

## Build order

`manuscript/order.txt` lists every manuscript file in final build order, one
per line. `scripts/combine.sh` reads this file to assemble the combined
document — a manuscript file that exists but isn't listed here will not
appear in the final PDF.

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
   edge-clipping math and flip the arrowhead direction. Workaround: add a
   per-node `text width=24mm` override to shrink each box just enough to
   leave a few millimeters of gap. See `fragments/fig-sec07-lineage.tex` for
   the pattern.
