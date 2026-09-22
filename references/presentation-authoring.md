# Presentation authoring contract

This reference defines how to choose ReportKit's executive presentation compositions and how to write assertions that preserve the evidence canvas. It covers the typography and composition refinement target without changing the repository boundary or the renderer/theme split.

The presentation publication type owns semantic composition names. The slides theme owns point sizes, spacing, gutters, density, and other appearance values. Authoring guidance must select a semantic role; it must not encode a theme name or repair a layout with local typography.

## Composition roles

Presentation compositions are content-only: put them inside an explicit Beamer `frame` and add `[fragile]` to that author-owned frame when the body needs it. The role, not the visual size alone, determines which composition to choose.

| Composition | Role | Use it when | Do not use it for |
| --- | --- | --- | --- |
| `messageslide` | Sparse hero assertion | One message should dominate a quiet frame and supporting copy is short. | A normal evidence slide with a grid, process, comparison, or substantial diagram. |
| `assertionslide` | Standard working slide | One assertion should orient the reader while the evidence body occupies most of the safe canvas. | A sparse closing message or a slide whose main rhetoric is explicitly Claim → Evidence. |
| `evidenceslide` | Explicit Claim → Evidence | The slide benefits from visible `CLAIM`, divider, and `EVIDENCE` labels. | A generic wrapper for every evidence-bearing slide; it is not an alias for `assertionslide`. |
| `titleslide` | Document identity | The audience needs title, subtitle, author, date, or other front-matter orientation. | A working assertion or an evidence canvas. |
| `sectiondivider` / `appendixdivider` | Section transition | The slide marks a new section or appendix and should be sparse. | A place to hide evidence that needs a normal working slide. |
| `closingslide` | Deliberate conclusion | The deck needs a final recommendation, implication, or call to action with intentional closing emphasis. | A standard assertion just because it is near the end. |
| `referenceslide` | Sources and use | A source-heavy closing or appendix needs readable references and an optional usage/limitation note. | A footer substitute or a dense bibliography forced into microscopic type. |

The first six names above are part of the current presentation composition vocabulary. `assertionslide`, `referenceslide`, `referenceitem`, and the dense card-grid contract are refinement targets; when working from a checkout that does not yet expose them through `reportkit context --json`, do not emulate them with arbitrary local TeX. Use the current stable composition that best matches the role and keep the target API documented here for the implementation checkpoint.

## Assertion writing and fit

An assertion is one decision-relevant claim, not a report-section title or a sentence that summarizes every card below it.

- One line is ideal.
- Two lines are acceptable; the compact assertion treatment may be used when the measured header fit requires it.
- Three lines should generally be rewritten before build. If the claim still cannot fit after rewriting, split the slide.

The planned fit contract has only three states: `standard`, `compact`, and `invalid`. It measures the rendered assertion against a bounded header, tries the standard assertion scale first, then the compact scale, and fails with `PRESENTATION_ASSERTION_TOO_LONG` if the compact assertion still does not fit. It does not continuously scale the font.

Never shrink body, dense-body, source, or reference text to rescue an oversized assertion. Rewrite or split the assertion/slide. Do not add a local `\\fontsize`, `\\small`, `\\scriptsize`, negative spacing, or per-card override; typography values belong to the theme's presentation tokens and semantic density roles.

The executive refinement targets are approximately 18.5/22pt for a standard assertion, 16.5/20pt for compact assertions, and a 24 mm maximum assertion header, tuned only through native fixture review. These are theme-owned targets, not author-level magic numbers.

A planned `assertionslide` has this semantic shape:

    \\begin{frame}
      \\begin{assertionslide}[kicker={Parenting constitution}]{Six household rules prevent most major unforced errors.}[Agree on these before you are tired, stressed, or negotiating in front of the child.]
        % arbitrary evidence/body
      \\end{assertionslide}
    \\end{frame}

The exact implementation may expose equivalent xparse keys, but the contract remains: optional kicker, one required assertion, optional deck, bounded header, and arbitrary body evidence. The body must start below a stable header envelope; it must not be vertically rescued with content-dependent filler.

## Planned dense semantic layouts

The current API already has small fixed compositions such as `comparison`/`comparisoncolumn` and `threepart`/`threepartcolumn`. Those are useful for their existing contracts but do not provide a general dense-card grammar. The refinement target is a composition-level `cardgrid`/`carditem` API, or an equivalent small family of named semantic compositions, with theme-owned gutters, padding, density, and minimum text sizes.

| Planned layout | Intended content | Semantic constraints |
| --- | --- | --- |
| 2×2 cards | Four comparable rules, risks, choices, or evidence points. | Two columns, two equal-height rows, top-aligned content. |
| 2×3 cards | Six compact rules or evidence points. | Two columns, three equal-height rows; shorten content or split if cards become prose paragraphs. |
| Three-column cards | Three capabilities, options, or workstreams that deserve equal weight. | Three equal columns, aligned headings and stable internal padding. |
| Four-step layout | An ordered process, method, or decision sequence. | Four equal horizontal steps with explicit order; use a process primitive when relationships/branching matter more than card text. |

The intended target shape is illustrative until the owning implementation publishes the contract block:

    \\begin{cardgrid}[columns=2]
      \\carditem[variant=surface]{Fear}{Violence, humiliation, and threats}
      \\carditem[variant=accent-rail]{Repair}{Return to the conversation and name the harm}
      % two more items for the 2×2 form
    \\end{cardgrid}

Use `columns=2` with four items for 2×2, six items for 2×3, `columns=3` with three items for the three-column form, and `columns=4` with four ordered/numbered items for the four-step form. A named `fourstep` composition is equally acceptable if the implementation freezes that spelling; the semantic requirements are the same.

Grid rules:

- gutters, padding, card density, and minimum text sizes come from presentation theme tokens;
- items in one row have equal height and top-aligned content;
- ordinal, rail, rule weight, or labels must preserve meaning in grayscale;
- dense body and annotation roles are semantic roles, not local point-size patches;
- if content does not fit at the minimum role size, shorten it, change the layout, or split the slide.

### Card variants

Use variants to encode a meaningful hierarchy without turning every card into the same pale rectangle:

| Variant | Meaning and treatment |
| --- | --- |
| `plain` | Border and white fill for neutral peer items. |
| `surface` | The quiet surface treatment for ordinary supporting cards. |
| `accent-rail` | A 2–3pt semantic rail for a marked item; the rail is not the only signal. |
| `numbered` | A visible ordinal for sequence, ranking, or reading order. |
| `emphasis` | Stronger rule weight for a priority item, not merely a more saturated fill. |

Do not add gradients, shadows, ornamental chrome, an icon library, or color-only meaning. Do not rebuild these modes with nested manual columns and local font-size hacks. If the planned helper is not present in the capability catalog yet, keep the body concise and wait for the semantic API rather than copying implementation geometry into content.

## References and continuation

The planned `referenceslide`/`referenceitem` composition is for a source-heavy closing or appendix frame:

    \\begin{frame}
      \\begin{referenceslide}{Sources and use}
        \\referenceitem{Author or organization. Title. Year. Link.}
        \\referenceitem{Author or organization. Title. Year. Link.}
        \\referenceitem{Author or organization. Title. Year. Link.}
      \\end{referenceslide}
    \\end{frame}

Keep 3–8 short references in one slide when they remain readable. Reference items are real text and links, not rasterized images. Add a short usage or limitation note when the audience needs to understand how the sources were used.

A short `\\source{...}` line or diagram `source={...}` value is provenance for the visual on the current slide; it is not a replacement for a full bibliographic reference. Keep the short provenance line in the footer or visual caption and move full citations to `referenceslide`.

If references exceed the slide's stable capacity, add a continuation slide such as `Sources and use (continued)` or an appendix references slide. Preserve the same readable reference role and spacing. Never solve overflow by shrinking references or footer text below the configured source/reference minimum.

## Contract, boundary, and validation

`reportkit context --json` is the authoritative machine-readable capability catalog. `reportkit docs --check --json` is the documentation-drift gate. Contract inventories such as `references/primitive-contract.md` are generated from owning contract blocks or the supported registry command; do not hand-edit generated files. If a public composition changes, the implementation owner updates its contract source and reruns the supported generator/check.

The ReportKit repository is the reusable engine, not a publication workspace. Keep manuscripts, fragments, assets, generated figures, build output, and final PDFs in a separate consumer project; follow [repository-boundary.md](repository-boundary.md). This documentation does not authorize adding a deck fixture or generated artifact to the engine repository.

For a full build, use `reportkit build --source-root <publication-project>`, render only relevant pages/slides with `reportkit render --source-root <publication-project> --pages ... --dpi 150`, and run `reportkit inspect --source-root <publication-project>`. Review rendered slides for clipped text, header/body overlap, unsafe margins, broken diagrams, missing sources, and meanings conveyed only by color. A successful TeX exit code alone is not completion.