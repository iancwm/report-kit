# Executive-brief authoring

> Scope: `executive-brief` structure × `executive` or `institutional-research` look. TeX and Markdown are supported. Both themes use LuaLaTeX.

Use this format for a short management decision document: recommendation, key findings, implication, risks, next steps, and sources. The canonical [`executive-brief` example](../latex_templates/examples/executive-brief/) shows the page flow under both supported themes.

Open with `briefheader` and its decision metadata. State the recommendation directly, then connect each finding to its evidence and consequence. Use concise exhibits for quantitative evidence, make ownership explicit in the action list, and include source notes. The target-scoped context slice and generated primitive contract identify the available role names and signatures.

Select roles for the decision being made. A decision callout, metric, exhibit, or action entry should carry its own semantic purpose; routine narrative remains in the body. Use the theme for typography, color, and spacing rather than local layout adjustments.

## References and contents

Briefs default to numeric citations with a compact Sources list; `\RKContents`
renders a one-line contents element only where it is called. Declare
`bibliography.file` in `publication.yaml`, cite with `\citep` or `[@key]`,
and place `\RKBibliography` where the sources belong. Without a `.bib` file,
use the manual `briefsources` environment instead. See [bibliography and
contents](bibliography-and-contents.md).

The canonical [`composition-brief.json`](../latex_templates/examples/executive-brief/composition-brief.json) is a starting point, not a fixed quota. Adapt the required roles and manual review items to the assignment. Run `reportkit check --source-root <project> --json`, build through ReportKit, and review all rendered pages for decision hierarchy, readable evidence, and clear ownership.
