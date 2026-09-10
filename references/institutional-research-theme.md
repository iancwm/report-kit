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
build if Google Sans specifically cannot be resolved. Neither
`document.theme` nor `theme.*` are wired into the markdown-driven
publication pipeline yet -- every example that uses this theme sets
`\documentclass[...]` options directly in `report.tex`, the same way it
already sets `\setreportkitleftheader` etc.

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
`FIGURE_SIZES` gains `half` (sized for an `exhibitpair` pane) and
`dominant` (an alias of the pre-existing `wide`) under every theme.
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
