# Operator theme

> Scope: `technical-report` structure × `operator` look. This pairing is experimental and uses pdfLaTeX. TeX and Markdown source are supported. The [canonical fixture](../latex_templates/examples/operator-report/) shows the complete target; [its composition brief](../latex_templates/examples/operator-report/composition-brief.json) is a starting point for report planning.

The `technical-report` structure supplies page roles and authoring primitives. The `operator` theme supplies the visual system: Latin Modern typography, a compact indigo-and-teal palette, sans-serif tables, product identity, capability glyphs, and dark terminal and diff surfaces. Set the target before authoring and use the resolved target context as the source of truth for available primitives:

```sh
reportkit target set \
  --source-root <project> \
  --publication-type technical-report \
  --theme operator \
  --source-mode markdown \
  --request "<verbatim request>"
reportkit context --source-root <project> --slice primitives --json
```

Use `--source-mode tex` for direct TeX. Keep projects and generated publication artifacts outside the ReportKit engine checkout. The `operator` theme is experimental while its canonical fixture awaits pinned-toolchain visual review; see the general [build and review loop](../SKILL.md#the-loop).

## Product identity

Use `\productchip{initial}{name}{tag}` for a compact text label, including in tables. Its `initial` argument is retained for API symmetry and is not displayed. Use `\productavatar{initial}{name}{tag}` in prose when the initial should appear in a circular avatar; it is not valid inside a table or other alignment. Use `\pricepill{price}{plan}` for a price and plan, and `\statusdot{state}` for a semantic status. Valid states are `verified`, `flag`, `accent`, and `neutral`.

```latex
\productavatar{A}{Atlas CLI}{first-party}
\productchip{}{Beacon Studio}{open-source}
\pricepill{\$12}{Team}
\statusdot{verified}
```

The status argument names meaning rather than a color, so the theme controls its appearance consistently.

## Capability comparisons

`capabilitygrid` builds a table from the comma-separated headings you supply. Each `\capabilityrow` has one `D`, `U`, or `-` marker for every heading: `D` marks a documented capability, `U` an unestablished one, and `-` renders an em dash. The optional row tag is useful for provenance such as `first-party`; `score=auto` adds a count of documented (`D`) cells, while the default `score=none` omits it. Keep headings concise because they are rotated to fit dense grids.

```latex
\begin{capabilitygrid}[score=auto]{Local,Remote,Plans,MCP}
\capabilityrow[first-party]{Atlas CLI}{DDUD}
\capabilityrow[open-source]{Beacon Studio}{DUDU}
\end{capabilitygrid}
```

The number of markers in each row must match the number of headings. ReportKit checks the markers and reports a row-length mismatch during TeX processing.

## Terminal and diff blocks

The terminal and diff environments are breakable reading units. Put one line in each macro; special TeX characters in direct TeX source must be escaped as usual. The prompt macro adds its `$` marker, so omit it from the command argument. `\termcomment` marks the line as muted; omit the Markdown `#` classifier from its TeX argument. Diff add/delete macros add their gutter markers; context text retains its source indentation.

```latex
\begin{terminalblock}[Build output]
\termcomment{Generated from the fixture project.}
\termprompt{reportkit build --source-root demo}
\termline{Build complete: 3 pages}
\end{terminalblock}

\begin{diffblock}[src/settings.py]
\diffhunk{@@ -4,1 +4,1 @@}
\diffdel{limit = 10}
\diffadd{limit = 12}
\diffctx{enabled = True}
\end{diffblock}
```

Each line macro belongs inside its corresponding block. Empty line arguments retain a blank line; leading spaces can be written as `~` or `\ ` in TeX. Long lines wrap within the block.

### Markdown directives

For terminal, diff, and capability-grid directives, use `content: |` so the parser keeps line boundaries, blank lines, and indentation. Indent content lines by two spaces in the directive; the block indent is removed before rendering. The renderer classifies terminal lines beginning with `$ ` as commands and `# ` as comments. For diffs, `@@` selects a hunk header, `+` an addition, and `-` a deletion; all other lines are context. A prefix is removed before rendering, and leading payload spaces are preserved.

````markdown
```reportkit terminalblock
title: Build output
content: |
  # generated from the fixture project
  $ reportkit build --source-root demo
  Build complete: 3 pages
```

```reportkit diffblock
title: src/settings.py
content: |
  @@ -4,1 +4,1 @@
  - limit = 10
  + limit = 12
    enabled = True
```
````

For a capability grid, put the comma-separated headings in `columns:` and use one pipe-separated row per product. Rows may be `name | cells` or `name | tag | cells`; each cell string may contain only `D`, `U`, and `-`.

````markdown
```reportkit capabilitygrid
columns: Local,Remote,Plans,MCP
options: score=auto
content: |
  Atlas CLI | first-party | DDUD
  Beacon Studio | open-source | DUDU
```
````

In Markdown, the directive renderer escapes line payloads for TeX and preserves leading spaces. It removes classifier prefixes such as `+` and `-`; the `@@` hunk marker is retained as part of the `\diffhunk` argument. The TeX grid still checks that each row has exactly one marker per declared heading.

## Charts

Use the selected chart theme before creating figures. Store the script, data, and provenance with the consumer project, export with `save_figure`, and explain the evidence in the report caption and source line. The theme provides hatches and line dashes so a chart does not depend on color alone.

```python
import reportkit_viz as rkv

rkv.apply_theme("operator")
fig, ax = rkv.stacked_bar_chart(
    costs,
    value_formatter="currency",
    axis_label="Cost per attempt",
)
rkv.save_figure(fig, "figures/cost-per-attempt")
```

`stacked_bar_chart` accepts a DataFrame whose rows are categories and whose columns are stack segments, or a mapping with the equivalent category-to-segment shape. Segments draw bottom to top in column order. `line_chart` accepts a Series or DataFrame indexed by numeric x values; it supports `xlabel`, `ylabel`, axis formatters, an optional `vertical_marker` and `vertical_marker_label`, and a legend. For a categorical comparison with outside value labels, use `bar_chart(..., value_labels="outside")`; omit the option to disable those labels. Chart options and target availability are also listed in the [chart reference](charts.md) and resolved context.

## Composition and review

Use callouts for meaningful caveats or decisions, and keep the supporting explanation in the main text. Use the theme's metric, diagram, algorithm, and table styling through their normal semantic primitives; do not add theme-specific commands for those structures. The [canonical report](../latex_templates/examples/operator-report/report.tex) demonstrates the intended mix.

Run `reportkit check --source-root <project> --json`, then `reportkit build --source-root <project> --json`. Review rendered pages for table fit, capability-glyph legibility, terminal contrast, chart labels, and page breaks. Follow the required [ReportKit loop](../SKILL.md#the-loop), including recording visual-review status.
