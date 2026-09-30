# Institutional research and equity research

> Scope: `equity-research` structure × `institutional-research` look. The theme requires LuaLaTeX. TeX source and Markdown fragments are supported; read the target context for the available primitives.

The **structure** supplies equity-research roles; the **look** supplies typography, page geometry, palette, and chart styling. The [canonical example](../latex_templates/examples/equity-research/) includes TeX and Markdown fragments. Its class options are:

```latex
\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}
```

Set the target through `reportkit target set` or the `document:` block, then let `reportkit build` select the theme's engine and apply the same target gates to either source mode.

## Exhibit-led authoring

Lead with the research finding and its evidence. Exhibit titles state a conclusion rather than name a metric. Use the main narrative column for the thesis; use the sidebar for market data and reference information. Prefer a real analytical exhibit when quantitative evidence carries the point, and use semantic callouts for their established meaning.

The target roles include the research front page, rating strip, estimate changes, exhibits, financial tables and scenarios. Use the generated primitive contract below for signatures and constraints. In particular, `researchmain` and `researchsidebar` must be adjacent in source: place `\end{researchmain}` immediately before `\begin{researchsidebar}` so the sidebar remains beside the main column.

For data tables, use `financialtable` with `tabular`/`tabularx` and the supported column types. A dense model can use `financialmodelpage`; its local sizing ends with that environment. Read the canonical example before composing exhibit pairs, grids, and scenario cases.

## Charts and typography

Apply `rkv.apply_theme("institutional-research")` before drawing. It selects the theme's chart palette and geometry. Use `rkv.risk_reward_chart()` for a genuine bull/base/bear valuation view; there is no matching LaTeX chart macro. Save source data and the chart script with the consumer project. The [charts reference](charts.md) covers figure creation and export.

The font policy may fall back through the configured sans-serif families or be set to `strict`. Language and script support is documented in [agent-contract.md](agent-contract.md#language-and-script-support). The working example's font and class settings are part of the fixture; use the pipeline build to stage and validate those options.

## Composition and review

Use the canonical [`composition-brief.json`](../latex_templates/examples/equity-research/composition-brief.json) as a starting point and adapt its roles to the actual assignment. `reportkit check --source-root <project> --json` checks source composition before TeX, and `reportkit build` applies the same gate. Review every rendered page for evidence hierarchy, table fit, caption/source readability, and chart meaning.

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent and explicit virtual contract metadata. Do not edit it by hand.

### Callout primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `assumption` | `o g` | `title` (text, optional) — Optional replacement title; replaces the semantic default.<br>`legacy_suffix` (text, optional) — Optional legacy braced suffix appended to the semantic default. | — | stable since 1.0.0 | <code>\begin{assumption}[Example]&lt;br&gt;Example content.&lt;br&gt;\end{assumption}</code> |
| `metric` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.0.0 | <code>\begin{metric}{Example}{1}&lt;br&gt;Example content.&lt;br&gt;\end{metric}</code> |
| `redflag` | `o g` | `title` (text, optional) — Optional replacement title; replaces the semantic default.<br>`legacy_suffix` (text, optional) — Optional legacy braced suffix appended to the semantic default. | — | stable since 1.0.0 | <code>\begin{redflag}[Example]&lt;br&gt;Example content.&lt;br&gt;\end{redflag}</code> |
| `researchproblem` | `o g` | `title` (text, optional) — Optional replacement title; replaces the semantic default.<br>`legacy_suffix` (text, optional) — Optional legacy braced suffix appended to the semantic default. | — | stable since 1.0.0 | <code>\begin{researchproblem}[Example]&lt;br&gt;Example content.&lt;br&gt;\end{researchproblem}</code> |

### Figure primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `reportarchitecture` | `O{}` | `options` (options, optional=) — Architecture layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Platform architecture.},description={Three platform layers.}]&lt;br&gt;\begin{reportarchitecture}&lt;br&gt;\layer{Experience}{Reader,Author}&lt;br&gt;\layer{Services}{Build,Validation}&lt;br&gt;\layer{Data}{Sources,Archive}&lt;br&gt;\end{reportarchitecture}&lt;br&gt;\end{diagram}</code> |
| `reportflow` | `O{}` | `options` (options, optional=) — Direction and step-spacing keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Publication flow.},description={Three ordered publication steps.}]&lt;br&gt;\begin{reportflow}&lt;br&gt;\step{draft}{Draft}&lt;br&gt;\step{review}{Review}&lt;br&gt;\step{publish}{Publish}&lt;br&gt;\flowedge{draft}{review}&lt;br&gt;\flowedge{review}{publish}&lt;br&gt;\end{reportflow}&lt;br&gt;\end{diagram}</code> |
| `reportmatrix` | `O{}` | `options` (options, optional=) — Axis, size, and highlight keys. | Point coordinates must lie between zero and one. | stable since 1.0.0 | <code>\begin{diagram}[caption={Priority matrix.},description={A two-axis matrix with one labelled point.}]&lt;br&gt;\begin{reportmatrix}&lt;br&gt;\quadrant{low}{high}{Quick wins}&lt;br&gt;\point{Pilot}{.25}{.75}&lt;br&gt;\end{reportmatrix}&lt;br&gt;\end{diagram}</code> |
| `reporttimeline` | `O{}` | `options` (options, optional=) — Track, span, and label-layout keys. | — | stable since 1.0.0 | <code>\begin{diagram}[caption={Event timeline.},description={Two events on one time track.}]&lt;br&gt;\begin{reporttimeline}[tracks={Event time}]&lt;br&gt;\event{Event time}{.2}{A}&lt;br&gt;\event{Event time}{.8}{B}&lt;br&gt;\watermark{Event time}{.6}{close}&lt;br&gt;\end{reporttimeline}&lt;br&gt;\end{diagram}</code> |

### Chart primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `bar_chart` | `data, *, horizontal=True, highlight=None, value_formatter=None, value_labels=None, axis_label=None, sort=False, zero_line=True, size='full', title=None` | `data` (data, required)<br>`horizontal` (option, optional=True)<br>`highlight` (option, optional=None)<br>`value_formatter` (option, optional=None)<br>`value_labels` (option, optional=None) — Set to outside to label values past the bar ends.<br>`axis_label` (option, optional=None)<br>`sort` (option, optional=False)<br>`zero_line` (option, optional=True)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | Only the outside placement is supported; omit the option to disable labels. | stable since 1.0.0 | <code>fig, ax = rkv.bar_chart({"A": 2, "B": 1}, value_labels="outside")</code> |
| `drawdown_chart` | `drawdown, *, ylabel='Drawdown', y_formatter='percent', size='full', title=None` | `drawdown` (data, required)<br>`ylabel` (option, optional='Drawdown')<br>`y_formatter` (option, optional='percent')<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.drawdown_chart(pd.Series([0, -0.1, -0.05]))</code> |
| `risk_reward_chart` | `price_history, *, bear, base, bull, current=None, bear_label='Bear', base_label='Base', bull_label='Bull', value_formatter=None, ylabel='Share price ($)', xlabel=None, size='full', title=None` | `price_history` (data, required)<br>`bear` (option, required)<br>`base` (option, required)<br>`bull` (option, required)<br>`current` (option, optional=None)<br>`bear_label` (option, optional='Bear')<br>`base_label` (option, optional='Base')<br>`bull_label` (option, optional='Bull')<br>`value_formatter` (option, optional=None)<br>`ylabel` (option, optional='Share price ($)')<br>`xlabel` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>prices = pd.Series([90, 100]); fig, ax = rkv.risk_reward_chart(prices, bear=80, base=110, bull=140)</code> |
| `scatter_plot` | `x, y, *, xlabel, ylabel, fit_line=False, x_formatter=None, y_formatter=None, reference_x=None, reference_y=None, size='full', title=None` | `x` (data, required)<br>`y` (option, required)<br>`xlabel` (option, required)<br>`ylabel` (option, required)<br>`fit_line` (option, optional=False)<br>`x_formatter` (option, optional=None)<br>`y_formatter` (option, optional=None)<br>`reference_x` (option, optional=None)<br>`reference_y` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.scatter_plot([1, 2], [2, 3], xlabel="X", ylabel="Y")</code> |
| `timeseries` | `data, *, ylabel=None, xlabel=None, y_formatter=None, benchmark=None, reference_line=None, legend=True, size='full', title=None` | `data` (data, required)<br>`ylabel` (option, optional=None)<br>`xlabel` (option, optional=None)<br>`y_formatter` (option, optional=None)<br>`benchmark` (option, optional=None)<br>`reference_line` (option, optional=None)<br>`legend` (option, optional=True)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>data = pd.Series([1, 2, 3]); fig, ax = rkv.timeseries(data)</code> |
| `waterfall_chart` | `contributions, *, opening=0.0, opening_label='Opening', total_label='Total', subtotals=None, closing_total=None, value_formatter=None, ylabel=None, size='full', title=None` | `contributions` (data, required)<br>`opening` (option, optional=0.0)<br>`opening_label` (option, optional='Opening')<br>`total_label` (option, optional='Total')<br>`subtotals` (option, optional=None)<br>`closing_total` (option, optional=None)<br>`value_formatter` (option, optional=None)<br>`ylabel` (option, optional=None)<br>`size` (option, optional='full')<br>`title` (option, optional=None) | — | stable since 1.0.0 | <code>fig, ax = rkv.waterfall_chart({"Growth": 10, "Costs": -4})</code> |

### Composition primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `analystblock` | `` | — | — | stable since 1.8.0 | <code>\begin{analystblock}&lt;br&gt;Example content.&lt;br&gt;\end{analystblock}</code> |
| `codeblock` | `O{} O{} m` | `title` (text, optional=) — Optional free-text label shown left of the language badge.<br>`options` (options, optional=) — keep=auto opts into measured, whole-unit pagination; omitted, behaviour is unchanged.<br>`language` (text, required) — Listings language name, e.g. Python, SQL, HTML. | keep=auto must be requested explicitly via the second optional argument; the default reservation is unchanged when it is omitted. | experimental since 1.3.0 | <code>\begin{codeblock}[Two-pointer scan][keep=auto]{Python}&lt;br&gt;def solve(nums):&lt;br&gt;    return nums&lt;br&gt;\end{codeblock}</code> |
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
| `basecase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\basecase{1}{Example}</code> |
| `bearcase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\bearcase{1}{Example}</code> |
| `bullcase` | `m m` | `value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\bullcase{1}{Example}</code> |
| `change` | `m m m` | `date` (text, required)<br>`headline` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\change{Example}{Example}{Example}</code> |
| `exhibitpane` | `O{} m` | `options` (options, optional=)<br>`content` (text, required) | — | stable since 1.8.0 | <code>\exhibitpane[]{Example}</code> |
| `ratingitem` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.8.0 | <code>\ratingitem{Example}{1}</code> |
| `rkscenario` | `m m m m` | `label` (text, required)<br>`color` (text, required)<br>`value` (text, required)<br>`detail` (text, required) | — | stable since 1.8.0 | <code>\rkscenario{Example}{Accent}{1}{Example}</code> |
| `sidebarrow` | `m m` | `label` (text, required)<br>`value` (text, required) | — | stable since 1.8.0 | <code>\sidebarrow{Example}{1}</code> |

<!-- REPORTKIT-CONTRACT:END -->
