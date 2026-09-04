# ReportKit Visual Grammar Specification

**Status:** Implemented; native raster visual QA pending
**Target release:** v1.4.0
**Audience:** ReportKit maintainers and report-authoring agents

## 1. Purpose

ReportKit shall provide a small, coherent visual language for professional
technical and analytical reports. Authors should express the *meaning* of a
visual (for example, ``prioritize initiatives by value and effort``), rather
than hand-authoring TikZ coordinates.

The system has two complementary rendering paths:

| Path | Use for | Primary implementation |
| --- | --- | --- |
| Native conceptual diagrams | relationships, process, hierarchy, architecture, qualitative positioning | ReportKit semantic macros over TikZ |
| Analytical charts | measured quantities, scales, distributions, financial bridges, time series | `reportkit_viz.py` / Matplotlib, embedded as vector PDF |

This distinction is normative. A conceptual funnel may illustrate a process;
a funnel whose widths encode measured conversion must be generated as an
analytical figure. Likewise, use a native matrix for qualitative
prioritization and a scatter plot for scored or measured coordinates.

## 2. Product principles

1. **Semantics before decoration.** Each primitive represents one reading
   task. Similar shapes with different meanings remain distinct: a stack means
   increasing rigor, while a funnel means declining population.
2. **Author intent over coordinates.** Public APIs accept labels, semantic
   positions, stages, and data. Coordinates, node sizes, and routing are
   implementation details.
3. **Consistent report reading.** All primitives use ReportKit typography,
   palette, line weights, captions, sources, and non-floating placement.
4. **Accessible without colour.** Meaning is carried by position, labels,
   shape, and line style; colour is secondary. Every diagram has a concise
   `description` supplied through the existing `diagram` wrapper.
5. **Predictable failure.** Invalid keys, dimensions, positions, or data
   values produce actionable package errors, never silently malformed output.
6. **Composition over a macro catalogue.** The public library is limited to
   fundamental visual primitives. Domain-specific diagrams compose these
   primitives or use the low-level node and edge API.

## 3. Current baseline

The existing native layer in `latex_templates/reportkit-diagrams.sty`
already provides:

- `diagram` metadata and placement wrapper;
- low-level `RKNode`, `RKNodeRel`, and typed `RKEdge` primitives;
- `RKMatrix`, `RKMatrixCell`, `RKLane`, `RKLaneNode`, and `RKLayer`;
- `RKStack`, `RKCycle`, and `RKFunnel` primitives.

The existing Python layer in `python_scripts/reportkit_viz.py` supplies the
theme and export path for analytical charts. v1.4.0 shall preserve these APIs
for backwards compatibility while introducing documented semantic interfaces.

## 4. Scope

### 4.1 Core native primitives

The following interfaces are the v1.4.0 native-diagram scope. They are grouped
by the reader question they answer, not by drawing technique.

| Family | Primitive | Reader question | Minimum supported forms |
| --- | --- | --- | --- |
| Positioning | `reportmatrix` | What belongs where on two axes? | qualitative 2x2; point matrix |
| Risk | `riskheatmap` | Which risks need attention? | 3x3 and 5x5; numbered risks; legend |
| Process | `reportflow` | What happens, in what order? | horizontal, vertical, branching, fan-in/out, feedback |
| Process | `reportswimlane` | Who owns each part of the process? | lanes, steps, cross-lane handoffs |
| Architecture | `reportarchitecture` | How are responsibilities separated? | ordered layers; multiple components per layer |
| Structure | `reporttree` | How is this concept decomposed? | arbitrary depth; issue, hierarchy, decision modes |
| Planning | `reportroadmap` | What happens now, next, and later? | horizon-based and dated milestones |
| Strategy | `capabilitymap` | Which capabilities belong to each domain? | domains containing capability cards |
| Strategy | `strategicpillars` | What levers support the objective? | objective plus 3--6 pillars |
| Strategy | `maturitymodel` | How does capability progress? | 4--6 ordered stages |
| Conceptual | `continuum` | Where do items lie between endpoints? | two endpoints and labelled markers |
| Relationship | `reportnetwork` | What depends on or influences what? | directed and undirected; typed edges |
| Relationship | `causalloop` | What feedback structure drives the system? | signed `+`/`-` causal edges |

`RKStack`, `RKCycle`, and `RKFunnel` remain first-class native primitives and
must receive semantic wrappers or an equivalently simple public syntax.

### 4.2 Analytical chart extensions

The following are Python-rendered chart requirements, because their geometry
encodes actual values:

| Chart | Required behavior |
| --- | --- |
| Treemap | flat and hierarchical input; labels, values, palette assignment, small-category handling |
| Waterfall | opening/closing totals; positive/negative deltas; subtotal support; zero baseline |
| Tornado | paired low/high sensitivity bars around a labelled base case; ordered by spread |
| Scatter / bubble matrix | numeric axes, optional size and labels, quadrant reference lines |
| Timeline / Gantt | date or quarter scale, milestones, workstreams, optional current-date marker |
| Sankey | only after an implementation spike confirms an accessible, vector-capable output path |

Existing standard charts (bar, stacked bar, 100% stacked bar, line, area,
histogram, radar where justified, and dumbbell) remain part of the analytical
layer. Pie charts are not a standard ReportKit primitive; prefer a treemap or
bar chart once there are more than four categories.

### 4.3 Explicit non-goals for v1.4.0

- An automatic general-purpose graph layout engine.
- A raw TikZ abstraction capable of reproducing arbitrary illustrations.
- Native LaTeX implementations of statistically scaled charts.
- A Sankey implementation before its output, dependency, and accessibility
  requirements have passed a separate spike.
- More than three sets in a Venn diagram; use a table or UpSet-style figure.

## 5. Public authoring DSL

### 5.1 Conventions

All semantic environments shall use `pgfkeys` keys and a body of declarative
commands. Public commands are namespaced by their environment and shall not
require manually named TikZ nodes. Every environment can appear inside the
existing `diagram` wrapper.

Content authors shall provide the caption, source, and meaningful visual
description at the wrapper layer:

```latex
\begin{diagram}[
  type=matrix,
  caption={Initiatives by implementation complexity and expected value.},
  source={Workshop assessment, September 2026.},
  description={A four-quadrant matrix with two labelled initiatives in the high-value quadrants.}
]
  % semantic primitive goes here
\end{diagram}
```

All labels are LaTeX text. Authors use `\\` for intentional line breaks;
the renderer determines ordinary wrapping from its available width.

### 5.2 Positioning matrix

```latex
\begin{reportmatrix}[
  xlabel={Implementation complexity}, ylabel={Expected value},
  xlow={Low}, xhigh={High}, ylow={Low}, yhigh={High},
  highlight={high/high}
]
  \quadrant{low}{high}{Quick wins}
  \quadrant{high}{high}{Strategic priorities}
  \quadrant{low}{low}{Deprioritize}
  \quadrant{high}{low}{Reconsider}
  \point{Knowledge graph}{0.72}{0.83}
  \point{LMS upgrade}{0.35}{0.61}
\end{reportmatrix}
```

`\point` accepts normalized coordinates in `[0,1]`. Values outside that
range are package errors. A matrix with no `\point` commands is a qualitative
quadrant matrix. Point labels must avoid overlap where possible; explicit
`label-position={above|below|left|right}` overrides the deterministic default.

### 5.3 Risk heatmap

```latex
\begin{riskheatmap}[size=5, impact={Impact}, likelihood={Likelihood}]
  \risk{R1}{4}{5}{Identity dependency}{owner=Security,status=mitigating}
  \risk{R2}{2}{3}{Migration delay}{owner=Platform,status=open}
\end{riskheatmap}
```

Rows and columns are ordinal integers from `1` through `size`. Severity colour
and label are calculated from a documented, overridable threshold table.
`\risk` places its identifier in the relevant cell and produces a risk register
under the grid when owner or status metadata is present. Multiple risks in one
cell stack in reading order. The default legend uses Critical, High, Medium,
and Low; labels and thresholds are configurable.

### 5.4 Flow and swimlane

```latex
\begin{reportflow}[direction=horizontal]
  \step{id}{Identity check}
  \step{review}{Human review}
  \step{publish}{Publish}
  \flowedge{id}{review}
  \flowedge{review}{publish}
\end{reportflow}

\begin{reportswimlane}[lanes={User,Frontend,Backend,Reviewer}]
  \lanestep{request}{User}{Request}{1}
  \lanestep{validate}{Frontend}{Validate}{2}
  \lanestep{process}{Backend}{Process}{3}
  \lanestep{approve}{Reviewer}{Approve}{4}
  \handoff{request}{validate}
  \handoff{validate}{process}
  \handoff{process}{approve}
\end{reportswimlane}
```

Flow layout is deterministic: declaration order defines the primary sequence;
`branch` and `merge` commands explicitly introduce non-linear paths. Swimlane
steps use ordered columns, not arbitrary coordinates. Cross-lane connections
use the existing dashed handoff semantics.

### 5.5 Architecture, tree, and network

```latex
\begin{reportarchitecture}
  \layer{Consumers}{Web client, Analyst workspace}
  \layer{Services}{API gateway, Decision service}
  \layer{Data}{Operational store, Analytics warehouse}
\end{reportarchitecture}

\begin{reporttree}[kind=issue]
  \root{Why did revenue fall?}
  \branch{Volume}{Customers, Usage}
  \branch{Price}{List price, Discounts}
\end{reporttree}
```

Architecture layers have a title and one or more comma-delimited components,
which render as horizontally arranged cards. Trees use a stable declaration
order, permit arbitrary depth, and render with `forest` only when its presence
is verified at bootstrap; otherwise a TikZ fallback covers the documented
simple form. Networks retain the existing lower-level nodes and typed edges,
but add a wrapper that provides a stable grid or radial layout. The DSL never
claims automatic layout will solve arbitrary dense graphs.

### 5.6 Roadmap, capability map, pillars, maturity, and continuum

```latex
\begin{reportroadmap}[mode=horizons]
  \horizon{Now}{Foundation}{Data model, Governance, Infrastructure}
  \horizon{Next}{Integration}{APIs, Pilot, Migration}
  \horizon{Later}{Scale}{Automation, ML, Optimization}
\end{reportroadmap}

\begin{strategicpillars}[objective={Build scalable analytics capability}]
  \pillar{People}{Skills and operating model}
  \pillar{Process}{Standards and governance}
  \pillar{Technology}{Platform and automation}
\end{strategicpillars}
```

`reportroadmap` also supports `mode=dated` with ordered period labels and
milestones. `capabilitymap` accepts `\domain{name}{capability list}`.
`strategicpillars` accepts three to six pillars. `maturitymodel` accepts four
to six ordered `\stage` commands and may include a current-stage marker.
`continuum` requires exactly two endpoint labels and supports zero or more
normalized `\marker` values.

## 6. Rendering and package architecture

1. `reportkit-diagrams.sty` remains the public entry point and common style
   owner. It owns semantic styles, diagram metadata integration, errors, and
   backwards-compatible aliases.
2. New implementation files are split by concern and loaded by the entry
   point: `reportkit-spatial.sty`, `reportkit-process.sty`, and
   `reportkit-structure.sty`.
3. The v1.4.0 native primitives rely on the existing TikZ stack. The dated
   roadmap and tree implementations use deterministic layouts, so they do not
   add `pgfgantt` or `forest` as bootstrap dependencies.
4. `reportkit_viz.py` owns quantitative figure constructors and uses the
   existing ReportKit palette, fonts, `save_figure`, and PDF/PNG export
   convention. Its public chart functions receive tabular values rather than
   TeX fragments.
5. The conventional document width is 156 mm. Native primitives must fit this
   width by default and expose a documented `width` key where appropriate.
   They may wrap text or move to a fresh page through `diagram`; they must
   never silently exceed `\textwidth`.

## 7. Data, provenance, and accessibility rules

- The `diagram` wrapper's `source` is required for report deliverables.
  `Conceptual diagram.` remains a valid explicit source for non-data visuals.
- Native diagrams that show numbers must state whether values are illustrative
  or measured. Measured values should normally use the Python chart path.
- Analytical figures require a source note in the surrounding LaTeX document
  and an adjacent data/figure-generation script retained with the report.
- `description` must name the visual form, its axes or structural elements,
  and the main conclusion when one is intended.
- Colour combinations must meet ReportKit's existing restrained palette and
  must not make risk severity or positive/negative value colour-only.
- Captions describe what the reader should learn; sources describe provenance.

## 8. Error handling and limits

Every semantic primitive shall validate its required fields, cardinality, and
range. Examples:

| Condition | Required result |
| --- | --- |
| Matrix point outside `[0,1]` | Package error naming the point and allowed range |
| Risk row/column outside heatmap size | Package error naming the risk and allowed range |
| Pillar count outside 3--6 | Package error and no partially rendered diagram |
| Invalid flow reference | Package error identifying the unknown step id |
| Width too narrow for a fixed-card layout | Warning with the required minimum width or layout adjustment |
| Dense network beyond documented layout limit | Warning directing the author to explicit low-level placement or an external figure |

The v1.4.0 documentation shall publish practical limits for each primitive
(such as 12 points in a matrix and 15 nodes in an automatic tree/network
layout). These are readability limits, not parser limits.

## 9. Acceptance requirements

The acceptance suite shall contain one minimal compiled example for every
public primitive and variant promised above. Each example must include a
caption, source, and description. The suite shall verify:

1. pdflatex compilation succeeds twice with no `Package Error`, arithmetic,
   overfull-box, or missing-reference failure signatures;
2. the existing v1.2 public API continues to compile unchanged;
3. invalid-key/range fixture files fail with the expected actionable package
   error;
4. Python chart tests validate function inputs and save vector PDF plus PNG;
5. rendered PDFs are rasterized at 150 dpi and visually inspected for clipping,
   overlapping labels, broken arrows, unintended page breaks, and
   colour-dependent meaning;
6. `reportkit_doctor.py` still reports its actual build mode and bootstrap
   copies every newly required core file.

## 10. Delivery plan

### Phase 1 — Semantic foundation

Document the visual-selection rubric; introduce public wrappers for the
current matrix, lanes, layers, stack, cycle, and funnel primitives; add input
validation and complete acceptance examples. This phase establishes the DSL
conventions without changing existing output by default.

### Phase 2 — High-ROI qualitative diagrams

Implement `reportmatrix` points, `riskheatmap`, `reportflow`,
`reportswimlane`, `reportarchitecture`, `reportroadmap`, and
`strategicpillars`. Add the matching reference guide with copyable examples.

### Phase 3 — Hierarchy and strategy

Implement `reporttree`, `capabilitymap`, `maturitymodel`, `continuum`, and
the network/causal-loop wrappers. Confirm optional-package behavior in a
fresh bootstrap environment.

### Phase 4 — Analytical parity

Add Python treemap, waterfall, tornado, scatter/bubble, and planning-chart
functions with sample data, tests, and visual QA artefacts. Run a focused
Sankey spike and only promote it when it meets the same export and
accessibility requirements.

## 11. Documentation deliverables

- A visual-selection guide mapping report questions to primitives and
  explicitly distinguishing conceptual from data-driven visuals.
- A reference page for each public DSL environment, with required keys,
  defaults, limits, output semantics, and a minimal compiling example.
- An updated `SKILL.md` capability section directing report agents to choose
  a primitive by reasoning task before using an API.
- A generated or maintained gallery PDF showing every primitive with a
  caption, source, and visual description.

## 12. Definition of done

v1.4.0 is complete when the Phase 1--3 native interfaces and their
documentation compile in a clean bootstrap environment, existing public
macros remain compatible, required validation fixtures pass, and every
primitive has received rasterized visual QA. Phase 4 analytical features may
ship as v1.5.0 if their data, test, and visual-QA work is not ready without
compromising the native DSL release.
