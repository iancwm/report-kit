---
name: reportkit
description: Create polished technical or analytical PDF reports with the bundled ReportKit LaTeX class, semantic diagrams, callouts, and matched Matplotlib charts. Use for a designed report or brief PDF, not plain prose, a quick document, or slides.
---

# ReportKit

ReportKit produces evidence-led, reader-oriented technical reports. It combines a local LaTeX class, semantic callouts and diagrams, and a matched Python/Matplotlib chart theme.

Use it when the requested deliverable is a finished technical, analytical, evaluation, strategy, or research-report PDF. Do not use it for an informal memo, generic prose, a presentation, or any deliverable that does not need a designed PDF.

Git tags are the reproducible release identifiers. Check `reportkit.cls` when the class version itself matters.

For host-neutral automation, treat `reportkit context --json` as the
authoritative primitive and command contract. Use `reportkit docs --check
--json` as the drift gate; the version policy, exit classes, pinned toolchain,
and trust boundary are in
[references/agent-contract.md](references/agent-contract.md).

## Set up the report

**This repository is a reusable engine, not a place for report content.** Keep generated TeX files, figures, and any publication's manuscript outside this repository — in a separate report or publication directory. See [references/repository-boundary.md](references/repository-boundary.md) for the full boundary and guardrails.

From a clone of this skill, bootstrap a separate report directory:

```bash
git clone https://github.com/iancwm/report-kit.git <skill-directory>
bash <skill-directory>/shell_scripts/bootstrap.sh <skill-directory> <report-directory>
cd <report-directory>
python3 reportkit_doctor.py
```

`bootstrap.sh` refuses to run if `<report-directory>` resolves inside `<skill-directory>` — pick a directory outside the clone. It copies the required class, style files, and Python modules; scaffolds `manuscript/`, `fragments/`, `assets/`, `figures/`, `build/`, `output/`, and a `publication.yaml` stub; and installs the bundled Libertinus fonts when needed. Trust the actual `MODE:` line:

- `FULL BUILD`: TeX and ReportKit's required fonts work; a compiled PDF may be delivered.
- `SOURCE BUILD + FIGURES`: create source and figures, but do not claim that the PDF compiled.
- `SOURCE BUILD`: create a portable source bundle only.

For a single short report, copy `latex_templates/REPORT_TEMPLATE.tex` to `<report-directory>/report.tex` to start. Use `lualatex` for Unicode content outside pdfLaTeX's T1 encoding. For environment or font problems, read [references/troubleshooting.md](references/troubleshooting.md) and [references/font-setup.md](references/font-setup.md).

### Long-form publications

For a multi-chapter publication (a guide, book, or report assembled from several manuscript files), write Markdown into `<report-directory>/manuscript/` (listed in `manuscript/order.txt`), place diagram fragments in `fragments/`, and fill in `<report-directory>/publication.yaml` with at least a `title`. Then build with the pipeline facade instead of compiling `report.tex` directly:

```bash
<skill-directory>/reportkit build \
  --source-root <report-directory> --output-root <report-directory>/build
```

This never writes into `<skill-directory>` — every build artefact, including `reportkit.lock` (the pinned ReportKit ref and toolchain versions), lands under `<report-directory>`. See [`publication_pipeline/README.md`](publication_pipeline/README.md) for the section-build and validation commands.

## Write for the decision

- Establish the question, scope, evidence, method, and material assumptions before conclusions.
- Separate facts, interpretation, uncertainty, and recommendation. Never invent citations, data, or spurious precision.
- Make the executive summary a short narrative: problem, strongest evidence, conclusion, and implication.
- Use semantic callouts only when their meaning matters: `principle`, `decisionpoint`, `researchproblem`, `assumption`, `redflag`, `evidencenote`, `limitationnote`, `tipnote`, `deliverablenote`, and `metric`.
- Use `\source{...}` for every figure and diagram. A conceptual visual may explicitly use `Conceptual diagram.` as its source.

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

## Diagram contract

Place every conceptual visual in a `diagram` wrapper. It keeps the visual non-floating, reserves page space, and attaches caption and provenance to the prose.

```latex
\begin{diagram}[
  type=matrix,
  caption={Initiatives by implementation complexity and expected value.},
  source={Workshop assessment, September 2026.},
  description={A four-quadrant matrix with two labelled initiatives in the high-value quadrants.}
]
  % One semantic environment
\end{diagram}
```

`description` must name the visual form, its axes or structure, and the intended conclusion where there is one. Keep labels short; use `\\` only for deliberate line breaks. Do not hand-author coordinates unless a semantic primitive cannot represent the relationship.

`reportkit-diagrams.sty` is the public entry point and loads the spatial, process, and structural primitives. Their source files are the definitive key and argument reference:

- `latex_templates/reportkit-spatial.sty`: matrix and risk heatmap
- `latex_templates/reportkit-process.sty`: flows, swimlanes, networks, and causal loops
- `latex_templates/reportkit-structure.sty`: architecture, roadmap, strategy, maturity, continuum, capability map, and tree
- `latex_templates/reportkit-diagrams.sty`: wrapper plus low-level `RK...` primitives

Read only the relevant source file before using a primitive not shown below.

## Native diagram reference

### Positioning and risk

Use `reportmatrix` for qualitative quadrants or normalized point placement. Points require values in `[0,1]`; use `label-position=above`, `below`, `left`, or `right` when automatic placement is unclear.

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
  \point[label-position=below]{LMS upgrade}{0.35}{0.61}
\end{reportmatrix}
```

Use `riskheatmap` for ordinal likelihood and impact, not estimated probabilities or financial exposure. It supports 3×3 and 5×5 matrices; each risk takes an identifier, impact, likelihood, description, and optional owner/status metadata. A risk register appears when metadata is supplied.

```latex
\begin{riskheatmap}[size=5, impact={Impact}, likelihood={Likelihood}]
  \risk{R1}{4}{5}{Identity dependency}{owner=Security,status=mitigating}
  \risk{R2}{2}{3}{Migration delay}{owner=Platform,status=open}
\end{riskheatmap}
```

### Process and relationships

Declaration order establishes a flow's main reading sequence. Use `branch` and `merge` only for explicit divergence and convergence. For a bounded, deterministic branch layout, use `\stepat[<style>]{id}{x}{y}{label}` and `\flowedge[route=orthogonal,label-position=below,label={...}]{from}{to}`; routes also accept `straight`, `bend left=<degrees>`, and `bend right=<degrees>`. Use a swimlane when ownership is central; its steps take an id, a declared lane name, a label, and a one-based column. Supply `columns=` when the declared width must bound all process nodes; `node width=`, `column spacing=`, and `label gutter=` tune that bounded layout.

```latex
\begin{reportflow}[direction=horizontal]
  \step{id}{Identity check}
  \step{review}{Human review}
  \step{publish}{Publish}
  \flowedge{id}{review}
  \flowedge{review}{publish}
\end{reportflow}

\begin{reportswimlane}[lanes={User,Frontend,Backend,Reviewer},columns=4]
  \lanestep{request}{User}{Request}{1}
  \lanestep{validate}{Frontend}{Validate}{2}
  \lanestep{process}{Backend}{Process}{3}
  \lanestep{approve}{Reviewer}{Approve}{4}
  \handoff{request}{validate}
  \handoff{validate}{process}
  \handoff{process}{approve}
\end{reportswimlane}
```

`reportstate` keeps its sequential declaration API and also supports explicit positions: `\stateat[<style>]{id}{x}{y}{label}` and `\terminalstateat[<style>]{id}{x}{y}{label}`. Use `\transition[route={bend left=30},label-position=above]{from}{to}{label}` for a readable retry loop or terminal branch. Timeline watermarks accept `label-position=above|below|left|right`, `label-width=<length>`, and `label-anchor=<TikZ anchor>`.

Use `reportnetwork` for a compact relationship map. Use `causalloop` only for a feedback system; causal-edge labels normally indicate `+` or `-`. Dense networks need an external figure or deliberate low-level placement—automatic layout is intentionally limited.

```latex
\begin{reportnetwork}
  \networknode{client}{Web client}
  \networknode{api}{API gateway}
  \networknode{store}{Data store}
  \networkedge{client}{api}[request]
  \networkedge{api}{store}[read/write]
\end{reportnetwork}

\begin{causalloop}
  \causalnode{demand}{Demand}
  \causalnode{investment}{Investment}
  \causalnode{capacity}{Capacity}
  \causaledge{demand}{investment}{+}
  \causaledge{investment}{capacity}{+}
  \causaledge{capacity}{demand}{-}
\end{causalloop}
```

### Architecture, plan, and strategy

Architecture layers show responsibility or technical separation; components within a layer are comma-delimited. `reportroadmap` uses either qualitative horizons or ordered dated periods. Capability maps group capabilities by domain. Strategic pillars require an objective and three to six distinct levers.

```latex
\begin{reportarchitecture}[annotation={Ownership remains explicit across layers.},annotation-position=top]
  \layer{Consumers}{Web client, Analyst workspace}
  \layer{Services}{API gateway, Decision service}
  \layer{Data}{Operational store, Analytics warehouse}
\end{reportarchitecture}

\begin{reportroadmap}[mode=horizons]
  \horizon{Now}{Foundation}{Data model, Governance, Infrastructure}
  \horizon{Next}{Integration}{APIs, Pilot, Migration}
  \horizon{Later}{Scale}{Automation, ML, Optimization}
\end{reportroadmap}

\begin{reportroadmap}[mode=dated]
  \period{2026 Q4}
  \period{2027 Q1}
  \milestone{2026 Q4}{Design}
  \milestone{2027 Q1}{Pilot}
\end{reportroadmap}
```

```latex
\begin{strategicpillars}[objective={Build scalable analytics capability}]
  \pillar{People}{Skills and operating model}
  \pillar{Process}{Standards and governance}
  \pillar{Technology}{Platform and automation}
\end{strategicpillars}

\begin{capabilitymap}
  \domain{Data management}{Acquisition, Governance, Quality}
  \domain{Analytics}{BI, Statistics, ML}
\end{capabilitymap}
```

### Progression, hierarchy, and conceptual shapes

`maturitymodel` requires four to six ordered stages; `current` accepts an exact stage label or its one-based number. A continuum needs named endpoints and normalized marker positions. Tree node labels must be unique; `\branch[parent]{label}{children}` attaches below a previously declared label. Split a deep or dense tree rather than relying on its compact layout.

Use `\rkcode{...}` for literal technical tokens inside a direct label argument, especially an identifier with an underscore, such as `\rkcode{event_date}`. It is safe when a semantic primitive stores label text for later rendering. In a tree, it is display-only and cannot be used as a `\branch[parent]{...}` reference or in the comma-delimited child list; use a direct `\root{...}` or `\branch{...}{children}` label instead. `\rkcode` is deliberately limited to short identifier-like tokens, not general verbatim text.

```latex
\begin{maturitymodel}[current=Managed]
  \stage{Ad hoc}{Local and inconsistent}
  \stage{Defined}{Common practices}
  \stage{Managed}{Measured execution}
  \stage{Optimized}{Continuous improvement}
\end{maturitymodel}

\begin{continuum}[left={Centralized},right={Decentralized}]
  \marker{Company A}{.32}
  \marker{Company B}{.73}
\end{continuum}

\begin{reporttree}[kind=issue]
  \root{Why did revenue fall?}
  \branch{Volume}{Customers, Usage}
  \branch{Price}{List price, Discounts}
\end{reporttree}
```

An evidence stack narrows upward because its tiers represent increasing rigor or rarity. A cycle has no natural start or end. A conceptual funnel narrows because a population declines—never use it to encode measured conversion.

```latex
\begin{evidencestack}[tiers=3]
  \evidencetier{Credential}
  \evidencetier{Project}
  \evidencetier[rk accent]{Measured impact}
\end{evidencestack}

\begin{reportcycle}[stages=4]
  \cyclestage{observe}{Observe}
  \cyclestage{learn}{Learn}
  \cyclestage{act}{Act}
  \cyclestage{measure}{Measure}
  \cycleedge{observe}{learn}
  \cycleedge{learn}{act}
  \cycleedge{act}{measure}
  \cycleedge{measure}{observe}
\end{reportcycle}

\begin{reportfunnel}
  \funnelstage{1.00}{.72}{Applications}
  \funnelstage{.72}{.42}{Screens}
  \funnelstage{.42}{.20}{Interviews}
  \funnelstage[rk accent]{.20}{.10}{Offers}
\end{reportfunnel}
```

## Analytical figures

Use `python_scripts/reportkit_viz.py` whenever geometry encodes data. It provides `timeseries`, `bar_chart`, `distribution`, `scatter_plot`, `heatmap`, `drawdown_chart`, `waterfall_chart`, `treemap_chart`, `tornado_chart`, `bubble_matrix`, and `timeline_chart`, plus theme, formatter, annotation, and export helpers.

```python
import reportkit_viz as rkv

rkv.apply_theme()
fig, ax = rkv.timeseries(data, ylabel="Cumulative return")
rkv.save_figure(fig, "figures/performance")
```

`save_figure` produces a vector PDF for LaTeX and a PNG for QA. Keep the figure-generation script and input/provenance alongside the report. Prefer a bar chart or treemap for more than four categories; pie charts are not a ReportKit standard. Keep analytical titles in the LaTeX caption unless the figure must stand alone.

## Institutional-research theme (equity research)

For an equity-research, investment-strategy, or other institutional analytical publication, use `\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}` instead of the default theme. It is exhibit-led (prefer an analytical exhibit over a decorative callout when quantitative evidence exists; exhibit titles state the finding, not just the metric) and requires `lualatex`, not `pdflatex`, since it loads Google Sans via `fontspec`. See [references/institutional-research-theme.md](references/institutional-research-theme.md) for the full primitive reference (`researchfrontpage`, `ratingstrip`, `whatschanged`, `exhibit`, `exhibitpair`/`exhibitgrid`, `financialtable`, `financialmodelpage`, `bullcase`/`basecase`/`bearcase`), the `researchmain`/`researchsidebar` minipage-adjacency requirement, the `exhibitgrid` column-count limit, and `rkv.apply_theme("institutional-research")`/`rkv.risk_reward_chart()` usage. [latex_templates/examples/equity-research/](latex_templates/examples/equity-research/) is a complete worked example.

## Build and inspect

On a `FULL BUILD`, use the CLI build so the standard compilation, diagnostic
gate, page rendering, and build manifest are applied consistently:

```bash
./reportkit build --source-root <publication-project>
./reportkit inspect --source-root <publication-project>
```

Read the `.log` before retrying a failed compile. Inspect every rendered page for clipped text, overlapping labels, broken arrows, bad page breaks, missing figures, and meanings conveyed only by colour. A successful TeX exit code alone is not completion.

When modifying ReportKit itself, run its regression suite:

```bash
bash scripts/acceptance_check.sh
```

The suite compiles the backwards-compatibility and visual-grammar fixtures with `pdflatex`, the institutional-research/equity-research fixture with `lualatex`, and checks Python imports; each engine check warns and skips (not blocking) if that engine is not installed. For a known failure or a surprising diagnostic result, consult [references/known-fixes.md](references/known-fixes.md) before changing implementation.

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent contract metadata. Do not edit it by hand.

### Callout primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `assumption` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{assumption}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{assumption}</code> |
| `decisionpoint` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{decisionpoint}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{decisionpoint}</code> |
| `deliverablenote` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{deliverablenote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{deliverablenote}</code> |
| `evidence` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{evidence}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{evidence}</code> |
| `evidencenote` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{evidencenote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{evidencenote}</code> |
| `execsummary` | `` | — | — | stable since 1.0.0 | <code>\begin{execsummary}&lt;br&gt;Example content.&lt;br&gt;\end{execsummary}</code> |
| `limitation` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{limitation}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{limitation}</code> |
| `limitationnote` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{limitationnote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{limitationnote}</code> |
| `metric` | `m m` | `label` (text, required) — Label.<br>`value` (text, required) — Value. | — | stable since 1.0.0 | <code>\begin{metric}{Example}{1}&lt;br&gt;Example content.&lt;br&gt;\end{metric}</code> |
| `principle` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{principle}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{principle}</code> |
| `redflag` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{redflag}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{redflag}</code> |
| `researchproblem` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{researchproblem}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{researchproblem}</code> |
| `tip` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{tip}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{tip}</code> |
| `tipnote` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\begin{tipnote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{tipnote}</code> |

### Figure primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `capabilitymap` | `O{}` | `options` (options, optional=) — Capability-map layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Capability map.},description={Two domains group four capabilities.}]&lt;br&gt;\begin{capabilitymap}&lt;br&gt;\domain{Data}{Acquire,Govern}&lt;br&gt;\domain{Analytics}{Model,Explain}&lt;br&gt;\end{capabilitymap}&lt;br&gt;\end{diagram}</code> |
| `causalloop` | `O{}` | `options` (options, optional=) — Causal-loop layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Capacity loop.},description={Demand, investment, and capacity form a feedback loop.}]&lt;br&gt;\begin{causalloop}&lt;br&gt;\causalnode{demand}{Demand}&lt;br&gt;\causalnode{investment}{Investment}&lt;br&gt;\causalnode{capacity}{Capacity}&lt;br&gt;\causaledge{demand}{investment}{+}&lt;br&gt;\causaledge{investment}{capacity}{+}&lt;br&gt;\causaledge{capacity}{demand}{-}&lt;br&gt;\end{causalloop}&lt;br&gt;\end{diagram}</code> |
| `continuum` | `O{}` | `options` (options, optional=) — Endpoint labels and layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Operating continuum.},description={Two positions between centralized and distributed.}]&lt;br&gt;\begin{continuum}[left={Centralized},right={Distributed}]&lt;br&gt;\marker{Team A}{.3}&lt;br&gt;\marker{Team B}{.7}&lt;br&gt;\end{continuum}&lt;br&gt;\end{diagram}</code> |
| `evidencestack` | `O{}` | `options` (options, optional=) — Evidence-stack layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Evidence stack.},description={Three tiers increase in rigor.}]&lt;br&gt;\begin{evidencestack}&lt;br&gt;\evidencetier{Credential}&lt;br&gt;\evidencetier{Project}&lt;br&gt;\evidencetier{Measured impact}&lt;br&gt;\end{evidencestack}&lt;br&gt;\end{diagram}</code> |
| `maturitymodel` | `O{}` | `options` (options, optional=) — Maturity layout and current-stage keys. | Declare four to six stages. | stable since 1.0.0 | <code>\begin{diagram}[caption={Maturity progression.},description={Four ordered maturity stages.}]&lt;br&gt;\begin{maturitymodel}[current={Managed}]&lt;br&gt;\stage{Ad hoc}{Local}&lt;br&gt;\stage{Defined}{Common}&lt;br&gt;\stage{Managed}{Measured}&lt;br&gt;\stage{Optimized}{Improving}&lt;br&gt;\end{maturitymodel}&lt;br&gt;\end{diagram}</code> |
| `reportarchitecture` | `O{}` | `options` (options, optional=) — Architecture layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Platform architecture.},description={Three platform layers.}]&lt;br&gt;\begin{reportarchitecture}&lt;br&gt;\layer{Experience}{Reader,Author}&lt;br&gt;\layer{Services}{Build,Validation}&lt;br&gt;\layer{Data}{Sources,Archive}&lt;br&gt;\end{reportarchitecture}&lt;br&gt;\end{diagram}</code> |
| `reportcompare` | `O{}` | `options` (options, optional=) — Panel spacing and row layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Join comparison.},description={A before and after comparison of data grain.}]&lt;br&gt;\begin{reportcompare}&lt;br&gt;\panel{before}{Before}&lt;br&gt;\panelitem{before}{0}{one order}&lt;br&gt;\panel{after}{After}&lt;br&gt;\panelitem{after}{0}{three items}&lt;br&gt;\transformarrow{join}&lt;br&gt;\end{reportcompare}&lt;br&gt;\end{diagram}</code> |
| `reportcycle` | `O{}` | `options` (options, optional=) — Cycle layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Learning cycle.},description={Four stages form a closed cycle.}]&lt;br&gt;\begin{reportcycle}&lt;br&gt;\cyclestage{observe}{Observe}&lt;br&gt;\cyclestage{learn}{Learn}&lt;br&gt;\cyclestage{act}{Act}&lt;br&gt;\cyclestage{measure}{Measure}&lt;br&gt;\cycleedge{observe}{learn}&lt;br&gt;\cycleedge{learn}{act}&lt;br&gt;\cycleedge{act}{measure}&lt;br&gt;\cycleedge{measure}{observe}&lt;br&gt;\end{reportcycle}&lt;br&gt;\end{diagram}</code> |
| `reportflow` | `O{}` | `options` (options, optional=) — Direction and step-spacing keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Publication flow.},description={Three ordered publication steps.}]&lt;br&gt;\begin{reportflow}&lt;br&gt;\step{draft}{Draft}&lt;br&gt;\step{review}{Review}&lt;br&gt;\step{publish}{Publish}&lt;br&gt;\flowedge{draft}{review}&lt;br&gt;\flowedge{review}{publish}&lt;br&gt;\end{reportflow}&lt;br&gt;\end{diagram}</code> |
| `reportfunnel` | `O{}` | `options` (options, optional=) — Funnel layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Conversion funnel.},description={Four stages narrow from applications to offers.}]&lt;br&gt;\begin{reportfunnel}&lt;br&gt;\funnelstage{1.0}{.7}{Applications}&lt;br&gt;\funnelstage{.7}{.4}{Screens}&lt;br&gt;\funnelstage{.4}{.2}{Interviews}&lt;br&gt;\funnelstage{.2}{.1}{Offers}&lt;br&gt;\end{reportfunnel}&lt;br&gt;\end{diagram}</code> |
| `reportmatrix` | `O{}` | `options` (options, optional=) — Axis, size, and highlight keys. | Point coordinates must lie between zero and one. | stable since 1.0.0 | <code>\begin{diagram}[caption={Priority matrix.},description={A two-axis matrix with one labelled point.}]&lt;br&gt;\begin{reportmatrix}&lt;br&gt;\quadrant{low}{high}{Quick wins}&lt;br&gt;\point{Pilot}{.25}{.75}&lt;br&gt;\end{reportmatrix}&lt;br&gt;\end{diagram}</code> |
| `reportnetwork` | `O{}` | `options` (options, optional=) — Network layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Service network.},description={Three connected service nodes.}]&lt;br&gt;\begin{reportnetwork}&lt;br&gt;\networknode{client}{Client}&lt;br&gt;\networknode{api}{API}&lt;br&gt;\networknode{store}{Store}&lt;br&gt;\networkedge{client}{api}[request]&lt;br&gt;\networkedge{api}{store}[write]&lt;br&gt;\end{reportnetwork}&lt;br&gt;\end{diagram}</code> |
| `reportroadmap` | `O{}` | `options` (options, optional=) — Roadmap mode and layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Delivery roadmap.},description={Three delivery horizons.}]&lt;br&gt;\begin{reportroadmap}&lt;br&gt;\horizon{Now}{Foundation}{Model,Governance}&lt;br&gt;\horizon{Next}{Integration}{API,Pilot}&lt;br&gt;\horizon{Later}{Scale}{Automation,Optimization}&lt;br&gt;\end{reportroadmap}&lt;br&gt;\end{diagram}</code> |
| `reportstate` | `O{}` | `options` (options, optional=) — State layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Task states.},description={A task moves from scheduled to running and done.}]&lt;br&gt;\begin{reportstate}&lt;br&gt;\state{scheduled}{Scheduled}&lt;br&gt;\state{running}{Running}&lt;br&gt;\terminalstate{done}{Done}&lt;br&gt;\transition{scheduled}{running}{start}&lt;br&gt;\transition{running}{done}{finish}&lt;br&gt;\end{reportstate}&lt;br&gt;\end{diagram}</code> |
| `reportswimlane` | `O{}` | `options` (options, optional=) — Lane names, width, columns, and spacing keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Review ownership.},description={Three steps move across responsibility lanes.}]&lt;br&gt;\begin{reportswimlane}[lanes={Author,Reviewer},columns=3]&lt;br&gt;\lanestep{draft}{Author}{Draft}{1}&lt;br&gt;\lanestep{review}{Reviewer}{Review}{2}&lt;br&gt;\lanestep{publish}{Author}{Publish}{3}&lt;br&gt;\handoff{draft}{review}&lt;br&gt;\handoff{review}{publish}&lt;br&gt;\end{reportswimlane}&lt;br&gt;\end{diagram}</code> |
| `reporttimeline` | `O{}` | `options` (options, optional=) — Track, span, and label-layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Event timeline.},description={Two events on one time track.}]&lt;br&gt;\begin{reporttimeline}[tracks={Event time}]&lt;br&gt;\event{Event time}{.2}{A}&lt;br&gt;\event{Event time}{.8}{B}&lt;br&gt;\watermark{Event time}{.6}{close}&lt;br&gt;\end{reporttimeline}&lt;br&gt;\end{diagram}</code> |
| `reporttree` | `O{}` | `options` (options, optional=) — Tree layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Issue tree.},description={Revenue splits into volume and price.}]&lt;br&gt;\begin{reporttree}&lt;br&gt;\root{Revenue}&lt;br&gt;\branch{Volume}{Customers,Usage}&lt;br&gt;\branch{Price}{List price,Discounts}&lt;br&gt;\end{reporttree}&lt;br&gt;\end{diagram}</code> |
| `riskheatmap` | `O{}` | `options` (options, optional=) — Heatmap size, labels, and threshold keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Risk heatmap.},description={One high-impact operational risk.}]&lt;br&gt;\begin{riskheatmap}&lt;br&gt;\risk{R1}{5}{4}{Identity dependency}{owner=Security,status=mitigating}&lt;br&gt;\end{riskheatmap}&lt;br&gt;\end{diagram}</code> |
| `strategicpillars` | `O{}` | `options` (options, optional=) — Pillar layout keys. | Declare three to six pillars. | stable since 1.0.0 | <code>\begin{diagram}[caption={Strategic pillars.},description={Three pillars support an objective.}]&lt;br&gt;\begin{strategicpillars}[objective={Trusted reporting}]&lt;br&gt;\pillar{People}{Skills}&lt;br&gt;\pillar{Process}{Standards}&lt;br&gt;\pillar{Technology}{Platform}&lt;br&gt;\end{strategicpillars}&lt;br&gt;\end{diagram}</code> |

### Chart primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `bar_chart` | `data, *, horizontal=True, highlight=None, value_formatter=None, axis_label=None, sort=False, zero_line=True, size='full', title=None` | `data` (data, required) — Data.<br>`horizontal` (option, optional=True) — Horizontal.<br>`highlight` (option, optional=None) — Highlight.<br>`value_formatter` (option, optional=None) — Value formatter.<br>`axis_label` (option, optional=None) — Axis label.<br>`sort` (option, optional=False) — Sort.<br>`zero_line` (option, optional=True) — Zero line.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.bar_chart({"A": 2, "B": 1})</code> |
| `bubble_matrix` | `data, *, x, y, xlabel, ylabel, size_column=None, label_column=None, group_column=None, reference_x=None, reference_y=None, quadrant_labels=None, x_formatter=None, y_formatter=None, size='full', title=None` | `data` (data, required) — Data.<br>`x` (option, required) — X.<br>`y` (option, required) — Y.<br>`xlabel` (option, required) — Xlabel.<br>`ylabel` (option, required) — Ylabel.<br>`size_column` (option, optional=None) — Size column.<br>`label_column` (option, optional=None) — Label column.<br>`group_column` (option, optional=None) — Group column.<br>`reference_x` (option, optional=None) — Reference x.<br>`reference_y` (option, optional=None) — Reference y.<br>`quadrant_labels` (option, optional=None) — Quadrant labels.<br>`x_formatter` (option, optional=None) — X formatter.<br>`y_formatter` (option, optional=None) — Y formatter.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>data = pd.DataFrame({"x":[1],"y":[2]}); fig, ax = rkv.bubble_matrix(data, x="x", y="y", xlabel="X", ylabel="Y")</code> |
| `distribution` | `values, *, bins='fd', xlabel=None, x_formatter=None, reference=None, density=False, size='full', title=None` | `values` (data, required) — Values.<br>`bins` (option, optional='fd') — Bins.<br>`xlabel` (option, optional=None) — Xlabel.<br>`x_formatter` (option, optional=None) — X formatter.<br>`reference` (option, optional=None) — Reference.<br>`density` (option, optional=False) — Density.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.distribution([1, 2, 2, 3])</code> |
| `donut_chart` | `data, *, title=None, size='sidebar', colors=None` | `data` (data, required) — Data.<br>`title` (option, optional=None) — Title.<br>`size` (option, optional='sidebar') — Size.<br>`colors` (option, optional=None) — Colors. | Use two to four proportional slices. | stable since 1.0.0 | <code>fig, ax = rkv.donut_chart({"Core": 70, "Other": 30})</code> |
| `drawdown_chart` | `drawdown, *, ylabel='Drawdown', y_formatter='percent', size='full', title=None` | `drawdown` (data, required) — Drawdown.<br>`ylabel` (option, optional='Drawdown') — Ylabel.<br>`y_formatter` (option, optional='percent') — Y formatter.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.drawdown_chart(pd.Series([0, -0.1, -0.05]))</code> |
| `heatmap` | `matrix, *, row_labels=None, col_labels=None, center=0.0, vmin=None, vmax=None, annotate=False, annotation_format='.2f', cbar_label=None, size='square', title=None` | `matrix` (data, required) — Matrix.<br>`row_labels` (option, optional=None) — Row labels.<br>`col_labels` (option, optional=None) — Col labels.<br>`center` (option, optional=0.0) — Center.<br>`vmin` (option, optional=None) — Vmin.<br>`vmax` (option, optional=None) — Vmax.<br>`annotate` (option, optional=False) — Annotate.<br>`annotation_format` (option, optional='.2f') — Annotation format.<br>`cbar_label` (option, optional=None) — Cbar label.<br>`size` (option, optional='square') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.heatmap([[1, 2], [3, 4]])</code> |
| `risk_reward_chart` | `price_history, *, bear, base, bull, current=None, bear_label='Bear', base_label='Base', bull_label='Bull', value_formatter=None, ylabel='Share price ($)', xlabel=None, size='full', title=None` | `price_history` (data, required) — Price history.<br>`bear` (option, required) — Bear.<br>`base` (option, required) — Base.<br>`bull` (option, required) — Bull.<br>`current` (option, optional=None) — Current.<br>`bear_label` (option, optional='Bear') — Bear label.<br>`base_label` (option, optional='Base') — Base label.<br>`bull_label` (option, optional='Bull') — Bull label.<br>`value_formatter` (option, optional=None) — Value formatter.<br>`ylabel` (option, optional='Share price ($)') — Ylabel.<br>`xlabel` (option, optional=None) — Xlabel.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>prices = pd.Series([90, 100]); fig, ax = rkv.risk_reward_chart(prices, bear=80, base=110, bull=140)</code> |
| `scatter_plot` | `x, y, *, xlabel, ylabel, fit_line=False, x_formatter=None, y_formatter=None, reference_x=None, reference_y=None, size='full', title=None` | `x` (data, required) — X.<br>`y` (option, required) — Y.<br>`xlabel` (option, required) — Xlabel.<br>`ylabel` (option, required) — Ylabel.<br>`fit_line` (option, optional=False) — Fit line.<br>`x_formatter` (option, optional=None) — X formatter.<br>`y_formatter` (option, optional=None) — Y formatter.<br>`reference_x` (option, optional=None) — Reference x.<br>`reference_y` (option, optional=None) — Reference y.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.scatter_plot([1, 2], [2, 3], xlabel="X", ylabel="Y")</code> |
| `timeline_chart` | `tasks, *, label_column='label', start_column='start', end_column='end', workstream_column='workstream', milestone_column='milestone', current_date=None, scale='auto', size='full', title=None` | `tasks` (data, required) — Tasks.<br>`label_column` (option, optional='label') — Label column.<br>`start_column` (option, optional='start') — Start column.<br>`end_column` (option, optional='end') — End column.<br>`workstream_column` (option, optional='workstream') — Workstream column.<br>`milestone_column` (option, optional='milestone') — Milestone column.<br>`current_date` (option, optional=None) — Current date.<br>`scale` (option, optional='auto') — Scale.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | A timeline supports at most 30 tasks. | stable since 1.0.0 | <code>fig, ax = rkv.timeline_chart([{"label":"Build","start":"2026 Q1","end":"2026 Q2"}])</code> |
| `timeseries` | `data, *, ylabel=None, xlabel=None, y_formatter=None, benchmark=None, reference_line=None, legend=True, size='full', title=None` | `data` (data, required) — Data.<br>`ylabel` (option, optional=None) — Ylabel.<br>`xlabel` (option, optional=None) — Xlabel.<br>`y_formatter` (option, optional=None) — Y formatter.<br>`benchmark` (option, optional=None) — Benchmark.<br>`reference_line` (option, optional=None) — Reference line.<br>`legend` (option, optional=True) — Legend.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>data = pd.Series([1, 2, 3]); fig, ax = rkv.timeseries(data)</code> |
| `tornado_chart` | `sensitivities, *, base_case=0.0, low_column='low', high_column='high', label_column=None, value_formatter=None, xlabel=None, size='full', title=None` | `sensitivities` (data, required) — Sensitivities.<br>`base_case` (option, optional=0.0) — Base case.<br>`low_column` (option, optional='low') — Low column.<br>`high_column` (option, optional='high') — High column.<br>`label_column` (option, optional=None) — Label column.<br>`value_formatter` (option, optional=None) — Value formatter.<br>`xlabel` (option, optional=None) — Xlabel.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.tornado_chart({"Price": (-10, 15), "Volume": (-5, 8)})</code> |
| `treemap_chart` | `data, *, label_column='label', value_column='value', parent_column=None, group_column=None, min_category_fraction=0.02, min_label_fraction=0.045, other_label='Other', value_formatter=None, size='full', title=None` | `data` (data, required) — Data.<br>`label_column` (option, optional='label') — Label column.<br>`value_column` (option, optional='value') — Value column.<br>`parent_column` (option, optional=None) — Parent column.<br>`group_column` (option, optional=None) — Group column.<br>`min_category_fraction` (option, optional=0.02) — Min category fraction.<br>`min_label_fraction` (option, optional=0.045) — Min label fraction.<br>`other_label` (option, optional='Other') — Other label.<br>`value_formatter` (option, optional=None) — Value formatter.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.treemap_chart({"A": 60, "B": 40})</code> |
| `waterfall_chart` | `contributions, *, opening=0.0, opening_label='Opening', total_label='Total', subtotals=None, closing_total=None, value_formatter=None, ylabel=None, size='full', title=None` | `contributions` (data, required) — Contributions.<br>`opening` (option, optional=0.0) — Opening.<br>`opening_label` (option, optional='Opening') — Opening label.<br>`total_label` (option, optional='Total') — Total label.<br>`subtotals` (option, optional=None) — Subtotals.<br>`closing_total` (option, optional=None) — Closing total.<br>`value_formatter` (option, optional=None) — Value formatter.<br>`ylabel` (option, optional=None) — Ylabel.<br>`size` (option, optional='full') — Size.<br>`title` (option, optional=None) — Title. | — | stable since 1.0.0 | <code>fig, ax = rkv.waterfall_chart({"Growth": 10, "Costs": -4})</code> |

### Composition primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `RKShortListing` | `O{}` | `options` (options, optional=) — Options. | — | stable since 1.0.0 | <code>\begin{RKShortListing}[]&lt;br&gt;Example content.&lt;br&gt;\end{RKShortListing}</code> |
| `analystblock` | `` | — | — | stable since 1.8.0 | <code>\begin{analystblock}&lt;br&gt;Example content.&lt;br&gt;\end{analystblock}</code> |
| `diagram` | `O{}` | `options` (options, optional=) — Options. | — | stable since 1.0.0 | <code>\begin{diagram}[]&lt;br&gt;Example content.&lt;br&gt;\end{diagram}</code> |
| `estimatesblock` | `` | — | — | stable since 1.8.0 | <code>\begin{estimatesblock}&lt;br&gt;Example content.&lt;br&gt;\end{estimatesblock}</code> |
| `exhibit` | `O{}` | `options` (options, optional=) — Options. | — | stable since 1.8.0 | <code>\begin{exhibit}[]&lt;br&gt;Example content.&lt;br&gt;\end{exhibit}</code> |
| `exhibitgrid` | `O{}` | `options` (options, optional=) — Options. | An exhibit grid supports at most three columns. | stable since 1.8.0 | <code>\begin{exhibitgrid}[]&lt;br&gt;Example content.&lt;br&gt;\end{exhibitgrid}</code> |
| `exhibitpair` | `` | — | — | stable since 1.8.0 | <code>\begin{exhibitpair}&lt;br&gt;Example content.&lt;br&gt;\end{exhibitpair}</code> |
| `financialmodelpage` | `` | — | — | stable since 1.8.0 | <code>\begin{financialmodelpage}&lt;br&gt;Example content.&lt;br&gt;\end{financialmodelpage}</code> |
| `financialtable` | `` | — | — | stable since 1.8.0 | <code>\begin{financialtable}&lt;br&gt;Example content.&lt;br&gt;\end{financialtable}</code> |
| `fullwidthexhibit` | `` | — | — | stable since 1.8.0 | <code>\begin{fullwidthexhibit}&lt;br&gt;Example content.&lt;br&gt;\end{fullwidthexhibit}</code> |
| `marketdatablock` | `` | — | — | stable since 1.8.0 | <code>\begin{marketdatablock}&lt;br&gt;Example content.&lt;br&gt;\end{marketdatablock}</code> |
| `outputblock` | `` | — | — | stable since 1.0.0 | <code>\begin{outputblock}&lt;br&gt;Example content.&lt;br&gt;\end{outputblock}</code> |
| `ratingstrip` | `o` | `item_count` (options, optional) — Item count. | — | stable since 1.8.0 | <code>\begin{ratingstrip}[]&lt;br&gt;Example content.&lt;br&gt;\end{ratingstrip}</code> |
| `researchfrontpage` | `` | — | — | stable since 1.8.0 | <code>\begin{researchfrontpage}&lt;br&gt;Example content.&lt;br&gt;\end{researchfrontpage}</code> |
| `researchmain` | `` | — | researchmain must be immediately followed by researchsidebar. | stable since 1.8.0 | <code>\begin{researchmain}&lt;br&gt;Example content.&lt;br&gt;\end{researchmain}</code> |
| `researchsidebar` | `` | — | researchsidebar must immediately follow researchmain. | stable since 1.8.0 | <code>\begin{researchsidebar}&lt;br&gt;Example content.&lt;br&gt;\end{researchsidebar}</code> |
| `whatschanged` | `` | — | — | stable since 1.8.0 | <code>\begin{whatschanged}&lt;br&gt;Example content.&lt;br&gt;\end{whatschanged}</code> |

### Command primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `RKCycleEdge` | `O{} m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\RKCycleEdge[]{a}{b}</code> |
| `RKCycleNode` | `O{} m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`angle` (text, required) — Angle.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKCycleNode[]{a}{1}{Example}</code> |
| `RKCycleSetup` | `m` | `radius` (text, required) — Radius. | — | stable since 1.0.0 | <code>\RKCycleSetup{1}</code> |
| `RKDiagramSection` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\RKDiagramSection{Example}</code> |
| `RKDiagramSubsection` | `m` | `title` (text, required) — Title. | — | stable since 1.0.0 | <code>\RKDiagramSubsection{Example}</code> |
| `RKEdge` | `O{} m m m` | `options` (options, optional=) — Options.<br>`kind` (text, required) — Kind.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\RKEdge[]{Example}{a}{b}</code> |
| `RKFunnelSetup` | `m m` | `width` (text, required) — Width.<br>`stage_height` (text, required) — Stage height. | — | stable since 1.0.0 | <code>\RKFunnelSetup{1}{1}</code> |
| `RKFunnelStage` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`row` (text, required) — Row.<br>`width` (text, required) — Width.<br>`label` (text, required) — Label.<br>`detail` (text, required) — Detail. | — | stable since 1.0.0 | <code>\RKFunnelStage[]{1}{1}{Example}{Example}</code> |
| `RKLane` | `m m` | `row` (text, required) — Row.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKLane{1}{Example}</code> |
| `RKLaneNode` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`column` (text, required) — Column.<br>`row` (text, required) — Row.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKLaneNode[]{a}{1}{1}{Example}</code> |
| `RKLayer` | `O{} m m m` | `options` (options, optional=) — Options.<br>`row` (text, required) — Row.<br>`label` (text, required) — Label.<br>`detail` (text, required) — Detail. | — | stable since 1.0.0 | <code>\RKLayer[]{1}{Example}{Example}</code> |
| `RKLayerSetup` | `m m` | `width` (text, required) — Width.<br>`layer_height` (text, required) — Layer height. | — | stable since 1.0.0 | <code>\RKLayerSetup{1}{Example}</code> |
| `RKLink` | `m` | `key` (link-key, required) — Registered link key. | Use a key declared in links.yaml; unknown values fall back to literal URLs. | stable since 1.5.0 | <code>\RKLink{project-home}</code> |
| `RKMatrix` | `m m` | `x_label` (text, required) — X label.<br>`y_label` (text, required) — Y label. | — | stable since 1.0.0 | <code>\RKMatrix{Example}{Example}</code> |
| `RKMatrixCell` | `O{} m m m` | `options` (options, optional=) — Options.<br>`column` (text, required) — Column.<br>`row` (text, required) — Row.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKMatrixCell[]{1}{1}{Example}</code> |
| `RKMatrixSetup` | `m m` | `width` (text, required) — Width.<br>`height` (text, required) — Height. | — | stable since 1.0.0 | <code>\RKMatrixSetup{1}{1}</code> |
| `RKNode` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`x` (text, required) — X.<br>`y` (text, required) — Y.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKNode[]{a}{1}{1}{Example}</code> |
| `RKNodeRel` | `O{} m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`position` (text, required) — Position.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKNodeRel[]{a}{1}{Example}</code> |
| `RKPath` | `m` | `path` (text, required) — Path. | — | stable since 1.0.0 | <code>\RKPath{https://example.com}</code> |
| `RKStackSetup` | `m m m` | `width` (text, required) — Width.<br>`tier_height` (text, required) — Tier height.<br>`tier_count` (text, required) — Tier count. | — | stable since 1.0.0 | <code>\RKStackSetup{1}{1}{1}</code> |
| `RKStackTier` | `O{} m m` | `options` (options, optional=) — Options.<br>`row` (text, required) — Row.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\RKStackTier[]{1}{Example}</code> |
| `RKSwimlaneSetup` | `m m` | `width` (text, required) — Width.<br>`lane_height` (text, required) — Lane height. | — | stable since 1.0.0 | <code>\RKSwimlaneSetup{1}{1}</code> |
| `RKTitlePage` | `O{} m` | `options` (options, optional=) — Options.<br>`title` (text, required) — Title. | — | stable since 1.0.0 | <code>\RKTitlePage[]{Example}</code> |
| `basecase` | `m m` | `value` (text, required) — Value.<br>`detail` (text, required) — Detail. | — | stable since 1.8.0 | <code>\basecase{1}{Example}</code> |
| `bearcase` | `m m` | `value` (text, required) — Value.<br>`detail` (text, required) — Detail. | — | stable since 1.8.0 | <code>\bearcase{1}{Example}</code> |
| `branch` | `O{} m m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\branch[]{a}{b}{Example}</code> |
| `bullcase` | `m m` | `value` (text, required) — Value.<br>`detail` (text, required) — Detail. | — | stable since 1.8.0 | <code>\bullcase{1}{Example}</code> |
| `causaledge` | `m m m` | `source` (text, required) — Source.<br>`target` (text, required) — Target.<br>`polarity` (text, required) — Polarity. | — | stable since 1.0.0 | <code>\causaledge{a}{b}{+}</code> |
| `causalnode` | `O{} m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\causalnode[]{a}{Example}</code> |
| `change` | `m m m` | `date` (text, required) — Date.<br>`headline` (text, required) — Headline.<br>`detail` (text, required) — Detail. | — | stable since 1.8.0 | <code>\change{Example}{Example}{Example}</code> |
| `cycleedge` | `O{} m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\cycleedge[]{a}{b}</code> |
| `cyclestage` | `O{} m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\cyclestage[]{a}{Example}</code> |
| `event` | `O{} m m m` | `options` (options, optional=) — Options.<br>`track` (text, required) — Track.<br>`position` (text, required) — Position.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\event[]{a}{1}{Example}</code> |
| `evidencetier` | `O{} m` | `options` (options, optional=) — Options.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\evidencetier[]{Example}</code> |
| `exhibitpane` | `O{} m` | `options` (options, optional=) — Options.<br>`content` (text, required) — Content. | — | stable since 1.8.0 | <code>\exhibitpane[]{Example}</code> |
| `flowedge` | `O{} m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\flowedge[]{a}{b}</code> |
| `funnelstage` | `O{} m m m` | `options` (options, optional=) — Options.<br>`width` (text, required) — Width.<br>`label` (text, required) — Label.<br>`detail` (text, required) — Detail. | — | stable since 1.0.0 | <code>\funnelstage[]{1}{Example}{Example}</code> |
| `handoff` | `O{} m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\handoff[]{a}{b}</code> |
| `laneflow` | `O{} m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target. | — | stable since 1.0.0 | <code>\laneflow[]{a}{b}</code> |
| `lanestep` | `m m m m` | `lane` (text, required) — Lane.<br>`id` (text, required) — Id.<br>`column` (text, required) — Column.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\lanestep{Example}{a}{1}{Example}</code> |
| `merge` | `O{} m m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\merge[]{a}{b}{Example}</code> |
| `networkedge` | `O{dependency} m m O{}` | `relationship` (options, optional=dependency) — Relationship.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target.<br>`options` (options, optional=) — Options. | — | stable since 1.0.0 | <code>\networkedge[]{a}{b}[]</code> |
| `networknode` | `O{} m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\networknode[]{a}{Example}</code> |
| `panel` | `m m` | `id` (text, required) — Id.<br>`title` (text, required) — Title. | — | stable since 1.0.0 | <code>\panel{a}{Example}</code> |
| `panelitem` | `m m m` | `panel` (text, required) — Panel.<br>`label` (text, required) — Label.<br>`detail` (text, required) — Detail. | — | stable since 1.0.0 | <code>\panelitem{a}{Example}{Example}</code> |
| `point` | `O{} m m m` | `options` (options, optional=) — Options.<br>`x` (text, required) — X.<br>`y` (text, required) — Y.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\point[]{1}{1}{Example}</code> |
| `quadrant` | `m m m` | `column` (text, required) — Column.<br>`row` (text, required) — Row.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\quadrant{1}{1}{Example}</code> |
| `ratingitem` | `m m` | `label` (text, required) — Label.<br>`value` (text, required) — Value. | — | stable since 1.8.0 | <code>\ratingitem{Example}{1}</code> |
| `risk` | `m m m m m` | `likelihood` (text, required) — Likelihood.<br>`impact` (text, required) — Impact.<br>`label` (text, required) — Label.<br>`owner` (text, required) — Owner.<br>`status` (text, required) — Status. | — | stable since 1.0.0 | <code>\risk{1}{1}{Example}{Example}{Example}</code> |
| `rkscenario` | `m m m m` | `label` (text, required) — Label.<br>`color` (text, required) — Color.<br>`value` (text, required) — Value.<br>`detail` (text, required) — Detail. | — | stable since 1.8.0 | <code>\rkscenario{Example}{Accent}{1}{Example}</code> |
| `selfloop` | `O{} m m` | `options` (options, optional=) — Options.<br>`state` (text, required) — State.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\selfloop[]{a}{Example}</code> |
| `sidebarrow` | `m m` | `label` (text, required) — Label.<br>`value` (text, required) — Value. | — | stable since 1.8.0 | <code>\sidebarrow{Example}{1}</code> |
| `skewarrow` | `m m m m` | `source_track` (text, required) — Source track.<br>`source_position` (text, required) — Source position.<br>`target_track` (text, required) — Target track.<br>`target_position` (text, required) — Target position. | — | stable since 1.0.0 | <code>\skewarrow{a}{Example}{b}{Example}</code> |
| `state` | `O{} m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\state[]{a}{Example}</code> |
| `stateat` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`x` (text, required) — X.<br>`y` (text, required) — Y.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\stateat[]{a}{1}{1}{Example}</code> |
| `step` | `m m` | `id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\step{a}{Example}</code> |
| `stepat` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`x` (text, required) — X.<br>`y` (text, required) — Y.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\stepat[]{a}{1}{1}{Example}</code> |
| `terminalstate` | `O{} m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\terminalstate[]{a}{Example}</code> |
| `terminalstateat` | `O{} m m m m` | `options` (options, optional=) — Options.<br>`id` (text, required) — Id.<br>`x` (text, required) — X.<br>`y` (text, required) — Y.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\terminalstateat[]{a}{1}{1}{Example}</code> |
| `transformarrow` | `m` | `label` (text, required) — Label. | — | stable since 1.0.0 | <code>\transformarrow{Example}</code> |
| `transition` | `O{} m m m` | `options` (options, optional=) — Options.<br>`source` (text, required) — Source.<br>`target` (text, required) — Target.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\transition[]{a}{b}{Example}</code> |
| `watermark` | `O{} m m m` | `options` (options, optional=) — Options.<br>`start` (text, required) — Start.<br>`end` (text, required) — End.<br>`label` (text, required) — Label. | — | stable since 1.0.0 | <code>\watermark[]{1}{1}{Example}</code> |

<!-- REPORTKIT-CONTRACT:END -->
