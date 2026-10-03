# Visual grammar

> Scope: the examples describe technical-report and book grammar. Executive briefs may use the subset returned by their target context. Feature articles and presentations use their target-specific authoring references.

Choose a visual to answer the reader’s question. A publication type defines its structure and available primitives; a theme defines their appearance. Resolve the target first, then use its `reportkit context --slice primitives --json` result as the current contract.

## Visual grammar

Choose a visual by the question the reader needs answered, not by decoration. Native diagrams express qualitative relationships. Python charts express measurements.

| Reader question | Use |
| --- | --- |
| What belongs where on two qualitative axes? | `reportmatrix` |
| Which risks need attention? | `riskheatmap` |
| What happens, in what order? | `reportflow` |
| Who owns each process step? | `reportswimlane` |
| How are responsibilities separated? | `reportarchitecture` |
| What happens now, next, and later? | `reportroadmap` |
| Which capabilities belong to each domain? | `capabilitymap` |
| What levers support an objective? | `strategicpillars` |
| How does a capability progress? | `maturitymodel` |
| Where do items lie between endpoints? | `continuum` |
| How is a concept decomposed? | `reporttree` |
| What depends on or influences what? | `reportnetwork` or `causalloop` |
| How does evidence grow in rigor? | `evidencestack` |
| What repeats without a true endpoint? | `reportcycle` |
| How does a conceptual population narrow? | `reportfunnel` |
| How does something move between states, and what happens on failure? | `reportstate` |
| What changed between two arrangements? | `reportcompare` |
| When did things happen, on more than one clock? | `reporttimeline` |
| What do measured values show? | `reportkit_viz.py` |

The distinction is strict:

- A qualitative prioritization matrix is native; scored or measured coordinates require a scatter/bubble plot.
- A conceptual funnel explains stages; a funnel whose widths encode actual conversions must be a quantitative chart.
- Architecture layers express separation of responsibility; capability maps group business capabilities; neither is a measurement.

Meaning must remain clear without colour: use labels, position, shape, and solid/dashed line semantics. Do not rely on red/green or intensity alone.

## References and contents

Technical reports default to numeric citations with a References list and a
full Contents page: declare `bibliography.file` in `publication.yaml`, cite
with `\citep`/`\citet` or `[@key]`, and place `\RKBibliography` (or the
`reportkit references` fence) and `\RKContents` where they belong. See
[bibliography and contents](bibliography-and-contents.md) for the full workflow.
