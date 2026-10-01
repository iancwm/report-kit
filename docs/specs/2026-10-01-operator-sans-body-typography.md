# Operator theme: sans-serif body typography

**Status:** Implemented-pending-verification  
**Date:** 2026-10-01  
**Scope:** `operator` theme for paged technical reports

## Problem

The operator theme uses sans-serif titles, headings, tables, captions, and page
furniture, but its running prose uses Latin Modern Roman. In a prose-heavy
publication, the serif body dominates the page and the result does not read as
the intended operator look. For example, the two-page Maya operations article
selects `technical-report` × `operator`, yet approximately 89% of its extracted
text characters use Latin Modern Roman.

This is a theme contract mismatch, not a theme-selection or font-installation
failure. The current operator spec explicitly requires Roman body prose in
decision O2 and acceptance criterion AC3. The LaTeX theme loads `lmodern`
without changing LaTeX's default Roman text family; the paged adapter applies
`\sffamily` only to selected elements. The Python theme likewise declares
`typography.body` and the Latin-script body stack as Latin Modern Roman.

## Decision

Make **Latin Modern Sans the default text family for the entire operator
theme**, including ordinary paragraphs, lists, footnotes, source notes,
captions, callout body copy, and ordinary text inside tables. Keep Latin Modern
Mono for code, terminal, and diff content. Mathematical typesetting may retain
its existing math font; explicit author requests for Roman text remain possible.

This replaces the Roman-body part of O2 and AC3 in
`docs/superpowers/specs/2026-09-30-reportkit-operator-theme-spec.md`. The
pdfLaTeX, T1, and `lmodern` decisions remain. The operator theme remains a
single visual system across TeX and Markdown input.

### Why theme-wide

A publication-local font override would make the Maya article look different
while leaving every other prose-heavy operator publication with the same
problem. A theme-level default expresses the intended visual system once and
also reaches ordinary text emitted by both TeX and Markdown authors. Do not
change the defaults of other themes or the shared `reportkit.cls`.

## Required changes

1. In `latex_templates/themes/reportkit-theme-operator.sty`, select Latin
   Modern Sans as the operator theme's default text family after loading
   `lmodern`. Preserve T1 encoding and pdfLaTeX. Scope the selection to this
   theme package; do not use a shared-core or publication-specific override.
2. In `python_scripts/reportkit/themes/operator.py`, set
   `TYPOGRAPHY.body` and the `Latn` `ScriptFontStack.body` to Latin Modern
   Sans. Keep display, heading, metadata, table, and chart as Sans and mono
   as Latin Modern Mono. If any body-font declaration elsewhere is derived
   from these tokens, update it consistently.
3. Update `references/operator-theme.md` and the original operator spec's
   O2 and AC3 so the published authoring contract and acceptance gate describe
   a sans body. Record this as a deliberate typography revision, not a
   fallback caused by missing fonts.
4. Review operator-specific font tokens that use `\normalfont` or inherit the
   default family, especially book body/reference tokens if that pairing is
   enabled later. They must resolve to the sans default under `operator`.
   Explicit `\sffamily` tokens may remain for clarity. Preserve `\ttfamily`
   execution surfaces and mathematics.
5. Rebuild the canonical operator fixture and at least one prose-heavy
   technical report. Reinspect every rendered page after the font change,
   because different glyph widths can change line breaks, table fit, and
   pagination. No fixed page count is required.

## Acceptance criteria

| ID | Criterion | Verification |
| --- | --- | --- |
| S1 | Ordinary prose in an operator PDF uses Latin Modern Sans, including regular, bold, and italic emphasis. | Inspect font names on representative prose spans in the Maya article and canonical fixture using PyMuPDF or pdfplumber. The spans must identify `LMSans`, not `LMRoman`. |
| S2 | The operator title, headings, running furniture, captions, tables, and ordinary callout text remain sans serif; terminal/diff text remains monospaced. | Inspect font names by page region or semantic element, not only the PDF's document-wide font list. |
| S3 | No unrequested Latin Modern Roman text remains in the prose-heavy sample. Explicit Roman author markup and math are exempt. | Review extracted spans and visually inspect all rendered pages. A PDF font inventory alone is insufficient because it does not locate usage. |
| S4 | Python theme typography and Latin-script font-stack metadata report Sans for body text. | Theme contract tests and `reportkit_viz check-theme --theme operator`. |
| S5 | The canonical operator fixture and prose-heavy sample compile with pdfLaTeX without font substitution errors, overfull boxes, clipped content, or stranded headings introduced by the typography change. | Run ReportKit build/check, inspect logs, and render all pages for visual review. |
| S6 | Existing non-operator theme output is unchanged. | Run theme contract tests and compare representative default/technical fixture renders against their existing visual baselines. |

## Out of scope

This revision does not change the operator palette, geometry, content
structure, semantic primitives, math typography, or font technology. It does
not add an author-facing switch between serif and sans body text. Future
operator pairings should inherit the same sans body default when supported.

## Risks and review focus

- Latin Modern Sans has different metrics from Roman. Inspect paragraph
  wrapping, table width, captions, and page breaks rather than assuming the
  existing layout still fits.
- Theme-wide font selection can affect components that currently inherit
  `\normalfont`. Confirm those results are intended, especially source notes,
  footnotes, callouts, and any book tokens exposed through the paged adapter.
- A test that merely finds `LMSans` somewhere in a PDF can pass while prose
  remains serif. Verify actual prose spans and locations.
