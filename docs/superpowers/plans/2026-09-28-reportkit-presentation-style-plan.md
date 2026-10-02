# ReportKit presentation style implementation plan

**Status:** Proposed; not started as of 2026-10-02

**Goal:** Add reusable explanatory slide patterns to venture and a distinct analyst briefing presentation theme while keeping compositions theme neutral.

**Source:** ReportKit presentation style specification supplied on 2026-09-28.

## Existing system and design boundary

- `latex_templates/publication_types/reportkit-presentation.sty` already provides `assertionslide`, `comparison`, `threepart`, `cardgrid`, and other content-only compositions. Authors wrap each in an explicit Beamer `frame`.
- `reportcompare`, `reportfunnel`, `reportnetwork`, and `reportflow` already express the requested visual relationships. `reportfunnel` has a label and detail for every tier. Test these before adding a new composition.
- The venture and executive slide adapters own their presentation tokens. Venture already has Google Sans, wider safe margins, light/dark surfaces, and controlled brand overrides. Preserve those behaviors.
- Several shared composition implementations select `\sffamily` directly. A serif analyst headline therefore requires a shared, theme-owned typography role; changing only the new adapter cannot produce the intended distinction.
- `python_scripts/reportkit/publications.py` declares valid publication/theme pairs; `python_scripts/reportkit/themes/__init__.py` and a theme module supply chart and diagram tokens. Both registries must include a new theme before pipeline builds can use it.

## 1. Prototype the four patterns with current APIs

Create a small native prototype source or fixture with short, realistic copy and no local size, spacing, or color commands. Use one clear claim per working slide.

| Pattern | First implementation to try | Prototype decision |
| --- | --- | --- |
| Claim-led evidence | `assertionslide` with a diagram or chart body; optional deck for the implication | Confirm the header leaves enough evidence space in venture. Keep the deck to one line. |
| Before and after | `assertionslide` plus `reportcompare` or `comparison` | Prefer `reportcompare` when state transformation matters; verify aligned labels, readable details, and a text-labeled direction of change. |
| Tiered funnel | `assertionslide` plus `reportfunnel` and concise `\funnelstage` details | Verify three or four stages fit at venture projection size. State whether widths are conceptual or based on measured values. |
| Connected framework | `assertionslide` plus `reportnetwork` with a central conclusion and a few labeled factors | Verify that the graph communicates the central relationship and fits without manual TikZ positioning. |

Use the spec's descriptions of reference slides 4, 8, and 9 as the visual target. If the reference deck becomes available, compare those pages directly during visual review. Record which prototypes pass and the exact limitation of any that fail before changing a public API.

**Gate:** A pattern earns a new shared composition only if the current primitives cannot represent its meaning cleanly, or if repeated authors would otherwise need to copy layout geometry. Any addition goes in `reportkit-presentation.sty` with source-adjacent contract metadata and must compile under executive, venture, and analyst briefing.

## 2. Resolve shared typography and any missing semantics

1. In `latex_templates/reportkit-core.sty`, add only the presentation font-family or typography tokens needed to let theme adapters choose sans versus serif by semantic role. Replace forced `\sffamily` in shared presentation compositions where it blocks this contract. Do not embed a theme-name branch or visual values in the composition file.
2. Prototype a quotation with attribution and a numbered checklist/directive slide using current `cardgrid`, `threepart`, and standard text. If attribution or ordered directives cannot be represented as a stable, author-facing structure, add the smallest reusable shared composition or command pair. Require explicit attribution for quotation content and explicit numbers or labels for directives.
3. Extend the generated composition contract and constrained Markdown directive validation/rendering only for public APIs added in this step. Re-run the supported contract/doc generator; do not edit generated inventories by hand.
4. Add targeted compile and authoring tests for new API signatures, misuse diagnostics, theme neutrality, and three-theme compatibility. Keep arbitrary diagrams as trusted fragments where that is the existing authoring path.

**Gate:** The same composition source renders with each theme's own typography and spacing. The shared layer contains no analyst, executive, or venture-specific conditional styling.

## 3. Finish venture pattern support

1. Tune presentation and diagram tokens in `latex_templates/themes/reportkit-theme-venture-slides.sty` and, only where relevant, semantic diagram tokens in `latex_templates/themes/reportkit-theme-venture.sty` and `python_scripts/reportkit/themes/venture.py`. Preserve Google Sans body text, display hierarchy, 12 mm side margins, light/dark surface mapping, and the existing brand override path.
2. Add before/after, funnel, and connected-framework slides to `latex_templates/examples/venture-presentation/`. Put a short decision claim above each; keep details inside the semantic diagram or composition. Split content that needs several paragraphs.
3. Build the venture example with its existing brand colors and logo, then build the same slides with default venture branding. Check that the overrides still affect only the approved brand roles and that text/diagrams remain legible in both cases.

**Gate:** All three patterns render without local font-size or spacing overrides, with one readable claim per slide and no meaning conveyed by color alone.

## 4. Implement the analyst briefing theme

1. Add `latex_templates/themes/reportkit-theme-analyst-briefing.sty` for fonts, colors, and semantic appearance; add `reportkit-theme-analyst-briefing-slides.sty` for 16:9 safe margins, footline, surface roles, and every presentation token. Start from the executive slide adapter's geometry and density, then tune for a white canvas, dark serif headlines, navy accents, fine dividers, and compact explanatory layouts. Choose a reproducible serif font available in the pinned toolchain and verify its face and glyph coverage. Keep supporting text and sources readable at full-slide size.
2. Add `python_scripts/reportkit/themes/analyst_briefing.py` with matching chart, diagram, geometry, font, and color tokens. Register `analyst-briefing` as a slides-only presentation theme in `publications.py` and `themes/__init__.py`. Do not enable venture's brand override mechanism for this theme.
3. Generate the LaTeX publication registry through its supported command. Extend theme selection, preflight, registry, color parity, and build-target tests for the new valid pairing and invalid pairings.
4. Create `latex_templates/examples/analyst-briefing-presentation/` with a three-column explainer, attributed quotation, checklist or numbered directives, semantic diagram, and concise summary slide. Use enough supporting copy to demonstrate briefing density without turning a slide into a report page. Include source attribution where claims or quotations require it.

**Gate:** The briefing fixture builds through `reportkit build`; its serif/navy editorial system is visibly distinct from venture and executive while preserving the same composition API.

## 5. Cross-theme render and release review

1. Build a paired fixture containing identical composition source for venture, executive, and analyst briefing. Include at least `assertionslide`, before/after, funnel, connected framework, and any new quotation/directive API.
2. Render all representative PDF pages at presentation size. Inspect page images for clipped text, overlaps, hierarchy, safe margins, card alignment, diagram labels, and readable source lines. Inspect PDF text extraction for selectable prose and diagram labels; inspect vector drawing content for semantic diagrams where practical.
3. Render grayscale versions of the comparison, funnel, framework, checklist, and summary pages. Check that labels, ordinals, boundaries, and connector direction preserve meaning without hue.
4. Run the relevant presentation, theme, registry, pipeline, accessibility, and documentation checks, followed by the repository's native acceptance script. Fix source or theme tokens and repeat only the affected render checks until all gates pass.

**Release gate:** No clipped or overlapping content, no unsafe margins, no unreadably small sources, no color-only meaning, and visible typographic distinction when identical content is rendered in the different themes.

## 6. Update author guidance

Update `references/presentation-authoring.md`, the presentation sections of `SKILL.md` and `publication_pipeline/README.md`, and generated capability references through their generator. Document:

- **Venture:** short, projected pitch claims; one visual argument per slide; larger display type and brand-controlled colors.
- **Executive:** consulting and decision presentations with moderate density and a restrained sans system.
- **Analyst briefing:** research briefings, playbooks, and self-guided training that need compact explanatory copy, serif headlines, sources, and directives.
- Use a claim-led assertion plus the relevant semantic diagram for the four new patterns. Split a slide when supporting copy becomes several paragraphs, an assertion needs a third line, source text falls below its theme role, or the diagram cannot be read at presentation size.

Document the final prototype-to-API decisions so authors know which existing primitive to choose and why. Confirm `reportkit docs --check --json` passes after generation.
