# Institutional-research theme + equity-research publication type

Full spec:
[docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](../docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md).
Working example:
[latex_templates/examples/equity-research/](../latex_templates/examples/equity-research/)
(a fictional four-page publication -- front page, analysis exhibits,
risk/reward, financial model -- built from nothing but the primitives
below; read its `report.tex` before writing a new one).

This is a **theme** (`institutional-research`: typography, geometry,
palette, chart styling) composed with a **publication type**
(`equity-research`: front page, rating strip, exhibits, financial-model
and risk/reward pages). They vary independently -- `theme=
institutional-research` alone gives quieter, denser Letter-format prose
with no stock-rating primitives; a future `publication-type=
strategy-report` could reuse this theme without exposing them either.
`publication-type=equity-research` requires a theme that defines the
type-scale tokens below (today, only `institutional-research`) and fails
at load time, not at first use, if that requirement is not met.

## Selecting it

```latex
\documentclass[
  theme=institutional-research,
  publication-type=equity-research
]{reportkit}
```

**Requires `lualatex`**, not `pdflatex` -- the theme loads Google Sans via
`fontspec`. `reportkit check`/`reportkit build` refuse to proceed if
`document.engine` isn't `lualatex` while `document.theme` is
`institutional-research` (config.py's `theme_engine_conflict()`); the
theme file repeats the same guard at the TeX level for anyone invoking
`lualatex`/`pdflatex` directly. In `publication.yaml`:

```yaml
document:
  engine: lualatex
  theme: institutional-research
  publication_type: equity-research
  paper: letter
theme:
  font_policy: fallback   # or: strict
```

`font_policy: fallback` (the default) walks Google Sans -> Inter -> Noto
Sans -> TeX Gyre Heros and warns which one it used; `strict` fails the
build if Google Sans specifically cannot be resolved. The target-aware
pipeline now propagates `document.theme` and `document.publication_type` into
the staged class options. The Markdown/fragments path for the worked equity
fixture can be built with:

```bash
<report-kit-clone>/reportkit build \
  --source-root <report-kit-clone>/latex_templates/examples/equity-research \
  --output-root <report-kit-clone>/build/equity-research
```

`report.tex` remains the direct-TeX compatibility witness, while the
`manuscript/` and `fragments/` files exercise the normal pipeline. Theme font
settings and the constrained brand surface resolve through one effective-theme
record; the pipeline materializes configured values into its generated TeX
override file and records the corresponding hashes in `build-report.json`.
The current registry keeps brand overrides opt-in, and no registered theme
currently enables them.

## Exhibit-led authoring

The theme is exhibit-led, not card-led. When writing for it:

- Prefer an analytical exhibit over a decorative callout when quantitative
  evidence exists.
- Exhibit titles should state the **finding** the reader should draw
  ("Platform mix is rising as a share of total revenue"), not just name a
  metric ("Revenue Mix").
- Do not place ordinary paragraphs inside boxes.
- Sidebars (`analystblock`/`marketdatablock`/`estimatesblock`) hold
  reference information, not the core thesis -- use the main column
  (`researchmain`) for the research argument.
- Do not force a visual onto every section; deliberate whitespace is
  fine.
- Avoid dashboard layouts of repeated, equally weighted cards.
- Main narrative prose is visually more prominent than metadata: body
  text is 10.7pt/14.6pt; sidebar/metadata text is 7.6pt/9.5pt
  (`\rkbodysize` vs `\rksidebarsize`) -- never make sidebar text carry the
  argument.
- Semantic callouts (`principle`, `decisionpoint`, `redflag`, ...) still
  work under this theme; they restyle to a thin left rule and a small
  uppercase label instead of a colored box, per the theme's quieter
  chrome -- use them for their existing semantic meaning, not decoration.

## Primitive reference

Source: `latex_templates/publication_types/reportkit-equity-research.sty`
(the definitive argument reference; read it before using a primitive not
covered here).

| Primitive | Purpose |
| --- | --- |
| `researchfrontpage` | Front-page wrapper (page style, top spacing) |
| `\researchkicker{sector / region}` | Small accent-colored sector/geography line |
| `\researchheadline{...}` | The main finding, in one sentence |
| `\researchdeck{...}` | One-paragraph summary below the headline |
| `ratingstrip` / `\ratingitem{label}{value}` | Horizontal rating/PT/current-price strip -- no boxed KPI; wrap a value in `\color{Accent}` for the one allowed accent use |
| `whatschanged` / `\change{label}{from}{to}` | Compact estimate-revision summary |
| `researchmain` / `researchsidebar` | ~68%/28% two-column body. **`\end{researchmain}` and `\begin{researchsidebar}` must have no blank line between them in the source** -- a blank line starts a new paragraph and breaks the sidebar out from beside the main column to below it |
| `analystblock` / `marketdatablock` / `estimatesblock` | Sidebar contexts (small font, hairline separators); use `\sidebarrow{label}{value}` for simple rows, a `tabularx` for multi-column data |
| `exhibit[title=,source=,label=,number=]` | The core primitive -- auto-numbered (`number=` overrides the *displayed* number only); warns if `title=` is missing |
| `fullwidthexhibit` | Marks one exhibit as deliberately full-width inside a page otherwise composed of `exhibitpair`/`exhibitgrid` |
| `exhibitpair` | Exactly two `\exhibitpane{...}` |
| `exhibitgrid[columns=N]` / `\exhibitpane[width=]{...}` | N equal columns; pane widths are computed only for `columns=1/2/3` -- **`columns=4` or higher (or an uneven split) needs an explicit `width=<fraction>\linewidth` on every `\exhibitpane`**, there is no computed default |
| `financialtable` | Typographic context for a table (institutional font/spacing) -- open a `tabularx`/`tabular` with `booktabs` rules and the `Y`/`Z`/`C` column types inside it |
| `financialmodelpage` | Locally drops to 7.6pt/9pt dense table type for a model page; reverts at `\end{}` |
| `\rksubheading{...}` | Generic accent-kicker heading (Investment Thesis / Key Debates / Catalysts / Risks, or any other) |
| `\bullcase{value}{text}` / `\basecase{value}{text}` / `\bearcase{value}{text}` | The fixed Bull/Base/Bear triad, colored `SeriesGold`/`Accent`/`BearRed` |

No `\riskrewardchart` LaTeX macro exists on purpose -- generate that chart
in Python (below) and embed it like any other figure:
`\begin{exhibit}[...]\includegraphics{...}\end{exhibit}`.

Twelve `\rk...size` type-scale commands (`\rkmastheadsize` ...
`\rkdisclosuresize`, spec section 5) are available directly if a
composition needs a size the primitives above don't already apply --
prefer an existing primitive first.

## Charts (`reportkit_viz.py`)

```python
import reportkit_viz as rkv

rkv.apply_theme("institutional-research")   # switches colors, fonts, TEXT_WIDTH_IN,
                                             # FIGURE_SIZES, and mathtext for every
                                             # chart drawn after this call
fig, ax = rkv.risk_reward_chart(
    price_history, bear=135, base=245, bull=310, current=182.50,
    value_formatter=rkv.currency_formatter(),
)
rkv.save_figure(fig, "figures/risk_reward")
```

`apply_theme()` reassigns this module's color/geometry globals (`INK`,
`FIGURE_SIZES`, ...), so every existing chart function
(`bar_chart`, `timeseries`, `waterfall_chart`, ...) becomes theme-aware
automatically -- there is no separate institutional-theme chart API.
For paged themes, `FIGURE_SIZES` gains `half` (sized for an `exhibitpair`
pane) and `dominant` (an alias of the pre-existing `wide`). Slide-only themes
use their own `slide-*` slots instead.
`risk_reward_chart()` is the Python-side counterpart to the
Bull/Base/Bear primitives above; there is no dedicated stacked-bar
helper yet, so a platform-mix-style chart is ordinary Matplotlib code
built on `new_figure()`/`style_axes()`/`legend_above()`/`DATA_COLORS` --
see `latex_templates/examples/equity-research/figures.py` for a worked
example of exactly that.

`python3 reportkit_viz.py check-theme --theme institutional-research`
validates the Python and LaTeX palettes stay in sync.

## QA

```bash
python3 latex_templates/examples/equity-research/figures.py
python3 scripts/visual_qa_equity_research.py
```

Requires `lualatex`, PyMuPDF, and NumPy; warns and exits 0 (non-blocking)
if any are missing, the same convention as `scripts/acceptance_check.sh`.
It compiles the four-page example, runs ReportKit's own log diagnostics
(overfull/underfull boxes, undefined references), renders every page to
PNG, and pixel-diffs against
`latex_templates/examples/equity-research/expected/` -- see that
directory's `README.md` before running `--update-expected`.
`scripts/acceptance_check.sh` separately compiles a fast, compact
smoke-test fixture
(`latex_templates/examples/institutional_equity_acceptance_test.tex`)
with `lualatex` on every run, alongside its existing `pdflatex` fixtures.

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent contract metadata. Do not edit it by hand.

### Callout primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `assumption` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{assumption}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{assumption}</code> |
| `decisionpoint` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{decisionpoint}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{decisionpoint}</code> |
| `deliverablenote` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{deliverablenote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{deliverablenote}</code> |
| `evidence` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{evidence}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{evidence}</code> |
| `evidencenote` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{evidencenote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{evidencenote}</code> |
| `execsummary` | `` | — | — | stable since 1.0.0 | <code>\begin{execsummary}&lt;br&gt;Example content.&lt;br&gt;\end{execsummary}</code> |
| `limitation` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{limitation}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{limitation}</code> |
| `limitationnote` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{limitationnote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{limitationnote}</code> |
| `metric` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.0.0 | <code>\begin{metric}{Example}{1}&lt;br&gt;Example content.&lt;br&gt;\end{metric}</code> |
| `principle` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{principle}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{principle}</code> |
| `redflag` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{redflag}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{redflag}</code> |
| `researchproblem` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{researchproblem}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{researchproblem}</code> |
| `tip` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{tip}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{tip}</code> |
| `tipnote` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\begin{tipnote}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{tipnote}</code> |

### Figure primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `algorithmtrace` | `O{}` | `options` (options, optional=) — columns=, snapshot width=, snapshot height=, and gap= layout keys. | Declare two to eight snapshots. | experimental since 1.10.0 | <code>\begin{diagram}[type=trace,caption={Sliding-window advance.},description={Three ordered snapshots show the window advancing by one element.}]&lt;br&gt;\begin{algorithmtrace}[columns=3]&lt;br&gt;\snapshot{Initial}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}&lt;br&gt;\snapshot{Advance}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}&lt;br&gt;\snapshot{Shrink}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\end{arraystate}}&lt;br&gt;\end{algorithmtrace}&lt;br&gt;\end{diagram}</code> |
| `arraystate` | `O{}` | `options` (options, optional=) — Cell width, row height, and indices= layout keys. | Column and row indices are zero-based. | experimental since 1.10.0 | <code>\begin{diagram}[type=array,caption={Two-pointer scan.},description={A sorted array with left and right pointers bounding the active range.}]&lt;br&gt;\begin{arraystate}&lt;br&gt;\cell{-4}&lt;br&gt;\cell{-1}&lt;br&gt;\cell{-1}&lt;br&gt;\cell{0}&lt;br&gt;\cell{1}&lt;br&gt;\cell{2}&lt;br&gt;\pointer[below]{L}{2}&lt;br&gt;\pointer[below]{R}{6}&lt;br&gt;\range[state=active]{2}{6}&lt;br&gt;\end{arraystate}&lt;br&gt;\end{diagram}</code> |
| `capabilitymap` | `O{}` | `options` (options, optional=) — Capability-map layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Capability map.},description={Two domains group four capabilities.}]&lt;br&gt;\begin{capabilitymap}&lt;br&gt;\domain{Data}{Acquire,Govern}&lt;br&gt;\domain{Analytics}{Model,Explain}&lt;br&gt;\end{capabilitymap}&lt;br&gt;\end{diagram}</code> |
| `causalloop` | `O{}` | `options` (options, optional=) — Causal-loop layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Capacity loop.},description={Demand, investment, and capacity form a feedback loop.}]&lt;br&gt;\begin{causalloop}&lt;br&gt;\causalnode{demand}{Demand}&lt;br&gt;\causalnode{investment}{Investment}&lt;br&gt;\causalnode{capacity}{Capacity}&lt;br&gt;\causaledge{demand}{investment}{+}&lt;br&gt;\causaledge{investment}{capacity}{+}&lt;br&gt;\causaledge{capacity}{demand}{-}&lt;br&gt;\end{causalloop}&lt;br&gt;\end{diagram}</code> |
| `continuum` | `O{}` | `options` (options, optional=) — Endpoint labels and layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Operating continuum.},description={Two positions between centralized and distributed.}]&lt;br&gt;\begin{continuum}[left={Centralized},right={Distributed}]&lt;br&gt;\marker{Team A}{.3}&lt;br&gt;\marker{Team B}{.7}&lt;br&gt;\end{continuum}&lt;br&gt;\end{diagram}</code> |
| `dagstate` | `O{}` | `options` (options, optional=) — columns=, x spacing=, and y spacing= automatic grid-layout keys, as graphstate. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=dag,caption={Data-pipeline dependencies.},description={Three pipeline stages: the raw stage is ready with indegree zero, the clean stage depends on raw, and the features stage depends on clean.}]&lt;br&gt;\begin{dagstate}&lt;br&gt;\dagnode[indegree=0]{raw}{Raw}&lt;br&gt;\dagnode[indegree=1]{clean}{Clean}&lt;br&gt;\dagnode[indegree=1]{features}{Features}&lt;br&gt;\dependency{raw}{clean}&lt;br&gt;\dependency{clean}{features}&lt;br&gt;\readyqueue{raw}&lt;br&gt;\end{dagstate}&lt;br&gt;\end{diagram}</code> |
| `dptable` | `O{}` | `options` (options, optional=) — rows= and columns= (required) plus cell size= layout keys. | rows= and columns= must be provided. | experimental since 1.10.0 | <code>\begin{diagram}[type=dp,caption={Edit distance.},description={A four by five dynamic-programming table with the current cell and its two dependency cells marked.}]&lt;br&gt;\begin{dptable}[rows=4,columns=5]&lt;br&gt;\dpcell{1}{1}{0}&lt;br&gt;\dpcell{3}{4}{2}&lt;br&gt;\currentcell{3}{4}&lt;br&gt;\dependencycell{2}{4}&lt;br&gt;\dependencycell{3}{3}&lt;br&gt;\end{dptable}&lt;br&gt;\end{diagram}</code> |
| `evidencestack` | `O{}` | `options` (options, optional=) — Evidence-stack layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Evidence stack.},description={Three tiers increase in rigor.}]&lt;br&gt;\begin{evidencestack}&lt;br&gt;\evidencetier{Credential}&lt;br&gt;\evidencetier{Project}&lt;br&gt;\evidencetier{Measured impact}&lt;br&gt;\end{evidencestack}&lt;br&gt;\end{diagram}</code> |
| `graphstate` | `O{}` | `options` (options, optional=) — columns=, x spacing=, and y spacing= automatic grid-layout keys. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=graph,caption={BFS frontier.},description={A start node has been visited, its current neighbor is being processed, one neighbor is queued as frontier, and one neighbor is unseen.}]&lt;br&gt;\begin{graphstate}&lt;br&gt;\graphnode[state=visited]{A}{Start}&lt;br&gt;\graphnode[state=current]{B}{Current}&lt;br&gt;\graphnode[state=frontier]{C}{Queued}&lt;br&gt;\graphnode[state=unseen]{D}{Unseen}&lt;br&gt;\graphedge{A}{B}&lt;br&gt;\graphedge{B}{C}&lt;br&gt;\graphedge{B}{D}&lt;br&gt;\end{graphstate}&lt;br&gt;\end{diagram}</code> |
| `gridstate` | `O{}` | `options` (options, optional=) — rows= and columns= (required) plus cell size= layout keys. | rows= and columns= must be provided. | experimental since 1.10.0 | <code>\begin{diagram}[type=grid,caption={Flood fill.},description={A four by five grid with a flood-fill frontier expanding from the top-left corner.}]&lt;br&gt;\begin{gridstate}[rows=4,columns=5]&lt;br&gt;\gridcell{1}{1}[state=visited]&lt;br&gt;\gridcell{1}{2}[state=current]&lt;br&gt;\gridcell{2}{2}[state=frontier]&lt;br&gt;\gridcell{3}{3}[state=blocked]&lt;br&gt;\end{gridstate}&lt;br&gt;\end{diagram}</code> |
| `heapstate` | `O{}` | `options` (options, optional=) — cell width=, node spacing=, level height=, and tree gap= layout keys. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=heap,caption={A small max-heap.},description={A backing array of five values paired with its binary-tree view; the root is marked current.}]&lt;br&gt;\begin{heapstate}&lt;br&gt;\values{10,9,8,5,3}&lt;br&gt;\current{0}&lt;br&gt;\end{heapstate}&lt;br&gt;\end{diagram}</code> |
| `intervalstate` | `O{}` | `options` (options, optional=) — unit width= and row height= layout keys. | Each \interval or \merged call renders on its own row, in declaration order; overlap is not auto-detected. | experimental since 1.10.0 | <code>\begin{diagram}[type=interval,caption={Merge overlapping intervals.},description={Three intervals on a shared axis, two of which overlap, followed by their merged summary span.}]&lt;br&gt;\begin{intervalstate}&lt;br&gt;\interval[state=candidate]{A}{1}{4}&lt;br&gt;\interval[state=active]{B}{3}{6}&lt;br&gt;\interval[state=candidate]{C}{8}{10}&lt;br&gt;\merged{1}{6}&lt;br&gt;\end{intervalstate}&lt;br&gt;\end{diagram}</code> |
| `joinstate` | `O{}` | `options` (options, optional=) — width=, row spacing=, and input spacing= layout keys. | At least one left and one right input declaration are required. | experimental since 1.10.0 | <code>\begin{diagram}[type=join,caption={Hash join.},description={Two input relations feed a central hash index; matching keys produce joined output rows.}]&lt;br&gt;\begin{joinstate}&lt;br&gt;\joininput[side=left]{orders}{Orders}&lt;br&gt;\joininput[side=right]{customers}{Customers}&lt;br&gt;\hashbucket[state=active]{customer_id}{C42,C73}&lt;br&gt;\joinmatch{customer_id}{C42 -&gt; joined row}&lt;br&gt;\joinoutput{Joined rows}&lt;br&gt;\end{joinstate}&lt;br&gt;\end{diagram}</code> |
| `linkedliststate` | `O{}` | `options` (options, optional=) — direction=horizontal&#124;vertical and spacing= layout keys. | At least one listnode declaration is required. | experimental since 1.10.0 | <code>\begin{diagram}[type=linked-list,caption={Linked-list traversal.},description={Three linked nodes run from HEAD to TAIL and terminate at NULL; the middle node is current.}]&lt;br&gt;\begin{linkedliststate}&lt;br&gt;\listnode{a}{A}&lt;br&gt;\listnode[state=current]{b}{B}&lt;br&gt;\listnode{c}{C}&lt;br&gt;\nextlink{a}{b}&lt;br&gt;\nextlink{b}{c}&lt;br&gt;\head{a}&lt;br&gt;\tail{c}&lt;br&gt;\end{linkedliststate}&lt;br&gt;\end{diagram}</code> |
| `maturitymodel` | `O{}` | `options` (options, optional=) — Maturity layout and current-stage keys. | Declare four to six stages. | stable since 1.0.0 | <code>\begin{diagram}[caption={Maturity progression.},description={Four ordered maturity stages.}]&lt;br&gt;\begin{maturitymodel}[current={Managed}]&lt;br&gt;\stage{Ad hoc}{Local}&lt;br&gt;\stage{Defined}{Common}&lt;br&gt;\stage{Managed}{Measured}&lt;br&gt;\stage{Optimized}{Improving}&lt;br&gt;\end{maturitymodel}&lt;br&gt;\end{diagram}</code> |
| `queuestate` | `O{}` | `options` (options, optional=) — spacing= layout key (horizontal pitch between items). | Items are declared in enqueue order; the first \enqueue call is the front (dequeue end) and the last is the rear (enqueue end). | experimental since 1.10.0 | <code>\begin{diagram}[type=queue,caption={BFS work queue.},description={A three-element FIFO work queue with the front node marked current, the dequeue end labelled on the left, and the enqueue end labelled on the right.}]&lt;br&gt;\begin{queuestate}&lt;br&gt;\enqueue[state=current]{A}&lt;br&gt;\enqueue{B}&lt;br&gt;\enqueue{C}&lt;br&gt;\end{queuestate}&lt;br&gt;\end{diagram}</code> |
| `recursiontree` | `O{}` | `options` (options, optional=) — columns=, x spacing=, y spacing=, and node width= layout keys. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=recursion,caption={Memoized recursion.},description={A recursive call tree shows arguments, returned values, and one memoized subproblem.}]&lt;br&gt;\begin{recursiontree}&lt;br&gt;\recursionnode[arguments={n=4},state=current]{f4}{fib}{3}&lt;br&gt;\recursionnode[arguments={n=3}]{f3}{fib}{2}&lt;br&gt;\recursionnode[arguments={n=2},memoized]{f2}{fib}{1}&lt;br&gt;\recursionedge{f4}{f3}&lt;br&gt;\recursionedge{f3}{f2}&lt;br&gt;\end{recursiontree}&lt;br&gt;\end{diagram}</code> |
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
| `stackstate` | `O{}` | `options` (options, optional=) — spacing= layout key (vertical pitch between items). | Items are declared in push order, oldest first; the last \push call is the stack top. | experimental since 1.10.0 | <code>\begin{diagram}[type=stack,caption={Bracket matching.},description={A stack holding three unmatched opening brackets, with the most recently pushed bracket marked current and the stack top labelled.}]&lt;br&gt;\begin{stackstate}&lt;br&gt;\push{(}&lt;br&gt;\push{[}&lt;br&gt;\push[state=current]{&lt;}&lt;br&gt;\end{stackstate}&lt;br&gt;\end{diagram}</code> |
| `strategicpillars` | `O{}` | `options` (options, optional=) — Pillar layout keys. | Declare three to six pillars. | stable since 1.0.0 | <code>\begin{diagram}[caption={Strategic pillars.},description={Three pillars support an objective.}]&lt;br&gt;\begin{strategicpillars}[objective={Trusted reporting}]&lt;br&gt;\pillar{People}{Skills}&lt;br&gt;\pillar{Process}{Standards}&lt;br&gt;\pillar{Technology}{Platform}&lt;br&gt;\end{strategicpillars}&lt;br&gt;\end{diagram}</code> |
| `unionfindstate` | `O{}` | `options` (options, optional=) — columns=, x spacing=, and y spacing= automatic layout keys. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=union-find,caption={Union/find components.},description={Four nodes form two components; a parent pointer and a union operation join the components.}]&lt;br&gt;\begin{unionfindstate}&lt;br&gt;\ufnode{A}{A}&lt;br&gt;\ufnode{B}{B}&lt;br&gt;\ufnode{C}{C}&lt;br&gt;\ufnode[state=current]{D}{D}&lt;br&gt;\parent{B}{A}&lt;br&gt;\union{A}{C}&lt;br&gt;\findpath{D}{A}&lt;br&gt;\end{unionfindstate}&lt;br&gt;\end{diagram}</code> |
| `windowstate` | `O{}` | `options` (options, optional=) — Cell width and row height layout keys, as arraystate. | — | experimental since 1.10.0 | <code>\begin{diagram}[type=array,caption={Sliding window.},description={A six-element array with a window from index two to four.}]&lt;br&gt;\begin{windowstate}&lt;br&gt;\values{4,2,7,1,3,6}&lt;br&gt;\window{2}{4}&lt;br&gt;\entering{5}&lt;br&gt;\leaving{1}&lt;br&gt;\end{windowstate}&lt;br&gt;\end{diagram}</code> |

### Chart primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `bar_chart` | `data, *, horizontal=True, highlight=None, value_formatter=None, axis_label=None, sort=False, zero_line=True, size='full', title=None` | `data` (data, required)<br>`horizontal` (option, optional=True)<br>`highlight` (option, optional=None)<br>`value_formatter` (option, optional=None)<br>`axis_label` (option, optional=None)<br>`sort` (option, optional=False)<br>`zero_line` (option, optional=True)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.bar_chart({"A": 2, "B": 1})</code> |
| `bubble_matrix` | `data, *, x, y, xlabel, ylabel, size_column=None, label_column=None, group_column=None, reference_x=None, reference_y=None, quadrant_labels=None, x_formatter=None, y_formatter=None, size='full', title=None` | `data` (data, required)<br>`x` (option, required)<br>`y` (option, required)<br>`xlabel` (option, required)<br>`ylabel` (option, required)<br>`size_column` (option, optional=None)<br>`label_column` (option, optional=None)<br>`group_column` (option, optional=None)<br>`reference_x` (option, optional=None)<br>`reference_y` (option, optional=None)<br>`quadrant_labels` (option, optional=None)<br>`x_formatter` (option, optional=None)<br>`y_formatter` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>data = pd.DataFrame({"x":[1],"y":[2]}); fig, ax = rkv.bubble_matrix(data, x="x", y="y", xlabel="X", ylabel="Y")</code> |
| `distribution` | `values, *, bins='fd', xlabel=None, x_formatter=None, reference=None, density=False, size='full', title=None` | `values` (data, required)<br>`bins` (option, optional='fd')<br>`xlabel` (option, optional=None)<br>`x_formatter` (option, optional=None)<br>`reference` (option, optional=None)<br>`density` (option, optional=False)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.distribution([1, 2, 2, 3])</code> |
| `donut_chart` | `data, *, title=None, size='sidebar', colors=None` | `data` (data, required)<br>`title` (option, optional=None)<br>`size` (option, optional='sidebar')<br>`colors` (option, optional=None) | Use two to four proportional slices. | stable since 1.0.0 | <code>fig, ax = rkv.donut_chart({"Core": 70, "Other": 30})</code> |
| `drawdown_chart` | `drawdown, *, ylabel='Drawdown', y_formatter='percent', size='full', title=None` | `drawdown` (data, required)<br>`ylabel` (option, optional='Drawdown')<br>`y_formatter` (option, optional='percent')<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.drawdown_chart(pd.Series([0, -0.1, -0.05]))</code> |
| `heatmap` | `matrix, *, row_labels=None, col_labels=None, center=0.0, vmin=None, vmax=None, annotate=False, annotation_format='.2f', cbar_label=None, size='square', title=None` | `matrix` (data, required)<br>`row_labels` (option, optional=None)<br>`col_labels` (option, optional=None)<br>`center` (option, optional=0.0)<br>`vmin` (option, optional=None)<br>`vmax` (option, optional=None)<br>`annotate` (option, optional=False)<br>`annotation_format` (option, optional='.2f')<br>`cbar_label` (option, optional=None)<br>`size` (option, optional='square')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.heatmap([[1, 2], [3, 4]])</code> |
| `risk_reward_chart` | `price_history, *, bear, base, bull, current=None, bear_label='Bear', base_label='Base', bull_label='Bull', value_formatter=None, ylabel='Share price ($)', xlabel=None, size='full', title=None` | `price_history` (data, required)<br>`bear` (option, required)<br>`base` (option, required)<br>`bull` (option, required)<br>`current` (option, optional=None)<br>`bear_label` (option, optional='Bear')<br>`base_label` (option, optional='Base')<br>`bull_label` (option, optional='Bull')<br>`value_formatter` (option, optional=None)<br>`ylabel` (option, optional='Share price ($)')<br>`xlabel` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>prices = pd.Series([90, 100]); fig, ax = rkv.risk_reward_chart(prices, bear=80, base=110, bull=140)</code> |
| `scatter_plot` | `x, y, *, xlabel, ylabel, fit_line=False, x_formatter=None, y_formatter=None, reference_x=None, reference_y=None, size='full', title=None` | `x` (data, required)<br>`y` (option, required)<br>`xlabel` (option, required)<br>`ylabel` (option, required)<br>`fit_line` (option, optional=False)<br>`x_formatter` (option, optional=None)<br>`y_formatter` (option, optional=None)<br>`reference_x` (option, optional=None)<br>`reference_y` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.scatter_plot([1, 2], [2, 3], xlabel="X", ylabel="Y")</code> |
| `timeline_chart` | `tasks, *, label_column='label', start_column='start', end_column='end', workstream_column='workstream', milestone_column='milestone', current_date=None, scale='auto', size='full', title=None` | `tasks` (data, required)<br>`label_column` (option, optional='label')<br>`start_column` (option, optional='start')<br>`end_column` (option, optional='end')<br>`workstream_column` (option, optional='workstream')<br>`milestone_column` (option, optional='milestone')<br>`current_date` (option, optional=None)<br>`scale` (option, optional='auto')<br>`size` (option, optional='full')<br>`title` (option, optional=None) | A timeline supports at most 30 tasks. | stable since 1.0.0 | <code>fig, ax = rkv.timeline_chart([{"label":"Build","start":"2026 Q1","end":"2026 Q2"}])</code> |
| `timeseries` | `data, *, ylabel=None, xlabel=None, y_formatter=None, benchmark=None, reference_line=None, legend=True, size='full', title=None` | `data` (data, required)<br>`ylabel` (option, optional=None)<br>`xlabel` (option, optional=None)<br>`y_formatter` (option, optional=None)<br>`benchmark` (option, optional=None)<br>`reference_line` (option, optional=None)<br>`legend` (option, optional=True)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>data = pd.Series([1, 2, 3]); fig, ax = rkv.timeseries(data)</code> |
| `tornado_chart` | `sensitivities, *, base_case=0.0, low_column='low', high_column='high', label_column=None, value_formatter=None, xlabel=None, size='full', title=None` | `sensitivities` (data, required)<br>`base_case` (option, optional=0.0)<br>`low_column` (option, optional='low')<br>`high_column` (option, optional='high')<br>`label_column` (option, optional=None)<br>`value_formatter` (option, optional=None)<br>`xlabel` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.tornado_chart({"Price": (-10, 15), "Volume": (-5, 8)})</code> |
| `treemap_chart` | `data, *, label_column='label', value_column='value', parent_column=None, group_column=None, min_category_fraction=0.02, min_label_fraction=0.045, other_label='Other', value_formatter=None, size='full', title=None` | `data` (data, required)<br>`label_column` (option, optional='label')<br>`value_column` (option, optional='value')<br>`parent_column` (option, optional=None)<br>`group_column` (option, optional=None)<br>`min_category_fraction` (option, optional=0.02)<br>`min_label_fraction` (option, optional=0.045)<br>`other_label` (option, optional='Other')<br>`value_formatter` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.treemap_chart({"A": 60, "B": 40})</code> |
| `waterfall_chart` | `contributions, *, opening=0.0, opening_label='Opening', total_label='Total', subtotals=None, closing_total=None, value_formatter=None, ylabel=None, size='full', title=None` | `contributions` (data, required)<br>`opening` (option, optional=0.0)<br>`opening_label` (option, optional='Opening')<br>`total_label` (option, optional='Total')<br>`subtotals` (option, optional=None)<br>`closing_total` (option, optional=None)<br>`value_formatter` (option, optional=None)<br>`ylabel` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.waterfall_chart({"Growth": 10, "Costs": -4})</code> |

### Composition primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `RKShortListing` | `O{}` | `options` (options, optional=) | — | stable since 1.0.0 | <code>\begin{RKShortListing}[]&lt;br&gt;Example content.&lt;br&gt;\end{RKShortListing}</code> |
| `algorithmblock` | `O{} m` | `options` (options, optional=) — Optional label= and caption= (and linenumbers=&lt;step&gt;) keys.<br>`title` (text, required) — Algorithm name, shown after ALGORITHM in the box header. | Do not open or close the algorithmic environment directly inside algorithmblock; algorithmblock opens and closes it.<br>Never floats; a long algorithm may break across a page instead of drifting away from its introducing prose. | stable since 1.0.0 | <code>\begin{algorithmblock}{Two-pointer elimination}&lt;br&gt;\AlgorithmInput{Heights $h_0,\ldots,h_{n-1}$}&lt;br&gt;\AlgorithmOutput{Maximum container area}&lt;br&gt;\State $best \gets 0$&lt;br&gt;\end{algorithmblock}</code> |
| `analystblock` | `` | — | — | stable since 1.8.0 | <code>\begin{analystblock}&lt;br&gt;Example content.&lt;br&gt;\end{analystblock}</code> |
| `diagram` | `O{}` | `options` (options, optional=) | — | stable since 1.0.0 | <code>\begin{diagram}[]&lt;br&gt;Example content.&lt;br&gt;\end{diagram}</code> |
| `estimatesblock` | `` | — | — | stable since 1.8.0 | <code>\begin{estimatesblock}&lt;br&gt;Example content.&lt;br&gt;\end{estimatesblock}</code> |
| `exhibit` | `O{}` | `options` (options, optional=) | — | stable since 1.8.0 | <code>\begin{exhibit}[]&lt;br&gt;Example content.&lt;br&gt;\end{exhibit}</code> |
| `exhibitgrid` | `O{}` | `options` (options, optional=) | An exhibit grid supports at most three columns. | stable since 1.8.0 | <code>\begin{exhibitgrid}[]&lt;br&gt;Example content.&lt;br&gt;\end{exhibitgrid}</code> |
| `exhibitpair` | `` | — | — | stable since 1.8.0 | <code>\begin{exhibitpair}&lt;br&gt;Example content.&lt;br&gt;\end{exhibitpair}</code> |
| `financialmodelpage` | `` | — | — | stable since 1.8.0 | <code>\begin{financialmodelpage}&lt;br&gt;Example content.&lt;br&gt;\end{financialmodelpage}</code> |
| `financialtable` | `` | — | — | stable since 1.8.0 | <code>\begin{financialtable}&lt;br&gt;Example content.&lt;br&gt;\end{financialtable}</code> |
| `fullwidthexhibit` | `` | — | — | stable since 1.8.0 | <code>\begin{fullwidthexhibit}&lt;br&gt;Example content.&lt;br&gt;\end{fullwidthexhibit}</code> |
| `marketdatablock` | `` | — | — | stable since 1.8.0 | <code>\begin{marketdatablock}&lt;br&gt;Example content.&lt;br&gt;\end{marketdatablock}</code> |
| `outputblock` | `` | — | — | stable since 1.0.0 | <code>\begin{outputblock}&lt;br&gt;Example content.&lt;br&gt;\end{outputblock}</code> |
| `ratingstrip` | `o` | `item_count` (options, optional) | — | stable since 1.8.0 | <code>\begin{ratingstrip}[]&lt;br&gt;Example content.&lt;br&gt;\end{ratingstrip}</code> |
| `researchfrontpage` | `` | — | — | stable since 1.8.0 | <code>\begin{researchfrontpage}&lt;br&gt;Example content.&lt;br&gt;\end{researchfrontpage}</code> |
| `researchmain` | `` | — | researchmain must be immediately followed by researchsidebar. | stable since 1.8.0 | <code>\begin{researchmain}&lt;br&gt;Example content.&lt;br&gt;\end{researchmain}</code> |
| `researchsidebar` | `` | — | researchsidebar must immediately follow researchmain. | stable since 1.8.0 | <code>\begin{researchsidebar}&lt;br&gt;Example content.&lt;br&gt;\end{researchsidebar}</code> |
| `whatschanged` | `` | — | — | stable since 1.8.0 | <code>\begin{whatschanged}&lt;br&gt;Example content.&lt;br&gt;\end{whatschanged}</code> |

### Command primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `AlgorithmInput` | `m` | `text` (text, required) — Input description. | Use only inside algorithmblock, as with \State. | stable since 1.0.0 | <code>\AlgorithmInput{Heights $h_0,\ldots,h_{n-1}$}</code> |
| `AlgorithmOutput` | `m` | `text` (text, required) — Output description. | Use only inside algorithmblock, as with \State. | stable since 1.0.0 | <code>\AlgorithmOutput{Maximum container area}</code> |
| `RKCycleEdge` | `O{} m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\RKCycleEdge[]{a}{b}</code> |
| `RKCycleNode` | `O{} m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`angle` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKCycleNode[]{a}{1}{Example}</code> |
| `RKCycleSetup` | `m` | `radius` (text, required) | — | stable since 1.0.0 | <code>\RKCycleSetup{1}</code> |
| `RKDiagramSection` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\RKDiagramSection{Example}</code> |
| `RKDiagramSubsection` | `m` | `title` (text, required) | — | stable since 1.0.0 | <code>\RKDiagramSubsection{Example}</code> |
| `RKEdge` | `O{} m m m` | `options` (options, optional=)<br>`kind` (text, required)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\RKEdge[]{Example}{a}{b}</code> |
| `RKFunnelSetup` | `m m` | `width` (text, required)<br>`stage_height` (text, required) | — | stable since 1.0.0 | <code>\RKFunnelSetup{1}{1}</code> |
| `RKFunnelStage` | `O{} m m m m` | `options` (options, optional=)<br>`row` (text, required)<br>`width` (text, required)<br>`label` (text, required)<br>`detail` (text, required) | — | stable since 1.0.0 | <code>\RKFunnelStage[]{1}{1}{Example}{Example}</code> |
| `RKLane` | `m m` | `row` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKLane{1}{Example}</code> |
| `RKLaneNode` | `O{} m m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`column` (text, required)<br>`row` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKLaneNode[]{a}{1}{1}{Example}</code> |
| `RKLayer` | `O{} m m m` | `options` (options, optional=)<br>`row` (text, required)<br>`label` (text, required)<br>`detail` (text, required) | — | stable since 1.0.0 | <code>\RKLayer[]{1}{Example}{Example}</code> |
| `RKLayerSetup` | `m m` | `width` (text, required)<br>`layer_height` (text, required) | — | stable since 1.0.0 | <code>\RKLayerSetup{1}{Example}</code> |
| `RKLink` | `m` | `key` (link-key, required) — Registered link key. | Use a key declared in links.yaml; unknown values fall back to literal URLs. | stable since 1.5.0 | <code>\RKLink{project-home}</code> |
| `RKMatrix` | `m m` | `x_label` (text, required)<br>`y_label` (text, required) | — | stable since 1.0.0 | <code>\RKMatrix{Example}{Example}</code> |
| `RKMatrixCell` | `O{} m m m` | `options` (options, optional=)<br>`column` (text, required)<br>`row` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKMatrixCell[]{1}{1}{Example}</code> |
| `RKMatrixSetup` | `m m` | `width` (text, required)<br>`height` (text, required) | — | stable since 1.0.0 | <code>\RKMatrixSetup{1}{1}</code> |
| `RKNode` | `O{} m m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`x` (text, required)<br>`y` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKNode[]{a}{1}{1}{Example}</code> |
| `RKNodeRel` | `O{} m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`position` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKNodeRel[]{a}{1}{Example}</code> |
| `RKPath` | `m` | `path` (text, required) | — | stable since 1.0.0 | <code>\RKPath{https://example.com}</code> |
| `RKStackSetup` | `m m m` | `width` (text, required)<br>`tier_height` (text, required)<br>`tier_count` (text, required) | — | stable since 1.0.0 | <code>\RKStackSetup{1}{1}{1}</code> |
| `RKStackTier` | `O{} m m` | `options` (options, optional=)<br>`row` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\RKStackTier[]{1}{Example}</code> |
| `RKSwimlaneSetup` | `m m` | `width` (text, required)<br>`lane_height` (text, required) | — | stable since 1.0.0 | <code>\RKSwimlaneSetup{1}{1}</code> |
| `RKTitlePage` | `O{} m` | `options` (options, optional=)<br>`title` (text, required) | — | stable since 1.0.0 | <code>\RKTitlePage[]{Example}</code> |
| `annotation` | `m` | `text` (text, required) — Annotation text, typically an invariant or running computation. | Only valid inside arraystate. | experimental since 1.10.0 | <code>\annotation{P_4 - P_1 = 7}</code> |
| `basecase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\basecase{1}{Example}</code> |
| `bearcase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\bearcase{1}{Example}</code> |
| `branch` | `O{} m m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\branch[]{a}{b}{Example}</code> |
| `bullcase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\bullcase{1}{Example}</code> |
| `causaledge` | `m m m` | `source` (text, required)<br>`target` (text, required)<br>`polarity` (text, required) | — | stable since 1.0.0 | <code>\causaledge{a}{b}{+}</code> |
| `causalnode` | `O{} m m` | `options` (options, optional=)<br>`id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\causalnode[]{a}{Example}</code> |
| `cell` | `O{} m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`value` (text, required) — Cell content. | Only valid inside arraystate or a \row call. | experimental since 1.10.0 | <code>\cell[state=active]{7}</code> |
| `change` | `m m m` | `date` (text, required)<br>`headline` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\change{Example}{Example}{Example}</code> |
| `current` | `m` | `index` (text, required) — Zero-based index into the values already declared with \values. | Only valid inside heapstate.<br>index must be within the values already declared with \values. | experimental since 1.10.0 | <code>\current{0}</code> |
| `currentcell` | `m m` | `row` (text, required) — 1-based row index.<br>`column` (text, required) — 1-based column index. | Only valid inside dptable.<br>row and column must fall within the declared rows= and columns=. | experimental since 1.10.0 | <code>\currentcell{3}{4}</code> |
| `cycleedge` | `O{} m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\cycleedge[]{a}{b}</code> |
| `cyclestage` | `O{} m m` | `options` (options, optional=)<br>`id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\cyclestage[]{a}{Example}</code> |
| `dagnode` | `O{} m m` | `options` (options, optional=) — indegree= (a small integer badge drawn at the node's corner) and state= one of the nine shared algorithm states.<br>`id` (text, required) — Node id, referenced later by dependency and readyqueue.<br>`label` (text, required) — Node label. | Only valid inside dagstate. | experimental since 1.10.0 | <code>\dagnode[indegree=0,state=frontier]{raw}{Raw}</code> |
| `dependency` | `m m` | `source` (text, required) — Upstream node id (the dependency).<br>`target` (text, required) — Downstream node id (the dependent). | Only valid inside dagstate.<br>Both ids must already be declared with dagnode. | experimental since 1.10.0 | <code>\dependency{raw}{clean}</code> |
| `dependencycell` | `m m` | `row` (text, required) — 1-based row index.<br>`column` (text, required) — 1-based column index. | Only valid inside dptable.<br>row and column must fall within the declared rows= and columns=. | experimental since 1.10.0 | <code>\dependencycell{2}{4}</code> |
| `dpcell` | `m m O{} m` | `row` (text, required) — 1-based row index.<br>`column` (text, required) — 1-based column index.<br>`options` (options, optional=) — state= one of the nine shared algorithm states.<br>`value` (text, required) — Cell content, typically the computed DP value. | Only valid inside dptable.<br>row and column must fall within the declared rows= and columns=. | experimental since 1.10.0 | <code>\dpcell{3}{4}[state=current]{7}</code> |
| `enqueue` | `O{} m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`value` (text, required) — Item content. | Only valid inside queuestate. | experimental since 1.10.0 | <code>\enqueue[state=current]{X}</code> |
| `entering` | `m` | `value` (text, required) — Incoming value. | Only valid inside windowstate. | experimental since 1.10.0 | <code>\entering{5}</code> |
| `event` | `O{} m m m` | `options` (options, optional=)<br>`track` (text, required)<br>`position` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\event[]{a}{1}{Example}</code> |
| `evidencetier` | `O{} m` | `options` (options, optional=)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\evidencetier[]{Example}</code> |
| `exhibitpane` | `O{} m` | `options` (options, optional=)<br>`content` (text, required) | — | stable since 1.8.0 | <code>\exhibitpane[]{Example}</code> |
| `findpath` | `O{} m m` | `options` (options, optional=) — Optional label=; FIND is the default label.<br>`from` (text, required) — Starting node id.<br>`to` (text, required) — Representative node id. | Only valid inside unionfindstate.<br>Both ids must already be declared with ufnode. | experimental since 1.10.0 | <code>\findpath{D}{A}</code> |
| `flowedge` | `O{} m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\flowedge[]{a}{b}</code> |
| `funnelstage` | `O{} m m m` | `options` (options, optional=)<br>`width` (text, required)<br>`label` (text, required)<br>`detail` (text, required) | — | stable since 1.0.0 | <code>\funnelstage[]{1}{Example}{Example}</code> |
| `graphedge` | `m m` | `source` (text, required) — Source node id.<br>`target` (text, required) — Target node id. | Only valid inside graphstate.<br>Both ids must already be declared with graphnode. | experimental since 1.10.0 | <code>\graphedge{A}{B}</code> |
| `graphnode` | `O{} m m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`id` (text, required) — Node id, referenced later by graphedge.<br>`label` (text, required) — Node label. | Only valid inside graphstate. | experimental since 1.10.0 | <code>\graphnode[state=current]{B}{Current}</code> |
| `gridcell` | `m m O{}` | `row` (text, required) — 1-based row index.<br>`column` (text, required) — 1-based column index.<br>`options` (options, optional=) — state= one of the nine shared algorithm states. | Only valid inside gridstate.<br>row and column must fall within the declared rows= and columns=. | experimental since 1.10.0 | <code>\gridcell{1}{2}[state=current]</code> |
| `handoff` | `O{} m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\handoff[]{a}{b}</code> |
| `hashbucket` | `O{} m m` | `options` (options, optional=) — state= shared algorithm state for the index bucket.<br>`key` (text, required) — Join key or key expression.<br>`values` (text, required) — Indexed values, usually comma-separated. | Only valid inside joinstate. | experimental since 1.10.0 | <code>\hashbucket[state=active]{customer_id}{C42,C73}</code> |
| `head` | `m` | `id` (text, required) — Head node id. | Only valid inside linkedliststate.<br>id must be declared with listnode. | experimental since 1.10.0 | <code>\head{a}</code> |
| `interval` | `O{} m m m` | `options` (options, optional=) — state= one of the nine shared algorithm states (candidate and discarded are used verbatim; overlap maps onto active -- see this file's top-of-file note).<br>`label` (text, required) — Interval label, e.g. an identifier or source name.<br>`start` (text, required) — Interval start, on the shared numeric axis.<br>`end` (text, required) — Interval end, on the shared numeric axis. | Only valid inside intervalstate.<br>start must not exceed end. | experimental since 1.10.0 | <code>\interval[state=active]{B}{3}{6}</code> |
| `joininput` | `O{} m m` | `options` (options, optional=) — side=left&#124;right and state= shared algorithm state.<br>`side` (text, required) — Input side; retained as a positional convenience when side= is omitted.<br>`label` (text, required) — Relation or stream label. | Only valid inside joinstate.<br>side must be left or right. | experimental since 1.10.0 | <code>\joininput[side=left,state=unseen]{orders}{Orders}</code> |
| `joinmatch` | `O{} m m` | `options` (options, optional=) — state= shared algorithm state for the match; resolved is the default.<br>`key` (text, required) — Key matching a declared hashbucket.<br>`result` (text, required) — Joined-row description. | Only valid inside joinstate. | experimental since 1.10.0 | <code>\joinmatch{customer_id}{C42 -&gt; order/customer row}</code> |
| `joinoutput` | `O{} m` | `options` (options, optional=) — state= shared algorithm state; resolved is the default.<br>`label` (text, required) — Output label. | Only valid inside joinstate. | experimental since 1.10.0 | <code>\joinoutput{Joined rows}</code> |
| `joinunmatched` | `O{} m m` | `options` (options, optional=) — state= shared algorithm state; discarded is the default.<br>`side` (text, required) — Input side, left or right.<br>`key` (text, required) — Unmatched key. | Only valid inside joinstate.<br>side must be left or right. | experimental since 1.10.0 | <code>\joinunmatched{right}{C99}</code> |
| `laneflow` | `O{} m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required) | — | stable since 1.0.0 | <code>\laneflow[]{a}{b}</code> |
| `lanestep` | `m m m m` | `lane` (text, required)<br>`id` (text, required)<br>`column` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\lanestep{Example}{a}{1}{Example}</code> |
| `leaving` | `m` | `value` (text, required) — Outgoing value. | Only valid inside windowstate. | experimental since 1.10.0 | <code>\leaving{1}</code> |
| `listnode` | `O{} m m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`id` (text, required) — Node id referenced by nextlink, head, and tail.<br>`label` (text, required) — Node value or label. | Only valid inside linkedliststate. | experimental since 1.10.0 | <code>\listnode[state=current]{b}{B}</code> |
| `merge` | `O{} m m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\merge[]{a}{b}{Example}</code> |
| `merged` | `O{} m m` | `options` (options, optional=) — state= one of the nine shared algorithm states; defaults to resolved.<br>`start` (text, required) — Merged span start, on the shared numeric axis.<br>`end` (text, required) — Merged span end, on the shared numeric axis. | Only valid inside intervalstate.<br>start must not exceed end. | experimental since 1.10.0 | <code>\merged{1}{6}</code> |
| `networkedge` | `O{dependency} m m O{}` | `relationship` (options, optional=dependency)<br>`source` (text, required)<br>`target` (text, required)<br>`options` (options, optional=) | — | stable since 1.0.0 | <code>\networkedge[]{a}{b}[]</code> |
| `networknode` | `O{} m m` | `options` (options, optional=)<br>`id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\networknode[]{a}{Example}</code> |
| `nextlink` | `O{} m m` | `options` (options, optional=) — Optional label= for the pointer.<br>`source` (text, required) — Source node id.<br>`target` (text, required) — Target node id. | Only valid inside linkedliststate.<br>Both ids must already be declared with listnode. | experimental since 1.10.0 | <code>\nextlink{a}{b}</code> |
| `panel` | `m m` | `id` (text, required)<br>`title` (text, required) | — | stable since 1.0.0 | <code>\panel{a}{Example}</code> |
| `panelitem` | `m m m` | `panel` (text, required)<br>`label` (text, required)<br>`detail` (text, required) | — | stable since 1.0.0 | <code>\panelitem{a}{Example}{Example}</code> |
| `parent` | `O{} m m` | `options` (options, optional=) — Optional label= for the parent edge.<br>`child` (text, required) — Child node id.<br>`parent` (text, required) — Parent or representative node id. | Only valid inside unionfindstate.<br>Both ids must already be declared with ufnode. | experimental since 1.10.0 | <code>\parent{B}{A}</code> |
| `point` | `O{} m m m` | `options` (options, optional=)<br>`x` (text, required)<br>`y` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\point[]{1}{1}{Example}</code> |
| `pointer` | `O{} m m` | `options` (options, optional=) — above, below (default), or row= to target a named arraystate row.<br>`label` (text, required) — Cursor label, e.g. L, R, or mid.<br>`index` (text, required) — Zero-based cell index the cursor targets. | Only valid inside arraystate. | experimental since 1.10.0 | <code>\pointer[below]{L}{2}</code> |
| `push` | `O{} m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`value` (text, required) — Item content. | Only valid inside stackstate. | experimental since 1.10.0 | <code>\push[state=current]{X}</code> |
| `quadrant` | `m m m` | `column` (text, required)<br>`row` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\quadrant{1}{1}{Example}</code> |
| `range` | `O{} m m` | `options` (options, optional=) — state= (default active) and row= to target a named arraystate row.<br>`start` (text, required) — Zero-based start index, inclusive.<br>`end` (text, required) — Zero-based end index, inclusive. | Only valid inside arraystate.<br>start must not exceed end. | experimental since 1.10.0 | <code>\range[state=active]{2}{6}</code> |
| `ratingitem` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.8.0 | <code>\ratingitem{Example}{1}</code> |
| `readyqueue` | `m` | `ids` (text, required) — Comma-separated list of node ids already declared with dagnode. | Only valid inside dagstate.<br>Every id must already be declared with dagnode. | experimental since 1.10.0 | <code>\readyqueue{raw,clean}</code> |
| `recursionedge` | `O{} m m` | `options` (options, optional=) — Optional label= for the edge.<br>`parent` (text, required) — Calling node id.<br>`child` (text, required) — Called node id. | Only valid inside recursiontree.<br>Both ids must already be declared with recursionnode. | experimental since 1.10.0 | <code>\recursionedge{f4}{f3}</code> |
| `recursionnode` | `O{} m m m` | `options` (options, optional=) — arguments= text, state= shared algorithm state, and memoized flag.<br>`id` (text, required) — Call id referenced by recursionedge.<br>`call` (text, required) — Function or call label.<br>`return` (text, required) — Returned value. | Only valid inside recursiontree. | experimental since 1.10.0 | <code>\recursionnode[arguments={n=4},state=current]{f4}{fib}{3}</code> |
| `risk` | `m m m m m` | `likelihood` (text, required)<br>`impact` (text, required)<br>`label` (text, required)<br>`owner` (text, required)<br>`status` (text, required) | — | stable since 1.0.0 | <code>\risk{1}{1}{Example}{Example}{Example}</code> |
| `rkscenario` | `m m m m` | `label` (text, required)<br>`color` (text, required)<br>`value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\rkscenario{Example}{Accent}{1}{Example}</code> |
| `row` | `m m` | `name` (text, required) — Row name, referenced later by \pointer/\range/\annotation's row= key.<br>`values` (text, required) — Comma-separated cell values. | Only valid inside arraystate. | experimental since 1.10.0 | <code>\row{values}{3,1,4,2}</code> |
| `selfloop` | `O{} m m` | `options` (options, optional=)<br>`state` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\selfloop[]{a}{Example}</code> |
| `sidebarrow` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.8.0 | <code>\sidebarrow{Example}{1}</code> |
| `skewarrow` | `m m m m` | `source_track` (text, required)<br>`source_position` (text, required)<br>`target_track` (text, required)<br>`target_position` (text, required) | — | stable since 1.0.0 | <code>\skewarrow{a}{Example}{b}{Example}</code> |
| `snapshot` | `m m` | `title` (text, required) — Short step label, e.g. the action taken this step.<br>`content` (text, required) — Any algorithm-state primitive (arraystate, windowstate, or a later family), used exactly as inside a diagram. | Only valid inside algorithmtrace.<br>Reading order is left to right, then top to bottom. | experimental since 1.10.0 | <code>\snapshot{Initial}{\begin{arraystate}\cell{1}\end{arraystate}}</code> |
| `solvedcell` | `m m` | `row` (text, required) — 1-based row index.<br>`column` (text, required) — 1-based column index. | Only valid inside dptable.<br>row and column must fall within the declared rows= and columns=. | experimental since 1.10.0 | <code>\solvedcell{1}{1}</code> |
| `state` | `O{} m m` | `options` (options, optional=)<br>`id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\state[]{a}{Example}</code> |
| `stateat` | `O{} m m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`x` (text, required)<br>`y` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\stateat[]{a}{1}{1}{Example}</code> |
| `step` | `m m` | `id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\step{a}{Example}</code> |
| `stepat` | `O{} m m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`x` (text, required)<br>`y` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\stepat[]{a}{1}{1}{Example}</code> |
| `tail` | `m` | `id` (text, required) — Tail node id. | Only valid inside linkedliststate.<br>id must be declared with listnode. | experimental since 1.10.0 | <code>\tail{c}</code> |
| `terminalstate` | `O{} m m` | `options` (options, optional=)<br>`id` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\terminalstate[]{a}{Example}</code> |
| `terminalstateat` | `O{} m m m m` | `options` (options, optional=)<br>`id` (text, required)<br>`x` (text, required)<br>`y` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\terminalstateat[]{a}{1}{1}{Example}</code> |
| `transformarrow` | `m` | `label` (text, required) | — | stable since 1.0.0 | <code>\transformarrow{Example}</code> |
| `transition` | `O{} m m m` | `options` (options, optional=)<br>`source` (text, required)<br>`target` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\transition[]{a}{b}{Example}</code> |
| `ufnode` | `O{} m m` | `options` (options, optional=) — state= one of the nine shared algorithm states.<br>`id` (text, required) — Node id referenced by parent, union, and findpath.<br>`label` (text, required) — Node label. | Only valid inside unionfindstate. | experimental since 1.10.0 | <code>\ufnode[state=current]{D}{D}</code> |
| `union` | `O{} m m` | `options` (options, optional=) — Optional label=; UNION is the default label.<br>`left` (text, required) — First representative or component node id.<br>`right` (text, required) — Second representative or component node id. | Only valid inside unionfindstate.<br>Both ids must already be declared with ufnode. | experimental since 1.10.0 | <code>\union{A}{C}</code> |
| `values` | `m` | `values` (text, required) — Comma-separated cell values. | Only valid inside windowstate. | experimental since 1.10.0 | <code>\values{4,2,7,1,3,6}</code> |
| `watermark` | `O{} m m m` | `options` (options, optional=)<br>`start` (text, required)<br>`end` (text, required)<br>`label` (text, required) | — | stable since 1.0.0 | <code>\watermark[]{1}{1}{Example}</code> |
| `window` | `m m` | `start` (text, required) — Zero-based window start index, inclusive.<br>`end` (text, required) — Zero-based window end index, inclusive. | Only valid inside windowstate. | experimental since 1.10.0 | <code>\window{2}{4}</code> |

<!-- REPORTKIT-CONTRACT:END -->
