# Callout titles and image slots

**Status:** Proposed · 24 September 2026
**Scope:** Reusable ReportKit engine and authoring guidance; publication-specific image choices and files stay in consumer repositories.

## Problem and evidence

- `reportkit-boxes.sty` requires a braced title for each semantic callout and prints a fixed category prefix before it. A `redflag` titled `Weak` therefore reads **RED FLAG WEAK**; `tipnote` titled `Strong` reads **TIP STRONG**.
- `SKILL.md` names ten callout kinds but gives only “use ... only when their meaning matters.” It has no selection examples or Markdown directive examples. The generic pipeline fixture demonstrates a diagram sentinel, not a callout. This is a plausible contributor to underuse, not a measured causal finding; the authoring ergonomics and limited examples also matter.
- The build stages `assets/` and `figures/`, and `[[REPORTKIT-VISUAL:fig:<slug>]]` inserts a required trusted diagram fragment. There is no first-class image request or placeholder contract for a missing photograph or illustration. A missing image currently needs custom fragment logic or fails compilation. Third-party assets have separate licence and attribution requirements.

## 1. Flexible semantic callout titles

For the nine single-title environments (`principle`, `decisionpoint`, `researchproblem`, `assumption`, `redflag`, `evidencenote`, `limitationnote`, `tipnote`, `deliverablenote`) and the three compatibility aliases:

| Source | Printed heading | Intent |
| --- | --- | --- |
| `\begin{redflag} ...` | `RED FLAG` | Default semantic title |
| `\begin{redflag}[Weak] ...` | `WEAK` | Optional title replaces the default completely |
| `\begin{tipnote}[Strong] ...` | `STRONG` | Same green semantic treatment, concise title |
| `\begin{redflag}{Specific risk} ...` | `RED FLAG  SPECIFIC RISK` | Existing braced TeX form retained during migration |
| `` ```reportkit redflag`` with `title: Weak` | `WEAK` | Safe Markdown authoring uses the replacement title |

The semantic environment continues to select colour and appearance; only displayed heading text changes. An empty override is invalid or resolves to the default, never a blank heading. Keep theme-owned typography, spacing, breakability, and accessibility semantics. `metric` retains its separate label/value contract. Implement the legacy braced form without silently treating its title as body text; extend the xparse contract parser and safe directive renderer if a second optional argument form requires it. Update the machine-readable primitive metadata and generated reference docs through `reportkit docs`, not by hand.

## 2. Guidance that produces useful callouts

Expand `SKILL.md` and the publication authoring reference with a small decision table and two fenced `reportkit` examples. Use a box when the reader needs to locate and apply a discrete **principle, decision, risk, assumption, limitation, tip, evidence caveat, or output artifact** independently of the surrounding prose. A short Weak/Strong comparison can use `redflag[Weak]` and `tipnote[Strong]`. Keep supporting explanation outside the boxes.

Do not box ordinary paragraphs, every item in a list, numerical evidence better shown in a table/chart, or a passage merely to fill a page. Do not set a callout quota. Add one realistic pair to a generic manuscript fixture so the recommended Markdown syntax is exercised in a build. Check that documentation distinguishes callouts from feature-article sidebars and executive-brief exhibits.

## 3. Image requests and replaceable slots

Introduce a distinct image sentinel, for example `[[REPORTKIT-IMAGE:img:<slug>]]`, with one consumer-owned slot declaration per slug. A declaration records its narrative purpose, caption, alt description, target aspect ratio (wide, landscape, square, or portrait), exact replacement path such as `assets/images/<slug>.jpg`, source/creator, licence, attribution, and restrictions. The compiler resolves the sentinel into a non-floating, captioned image unit near its first reference. The image keeps its natural aspect ratio, fits the selected slot without cropping by default, and uses the existing theme's caption/source styling. Validate unique slugs, contained paths, supported raster/vector formats, missing metadata, and source/credit requirements.

At authoring time, first decide whether a real image clarifies an object, place, appearance, or observed state that prose or a semantic diagram cannot convey as well. If a suitable licensable image is available, download it to the consumer project's declared path, record its source and terms, and inspect the crop and legibility. Never fetch remote images during `reportkit build`. If none is available, leave a neutral, clearly marked **IMAGE NEEDED: <slug>** placeholder at the declared proportions, with the intended subject and exact replacement filename visible in the PDF and build report. Replacing that file and rebuilding swaps in the image without editing manuscript prose. A final/release check reports unresolved placeholders as blocking; draft builds remain possible. Do not ship third-party example imagery in the engine or mistake a placeholder for documentary evidence.

Keep the existing `REPORTKIT-VISUAL` diagram contract intact. Reuse its caption/provenance placement and page-anchoring behavior where possible. Feature-article `openingvisual` and `featureexhibit` remain their own composition choices; the image slot is for Markdown-based publications that need a replaceable photograph or illustration.

## Acceptance and verification

1. Compile each single-title callout with no title, `[Weak]`/`[Strong]`, and legacy `{title}` under the default and institutional themes. Verify the headings visually and by extracted PDF text; no duplicated labels, regressions in colour, or overflowing boxes.
2. Build a Markdown fixture with safe `title:` overrides and no-title callouts; `reportkit context` reports optional title arguments and `reportkit docs --check --json` passes.
3. Build a fixture with one supplied image and one missing image slot. Both maintain intended proportions and stay with their introducing text; the missing image is unmistakably a placeholder. Missing/unsafe paths and missing rights data produce actionable diagnostics; release mode rejects unresolved slots.
4. Run repository tests, the standard build and inspect commands, and visual review of pages with all callout and image variants. Existing consumer diagram sentinels and legacy braced callouts continue to build.

## Explicit boundaries

No publication-specific image, caption, or prose belongs in this engine. No mandatory number of boxes or images per section. No new image search service, automatic copyright inference, runtime network dependency, theme-specific colour override, or change to the underlying `reportkit` class.
