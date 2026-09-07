# Data Engineering Guide — Publication Review Log

**Build reviewed:** `data-engineering-guide.pdf`  
**Review date:** 2026-09-06  
**Format:** 56-page A4 PDF, generated with LaTeX/pdfTeX  
**Review status:** First visual/editorial pass; manuscript and PDF left unchanged  
**Companion planning file:** `publication-guidelines.md`

## Executive verdict

This is a strong readable draft with a coherent visual system: embedded Libertinus fonts, consistent margins, restrained blue accents, legible body text, selectable text, hyperlinks, and a useful PDF outline. It is not yet publication-ready. The most serious problems are not cosmetic: the visible table of contents is missing, section transitions occur mid-page while running headers name the next section, and at least two long paths run beyond the A4 text area and are visibly clipped. These issues can mislead readers or remove information from technical examples.

The second major gap is instructional density. The first build has nine figures across 56 pages, roughly one figure every six pages. That is enough to establish a visual style, but not enough for a guide that introduces distributed systems, storage layout, joins, event time, orchestration recovery, quality controls, governance, and capstone implementation. The next build should expand the figure set deliberately, using the priorities in `publication-guidelines.md`, while avoiding decorative filler.

The release should be treated as **blocked until all P0 items are resolved**. P1 items should be completed before public distribution; P2 items are final polish.

## Inspection method and evidence limits

- Rendered all 56 pages to PNG at 120 dpi and reviewed contact sheets for page rhythm, alignment, whitespace, hierarchy, figures, tables, and page breaks.
- Inspected representative pages at higher resolution, including pages 1, 2, 11, 13, 16–18, 20, 22–27, 29–36, 38–56.
- Used `pdfinfo`, `pdffonts`, `pdftotext -layout`, `pypdf`, and `pdfplumber` for structural checks, font embedding, outline/link checks, text extraction, and text bounding boxes.
- The PDF contains 22 outline/bookmark entries and embedded subset fonts. `pdfinfo` reports `Tagged: no`, and title, author, subject, and keyword metadata are blank.
- No source build log was supplied. This review therefore evaluates the rendered artifact and its extracted structure, not the reproducibility of the build toolchain.

## Priority rubric

- **P0 — release blocker:** incorrect, clipped, or materially misleading output; fix before sharing publicly.
- **P1 — publication quality:** important for navigation, accessibility, consistency, or sustained reading; fix in the next build.
- **P2 — polish:** worthwhile refinements after correctness and structure are stable.

## Issue log

### P0-01 — Add a real contents page and complete front matter

**Pages:** 1; affects the whole book  
**Evidence:** Page 1 moves from the title, Preface, and Reader’s Roadmap directly into Section 1. The roadmap text says that a generated publication table of contents is authoritative, but no visible `Contents`/`Table of Contents` page appears in the PDF text or rendered pages. The PDF outline exists, but bookmarks are not a substitute for a printed contents page or a stable page-numbered ebook navigation page.

**Why it matters:** A reader cannot scan the book, see page numbers, or understand the publication structure before entering the first section. The current page also carries a Section 1 running header while it is still front matter.

**Recommendation:** Build explicit front matter in this order: cover, half-title or title page, copyright/licence and disclaimer, acknowledgements (if applicable), Preface, contents, then Section 1. Use Roman numerals for front matter and Arabic numbering from Section 1. Keep PDF bookmarks and add clickable contents entries with page numbers.

**Acceptance check:** A rendered `Contents` page is present, its page numbers match the final PDF, every H1 appears once, and every entry links to the correct section.

### P0-02 — Make each H1 a true section opener and repair running headers

**Pages:** 1, 11, 17, 25, 40, 45, 48, 54, 55, 56  
**Evidence:** H1 sections begin in the middle of pages. For example, page 17 begins with the tail of ingestion before Section 3; page 25 begins with storage before Section 4; page 40 contains the end of orchestration before Section 6; page 56 contains the end of the glossary before Section 11. The running header changes early, so page 17 is labelled “Section 3 - Data Storage” while its top content is still ingestion. The same mismatch occurs at several later boundaries.

**Why it matters:** Readers use running heads to orient themselves. A header naming a section that is not yet on the page is semantically wrong and makes the book feel mechanically assembled. Orphaned H1s and large residual whitespace also create an uneven reading rhythm.

**Recommendation:** Force a page break before every H1 (`\\clearpage`/`\\newpage`, or a chapter-like heading command). Configure marks from the actual section heading and suppress section headers on the cover and front matter. Decide whether section openers use a consistent top treatment (for example, a larger title, short purpose statement, and optional key-outcomes box).

**Acceptance check:** Every H1 starts at the top of a new page; no page contains a running header for a section that has not begun; the glossary and references each have an unambiguous start.

### P0-03 — Remove text overflow and clipping from long paths

**Pages:** 16 and 44  
**Evidence:** High-resolution rendering shows the S3 path in page 16, numbered step 4, cut off at the right edge. The quarantine path in page 44, checklist item 8, is also visibly truncated. Bounding-box analysis confirms characters extending beyond the 595.276 pt A4 media box (approximately x=920 on page 16 and x=682 on page 44).

**Why it matters:** The reader cannot recover the complete URI. In a technical guide, an incomplete path is both a visual defect and a potentially invalid implementation example.

**Recommendation:** Prefer short, breakable logical examples such as `s3://crypto-lake/raw/trades/{event_date}/{event_hour}/...`. When the full URI is pedagogically necessary, typeset it with a breakable path/URL macro (`\\url`, `\\path`, or a dedicated `\\texttt` macro with `\\allowbreak` at `/`, `=`, and `_`). Do not rely on an unbreakable monospaced inline span.

**Acceptance check:** A text-bounding-box check finds no glyph outside the media box, and 200–300 dpi renders show every path in full without crossing the margin.

### P0-04 — Remove release-inappropriate “draft” signalling

**Pages:** all pages  
**Evidence:** The footer reads `A Practical Guide to Data Engineering · draft` throughout the PDF. The supplied artifact also starts with an interior title page rather than a cover, while a separate A4 cover asset exists in the workspace.

**Why it matters:** Publishing a free ebook with a draft footer undermines reader confidence and creates ambiguity about which build is citable. A title page without a cover, edition, author, and licence also makes the distribution package incomplete.

**Recommendation:** Replace `draft` with a deliberate release identifier such as `Version 1.0 · September 2026`, or remove the status marker. Include the A4 cover in the PDF/package and add title, author, edition/version, publication date, licence, disclaimer, and contact/project URL as front matter.

**Acceptance check:** The release candidate contains no accidental draft labels, has a consistent title/author/version identity, and opens with the intended cover or an explicit cover file in the distribution package.

### P1-01 — Balance table breaks and provide publication-grade table captions

**Pages:** 11, 22, 44–45, 51–52  
**Evidence:** The “Tools and Technology Landscape” table leaves only its final “Serving and consumption” row on page 52. The “Capstone Milestone Map” on page 44 is dense across four columns. Other tables begin close to a page bottom, reducing breathing room. Text extraction contains figure captions but no numbered table captions.

**Why it matters:** A one-row continuation looks accidental and makes scanning harder. Without captions and numbers, tables cannot be cited reliably in prose or referenced from a future LaTeX contents/list-of-tables system.

**Recommendation:** Number and caption substantive tables (`Table 1`, `Table 2`, …) and reference them in the text. Use `booktabs` plus `tabularx`/fixed-width columns for predictable wrapping, and `longtable` only where a split is unavoidable. Keep each caption, header, and at least two body rows together; repeat the header on continued pages. Reduce column count or split dense tables; use a landscape page only when it genuinely improves comprehension.

**Acceptance check:** No table has a stranded single row; continued tables repeat their header; every substantive table has a concise caption, label, and cross-reference.

### P1-02 — Improve figure scale, density, and source statements

**Pages:** figures on 2, 13, 20, 26, 34, 41, 46, 49, and 54  
**Evidence:** Figures 1, 2, 4, and 5 are narrow vertical diagrams centred on the page with substantial unused horizontal space. Their labels are readable but small relative to the page. Figure 6 is clear but has a large empty centre and small labels. Figure 8 is generally clear, but “Application or workload” wraps awkwardly in its left cell. Every figure uses the generic source line `Source: Conceptual diagram.`

**Why it matters:** Excess whitespace makes diagrams feel detached from the argument and forces small type where a wider, simpler composition could be clearer. Generic source wording does not tell the reader whether a figure is original, adapted, or reproduced.

**Recommendation:** Size each figure to the information it carries. Widen or recompose narrow flows, remove non-functional empty space, increase label size and contrast, and use consistent node widths and arrow weights. Rework Figure 8’s label cell so the phrase wraps intentionally. Replace generic source lines with `Source: Author’s synthesis.` for original artwork or a complete citation for adapted material. Add concise descriptive alt text in the source/LaTeX layer and cross-reference every figure from nearby prose.

**Acceptance check:** Figures remain legible at normal ebook zoom and in print, have consistent numbering/captions/source attribution, and each has a meaningful text alternative.

### P1-07 — Add high-value mechanism figures where prose carries too much cognitive load

**Pages:** whole document; especially Sections 2-8  
**Evidence:** The current PDF uses one anchor figure per major section. The prose explains several concepts that are difficult to understand from text alone: delivery semantics, CDC versus polling, partition pruning, small-file compaction, one-to-many join multiplication, event time and watermarks, retry/recovery states, quality reconciliation, data contracts, and serving surfaces.

**Why it matters:** These topics require the reader to track time, state, cardinality, or physical data layout. Tables and paragraphs can name the concepts, but they do not show how records move, duplicate, wait, get skipped, fail, recover, or become trustworthy. Without visual help, the reader has to hold too much invisible machinery in working memory.

**Recommendation:** Add a purposeful second wave of figures. Target roughly **16-19 total figures** for a 56-page A4 ebook, not as a quota but as a density range. Keep the existing section anchor figures where they work, then add mechanism/failure figures for the concepts most likely to confuse readers.

High-priority additions:

| Priority | Section | Figure | Purpose |
| --- | --- | --- | --- |
| Tier 1 | Section 4 | Join cardinality before/after | Show how one-to-many joins multiply rows and change grain. |
| Tier 1 | Section 4 | Event time versus processing time | Explain late events, watermarks, and window closure visually. |
| Tier 1 | Section 3 | Partition pruning and small files | Show why layout affects cost and query performance. |
| Tier 1 | Section 2 | CDC versus polling | Contrast transaction-log capture with timestamp queries, including deletes. |
| Tier 1 | Section 5 | Task recovery state diagram | Show scheduled, running, retrying, failed, succeeded, and skipped states. |
| Tier 1 | Section 6 | Quality control points | Place schema, freshness, volume, reconciliation, and anomaly checks in the pipeline. |
| Tier 1 | Section 7 | Data-contract anatomy | Connect producer, schema, grain, freshness, ownership, and consumers. |
| Tier 1 | Section 9 | Capstone reference architecture | Show the complete learner project from source through serving and monitoring. |

Secondary additions:

| Priority | Section | Figure | Purpose |
| --- | --- | --- | --- |
| Tier 2 | Section 2 | Batch versus streaming timeline | Make latency, compute cadence, and freshness visible. |
| Tier 2 | Section 2 | Backpressure rate/queue plot | Show input rate, output rate, and queue growth. |
| Tier 2 | Section 3 | Row versus column storage layout | Explain scan efficiency without relying on prose. |
| Tier 2 | Section 5 | Backfill interval timeline | Show reruns, catch-up windows, and idempotent replacement. |
| Tier 2 | Section 6 | Reconciliation flow | Show source totals, landed totals, transformed totals, and exception handling. |
| Tier 2 | Section 7 | Serving surfaces | Compare dashboard, API, feature store, extract, and reverse ETL outputs. |
| Tier 2 | Section 8 | Observability signal map | Place logs, metrics, traces, lineage, alerts, and run metadata. |

Use a varied visual grammar: timelines for time, state diagrams for retries and recovery, physical layouts for files and partitions, before/after diagrams for cardinality, control-point diagrams for quality and governance, and reference architecture diagrams for the capstone. Do not turn every figure into a vertical box-and-arrow flow.

**Acceptance check:** Each new figure has a semantic source filename under `assets/diagrams/`, a stable figure ID, caption, source statement, and alt text. Every figure is referenced from nearby prose and adds information that would be harder to communicate as a table.

### P1-03 — Add accessible PDF structure and complete metadata

**Pages:** whole document  
**Evidence:** `pdfinfo` reports `Tagged: no`; `Title`, `Author`, `Subject`, and `Keywords` are empty. The file is not encrypted and fonts are embedded/subset, which are good foundations. Bookmarks and hyperlinks are present.

**Why it matters:** Untagged PDFs are difficult to navigate with screen readers and do not expose reliable heading, figure, table, or reading-order semantics. Blank metadata harms search, citation, library indexing, and ebook cataloguing.

**Recommendation:** Use a tagging-capable LaTeX workflow/class where feasible; declare document language, heading hierarchy, figure alt text, table headers, and logical reading order. Set PDF metadata (`pdftitle`, `pdfauthor`, `pdfsubject`, `pdfkeywords`, and display-document-title settings). Preserve bookmarks and link destinations after every rebuild. Consider a PDF/A profile only if it does not compromise tagging or hyperlinks.

**Acceptance check:** A PDF accessibility checker reports tagged headings and reading order, figures expose alt text, links have meaningful labels, and `pdfinfo` contains complete release metadata.

### P1-04 — Give references a consistent bibliographic treatment

**Pages:** 56  
**Evidence:** The references are a short list of author/title pairs with inconsistent publication details and a raw Databricks URL. There are no years, editions, publishers, access dates, or hanging indents applied consistently.

**Why it matters:** Readers need to identify and retrieve sources, and a public technical book should make its evidence trail citable. Raw long URLs also create avoidable line-breaking and visual noise.

**Recommendation:** Choose one citation style and apply it uniformly. Add publication year, edition/publisher where relevant, stable URLs or DOIs, and access dates for web material. Use hanging indents and clickable short titles; keep the full URL in the link target rather than exposing an unwieldy string in running text. If the guide is released under an open licence, add a separate attribution/licensing note for quoted or adapted material.

**Acceptance check:** Every reference has enough information to locate the source, all web references have a stable link and access date, and the reference list has consistent indentation and punctuation.

### P1-05 — Separate glossary and references cleanly

**Pages:** 55–56  
**Evidence:** Page 56 is headed “Section 11 - References” but begins with the final glossary entries from Section 10 before the references heading appears lower on the page.

**Why it matters:** This is another navigation and running-header mismatch, and it makes the end matter look unfinished.

**Recommendation:** Start the glossary and references on separate pages (or use distinct unnumbered end-matter headings with explicit page breaks). Keep the running head aligned with the content actually occupying the page.

**Acceptance check:** No glossary definition appears under a References header, and the first reference begins on a page whose header identifies the references section.

### P1-06 — Make short code blocks and examples page-safe

**Pages:** 23–24 and 31–32  
**Evidence:** Short SQL/code examples begin near the bottom of one page and continue on the next. The continuation is understandable, but there is no explicit continuation marker.

**Why it matters:** Code is read as a single unit. A split block increases the chance that a reader misses the first line or mistakes the continuation for a new example.

**Recommendation:** Keep short blocks together with a `samepage`/minipage-style wrapper where possible. For longer blocks, add a caption such as “Listing 2 (continued)” and repeat a compact context line. Ensure code remains selectable and does not depend on colour alone.

**Acceptance check:** Short listings are not split; unavoidable splits are marked and preserve line numbering/context.

### P2-01 — Improve page rhythm and intentional whitespace

**Pages:** especially 19, 22, 25, 36, and 48  
**Evidence:** Several pages have generous unused lower-page space, often adjacent to a mid-page section transition or a narrow diagram. Page 25 is particularly unbalanced: the Section 4 heading appears after a short storage tail, leaving a large blank area below.

**Recommendation:** Fix structural page breaks first, then rebalance floats and paragraphs. Use the recovered space for a short “Key takeaways” box, a figure enlarged to a readable width, or a deliberate section-opener treatment. Avoid filling space merely to eliminate white space; quiet pages are useful when they signal a new unit.

**Acceptance check:** The post-break layout has a repeatable opener rhythm, no accidental half-empty pages, and no figures or tables reduced solely to force a fit.

### P2-02 — Validate colour and small-text contrast in print and grayscale

**Evidence:** Body text is highly legible, but the light blue running headers/footers and syntax colours should be checked against accessibility contrast requirements and a grayscale print proof.

**Recommendation:** Keep syntax highlighting redundant with typography or labels, darken low-contrast metadata text if needed, and check a representative page at 100% print size and in grayscale.

**Acceptance check:** Body, header/footer, links, code, captions, and table rules remain distinguishable in colour and grayscale without relying on hue alone.

### P2-03 — Clarify title-page identity and edition language

**Page:** 1  
**Evidence:** The title page repeats “DATA ENGINEERING GUIDE” in the running header and body, shows a date, but does not visibly identify an author, edition, licence, or project URL.

**Recommendation:** Establish one canonical title, subtitle, author/publisher credit, edition/version, and publication date. Move the running header off the title page and reserve the title treatment for the cover/title page.

**Acceptance check:** The title page alone tells a reader what the book is, who produced it, and which edition they are holding.

## What is already working

- The serif body type and sans-serif running furniture create a clear, restrained hierarchy.
- A4 margins, footer alignment, and page-number placement are visually consistent across the build.
- Ordinary prose has no obvious overlapping text, broken glyphs, or figure collisions in the inspected pages.
- Figures are centred, numbered 1–9, and captions are generally readable.
- Tables use a consistent minimalist rule treatment and do not show widespread cell overflow.
- Code blocks have a stable monospaced grid and useful syntax differentiation.
- The PDF retains selectable text, hyperlinks, bookmarks, and embedded fonts; these should be preserved in the next build.

## Recommended next-build order

1. Fix section/page-break logic and running marks (P0-02, P1-05).
2. Add the full front matter and visible contents page (P0-01, P0-04, P2-03).
3. Repair all overfull paths and run an automated bounding-box check (P0-03).
4. Reflow and caption tables; then resize/recompose existing diagrams (P1-01, P1-02).
5. Add the Tier 1 mechanism figures from P1-07 and `publication-guidelines.md`.
6. Add tagging, alt text, language, and metadata; verify links/bookmarks (P1-03).
7. Normalize references and end matter (P1-04).
8. Revisit code splits, colour contrast, page rhythm, and Tier 2 figures (P1-06, P2-01, P2-02).
9. Render a final proof at print resolution and inspect every page, not only contact sheets.

## Implementation update — P0-01 (2026-09-06)

**Status:** Addressed on `main` for the current source build.

- The combined builder now creates a title page, a publication-details page,
  Roman-numbered front matter, a generated linked `Contents` page, and Arabic
  numbering from Section 1 onward.
- The generated PDF now carries title, author, subject, keyword, language, and
  project URL metadata. The front matter states the CC BY 4.0 coverage,
  separate licensing for code and third-party assets, and an educational-use
  disclaimer.
- The root cause of the missing contents page was a tooling gap: the source
  YAML declared `toc: true`, but the body-only Pandoc pipeline never emitted
  `\\tableofcontents`. The fix is in the shared guide template and builder,
  with a regression test for the combined body plan.
- The new build was exercised with the source validator, 18 unit tests, all
  nine isolated section builds, and the 60-page combined PDF. The contents
  page contains all 11 main-section entries and its PDF links target the
  corresponding section pages.

**Flagged follow-up:** The review says an A4 cover asset already exists, but no
cover asset is currently present in this checkout. The title page is therefore
the current opening page; an actual cover remains part of P0-04/P2-03 rather
than being fabricated during this pass.

## Claude Code implementation prompt

Use this section as the handoff prompt for the next implementation agent.

```text
You are improving the first PDF build of "A Practical Guide to Data Engineering" toward publication quality.

Read these files first:
- data-engineering-guide-publication-review.md
- publication-guidelines.md
- data-engineering-guide.md
- manuscript/order.txt and the component files under manuscript/

Primary objective:
Create a cleaner second build of the ebook source. Do not build the PDF unless explicitly asked; focus on source, layout configuration, diagram source files, and reproducible build readiness.

Work in this order:
1. Fix P0 release blockers from the publication review:
   - add complete front matter and a visible linked contents page;
   - force every H1/main section to begin on a fresh page;
   - repair running headers so they match the content on the page;
   - remove or replace draft footer text;
   - make long paths and inline code break safely.
2. Improve publication structure:
   - add title/author/version/licence/disclaimer metadata;
   - separate glossary and references cleanly;
   - normalize references into one bibliographic style.
3. Improve tables and listings:
   - add table captions, labels, and references;
   - prevent stranded single-row table continuations;
   - keep short code listings together where possible.
4. Implement the Tier 1 figure backlog from the review and publication guide:
   - join cardinality before/after;
   - event time versus processing time/watermarks;
   - partition pruning and small-files/compaction;
   - CDC versus polling;
   - task recovery state diagram;
   - quality control points;
   - data-contract anatomy;
   - capstone reference architecture.
5. Use the diagram conventions in publication-guidelines.md:
   - place editable sources under assets/diagrams/;
   - use semantic filenames and figure IDs;
   - provide captions, source statements, and alt text;
   - vary visual grammar instead of using only vertical flowcharts;
   - keep the capstone visual layout consistent across the book.
6. Run source-level validation:
   - check Markdown heading hierarchy;
   - check that figure/table references resolve;
   - check that no line contains unbreakable long paths likely to overflow;
   - check that all required diagram files exist.

Deliverables:
- Updated manuscript/source files.
- Updated or new diagram source files.
- A concise change log listing every publication-review issue addressed, partially addressed, or deferred.
- Any recommended follow-up tasks that require PDF rendering or visual QA.

Do not remove user-authored content unless replacing it with a clearer equivalent. Preserve the component manuscript structure and recombine workflow.
```

## Release gate

Before calling the book a release candidate, require all of the following:

- no text or rule extends outside the media box;
- every H1, glossary, and references section starts where its header says it does;
- a visible, linked contents page agrees with the outline/bookmarks;
- no accidental `draft` labels remain;
- tables and figures are numbered, captioned, attributed, and cross-referenced;
- the figure set covers the high-cognitive-load concepts identified in P1-07;
- all figure sources use semantic filenames and preserve editable source assets;
- metadata is populated and accessibility/tagging has been checked;
- the cover, licence, disclaimer, and version identity are present in the distribution package;
- a clean 100% print/grayscale proof has been reviewed.
