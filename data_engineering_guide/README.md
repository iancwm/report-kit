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

One-time setup (all three build scripts below need this):

```bash
python3 -m venv build/.venv
build/.venv/bin/pip install pymupdf
```

(`pymupdf` rasterizes PDF pages to PNG for visual QA — no system PDF
rasterizer is assumed.)

- `bash scripts/build-section.sh manuscript/<file>.md` — build one section in
  isolation (fast QA loop for a single section's diagrams/content).
- `bash scripts/build-all.sh` — build all 9 instructional sections (1-9)
  individually.
- `bash scripts/combine.sh` — assemble and build the final combined PDF at
  `build/combined/data-engineering-guide.pdf`.

## Known upstream bugs in `../latex_templates/*.sty`

These are ReportKit template bugs this guide's fragments work around. Do not
try to fix them here — they're out of this project's scope — but know about
them before adding a 10th diagram:

1. **`reportflow`'s `direction=vertical` is silently ignored.** An
   `etoolbox` `\ifstrequal` expansion bug in `reportkit-process.sty` means
   the direction comparison is always false, so every `reportflow` renders
   horizontally regardless of the option. Workaround: for a vertical flow,
   skip `\begin{reportflow}[direction=vertical]` + `\step` entirely and lay
   the nodes out directly with `\RKNode`/`\flowedge`. See
   `fragments/fig-sec01-lifecycle.tex` for the pattern.

2. **`reportnetwork`'s default grid spacing is too tight for `rk node`'s
   rendered width on a horizontal chain, and reverses arrow direction.**
   The default grid step (3.15cm) is at or under the shared `rk node`
   style's rendered width (~31.5mm), so adjacent boxes touch/overlap by a
   fraction of a millimeter — enough to break pgf's automatic node-border
   edge-clipping math and flip the arrowhead direction. Workaround: add a
   per-node `text width=24mm` override to shrink each box just enough to
   leave a few millimeters of gap. See `fragments/fig-sec07-lineage.tex` for
   the pattern.
