# Feature-article authoring contract

This reference covers the `feature-article` publication type and the `editorial` theme (Phase E of the multi-format publication architecture). Both are **stable**: the canonical fixture and its structure/style boundary are tested, and the six-page pinned-toolchain visual baseline was reviewed on 2026-09-26.

Select them together:

```latex
\documentclass[theme=editorial,publication-type=feature-article]{reportkit}
```

or, in `publication.yaml`, `document.publication_type: feature-article`, `document.theme: editorial`, `document.engine: lualatex`. The editorial theme requires LuaLaTeX.

## Audit the intended composition

The class option chooses typography and feature styling, but cannot choose an
article's visual rhythm. Make two-column `featurecolumns` the normal reading
measure for narrative. A short one-column lead can introduce a section; a
full-width chart, diagram, image, or lookup table can interrupt it. Resume
columns after the interrupt. Do not leave long explanatory paragraphs full
width because a preceding table required the wider measure.

Before writing the source, name the visual reference
and expected roles in an `editorial-brief.json` in the consumer publication
directory. Start with the canonical example's
`latex_templates/examples/editorial-feature/editorial-brief.json` and change
the expectations to fit the actual assignment. For example:

```json
{
  "visual_reference": "client-provided editorial QA PDF",
  "required": ["openingvisual", "featurecolumns", "pullquote", "graphic-exhibit"],
  "minimum_exhibits": 2,
  "minimum_column_prose_ratio": 0.6,
  "section_minimum_column_prose_ratio": 0.5,
  "minimum_pullquotes": 2,
  "minimum_graphic_exhibits": 2,
  "section_minimum_pullquotes": 1,
  "section_minimum_graphic_exhibits": 1,
  "exclude_sections": ["Sources and notes"]
}
```

Run `reportkit audit-editorial report.tex --brief editorial-brief.json --json`
before compiling and again after editing. A source that only selects
`theme=editorial` will fail this brief. The audit also rejects local styling
overrides, reports the roles present, and estimates the share of narrative
words in columns for the whole article and each `featuresection`. The
section gate can exclude reference-only sections. A high count of short
column blocks cannot make up for long one-column prose passages. The audit
does not establish
that a quote is genuine, an exhibit is meaningful, data is sound, or pages are
well composed. Verify those by reading sources and comparing every rendered
page with the reference. The brief is publication-specific: a legitimate
feature may omit a pull quote or chart when evidence does not support one;
document that choice instead of inventing content to pass a generic quota.

## Structure versus style

`reportkit-feature-article.sty` owns what a feature is made of; the theme owns how it looks. Every size, family, color, rule, inset and spacing value a feature primitive uses is a `\RKTokFeature...` token populated by the theme's paged adapter (`reportkit-theme-editorial-paged.sty`). A second feature-compatible theme restyles the same article source without edits; `tests/test_editorial_theme.py` proves this by compiling the canonical fixture again under an unrelated probe theme.

Do not add local `\fontsize`, `\color`, `\vspace`, `minipage` or `\hspace` in the article body to adjust the look. Change the theme instead.

## Primitive roles

| Primitive | Role |
| --- | --- |
| `featureopening` | Opening block on the first page; applies the theme's opening page style. Use once. |
| `\featureheadline[kicker]{headline}` | The article headline with an optional topic kicker. |
| `\featuredeck{deck}` | One or two sentences stating what the article argues. |
| `\featurebyline{byline}[detail]` | Author credit plus an optional dateline or reading time. |
| `openingvisual` | Full-width opening image with caption and optional credit. |
| `\dropcap{initial}{lead}` | Drop cap at the start of the first paragraph (at most once per section). |
| `\featuresection{title}[standfirst]` | Section opener for a new movement of the story; registers the PDF outline and running head. |
| `featurecolumns` | Two-column prose. Not nestable; no floats inside. |
| `\pullquote{quote}[attribution]` | A short line from the article, set apart. Never invent quotes. |
| `featuresidebar` | Self-contained companion box; unbreakable, keep under about half a page. |
| `featureexhibit[span=...]{title}` | Numbered exhibit (`span=column` or `span=full`) with a finding-first title; credit it with `\imagecredit`. |
| `featuretable` | Wraps a hand-authored `tabularx`/`tabular` inside a `featureexhibit`, setting its font, color, row height and cell padding to the theme's table tokens so the table reads at the same proportion as its own `\imagecredit` line. There is no other data-table primitive in feature-article; this is the fallback, not `financialtable`. |
| `\imagecredit{credit}` | Credit or source line for a visual. |
| `featurereferences[title]` | Numbered notes and sources (`\item` entries) at the end of the article. |

## Layout rhythm

The rhythm vocabulary is closed on purpose; it is not a positioning API.

- **Two-column prose** is the normal feature reading measure: `featurecolumns`. A `span=column` exhibit inside it fills its column.
- **One-column prose** is deliberate: a short lead, transition, wide table, or reference material. A `span=column` exhibit here is an inset at the theme's inset width.
- **Full-width visuals** are `openingvisual` and `featureexhibit[span=full]`, placed outside `featurecolumns`. Using either inside columns fails with `FEATURE_EXHIBIT_FULL_SPAN_IN_COLUMNS` or `FEATURE_OPENING_VISUAL_IN_COLUMNS`; any other `span` value fails with `FEATURE_EXHIBIT_UNKNOWN_SPAN`.

Exhibits are not floats: they stay where they are written. If an exhibit leaves a large gap at a page foot, move it or the surrounding prose rather than adding spacing.

Plan at least one meaningful visual or graphic exhibit for each major movement of a long article, and use pull quotes at natural turning points. A visual can replace a table that merely encodes a relationship or decision path; retain wide tables for precise comparison or lookup, often in an appendix. Quotes must repeat or faithfully paraphrase a real sentence in the article or named source. Check pages as well as source: a visually repetitive run of tables, empty space, or uninterrupted prose needs another editorial pass even when the audit passes.

A tabular exhibit (a comparison, a metrics list, a scenario grid) is plain `tabularx`/`tabular` -- there is no coordinate-based table primitive -- but wrap it in `featuretable` rather than leaving it at the body-text size. Feature articles have no dedicated data-table primitive the way the institutional-research theme has `financialtable`; without `featuretable`, a hand-authored table reads noticeably larger than its own `\imagecredit` line, out of proportion with the rest of the exhibit.

```latex
\begin{featureexhibit}[span=full]{Old Harbour carries the densest part of the network}
\begin{featuretable}
\begin{tabularx}{\linewidth}{@{}l X@{}}
\toprule
District & Gauges installed \\
\midrule
Old Harbour & 11 \\
\bottomrule
\end{tabularx}
\end{featuretable}
\imagecredit{Source: Varenholm gauge survey, fictional data}
\end{featureexhibit}
```

## Typography and language coverage

The editorial theme sets body text in Libertinus Serif, headlines and section openers in Libertinus Serif Display, drop caps in Libertinus Serif Initials, and metadata, labels, captions, credits and chart text in Libertinus Sans. All four families ship in the pinned toolchain's bundled Libertinus archive.

Coverage is declared, not assumed: English Latin-script typography is verified by the fixture; Vietnamese is metadata-only; other scripts are undeclared even though Libertinus contains Greek and Cyrillic glyphs; RTL is unsupported.

Charts use `rkv.apply_theme("editorial")`, which exposes the paged size names plus `inset` and `column` sizes for the two exhibit spans. Matplotlib resolves Libertinus Sans only when the font is registered with fontconfig; otherwise it falls back to the next candidate.

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent contract metadata. Do not edit it by hand.

### Composition primitives

| Name | Signature | Canonical example |
| --- | --- | --- |
| `featurecolumns` | `` | <code>\begin{featurecolumns}&lt;br&gt;The survey began with a single gauge.&lt;br&gt;&lt;br&gt;Within a year there were forty.&lt;br&gt;\end{featurecolumns}</code> |
| `featureexhibit` | `O{} m` | <code>\begin{featureexhibit}[span=full]{Forty gauges halved the warning time}&lt;br&gt;\rule{\linewidth}{25mm}&lt;br&gt;\imagecredit{Source: fictional town survey}&lt;br&gt;\end{featureexhibit}</code> |
| `featureopening` | `` | <code>\begin{featureopening}&lt;br&gt;\featureheadline[Infrastructure]{The river that learned to count}&lt;br&gt;\featuredeck{How a fictional delta town rebuilt its flood defences around measurement.}&lt;br&gt;\featurebyline{By Mara Ellison}[Field report]&lt;br&gt;\end{featureopening}</code> |
| `featurereferences` | `O{\RKFeatureReferencesName}` | <code>\begin{featurereferences}&lt;br&gt;\item Delta Town Council (2026), Flood gauge survey. \url{https://example.com/survey}&lt;br&gt;\end{featurereferences}</code> |
| `featuresidebar` | `m` | <code>\begin{featuresidebar}{How the gauges work}&lt;br&gt;Each gauge reports water height every ten minutes.&lt;br&gt;\end{featuresidebar}</code> |
| `openingvisual` | `m o` | <code>\begin{openingvisual}{The delta at low water, drawn from the town survey.}[Illustration: ReportKit example]&lt;br&gt;\rule{\linewidth}{30mm}&lt;br&gt;\end{openingvisual}</code> |

### Command primitives

| Name | Signature | Canonical example |
| --- | --- | --- |
| `dropcap` | `m m` | <code>\dropcap{T}{he river} rose twice that spring before anyone thought to measure it.</code> |
| `featurebyline` | `m o` | <code>\featurebyline{By Mara Ellison}[Field report]</code> |
| `featuredeck` | `m` | <code>\featuredeck{How a fictional delta town rebuilt its flood defences around measurement.}</code> |
| `featureheadline` | `o m` | <code>\featureheadline[Infrastructure]{The river that learned to count}</code> |
| `featuresection` | `m o` | <code>\featuresection{Counting the water}[The first gauge cost less than a single sandbag wall.]</code> |
| `imagecredit` | `m` | <code>\imagecredit{Illustration: ReportKit example}</code> |
| `pullquote` | `m o` | <code>\pullquote{We stopped arguing about the river once we could see it.}[Harbour engineer]</code> |

<!-- REPORTKIT-CONTRACT:END -->
