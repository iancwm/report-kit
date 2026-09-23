---
name: reportkit
description: Create polished technical or analytical PDF reports and slide decks with the bundled ReportKit LaTeX class, semantic diagrams, callouts, and matched Matplotlib charts. Use for a designed report, brief, or presentation PDF, not plain prose or a quick document.
---

# ReportKit

ReportKit produces evidence-led, reader-oriented technical reports. It combines a local LaTeX class, semantic callouts and diagrams, and a matched Python/Matplotlib chart theme.

Use it when the requested deliverable is a finished technical, analytical, evaluation, strategy, research-report, or executive-presentation PDF. Do not use it for an informal memo, generic prose, or any deliverable that does not need a designed PDF.

Git tags are the reproducible release identifiers. Check `reportkit.cls` when the class version itself matters.

For host-neutral automation, treat `reportkit context --json` as the
authoritative primitive and command contract. Use `reportkit docs --check
--json` as the drift gate; the version policy, exit classes, pinned toolchain,
and trust boundary are in
[references/agent-contract.md](references/agent-contract.md).
For a small context window, load `reportkit context --slice quickstart --json`
first, then request only the on-demand slice needed for the selected target.

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

### Presentations

`reportkit build` can also produce a Beamer-based 16:9 slide deck end to end: set `document.publication_type: presentation` and `document.theme: executive` in `publication.yaml`, then build a plain-Markdown manuscript as usual. Headings become frames (Pandoc's Beamer writer, `--slide-level=1`); `reportkit-presentation.sty` also exposes named slide compositions usable as fenced `reportkit` directives — see [`publication_pipeline/README.md`](publication_pipeline/README.md) for the directive syntax and [the presentation authoring contract](references/presentation-authoring.md) for composition selection.

Choose a composition by rhetorical role:

- `messageslide` is a sparse hero assertion: the assertion is the visual and supporting copy is brief. Keep its existing hero-message scale; do not use it as the default wrapper for a slide that needs a grid, process, comparison, or other substantial evidence.
- `assertionslide` is the standard working slide: one assertion, optional context/deck, and an evidence body. Its standard or compact assertion scale leaves the evidence canvas dominant. Use it for ordinary evidence-heavy slides.
- `evidenceslide` is the explicit `CLAIM` → `EVIDENCE` composition. Use it when that rhetorical separation is meaningful; it is not an alias for `assertionslide`.
- `titleslide` establishes document identity, `sectiondivider`/`appendixdivider` orient the audience between sections, and `closingslide` delivers a deliberate conclusion or call to action. These title, divider, and closing roles are separate from a normal working assertion.

Write assertions as claims rather than report-section titles: one line is ideal; two lines are acceptable and may use the compact assertion treatment; three lines should generally be rewritten or split. Never shrink body text to rescue an oversized assertion. Rewrite the assertion, split the slide, or choose a more suitable composition instead of adding a local font-size override.

The presentation refinement adds semantic dense layouts for 2×2 cards, 2×3 cards, three equal columns, and four ordered steps, plus restrained card variants (`plain`, `surface`, `accent-rail`, `numbered`, and `emphasis`). Use the supported composition-level API and theme-owned density tokens; do not recreate these layouts with per-card `fontsize`/`small` hacks. See [references/presentation-authoring.md](references/presentation-authoring.md) for the selection rules and native release-gate guidance.

For source-heavy endings, the supported `referenceslide`/`referenceitem` contract provides a compact heading, readable references, and an optional usage or limitation note. Keep short provenance in a source/footer line; put full references on the references slide. If the list does not fit, continue it on another references slide rather than reducing type below the legibility floor.

The stable `executive` theme is the supported consulting/strategy slide system; the `default` and `institutional-research` themes remain paged-only. It uses the bundled Libertinus Sans family for reproducible builds. Metadata, outline, meaningful links, and diagram alternatives are checked automatically; tagged PDF remains explicitly unsupported for any renderer. See [references/agent-contract.md](references/agent-contract.md), [references/repository-boundary.md](references/repository-boundary.md), [references/presentation-authoring.md](references/presentation-authoring.md), and the canonical `latex_templates/examples/executive-presentation/` fixture.

`reportkit context --json` is the authoritative capability and contract catalog, and `reportkit docs --check --json` is the documentation-drift gate. If a composition or card helper is added, update its owning source contract and rerun the supported drift command; do not hand-edit generated contract inventories. Documentation must distinguish the supported API from future roadmap capability; it must not imply that an absent capability is already available.
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

## Algorithms and code

Three primitives look superficially similar (a boxed reading unit with a small title) but answer different questions -- pick by what the reader needs, not by which one renders first to mind:

| Reader question | Use |
| --- | --- |
| What does the executable source actually say? | `codeblock` |
| What is the language-neutral control-flow logic of an algorithm? | `algorithmblock` |
| What relationships or decisions connect process steps? | `reportflow` or `reportstate` |

`codeblock` (`reportkit-code.sty`) is monospace, syntax-highlighted, and language-specific -- use it for real source. `algorithmblock` (`reportkit-algorithms.sty`) is proportional, language-neutral pseudocode built on `algorithmicx`/`algpseudocode`, never the floating `algorithm` package -- like every ReportKit diagram, it is a non-floating reading unit that stays with its introducing prose and may break across a page instead of drifting away. Keywords (`if`, `while`, `for`, `else`, `return`, ...) render in LinkBlue bold sans; statement text stays in Ink, set in the normal text/math font, not monospace. `reportflow`/`reportstate` show the *relationships between* steps (ownership, sequencing, retry/failure paths) rather than one step's own internal logic -- use them for a process diagram, not for an algorithm's pseudocode.

```latex
\begin{algorithmblock}[label={alg:two-pointer}]{Two-pointer elimination}
  \AlgorithmInput{Heights $h_0,\ldots,h_{n-1}$}
  \AlgorithmOutput{Maximum container area}
  \State $L \gets 0$
  \State $R \gets n-1$
  \While{$L < R$}
    \If{$h_L \le h_R$}
      \State $L \gets L+1$
    \Else
      \State $R \gets R-1$
    \EndIf
  \EndWhile
  \State \Return $best$
\end{algorithmblock}
```

`algorithmic` is opened and closed by `algorithmblock` itself -- do not write `\begin{algorithmic}`/`\end{algorithmic}` directly. Supported options are `label=` and `caption=` (rendered below the pseudocode using the same caption/provenance convention as `diagram`) plus an optional `linenumbers=<step>`; line numbers are off by default. `\AlgorithmInput`/`\AlgorithmOutput` render compact INPUT/OUTPUT metadata lines and are only valid inside `algorithmblock`, immediately after `\State` would otherwise begin.

## Algorithm and execution-state visuals

`algorithmblock` shows an algorithm's control-flow logic; the primitives in `reportkit-algorithm-viz.sty` show the *state of the data* while that algorithm runs -- values, indices, pointers, active regions, and how state changes between steps. Reach for one of these instead of a generic `reportflow`/`reportnetwork` diagram whenever the reader needs to see a data structure's contents, not a process's stages:

| Reader question | Primitive |
| --- | --- |
| Where are the pointers in this array? | `arraystate` |
| Which range is currently active? | `arraystate` / `windowstate` |
| What is currently on the stack or in the queue? | `stackstate` / `queuestate` |
| Which graph nodes have been visited or are queued? | `graphstate` |
| Which grid cells have been reached? | `gridstate` |
| Which DAG nodes can execute, and how many dependencies remain? | `dagstate` |
| What is currently in the heap? | `heapstate` |
| Which intervals overlap or have been merged? | `intervalstate` |
| Which DP states are known, current, or a dependency? | `dptable` |
| How does state change from one iteration to the next? | `algorithmtrace` |

Every state-aware primitive shares one vocabulary of nine semantic states, set via `state=`: `current`, `active`, `candidate`, `frontier`, `visited`, `resolved`, `discarded`, `blocked`, `unseen`. Each carries a distinct border weight or line style in addition to its color, so meaning survives grayscale printing -- never the only signal for a state is its fill color.

```latex
\begin{diagram}[type=array,caption={Two-pointer scan.},description={A sorted array with left and right pointers bounding the active range.}]
\begin{arraystate}
  \cell{-4}
  \cell{-1}
  \cell{-1}
  \cell{0}
  \cell{1}
  \cell{2}
  \pointer[below]{L}{2}
  \pointer[below]{R}{5}
  \range[state=active]{2}{5}
\end{arraystate}
\end{diagram}
```

`arraystate` is the foundational primitive: `\cell[state=]{value}` appends a value (indices render automatically below row zero unless `indices=false`); `\pointer[above|below]{label}{index}` places a labelled cursor; `\range[state=][row=]{start}{end}` highlights an inclusive index span behind the row; `\annotation{text}` stacks a caption-style line below the array. Multi-row alignment (prefix sums, before/after arrays, DP rows) uses `\row{name}{v1,v2,...}` instead of bare `\cell` calls; `\pointer`/`\range`/`\annotation` then take `row=<name>` to target a specific row. Indices and ranges are zero-based.

`windowstate` is a thin composition over `arraystate` for sliding/moving contiguous regions: `\values{...}` declares the backing array, `\window{start}{end}` marks the active span with automatic left/right cursors, and `\entering{v}`/`\leaving{v}` annotate the incoming and outgoing values.

`algorithmtrace` composes ordered snapshots to show state evolving across steps -- the second highest-priority primitive after `arraystate`. Each `\snapshot{title}{content}` is a self-contained algorithm-state primitive (typically `arraystate` or `windowstate`), wrapping into a grid controlled by `columns=` (default 3):

Snapshot contents are normalized to the configured snapshot width so a wide
array or graph cannot overlap its neighboring step.

```latex
\begin{diagram}[type=trace,caption={Sliding-window advance.},description={Three ordered snapshots show the window advancing by one element.}]
\begin{algorithmtrace}[columns=3]
  \snapshot{Initial}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}
  \snapshot{Advance}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}
  \snapshot{Shrink}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}
\end{algorithmtrace}
\end{diagram}
```

Reading order is left to right, then top to bottom. ReportKit produces static documents -- `algorithmtrace` is the temporal-explanation mechanism; do not attempt animation.

`stackstate` (LIFO) and `queuestate` (FIFO), in `reportkit-algorithm-linear.sty`, share one internal linear-container renderer and the same `\cell`/pointer chrome as `arraystate`. `\push[state=]{value}` grows a `stackstate` upward, with the top entry visually marked; `\enqueue[state=]{value}` grows a `queuestate` rightward, with dequeue/enqueue ends marked:

```latex
\begin{diagram}[type=stack,caption={Bracket matching.},description={A stack of three open brackets with the most recent one current.}]
\begin{stackstate}
  \push{(}
  \push{[}
  \push[state=current]{<}
\end{stackstate}
\end{diagram}
```

`graphstate` and `gridstate`, in `reportkit-algorithm-graph.sty`, represent traversal state rather than static structure (that's `reportnetwork`'s job). `\graphnode[state=]{id}{label}` auto-lays-out nodes on a grid (`columns=` to control wrapping); `\graphedge{a}{b}` draws a directed edge between node ids. `\begin{gridstate}[rows=][columns=]` then `\gridcell{row}{col}[state=]` places a state-only cell at 1-based grid coordinates, for flood-fill/matrix-DP/maze-traversal explanations. Neither builds a dedicated BFS/DFS primitive -- pair `graphstate` with `queuestate` (BFS) or `stackstate` (DFS) in the same `diagram` or `algorithmtrace` snapshot instead, per the spec's composition-before-specialization principle:

```latex
\begin{diagram}[type=graph,caption={BFS frontier.},description={A start node visited, its current node, and two frontier nodes discovered but not yet processed.}]
\begin{graphstate}[columns=2]
  \graphnode[state=visited]{A}{Start}
  \graphnode[state=current]{B}{Current}
  \graphnode[state=frontier]{C}{Queued}
  \graphedge{A}{B}
  \graphedge{B}{C}
\end{graphstate}
\end{diagram}
```

`intervalstate` and `heapstate`, in `reportkit-algorithm-order.sty`, cover priority and ordering structures. `\interval[state=]{label}{start}{end}` draws a labelled bar on a shared numeric axis, one per declared interval; `\merged[state=]{start}{end}` (default `state=resolved`) draws a summary bar for a combined span:

```latex
\begin{diagram}[type=interval,caption={Merge intervals.},description={Three intervals on a shared axis, with the first and second overlapping and merged into one resolved span.}]
\begin{intervalstate}
  \interval[state=candidate]{A}{1}{4}
  \interval[state=active]{B}{3}{6}
  \interval[state=candidate]{C}{8}{10}
  \merged{1}{6}
\end{intervalstate}
\end{diagram}
```

`heapstate` shows a heap's backing array and its derived binary-tree view together -- authors declare `\values{v1,v2,...}` once and the tree layout is computed automatically from each value's array index (no manual tree coordinates); `\current{index}` marks the array cell and its mirrored tree node.

`dptable`, in `reportkit-algorithm-dp.sty`, represents dynamic-programming state at 1-based `(row, col)` coordinates like a plain grid, plus DP-specific cell markers: `\dpcell{row}{col}[state=]{value}` places a value, and `\currentcell{row}{col}`/`\dependencycell{row}{col}`/`\solvedcell{row}{col}` overlay the current/dependency/solved treatment on an already-placed cell (any call order works -- they draw a background-layer highlight, the same technique `arraystate`'s `\range` uses):

```latex
\begin{diagram}[type=dp,caption={Edit-distance table.},description={A four-by-four dynamic-programming table with one cell marked current and two of its dependency cells marked.}]
\begin{dptable}[rows=4,columns=4]
  \dpcell{1}{1}{0}
  \dpcell{1}{2}{1}
  \dpcell{2}{1}{1}
  \dpcell{2}{2}{0}
  \currentcell{2}{2}
  \dependencycell{1}{2}
  \dependencycell{2}{1}
\end{dptable}
\end{diagram}
```

`dagstate`, appended to `reportkit-algorithm-graph.sty` alongside `graphstate`, extends graph-state visualization for dependency algorithms (topological sort, DAG scheduling, dependency resolution). `\dagnode[indegree=][state=]{id}{label}` places a node with a small indegree badge; `\dependency{a}{b}` draws a dependency edge (reusing the same `rk edge dependency` style `reportnetwork` uses); `\readyqueue{id1,id2,...}` marks already-placed nodes as ready to execute:

```latex
\begin{diagram}[type=dag,caption={Data-pipeline dependency graph.},description={Three pipeline stages with raw ingest ready to execute and two downstream stages waiting on it.}]
\begin{dagstate}[columns=3]
  \dagnode[indegree=0]{raw}{Raw ingest}
  \dagnode[indegree=1]{clean}{Clean}
  \dagnode[indegree=1]{features}{Feature engineering}
  \dependency{raw}{clean}
  \dependency{clean}{features}
  \readyqueue{raw}
\end{dagstate}
\end{diagram}
```

Several of these primitives' spec-proposed state names aren't literally part of the shared nine-word vocabulary; each maps onto the closest real state instead of inventing new ones: intervalstate's "overlap"/"merged" become `active`/`resolved`; dptable's "solved"/"dependency"/"uncomputed" become `resolved`/`candidate`/the plain unmarked cell; dagstate's "ready"/"processed" become `frontier`/`resolved` (`blocked` is already shared). Gridstate likewise uses the shared vocabulary; a domain concept such as a pathfinding target should be conveyed with the closest state plus an explicit label or description.

P3 adds domain-specific extensions for the cases where the general state
grammar needs one more semantic relationship:

* `joinstate` shows two keyed inputs feeding a hash/index, matched keys, and
  joined output rows. Use `\joininput{left|right}{label}`,
  `\hashbucket{key}{values}`, `\joinmatch{key}{result}`, and
  `\joinoutput{label}`. `\joinunmatched{side}{key}` marks an excluded key
  with the shared `discarded` state.
* `unionfindstate` shows a disjoint-set forest. Declare `\ufnode`, connect
  parent relationships with `\parent{child}{parent}`, show a merge with
  `\union{left}{right}`, and mark a representative lookup with
  `\findpath{from}{to}`. Layout is automatic and all node state options use
  the shared nine-word vocabulary.
* `linkedliststate` shows singly linked nodes and next pointers. Declare
  `\listnode`, connect nodes with `\nextlink`, and optionally mark `\head`
  and `\tail`; HEAD, TAIL, and NULL labels are rendered explicitly. Set
  `direction=vertical` when a tall list reads better than a horizontal one.
* `recursiontree` extends the tree-like algorithm grammar with
  `\recursionnode[arguments={...},memoized]{id}{call}{return}` and
  `\recursionedge{parent}{child}`. Arguments, return values, and the
  MEMOIZED marker remain textual, while `state=current` and the other shared
  states show execution status.

These are compositions, not replacements for the general primitives:
`joinstate` is for keyed data movement, `unionfindstate` for component
membership, `linkedliststate` for next-pointer structure, and `recursiontree`
for call/return state. Put every one inside the standard `diagram` wrapper
with a plain-language `description=`.

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
- `latex_templates/reportkit-algorithm-viz.sty`: arraystate, windowstate, and algorithmtrace (see "Algorithm and execution-state visuals" above)
- `latex_templates/reportkit-algorithm-linear.sty`: stackstate and queuestate
- `latex_templates/reportkit-algorithm-graph.sty`: graphstate, gridstate, and dagstate
- `latex_templates/reportkit-algorithm-order.sty`: intervalstate and heapstate
- `latex_templates/reportkit-algorithm-dp.sty`: dptable
- `latex_templates/reportkit-algorithm-p3.sty`: joinstate, unionfindstate, linkedliststate, and recursiontree

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
./reportkit render --source-root <publication-project> --pages 1,3-4 --dpi 150
./reportkit inspect --source-root <publication-project>
```

Read the `.log` before retrying a failed compile. Use `reportkit render` to
inspect only the pages or slides relevant to the change; its output includes
an atomic page directory and `pages.json` manifest. Inspect every rendered
page for clipped text, overlapping labels, broken arrows, bad page breaks,
missing figures, and meanings conveyed only by colour. A successful TeX exit
code alone is not completion.

When modifying ReportKit itself, run its regression suite:

```bash
bash scripts/acceptance_check.sh
```

The suite compiles the backwards-compatibility and visual-grammar fixtures with `pdflatex`, the institutional-research/equity-research fixture with `lualatex`, and checks Python imports; each engine check warns and skips (not blocking) if that engine is not installed. For a known failure or a surprising diagnostic result, consult [references/known-fixes.md](references/known-fixes.md) before changing implementation.

## Generated primitive contract

The exact generated primitive signatures live in [references/primitive-contract.md](references/primitive-contract.md).
Use `reportkit context --json` as the authoritative machine-readable contract.
