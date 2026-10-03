# Feature-article authoring

> Scope: `feature-article` structure × `editorial` look. Full feature composition requires TeX; Markdown supports the opening only. The context slice for the locked target is the primitive contract.

The feature type defines an editorial reading rhythm; the theme supplies typography, color, and spacing. The canonical example is [`latex_templates/examples/editorial-feature/`](../latex_templates/examples/editorial-feature/). The selected class options are:

```latex
\documentclass[theme=editorial,publication-type=feature-article]{reportkit}
```

## Composition and reading rhythm

Use `featurecolumns` for the normal narrative measure. Open a one-column passage for a short lead or transition, wide data table, full-width visual, or references, then resume columns. Keep full-width `openingvisual` and `featureexhibit[span=full]` outside the columns. Exhibits stay where authored, so place each where its evidence supports the nearby prose.

A feature can use its native opening, headline, deck, byline, section, drop cap, column, pull quote, sidebar, exhibit, credit, and references roles. Use `featuretable` to place a hand-authored `tabular` or `tabularx` inside a `featureexhibit`; it applies the feature table tokens. The generated contract below contains the current signatures and examples.

Select visuals for the story's evidence, not to meet a quota. Place pull quotes at meaningful turns and repeat or faithfully paraphrase real source text. A source citation belongs with each visual. Avoid local typography and spacing changes: the selected theme owns those values.

## Composition brief and review

Use the canonical [`composition-brief.json`](../latex_templates/examples/editorial-feature/composition-brief.json) as a shape reference, then set requirements for the article's actual argument and evidence in the consumer project. A brief can name a reference, required roles, per-section prose and exhibit expectations, and sections to exclude. Do not invent content to satisfy a generic count.

`reportkit check --source-root <project> --json` runs the composition checks before compilation; `reportkit build` runs them again before TeX. Review the audit findings, then inspect every rendered page against the brief and any supplied visual reference. An audit checks source composition; it does not establish that claims are supported or that the rendered pages are well composed.

## Theme and language

The editorial theme uses Libertinus Serif for body text, Libertinus Serif Display for headlines and section openers, Libertinus Serif Initials for drop caps, and Libertinus Sans for metadata and visual text. English Latin-script typography is verified; Vietnamese is metadata-only; RTL is unsupported. Charts should use `rkv.apply_theme("editorial")`; see [charts](charts.md) for export guidance.

## References and contents

Features default to author-year citations with a References list in the
`featurereferences` style, while `\RKContents` renders an inline "In this
issue" strip that never breaks the page. Declare `bibliography.file` in
`publication.yaml`, cite with `\citet`/`\citep`, and place both commands where
they belong. Without a `.bib` file, use the manual `featurereferences`
environment instead. See [bibliography and
contents](bibliography-and-contents.md).

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent and explicit virtual contract metadata. Do not edit it by hand.

### Composition primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `featurecolumns` | `` | — | featurecolumns cannot be nested.<br>featureexhibit[span=full] and openingvisual are not allowed inside; close the columns, place the full-width visual, then reopen.<br>Do not place floating figure/table environments inside; use featureexhibit. | experimental since 1.10.0 | <code>\begin{featurecolumns}&lt;br&gt;The survey began with a single gauge.&lt;br&gt;&lt;br&gt;Within a year there were forty.&lt;br&gt;\end{featurecolumns}</code> |
| `featureexhibit` | `O{} m` | `options` (options, optional=) — span=column (default) or span=full. No other keys exist.<br>`title` (text, required) — Exhibit title stating the finding, not only the metric. | Only span=column and span=full are accepted; there are no coordinates, offsets or custom widths.<br>span=full inside featurecolumns fails with FEATURE_EXHIBIT_FULL_SPAN_IN_COLUMNS.<br>Exhibits stay where they are written; size the body to \linewidth. | experimental since 1.10.0 | <code>\begin{featureexhibit}[span=full]{Forty gauges halved the warning time}&lt;br&gt;\rule{\linewidth}{25mm}&lt;br&gt;\imagecredit{Source: fictional town survey}&lt;br&gt;\end{featureexhibit}</code> |
| `featureopening` | `` | — | Use once, at the start of the article body, before any prose.<br>The opening page's running furniture comes from the theme; do not call \thispagestyle yourself. | experimental since 1.10.0 | <code>\begin{featureopening}&lt;br&gt;\featureheadline[Infrastructure]{The river that learned to count}&lt;br&gt;\featuredeck{How a fictional delta town rebuilt its flood defences around measurement.}&lt;br&gt;\featurebyline{By Mara Ellison}[Field report]&lt;br&gt;\end{featureopening}</code> |
| `featurereferences` | `O{\RKFeatureReferencesName}` | `title` (text, optional=\RKFeatureReferencesName) — Heading for the list; defaults to the publication type's references name. | Contains only \item entries.<br>Place in one-column flow at the end of the article. | experimental since 1.10.0 | <code>\begin{featurereferences}&lt;br&gt;\item Delta Town Council (2026), Flood gauge survey. \url{https://example.com/survey}&lt;br&gt;\end{featurereferences}</code> |
| `featuresidebar` | `m` | `title` (text, required) — Sidebar title. | The article must still read correctly if the sidebar is skipped.<br>A sidebar does not break across pages or columns; keep it under about half a page. | experimental since 1.10.0 | <code>\begin{featuresidebar}{How the gauges work}&lt;br&gt;Each gauge reports water height every ten minutes.&lt;br&gt;\end{featuresidebar}</code> |
| `openingvisual` | `m o` | `caption` (text, required) — Caption describing what the visual shows.<br>`credit` (text, optional) — Optional image credit or source. | Always spans the full text width; size the body to \linewidth.<br>Credit every photograph or illustration not made for the article. | experimental since 1.10.0 | <code>\begin{openingvisual}{The delta at low water, drawn from the town survey.}[Illustration: ReportKit example]&lt;br&gt;\rule{\linewidth}{30mm}&lt;br&gt;\end{openingvisual}</code> |

### Command primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `RKBibliography` | `O{}` | `title` (text, optional=) — Optional heading; defaults to bibliography.title or the publication type's references title. | publication.yaml must declare bibliography.file; otherwise RK_BIBLIOGRAPHY_UNCONFIGURED.<br>Cite only entries that exist in the .bib file. | experimental since 1.11.0 | <code>\RKBibliography</code> |
| `RKContents` | `O{}` | `title` (text, optional=) — Optional heading; defaults to the publication type's contents title. | Call at most once; it reads the contents file. | experimental since 1.11.0 | <code>\RKContents</code> |
| `dropcap` | `m m` | `initial` (text, required) — The single initial letter.<br>`lead` (text, required) — The rest of the first word or first few words, set in the lead-in style. | Use only at the very start of a paragraph, at most once per section. | experimental since 1.10.0 | <code>\dropcap{T}{he river} rose twice that spring before anyone thought to measure it.</code> |
| `featurebyline` | `m o` | `byline` (text, required) — Author credit, e.g. By Name.<br>`detail` (text, optional) — Optional dateline, role or reading-time detail. | — | experimental since 1.10.0 | <code>\featurebyline{By Mara Ellison}[Field report]</code> |
| `featuredeck` | `m` | `deck` (text, required) — Deck text. | Keep the deck to one or two sentences; it is not a summary section. | experimental since 1.10.0 | <code>\featuredeck{How a fictional delta town rebuilt its flood defences around measurement.}</code> |
| `featureheadline` | `o m` | `kicker` (text, optional) — Optional short topic label shown above the headline.<br>`headline` (text, required) — The article headline; a complete, specific statement rather than a label. | Use one headline per article, normally inside featureopening. | experimental since 1.10.0 | <code>\featureheadline[Infrastructure]{The river that learned to count}</code> |
| `featuresection` | `m o` | `title` (text, required) — Section title.<br>`standfirst` (text, optional) — Optional one-sentence introduction to the section. | Place section openers in one-column flow, between featurecolumns blocks. | experimental since 1.10.0 | <code>\featuresection{Counting the water}[The first gauge cost less than a single sandbag wall.]</code> |
| `imagecredit` | `m` | `credit` (text, required) — Credit text, e.g. Photograph: Name / Agency. | — | experimental since 1.10.0 | <code>\imagecredit{Illustration: ReportKit example}</code> |
| `pullquote` | `m o` | `quote` (text, required) — The quoted line; it must appear in, or faithfully paraphrase, the article.<br>`attribution` (text, optional) — Optional speaker or source. | Keep to roughly 10-35 words; a pull quote is not a callout or summary.<br>Quote only text that exists in the article or its sources. | experimental since 1.10.0 | <code>\pullquote{We stopped arguing about the river once we could see it.}[Harbour engineer]</code> |

<!-- REPORTKIT-CONTRACT:END -->
