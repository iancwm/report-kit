# Presentation authoring

> Scope: `presentation` structure × `executive` or `venture` look. TeX and Markdown are supported. Both themes use LuaLaTeX; the venture theme is experimental.

The publication type supplies slide compositions; the theme owns typography, spacing, gutters, density, and color. The [canonical example](../latex_templates/examples/executive-presentation/) shows the executive theme. Use the target-scoped context slice and generated contract for the current composition vocabulary.

## Composition roles

Choose by rhetorical role, not by visual size:

| Role | Use |
| --- | --- |
| `titleslide` | Establish the deck's identity and orientation. |
| `assertionslide` | Orient a working slide with one decision-relevant claim and evidence. |
| `evidenceslide` | Separate an explicit claim from its supporting evidence. |
| `messageslide` | Give one sparse hero message room to dominate. |
| `sectiondivider` / `appendixdivider` | Mark a deliberate transition. |
| `closingslide` | Deliver a conclusion, implication, or action. |
| `referenceslide` | Present readable full references and optional usage notes. |

Keep compositions inside author-owned Beamer frames. A slide assertion should state one claim: one line is ideal, two lines can use the compact treatment, and longer claims should be rewritten or split. Keep evidence as the dominant canvas. Theme-owned density roles set text sizes and card spacing; if content does not fit, shorten it or split the slide.

## Evidence layouts and sources

Use a card grid for a small set of comparable points, equal-weight options, or ordered steps. Use a semantic process diagram when relationships, branches, or ownership matter more than card text. The context and generated contract provide current layout options and constraints. Preserve meaning in grayscale and keep labels concise.

Use a short source line for the visual on the slide and full citations on a references slide. Continue a source list when needed so that references remain readable. Review rendered slides for clipped content, header/body overlap, safe margins, broken diagrams, missing sources, and meaning that depends on color.

`reportkit check --source-root <project> --json` runs the target's source checks. Build through ReportKit, render the relevant slides, then record the manual review with `reportkit review`. See [charts](charts.md), [visual grammar](visual-grammar.md), and [repository-boundary.md](repository-boundary.md) for topic guidance.

## Photographs and illustrations

In a Markdown deck, place a photograph with an image slot and a diagram or
chart with a visual marker; both are listed under `markdown_forms` in the
primitives slice. See [Markdown authoring](markdown-authoring.md). The
`venture` theme also accepts organisation colours and a logo through
[brand overrides](markdown-authoring.md#brand-overrides).

## References and contents

Decks default to numeric citations with a References list that paginates at
eight entries per frame (with a `(cont.)` continuation title), while
`\RKContents` emits an agenda frame listing every `sectiondivider` title.
Declare `bibliography.file` in `publication.yaml` and use `\RKBibliography`
outside any frame; for a hand-written agenda, wrap `agendaslide` in a frame.
Without a `.bib` file, use the manual `referenceslide` with `\referenceitem`
entries instead. See [bibliography and
contents](bibliography-and-contents.md).

<!-- REPORTKIT-CONTRACT:START -->
## Generated primitive contract

This section is generated from source-adjacent and explicit virtual contract metadata. Do not edit it by hand.

### Composition primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `agendaslide` | `O{}` | `title` (text, optional=) — Heading; defaults to Agenda. | Content only; wrap in \begin{frame}...\end{frame}. | experimental since 1.11.0 | <code>\begin{frame}&lt;br&gt;\begin{agendaslide}&lt;br&gt;\end{agendaslide}&lt;br&gt;\end{frame}</code> |
| `appendixdivider` | `m` | `title` (text, required) — Appendix title, also registered as a \section (prefixed Appendix:) for the PDF outline/bookmarks. | Content only; wrap in \begin{frame}[plain]...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}[plain]&lt;br&gt;\begin{appendixdivider}{Example}&lt;br&gt;\end{appendixdivider}&lt;br&gt;\end{frame}</code> |
| `architectureslide` | `O{} O{}` | `caption` (text, optional=) — Optional caption, typeset the same way a diagram's is.<br>`source` (text, optional=) — Optional source line. | Same layout as fullvisual; named separately so an author or agent authoring an architecture slide finds it directly.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{architectureslide}[][]&lt;br&gt;Example content.&lt;br&gt;\end{architectureslide}&lt;br&gt;\end{frame}</code> |
| `assertionslide` | `O{} m O{}` | `options` (options, optional=) — Optional key list; currently supports kicker={...}.<br>`assertion` (text, required) — The single working-slide assertion.<br>`deck` (text, optional=) — Optional short supporting sentence in the deck hierarchy. | Content only; wrap in \begin{frame}...\end{frame}.<br>The header is measured and reserved at a fixed maximum height; body typography is not reduced to rescue an invalid assertion.<br>The assertion resolves to standard, compact, or invalid; invalid emits PRESENTATION_ASSERTION_TOO_LONG. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{assertionslide}[kicker={Parenting constitution}]{Six household rules prevent most major unforced errors.}[Agree on these before you are tired.]&lt;br&gt;Evidence body.&lt;br&gt;\end{assertionslide}&lt;br&gt;\end{frame}</code> |
| `cardgrid` | `O{}` | `options` (options, optional=) — columns=2, 3, or 4; optional default card variant. | Only columns=2, columns=3, and columns=4 are supported; invalid values emit a hard diagnostic.<br>Gutters, padding, minimum height, rule weight, and text roles come from presentation tokens.<br>Variants use borders, rails, ordinals, or rule weight in addition to fill.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{cardgrid}[columns=2,variant=surface]&lt;br&gt;\carditem[numbered]{Rule one}{Short evidence.}&lt;br&gt;\carditem[accent-rail]{Rule two}{Short evidence.}&lt;br&gt;\end{cardgrid}&lt;br&gt;\end{frame}</code> |
| `chartslide` | `O{right} m m` | `position` (options, optional=right) — left or right: which side the chart (this environment's content) renders on. Default right.<br>`heading` (text, required) — Heading for the text column.<br>`body` (text, required) — Supporting insight text for the text column. | Same layout as visualtext; named separately so an author or agent authoring a chart slide finds it directly.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{chartslide}[right]{Example}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{chartslide}&lt;br&gt;\end{frame}</code> |
| `closingslide` | `m` | `headline` (text, required) — Closing statement or call to action. | Content only; wrap in \begin{frame}[plain]...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}[plain]&lt;br&gt;\begin{closingslide}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{closingslide}&lt;br&gt;\end{frame}</code> |
| `comparison` | `` | — | Content must be exactly two \comparisoncolumn calls.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{comparison}&lt;br&gt;\comparisoncolumn{Example}{Example}&lt;br&gt;\comparisoncolumn{Example}{Example}&lt;br&gt;\end{comparison}&lt;br&gt;\end{frame}</code> |
| `evidenceslide` | `m` | `claim` (text, required) — The claim; content is the supporting evidence, visually separated from it. | Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{evidenceslide}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{evidenceslide}&lt;br&gt;\end{frame}</code> |
| `fullvisual` | `O{} O{}` | `caption` (text, optional=) — Optional caption, typeset the same way a diagram's is.<br>`source` (text, optional=) — Optional source line. | Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{fullvisual}[][]&lt;br&gt;Example content.&lt;br&gt;\end{fullvisual}&lt;br&gt;\end{frame}</code> |
| `herometric` | `m m` | `value` (text, required) — The number, dominating the frame.<br>`label` (text, required) — What the number is. | Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{herometric}{Example}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{herometric}&lt;br&gt;\end{frame}</code> |
| `messageslide` | `m` | `headline` (text, required) — The one assertion this slide makes. | Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{messageslide}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{messageslide}&lt;br&gt;\end{frame}</code> |
| `referenceslide` | `m O{}` | `title` (text, required) — Compact heading for the references frame.<br>`note` (text, optional=) — Optional usage or limitation note. | Content only; wrap in \begin{frame}...\end{frame}.<br>Use 3–8 referenceitem calls; more than eight emits a hard overflow diagnostic and should continue on another slide.<br>Reference items use the theme-owned source font and are never silently shrunk below it. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{referenceslide}{Sources and use}[Short usage note.]&lt;br&gt;\referenceitem{Author (2026), Title. \\url{https://example.com}}&lt;br&gt;\end{referenceslide}&lt;br&gt;\end{frame}</code> |
| `sectiondivider` | `O{Section} m` | `eyebrow` (text, optional=Section) — Optional small label above the section title; defaults to Section.<br>`title` (text, required) — Section title, also registered as a \section for the PDF outline/bookmarks. | Content only; wrap in \begin{frame}[plain]...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}[plain]&lt;br&gt;\begin{sectiondivider}[Section 01]{Example}&lt;br&gt;\end{sectiondivider}&lt;br&gt;\end{frame}</code> |
| `tableslide` | `O{right} m m` | `position` (options, optional=right) — left or right: which side the table (this environment's content) renders on. Default right.<br>`heading` (text, required) — Heading for the text column.<br>`body` (text, required) — Supporting insight text for the text column. | Same layout as visualtext; named separately so an author or agent authoring a table slide finds it directly.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{tableslide}[right]{Example}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{tableslide}&lt;br&gt;\end{frame}</code> |
| `threepart` | `` | — | Content must be exactly three \threepartcolumn calls.<br>Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{threepart}&lt;br&gt;\threepartcolumn{Example}{Example}&lt;br&gt;\threepartcolumn{Example}{Example}&lt;br&gt;\threepartcolumn{Example}{Example}&lt;br&gt;\end{threepart}&lt;br&gt;\end{frame}</code> |
| `titleslide` | `` | — | Content only; wrap in \begin{frame}[plain]...\end{frame}.<br>Reads \title/\subtitle/\author/\date and reportkit-core's \rk@leftheader (set with \setreportkitleftheader); set those before use, as with the paged renderer's \maketitle. | stable since 1.9.3 | <code>\begin{frame}[plain]&lt;br&gt;\begin{titleslide}&lt;br&gt;\end{titleslide}&lt;br&gt;\end{frame}</code> |
| `visualtext` | `O{right} m m` | `position` (options, optional=right) — left or right: which side the visual (this environment's content) renders on. Default right.<br>`heading` (text, required) — Heading for the text column.<br>`body` (text, required) — Supporting text for the text column. | Content only; wrap in \begin{frame}...\end{frame}. | stable since 1.9.3 | <code>\begin{frame}&lt;br&gt;\begin{visualtext}[right]{Example}{Example}&lt;br&gt;Example content.&lt;br&gt;\end{visualtext}&lt;br&gt;\end{frame}</code> |

### Command primitives

| Name | Signature | Arguments | Constraints | Stability | Canonical example |
| --- | --- | --- | --- | --- | --- |
| `RKBibliography` | `O{}` | `title` (text, optional=) — Optional heading; defaults to bibliography.title or the publication type's references title. | publication.yaml must declare bibliography.file; otherwise RK_BIBLIOGRAPHY_UNCONFIGURED.<br>Cite only entries that exist in the .bib file. | experimental since 1.11.0 | <code>\RKBibliography</code> |
| `RKContents` | `O{}` | `title` (text, optional=) — Optional heading; defaults to the publication type's contents title. | Call at most once; it reads the contents file. | experimental since 1.11.0 | <code>\RKContents</code> |
| `carditem` | `O{} m m` | `variant` (options, optional=) — plain, surface, accent-rail, numbered, or emphasis; defaults to the parent grid variant.<br>`heading` (text, required) — Card heading.<br>`body` (text, required) — Dense evidence text. | Use inside cardgrid.<br>Only plain, surface, accent-rail, numbered, and emphasis are supported. | stable since 1.9.3 | <code>\carditem[accent-rail]{Heading}{Evidence}</code> |
| `comparisoncolumn` | `m m` | `heading` (text, required) — Column heading.<br>`body` (text, required) — Column content. | Only valid inside a comparison environment. | stable since 1.9.3 | <code>\comparisoncolumn{Example}{Example}</code> |
| `referenceitem` | `m` | `reference` (text, required) — One short source or reference entry. | Only valid inside referenceslide. | stable since 1.9.3 | <code>\referenceitem{Author (2026), Title.}</code> |
| `threepartcolumn` | `m m` | `heading` (text, required) — Column heading.<br>`body` (text, required) — Column content. | Only valid inside a threepart environment. | stable since 1.9.3 | <code>\threepartcolumn{Example}{Example}</code> |

<!-- REPORTKIT-CONTRACT:END -->
