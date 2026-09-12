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

From a clone of this skill, initialize a separate report directory:

```bash
git clone https://github.com/iancwm/report-kit.git <skill-directory>
<skill-directory>/reportkit init <report-directory> --install-fonts
python3 -m venv <report-directory>/build/.venv
<report-directory>/build/.venv/bin/python -m pip install --require-hashes \
  -r <skill-directory>/toolchain/requirements.lock
<report-directory>/build/.venv/bin/python <skill-directory>/reportkit doctor \
  --require full-build
```

`reportkit init` refuses to run if `<report-directory>` resolves inside
`<skill-directory>` — pick a directory outside the clone. It scaffolds
`manuscript/`, `fragments/`, `assets/`, `figures/`, `build/`, `output/`, and a
`publication.yaml` stub without copying engine files. `--install-fonts` is
optional and installs the bundled Libertinus fonts into `TEXMFLOCAL`; it may
require system write permission. The pinned `toolchain/requirements.lock`
set supplies the Python dependencies for a full build. Trust the actual
`MODE:` line:

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

## Generated primitive contract

The exact generated primitive signatures live in [references/primitive-contract.md](references/primitive-contract.md).
Use `reportkit context --json` as the authoritative machine-readable contract.
