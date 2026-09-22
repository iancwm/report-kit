# ReportKit Presentation Typography and Composition Refinement

Implementation specification from visual review · 22 September 2026

**Status:** Proposed  
**Last updated:** 2026-09-22  
**Priority:** P0 for headline hierarchy and the general-purpose assertion composition; P1/P2 for density and polish follow-ons.  
**Scope:** The stable `presentation × slides × executive` target. This is a refinement of the Phase C baseline, not a new visual family.  
**Related architecture:** [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](2026-09-09-reportkit-multi-format-publication-architecture-spec.md)

## Executive summary

Visual review of a practical, information-dense presentation exposed a mismatch between ReportKit's stable executive slide system and a common consulting/strategy use case.

The current presentation system is strongest when a frame carries one large message. Its default message headline is deliberately large (`23/27pt`) and works for closing recommendations and sparse assertion slides. The same scale becomes inefficient when a slide also needs a process, matrix, timeline, comparison, six-card grid, or other substantial evidence. In those cases the heading consumes too much of the 160 × 90 mm canvas and forces the body into avoidable compression.

The core problem is therefore not "make all titles smaller." It is that ReportKit currently lacks a first-class distinction between:

1. a **hero message** whose job is to dominate the frame, and
2. a **standard assertion** whose job is to orient the reader while leaving most of the frame to evidence.

This spec introduces that distinction without breaking the renderer/theme/publication-type separation established by the multi-format architecture.

The first release slice is intentionally narrow:

> retain the existing hero message scale; add a smaller standard assertion scale; add a bounded `assertionslide` composition; add deterministic headline-fit validation; and add dense-slide regression fixtures.

Secondary work improves body density, source legibility, grid composition, and references slides after the P0 hierarchy is stable.

---

## 1. Problem statement

### 1.1 Evidence from the rendered deck

A visual review of an 11-slide practical guide showed these recurring issues:

| Slide pattern | Visible issue | Template implication |
| --- | --- | --- |
| Assertion + 2×2 evidence grid | Headline block takes a disproportionate share of vertical space | Standard evidence slides need a smaller assertion role |
| Assertion + four-step process | Process boxes are compressed after the headline/deck region | Header region needs a bounded height |
| Assertion + three capability cards | Cards become visually subordinate to the headline even though the cards contain the evidence | Headline/body hierarchy is too aggressive |
| Assertion + three paired comparison rows | Supporting content is pushed toward small local type | Body should not compensate for headline oversizing |
| Assertion + six-rule grid | Dense body fits only by shrinking text aggressively | Add a dense grid composition and a standard assertion scale |
| Diagram + assertion | Diagram is made smaller than necessary to coexist with the headline | Evidence canvas should dominate standard slides |
| Sources / usage | Slide reads like a paged report rather than a presentation | Add a references-oriented slide composition |

The review also showed that the title slide itself is not the main problem. A `29/33pt` title on a title frame is defensible. The defect is using a `23/27pt` message role as the de facto headline for slides that also carry substantial evidence.

### 1.2 Important review caveat

The inspected PDF was a design-token reproduction rather than a direct ReportKit LaTeX compile. Kicker/headline collisions visible in that reproduction are therefore **not** treated as evidence of a native ReportKit layout defect.

This spec addresses the issues that are attributable to the actual template contract:

- relative type scale,
- absence of a standard assertion role,
- lack of a bounded assertion header,
- lack of deterministic fit rules,
- weak support for dense card/grid slides,
- very small source/footer type,
- absence of a dedicated references composition.

Any implementation must validate against a native `reportkit build` output, not against the reproduction.

---

## 2. Design principles

### 2.1 Preserve the architecture split

The existing architecture remains binding:

- **publication type** owns semantic structures;
- **theme adapter** owns presentation sizes, spacing, density, and visual values;
- **renderer** owns frame mechanics;
- **content** remains independent of all three.

Therefore:

- `reportkit-presentation.sty` may introduce `assertionslide`, grid compositions, and validation-facing semantic roles;
- `reportkit-theme-executive-slides.sty` owns the actual point sizes and header envelope values;
- no presentation composition may test `theme=executive`;
- no executive adapter may define domain-specific content semantics.

### 2.2 Evidence should dominate ordinary working slides

For a standard assertion/evidence slide, the header is an orientation device, not the principal visual.

Target geometry:

- standard header envelope: **22–26 mm maximum** after the top safe margin;
- remaining usable area: **at least ~64% of the safe-area height** for body/evidence in the normal case;
- a headline that cannot fit the standard envelope must downshift to the compact scale or fail validation rather than silently compress the evidence.

This rule does not apply to `messageslide`, `titleslide`, `sectiondivider`, or a deliberate closing slide.

### 2.3 Prefer rewriting over microscopic type

ReportKit must not solve an overfull slide by shrinking body content below a legibility floor.

The fallback order is:

1. use standard assertion scale;
2. use compact assertion scale when the title wraps;
3. reject an overlong assertion and ask the author/agent to rewrite;
4. split the slide if the body still exceeds the body envelope.

Do not introduce arbitrary continuous font scaling.

---

## 3. Current state to preserve

The current executive slide adapter defines these presentation roles:

| Token | Current value |
| --- | --- |
| `RKTokPresentationKickerFont` | `8.5/10.5pt` |
| `RKTokPresentationTitleFont` | `29/33pt` |
| `RKTokPresentationSubtitleFont` | `12/15pt` |
| `RKTokPresentationDividerTitleFont` | `35/39pt` |
| `RKTokPresentationMessageFont` | `23/27pt` |
| `RKTokPresentationBodyFont` | `11.5/15pt` |
| `RKTokPresentationCaptionFont` | `7.5/9pt` |
| `RKTokPresentationColumnHeadingFont` | `12.5/15pt` |
| `RKTokPresentationClosingFont` | `25/29pt` |

The current `messageslide` uses `RKTokPresentationMessageFont` for its single assertion. That behavior is stable and remains appropriate for hero-message frames.

The current system does **not** expose a separate standard-assertion token or a general-purpose assertion-with-body composition.

---

## 4. P0 workstream A — split hero messages from standard assertions

### A1. Keep `messageslide` as the hero composition

Do not silently shrink `messageslide`.

Its purpose is a sparse frame whose message is the visual:

```latex
\begin{frame}
  \begin{messageslide}{Approve the governed decision layer as the 2027 platform priority.}
    Optional short supporting copy.
  \end{messageslide}
\end{frame}
```

The existing `RKTokPresentationMessageFont` remains the hero-message role. The executive theme may retain approximately `23/27pt`.

This preserves the canonical Phase C fixture's closing recommendation and avoids a breaking visual change.

### A2. Add standard and compact assertion tokens

Add new presentation-composition tokens to `reportkit-core.sty`:

```latex
\newcommand{\RKTokPresentationAssertionFont}{...}
\newcommand{\RKTokPresentationAssertionCompactFont}{...}
\newcommand{\RKTokPresentationAssertionDeckFont}{...}
\newcommand{\RKTokPresentationAssertionHeaderMaxHeight}{...}
```

Populate them in `reportkit-theme-executive-slides.sty`.

Initial executive targets:

| Role | Target |
| --- | --- |
| Standard assertion | **18.5/22pt** |
| Compact assertion | **16.5/20pt** |
| Assertion deck | **9.5–10.5/12–13pt** |
| Header maximum | **24 mm** initially; tune within 22–26 mm from fixture review |

These values are normative targets, not immutable magic numbers. The reviewed fixture decides the exact release values.

### A3. Do not overload `ColumnHeadingFont`

A slide assertion is not a column heading. Do not reuse `RKTokPresentationColumnHeadingFont` to avoid adding tokens.

The semantic hierarchy must remain explicit:

```
title / divider
hero message
standard assertion
compact assertion
column heading
body
caption / source
```

This is important for future themes and for machine-readable capability discovery.

---

## 5. P0 workstream B — add `assertionslide`

### B1. Purpose

Add a general-purpose working-slide composition that provides:

- optional kicker;
- one assertion;
- optional one-sentence deck;
- a bounded header region;
- an unrestricted content body below the header.

This is the default composition for slides where the evidence, not the title, should dominate.

### B2. Proposed TeX API

Preferred authoring form:

```latex
\begin{frame}
  \begin{assertionslide}
    [kicker={Parenting constitution}]
    {Six household rules prevent most major unforced errors.}
    [Agree on these before you are tired, stressed, or negotiating in front of the child.]

    % arbitrary evidence/body
  \end{assertionslide}
\end{frame}
```

If nested optional arguments make the public contract brittle, use xparse keys or a helper command. The semantic contract matters more than exact syntax.

Required inputs:

| Field | Required | Meaning |
| --- | --- | --- |
| assertion | yes | the one claim the slide makes |
| kicker | no | small navigation/context label |
| deck | no | one short supporting sentence |
| body | yes in normal use | evidence canvas |

### B3. Composition contract

The header must have deterministic spacing.

Recommended order:

```
kicker
1.5–2.0 mm gap
assertion
1.5–2.0 mm gap
deck (if present)
3–4 mm gap or rule
body
```

Constraints:

1. header maximum comes from `RKTokPresentationAssertionHeaderMaxHeight`;
2. body begins at a stable vertical coordinate for a given header class;
3. the composition does not use `\vfill` to make header/body placement depend on body size;
4. no body content may overlap the reserved header;
5. if the assertion cannot fit the envelope at compact scale, validation fails.

### B4. Why this should not replace `evidenceslide`

`evidenceslide` has explicit rhetorical semantics:

> CLAIM → divider → EVIDENCE

That structure remains useful.

`assertionslide` is a more general consulting/strategy canvas:

> context → assertion → optional deck → arbitrary evidence

Do not alias one to the other.

---

## 6. P0 workstream C — deterministic headline fitting

### C1. Required fit states

Every `assertionslide` assertion resolves to exactly one of:

```
standard
compact
invalid
```

There is no fourth state that scales text to an arbitrary size.

### C2. Fit behavior

A standard implementation may use measured TeX box height rather than character count.

Normative behavior:

1. typeset at `RKTokPresentationAssertionFont`;
2. if the assertion fits the standard title slot, use it;
3. otherwise typeset at `RKTokPresentationAssertionCompactFont`;
4. if it fits the same bounded header, use compact;
5. otherwise issue a presentation-specific hard diagnostic.

Suggested diagnostic:

```
PRESENTATION_ASSERTION_TOO_LONG:
Assertion exceeds the compact headline envelope.
Rewrite the assertion or split the slide; body text will not be compressed.
```

Character counts may be used by an authoring preflight as an early heuristic, but the TeX/layout decision must be based on actual rendered dimensions.

### C3. Authoring guidance heuristic

Expose a non-binding writing heuristic through SKILL/docs:

- one line: ideal;
- two lines: acceptable and may use compact;
- three lines: rewrite before build unless the actual measured fit proves otherwise.

The system should teach agents to write assertions, not report-section titles.

### C4. Validation before full build

If the constrained Markdown/IR path can know the selected composition, add a preflight diagnostic for obviously long assertions before invoking TeX.

This preflight must be advisory unless it can reproduce the renderer's measurement exactly. The compiled-fit gate remains authoritative.

---

## 7. P1 workstream D — restore body hierarchy and legibility

### D1. Do not shrink the global body font to create space

The current `11.5/15pt` body role is generous for presentation use. The main problem is the header, not the body.

After the P0 headline change, review the fixture before changing the base body token.

If a dense composition legitimately needs smaller text, introduce semantic roles rather than local ad hoc `\fontsize` calls:

```latex
\RKTokPresentationDenseBodyFont
\RKTokPresentationAnnotationFont
\RKTokPresentationSourceFont
```

Suggested initial targets:

| Role | Target |
| --- | --- |
| Dense body | 9.5–10.5 / 12–13pt |
| Annotation | 7.5–8.5 / 9–10pt |
| Source | 6.5–7 / 8–9pt |

### D2. Source/footer legibility

The executive footline currently uses roughly `5.6/7pt`; `\source{}` uses roughly `6.4/7.7pt`.

For a projected slide, this is too small to function as ordinary reading text.

Requirements:

- increase source text to a reviewed minimum in the **6.5–7pt** range;
- increase or simplify footer typography so it remains readable without competing with content;
- detailed bibliographic references belong on a references/appendix slide, not in a 5pt footer;
- a short provenance string may remain in the footer.

The goal is not to make citations prominent. It is to stop pretending that unreadably small text is usable evidence.

### D3. Cap prose line length

Full-width prose should not automatically span the full 144 mm safe width.

Add a presentation prose-width token or helper with a target around **105–115 mm** for ordinary paragraphs and decks. Full width remains allowed for tables, diagrams, and deliberately wide labels.

This is a composition concern only when a semantic prose block is being typeset; do not constrain arbitrary body visuals.

---

## 8. P1 workstream E — standard dense-grid compositions

### E1. Why

The reviewed deck repeatedly needed:

- 2 × 2 cards;
- 2 × 3 cards;
- a four-step horizontal process;
- three equal capability columns.

Authors can construct these manually, but manual geometry leads to inconsistent gutters, type sizes, and card heights. The result is a deck that is technically valid but visually mechanical.

### E2. Add layout primitives, not domain-specific slides

Add renderer-neutral presentation compositions/helpers for common grids.

Candidate API:

```latex
\begin{cardgrid}[columns=2]
  \carditem{Fear}{Violence, humiliation, threats}
  ...
\end{cardgrid}

\begin{cardgrid}[columns=3,density=dense]
  ...
\end{cardgrid}
```

Required supported modes in the first release:

- 2 columns × 2 rows;
- 2 columns × 3 rows;
- 3 equal columns;
- 4 equal horizontal steps.

If introducing one generic `cardgrid` creates excessive TeX complexity, expose a smaller set of named compositions. Prefer composition over one-off slide-specific environments.

### E3. Grid rules

- gutter values come from presentation theme tokens;
- equal-height items in one row;
- top-aligned text;
- stable internal padding;
- optional accent rail/number/icon slot;
- body uses a semantic dense-body role;
- no color-only distinction;
- grid refuses to shrink below minimum text size.

---

## 9. P1 workstream F — reduce card monotony

The executive theme's quiet `Surface` cards are useful, but dense decks become visually repetitive when every concept is rendered as the same pale rectangle.

Add optional card emphasis variants whose meaning survives grayscale:

- `plain`: border + white fill;
- `surface`: current quiet card;
- `accent-rail`: 2–3pt semantic rail;
- `numbered`: visible ordinal + content;
- `emphasis`: stronger rule weight, not merely saturated fill.

Do not create decorative gradients, shadows, icon libraries, or ornamental chrome. This remains a restrained executive system.

---

## 10. P2 workstream G — dedicated references composition

### G1. Add `referenceslide`

A source-heavy closing frame should not be authored as a generic message or arbitrary report page.

Proposed contract:

```latex
\begin{frame}
  \begin{referenceslide}{Sources and use}
    \referenceitem{...}
    \referenceitem{...}
    \referenceitem{...}
  \end{referenceslide}
\end{frame}
```

Requirements:

- compact heading, not hero-message scale;
- readable reference text;
- optional short usage/limitation note;
- stable spacing for 3–8 short references;
- overflow fails or requires a continuation references slide;
- references are real text and links, not rasterized.

### G2. Appendix relationship

A references slide belongs to the presentation publication type and may appear in an appendix. It is not a separate theme feature.

---

## 11. P2 workstream H — title and divider review

Do **not** globally shrink title and divider typography in the P0 change.

After standard assertions are fixed, visually review:

| Role | Current | Review target |
| --- | ---: | ---: |
| Title | 29/33 | retain unless fixture proves too large; likely 26–29 |
| Section divider | 35/39 | review independently; likely 30–35 |
| Closing | 25/29 | retain as hero role |
| Hero message | 23/27 | retain |
| Standard assertion | new | 18.5/22 |
| Compact assertion | new | 16.5/20 |

The point is differentiated hierarchy, not universal downsizing.

---

## 12. Native acceptance fixture

### 12.1 Add a dense presentation fixture

Create a fixture under the presentation examples that deliberately exercises the failure modes found in review.

Suggested path:

```
latex_templates/examples/executive-presentation-density/
```

Minimum slides:

1. title slide;
2. one-line standard assertion + 2×2 card grid;
3. two-line assertion + comparison;
4. compact assertion + four-step process;
5. assertion + three equal columns;
6. assertion + 2×3 rule grid;
7. assertion + diagram;
8. hero `messageslide`;
9. references slide.

The fixture must compile through the same target-aware pipeline as a user deck.

### 12.2 Before/after comparison

Store or generate a review artifact that shows:

- current stable executive fixture;
- new density fixture;
- at least one 140-DPI montage.

Do not require committed raster screenshots if repository policy avoids generated binaries. The acceptance workflow may render them as artifacts.

---

## 13. Automated acceptance gates

### 13.1 Token contract tests

Extend theme-contract tests so every slides-compatible theme must populate the new assertion tokens.

A future theme may choose different values, but it cannot leave the roles undefined.

### 13.2 Composition contract tests

Add tests that verify:

- `assertionslide` exists in the presentation publication type;
- it does not mention `executive`;
- it uses presentation tokens rather than hard-coded point sizes/colors;
- `messageslide` still uses the hero message token;
- `evidenceslide` behavior remains stable unless explicitly migrated.

### 13.3 Fit tests

Native compile tests must cover:

1. short assertion → standard state;
2. two-line assertion → standard or compact depending on measured fit;
3. longer assertion → compact;
4. excessive assertion → hard diagnostic;
5. long assertion failure does not silently reduce body typography.

If implementation cannot expose the resolved fit state directly, add a test marker or structured build diagnostic.

### 13.4 Visual overflow gate

For every density-fixture slide:

- no clipped text;
- no overlap between header and body;
- no content outside the 8 mm safe area except theme-owned footer furniture;
- no body text below the configured minimum;
- no source text below the configured source minimum.

Use the existing PDF inspection infrastructure where possible. Add image-based review only for geometry that cannot be validated mechanically.

### 13.5 Regression gate

The canonical `latex_templates/examples/executive-presentation/` fixture must still build.

The closing `messageslide` should remain visually close to the current baseline. The P0 work must not turn the existing sparse executive deck into a dense deck globally.

---

## 14. Files expected to change

P0 likely touches:

```
latex_templates/reportkit-core.sty
latex_templates/themes/reportkit-theme-executive-slides.sty
latex_templates/publication_types/reportkit-presentation.sty
latex_templates/examples/executive-presentation-density/
tests/test_theme_contract.py
tests/ or publication_pipeline/tests/ presentation composition tests
SKILL.md or presentation authoring reference docs
```

P1/P2 may additionally touch:

```
publication_pipeline/scripts/inspect_pdf.py
python_scripts/reportkit/authoring_ir.py
python_scripts/reportkit/tex_renderer.py
python_scripts/reportkit/markdown_directives.py
references/ presentation authoring docs
```

The implementer must locate the current test ownership before creating duplicate test modules.

---

## 15. Implementation sequence

### Phase 1 — P0 hierarchy

1. Add standard/compact assertion tokens and assertion-header envelope token.
2. Populate executive values.
3. Add `assertionslide`.
4. Implement deterministic standard → compact → invalid fitting.
5. Add density fixture slides that use only existing manual body layouts.
6. Add contract, fit, and native-build tests.
7. Visually review the native 140-DPI montage.

**Exit criterion:** ordinary working slides visibly allocate more space to evidence without changing the hero-message composition.

### Phase 2 — P1 density

1. Add dense-body, annotation, and source roles if fixture review confirms they are needed.
2. Raise source/footer legibility.
3. Add standard card/grid compositions.
4. Add card emphasis variants.
5. Add prose-width helper/token where appropriate.
6. Extend the density fixture.

**Exit criterion:** the 2×2, 2×3, three-column, and four-step examples require no local font-size hacks.

### Phase 3 — P2 polish

1. Add `referenceslide`.
2. Review title/divider scales independently.
3. Update presentation documentation and SKILL guidance.
4. Re-run canonical and density visual acceptance.

---

## 16. Non-goals

This spec does not:

- introduce a new theme;
- add PowerPoint/PPTX rendering;
- change the 160 × 90 mm / 16:9 canvas;
- replace Beamer;
- redesign chart styling;
- add animation;
- add decorative iconography;
- make arbitrary font auto-scaling acceptable;
- change paged themes;
- change domain semantics;
- require every slide to use `assertionslide`.

---

## 17. Definition of done

This refinement is complete when all of the following are true:

1. ReportKit distinguishes hero messages from standard working-slide assertions.
2. `messageslide` retains its hero role and current intent.
3. `assertionslide` exists as a stable presentation composition.
4. Standard assertions use a materially smaller scale than hero messages.
5. A two-line assertion can downshift deterministically to compact type.
6. An assertion that still cannot fit fails with a clear diagnostic.
7. Standard assertion headers occupy no more than the reviewed header envelope.
8. Dense evidence slides no longer compensate for oversized headings with microscopic body text.
9. 2×2, 2×3, three-column, and four-step layouts have a supported composition path.
10. Sources and references are legible at normal slide scale.
11. The native density fixture has no overlap, clipping, or safe-area violations.
12. The canonical executive presentation fixture continues to build without visual regression to its hero closing slide.
13. Presentation docs teach agents when to choose `messageslide` versus `assertionslide`.
14. All new appearance values live in the theme adapter; all new semantic structures live in the presentation publication type.

---

## 18. Recommended first implementation PR

Keep the first PR intentionally small:

**PR: Standard assertion hierarchy for executive presentations**

Include only:

- new standard/compact assertion tokens;
- executive token values;
- `assertionslide`;
- measured fit behavior;
- 4–5 density-fixture slides;
- tests;
- documentation for choosing `messageslide` vs `assertionslide`.

Defer card-grid abstractions and references slides to follow-up PRs unless the implementation reveals they are necessary to prove the P0 contract.

This preserves reviewability and makes the main hypothesis falsifiable:

> If the primary defect is the lack of a standard assertion role, then reducing the ordinary assertion scale while reserving hero typography for true message slides should materially improve information density without weakening the executive visual hierarchy.
