# ReportKit Presentation Typography and Composition Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Track progress with checkbox syntax and keep each workstream inside its declared file-ownership boundary.

**Status:** Proposed  
**Last updated:** 2026-09-22

**Goal:** Implement the presentation refinement spec so ReportKit distinguishes hero-message slides from ordinary assertion/evidence slides, preserves evidence canvas, supports deterministic headline fitting and dense presentation layouts, improves source/reference legibility, and proves the result through native ReportKit builds.

**Spec:** `docs/superpowers/specs/2026-09-22-reportkit-presentation-typography-and-composition-refinement-spec.md`

**Architecture:** One LaTeX workstream owns the presentation semantic and appearance contract. Three dependent workstreams own constrained authoring, visual acceptance/inspection, and documentation respectively. Their file sets do not overlap. A final integration gate runs the complete native build and visual review after all workstreams land.

**Tech stack:** LaTeX2e / Beamer / xparse / etoolbox, ReportKit theme tokens, Python typed authoring IR, pytest, PyMuPDF PDF inspection, LuaLaTeX, ReportKit publication pipeline.

---

## 1. Parallelization strategy

The implementation should not be fanned out by spec section alone because several spec sections modify the same files. In particular, P0 assertion hierarchy, P1 card/grid layouts, and P2 references all belong to `reportkit-presentation.sty` and the executive slides adapter. Splitting those into simultaneous agents would create merge conflicts and inconsistent token contracts.

Instead, use **file ownership**.

| Workstream | Ownership | Can run in parallel with |
| --- | --- | --- |
| A. LaTeX presentation system | presentation semantics, presentation tokens, executive slide adapter, LaTeX-only tests | none until P0 interface is established; then B/C/D |
| B. Constrained authoring integration | Python directive/IR/rendering/preflight files and Python authoring tests | C, D, and A's later P1/P2 work after A publishes stable P0 API |
| C. Native visual acceptance and inspection | density fixture, PDF inspector extensions, visual/geometry acceptance tests | B, D, and A's later P1/P2 work after P0 |
| D. Agent/docs contract | SKILL.md and presentation authoring/reference docs | B, C; start after A's public API names stabilize |
| E. Integration/release gate | scripts/build orchestration only if needed; no feature design | after A-D |

### Hard ownership rule

During parallel execution:

- Workstream A is the **only** stream allowed to edit:
  - `latex_templates/reportkit-core.sty`
  - `latex_templates/themes/reportkit-theme-executive-slides.sty`
  - `latex_templates/publication_types/reportkit-presentation.sty`
  - any new presentation-semantic `.sty` file if A decides to split one out
- Workstream B is the **only** stream allowed to edit:
  - `python_scripts/reportkit/markdown_directives.py`
  - `python_scripts/reportkit/authoring_ir.py`
  - `python_scripts/reportkit/tex_renderer.py`
  - `python_scripts/reportkit/authoring.py` if validation routing requires it
  - authoring-specific tests
- Workstream C is the **only** stream allowed to edit:
  - `latex_templates/examples/executive-presentation-density/`
  - `publication_pipeline/scripts/inspect_pdf.py`
  - density/slide geometry acceptance tests
- Workstream D is the **only** stream allowed to edit:
  - `SKILL.md`
  - presentation authoring/reference documentation under `references/` or `docs/` as appropriate
- Workstream E should avoid feature files. It may update `scripts/acceptance_check.sh` only if the new fixture is not already reached by an existing build gate.

If a workstream discovers it needs a file owned by another stream, stop and raise an interface request rather than editing across the boundary.

---

## 2. Shared interface checkpoint before parallel execution

Workstream A must land the P0 public interface before B, C, and D implement against it.

The checkpoint consists of these exact semantic roles, unless A documents a better xparse spelling while preserving the contract:

### Presentation tokens

```latex
\RKTokPresentationAssertionFont
\RKTokPresentationAssertionCompactFont
\RKTokPresentationAssertionDeckFont
\RKTokPresentationAssertionHeaderMaxHeight
```

Executive initial values:

- assertion: approximately `18.5/22pt`
- compact assertion: approximately `16.5/20pt`
- assertion deck: approximately `9.5–10.5/12–13pt`
- max assertion header: start at `24mm`, tune only through native fixture review

### Presentation composition

A stable `assertionslide` semantic composition with:

- required assertion;
- optional kicker;
- optional deck;
- arbitrary body;
- deterministic header envelope;
- standard → compact → invalid headline fit states.

The exact author-facing syntax must be frozen at this checkpoint and copied into this plan's Task A report so B-D do not guess.

### Diagnostic

The overlong assertion path must expose a recognizable failure:

```
PRESENTATION_ASSERTION_TOO_LONG
```

The exact TeX `\PackageError` prose may vary, but the stable diagnostic identifier must be available to tests and/or build diagnostics.

---

# Workstream A — LaTeX presentation system

**Purpose:** Own all presentation semantics and appearance refinements in one conflict-free stream.

**Spec coverage:** §§4–11, 13.1–13.3, 15 Phase 1/2/3 LaTeX portions.

**Files owned:**
- `latex_templates/reportkit-core.sty`
- `latex_templates/themes/reportkit-theme-executive-slides.sty`
- `latex_templates/publication_types/reportkit-presentation.sty`
- `tests/test_executive_theme.py`
- new LaTeX composition test file if existing tests are too broad, e.g. `tests/test_presentation_compositions.py`

Do not edit Python authoring files, the density fixture, `inspect_pdf.py`, or SKILL.md in this workstream.

## Task A1 — Establish P0 assertion token contract

- [ ] Read the presentation token section of `reportkit-core.sty` and all current uses in `reportkit-presentation.sty`.
- [ ] Add the four P0 assertion tokens to the core presentation-token contract using the same sentinel/error pattern as existing presentation tokens.
- [ ] Populate all four in `reportkit-theme-executive-slides.sty`.
- [ ] Keep `RKTokPresentationMessageFont` unchanged as the hero role.
- [ ] Do not reuse `RKTokPresentationColumnHeadingFont`.
- [ ] Extend theme-contract tests so a slides-compatible theme cannot omit any new assertion token.
- [ ] Compile the canonical executive fixture to prove no current composition regresses merely from adding tokens.

**Commit target:** `feat: add presentation assertion token hierarchy`

## Task A2 — Add bounded `assertionslide`

- [ ] Add `assertionslide` to `reportkit-presentation.sty`.
- [ ] Give it optional kicker and deck fields plus a required assertion and arbitrary body.
- [ ] Use fixed spacing and a bounded header region. Do not use `\vfill` between header and body.
- [ ] Ensure body placement is stable and cannot overlap the reserved header.
- [ ] Ensure composition code contains no `executive` theme-name branch.
- [ ] Add a reportkit-contract block matching the repository's existing public composition inventory format.
- [ ] Add compile tests for:
  - assertion only;
  - kicker + assertion;
  - assertion + deck;
  - kicker + assertion + deck + arbitrary body.

**Commit target:** `feat: add bounded assertion slide composition`

## Task A3 — Deterministic headline fitting

- [ ] Implement measured standard → compact → invalid behavior.
- [ ] Use actual rendered dimensions, not character count, as the authoritative decision.
- [ ] Keep the same maximum header envelope for standard and compact states.
- [ ] Raise a hard `PRESENTATION_ASSERTION_TOO_LONG` diagnostic if compact type still cannot fit.
- [ ] Do not continuously scale font size.
- [ ] Add tests proving:
  1. short assertion resolves at standard scale;
  2. longer assertion resolves at compact scale;
  3. excessive assertion fails;
  4. failure does not modify body typography;
  5. `messageslide` remains on the hero token.
- [ ] If fit state is not externally visible, add a test-only/log marker or stable diagnostic trace so tests can distinguish standard from compact.

**Checkpoint:** After A3 is merged, publish the exact `assertionslide` syntax and diagnostic behavior to B-D. Those streams may now start.

**Commit target:** `feat: enforce deterministic assertion fitting`

## Task A4 — Add semantic dense-text and source roles only where justified

Do this after A1-A3 compile cleanly.

- [ ] Add `RKTokPresentationDenseBodyFont`, `RKTokPresentationAnnotationFont`, and `RKTokPresentationSourceFont` only if native dense examples demonstrate a real need.
- [ ] Keep global `RKTokPresentationBodyFont` unchanged unless native fixture review proves it is itself defective.
- [ ] Increase source legibility to approximately 6.5–7pt.
- [ ] Review the executive footline's 5.6pt type and either:
  - raise it to a readable minimum; or
  - simplify the footer so only short provenance remains.
- [ ] Add an optional prose-width token/helper around 105–115mm for semantic prose blocks; do not constrain arbitrary visuals.

**Commit target:** `refactor: improve presentation supporting text hierarchy`

## Task A5 — Add dense layout semantics

- [ ] Add presentation-level layout primitives for:
  - 2×2 cards;
  - 2×3 cards;
  - three equal columns;
  - four equal horizontal steps.
- [ ] Prefer a coherent `cardgrid` / `carditem` API if it remains simple and testable; otherwise use a minimal family of named compositions.
- [ ] Add theme-owned tokens for gutter/padding/card density rather than hard-coded values in semantic structures.
- [ ] Ensure equal-height rows, top alignment, minimum text size, and grayscale-safe emphasis.
- [ ] Add card variants:
  - `plain`
  - `surface`
  - `accent-rail`
  - `numbered`
  - `emphasis`
- [ ] No gradients, shadows, decorative icon system, or color-only semantics.
- [ ] Add LaTeX compile tests for every layout and variant.

**Commit target:** `feat: add dense presentation grid compositions`

## Task A6 — Add `referenceslide`

- [ ] Add `referenceslide` and `referenceitem` to the presentation publication type.
- [ ] Use standard/compact presentation hierarchy, not hero-message typography.
- [ ] Support 3–8 short references plus an optional usage/limitation note.
- [ ] Fail or require continuation when references overflow; never silently shrink below the source minimum.
- [ ] Preserve real text and links.
- [ ] Add contract and compile tests.

**Commit target:** `feat: add presentation references composition`

## Task A7 — Independent title/divider review

Only after the standard assertion hierarchy is visually proven:

- [ ] Review title, divider, closing, and hero-message roles against the native density fixture.
- [ ] Do not shrink them merely for consistency.
- [ ] If changing title/divider sizes, treat each as a separate visual decision and record before/after values.
- [ ] Ensure canonical hero closing slide stays visually close to baseline.

**Commit target:** only if a change is warranted; otherwise record "no change" in the workstream report.

## Workstream A report contract

Return:

- status;
- commit list;
- exact frozen `assertionslide` syntax;
- exact fit-state behavior;
- token names and final executive values;
- pytest summary;
- canonical fixture compile result;
- any spec ambiguity resolved;
- explicit confirmation that `messageslide` remains the hero role.

---

# Workstream B — Constrained authoring and preflight

**Starts after:** A3 interface checkpoint.

**Purpose:** Make the Markdown/typed-IR path capable of producing and validating the new semantic compositions without touching LaTeX implementation files.

**Spec coverage:** §6.3–6.4, §14 Python files, §17.13 agent-facing behavior.

**Files owned:**
- `python_scripts/reportkit/markdown_directives.py`
- `python_scripts/reportkit/authoring_ir.py`
- `python_scripts/reportkit/tex_renderer.py`
- `python_scripts/reportkit/authoring.py` only if required
- `python_scripts/reportkit/diagnostics.py` only if structured preflight diagnostics belong there
- `tests/test_authoring_ir.py`
- new authoring-specific test module if useful

Do not edit `.sty` files or visual fixture files.

## Task B1 — Model `assertionslide` in typed IR

- [ ] Read current presentation directive/IR types and renderer paths.
- [ ] Add a typed assertion-slide node carrying:
  - assertion;
  - optional kicker;
  - optional deck;
  - body.
- [ ] Validate required/optional fields at IR construction time.
- [ ] Render the exact frozen A3 TeX API.
- [ ] Add round-trip tests from directive input → IR → rendered TeX.

## Task B2 — Advisory assertion-length preflight

- [ ] Add a non-authoritative preflight for obviously overlong assertions.
- [ ] The preflight may use character/word/line heuristics but must not claim to reproduce TeX measurement.
- [ ] Diagnostic wording must tell the author to rewrite or split the slide.
- [ ] TeX `PRESENTATION_ASSERTION_TOO_LONG` remains authoritative.
- [ ] Do not auto-truncate or rewrite content.
- [ ] Add tests showing reasonable assertions pass and clearly excessive assertions warn/fail according to the authoring validation convention already used by ReportKit.

## Task B3 — Dense-grid and references authoring support

Starts after A5/A6 API names stabilize.

- [ ] Add typed directive/IR representations for the supported dense layout API.
- [ ] Reject unsupported column counts/layout combinations before TeX.
- [ ] Add references slide IR and reference items.
- [ ] Preserve links and text.
- [ ] Add tests for valid and invalid authoring forms.

## Workstream B report contract

Return:

- status;
- commits;
- new IR node names;
- directive syntax;
- preflight diagnostic behavior;
- pytest summary;
- confirmation that no LaTeX/theme files were modified.

---

# Workstream C — Native density fixture and PDF inspection

**Starts after:** A3 interface checkpoint. Can add P0 fixture first, then extend after A5/A6.

**Purpose:** Prove the visual result using native ReportKit builds and mechanize the non-subjective parts of the release gate.

**Spec coverage:** §§12–13.5, §17.7–17.12.

**Files owned:**
- create `latex_templates/examples/executive-presentation-density/`
- `publication_pipeline/scripts/inspect_pdf.py`
- new `tests/test_presentation_density_fixture.py`
- slide-inspection tests under the existing appropriate test directory
- fixture-local manuscript/fragments/publication.yaml/report.tex only

Do not edit `reportkit-presentation.sty`, theme files, authoring Python files, or SKILL.md.

## Task C1 — Build the P0 density fixture

Create the new native fixture with at least:

1. title slide;
2. one-line standard assertion + 2×2 manual evidence layout;
3. two-line assertion + comparison;
4. compact assertion + four-step manual process;
5. assertion + three equal manual columns;
6. assertion + 2×3 manual rule grid;
7. assertion + existing semantic diagram;
8. hero `messageslide`.

At P0, body layouts may be manual because the purpose is to validate assertion hierarchy before A5 adds grid abstractions.

- [ ] Build through the target-aware ReportKit presentation pipeline.
- [ ] Verify `publication_type: presentation`, `theme: executive`, LuaLaTeX.
- [ ] Add a pytest that compiles the native fixture and checks expected page count/text presence.
- [ ] Render 140-DPI montage artifact for review.

## Task C2 — Mechanical assertion-envelope checks

Extend PDF inspection or test-local PyMuPDF geometry checks to verify:

- [ ] no text clips outside page bounds;
- [ ] no header/body overlap;
- [ ] ordinary assertion body begins below the header envelope;
- [ ] body retains at least the spec's target share of safe-area height where mechanically meaningful;
- [ ] nothing except theme-owned footer furniture enters the 8mm safe margin;
- [ ] hero `messageslide` is excluded from standard assertion-envelope checks.

Do not infer semantic font roles solely from visual size if the PDF does not expose a reliable mapping; prefer known fixture labels/coordinates.

## Task C3 — Extend fixture after dense-grid support

After A5:

- [ ] replace manual 2×2/2×3/three-column/four-step layouts with the supported semantic grid API;
- [ ] assert no local `\fontsize` hacks remain in the fixture;
- [ ] add grayscale render review for card emphasis variants;
- [ ] verify equal-height rows and stable gutters.

## Task C4 — Add references acceptance

After A6:

- [ ] add a ninth `referenceslide`;
- [ ] verify 3–8 references remain readable and within safe area;
- [ ] add overflow-negative test;
- [ ] verify source text is not below the configured minimum where PDF font metadata permits measurement.

## Task C5 — Canonical fixture regression

- [ ] Build `latex_templates/examples/executive-presentation/`.
- [ ] Compare page count and expected semantic text.
- [ ] Render a 140-DPI montage before/after.
- [ ] Confirm the hero closing frame has not been unintentionally demoted.

## Workstream C report contract

Return:

- status;
- commits;
- density fixture slide inventory;
- pytest/inspection results;
- 140-DPI visual review notes slide by slide;
- grayscale review notes;
- canonical fixture regression result;
- unresolved subjective visual concerns for integration review.

---

# Workstream D — Agent and documentation contract

**Starts after:** A3 interface checkpoint. Extend after A5/A6.

**Purpose:** Teach authors and agents how to select presentation compositions and prevent the old oversized-headline behavior from reappearing through authoring choices.

**Spec coverage:** §6.3, §15 documentation portions, §17.13.

**Files owned:**
- `SKILL.md`
- presentation-specific files under `references/` if present
- relevant docs under `docs/`, excluding the spec and this implementation plan unless status updates are required

Do not edit implementation or fixture code.

## Task D1 — Composition selection guidance

Document:

- `messageslide` = sparse hero assertion;
- `assertionslide` = normal working slide with evidence;
- `evidenceslide` = explicit CLAIM → EVIDENCE rhetoric;
- title/divider slides remain separate.

Include the writing heuristic:

- one line ideal;
- two lines acceptable;
- three lines should generally be rewritten before build.

Explicitly say that body text must not be shrunk to rescue an oversized assertion.

## Task D2 — Dense layout guidance

After A5:

- [ ] document when to use 2×2, 2×3, three-column, and four-step layouts;
- [ ] document semantic card variants;
- [ ] warn against manually recreating those layouts with local font-size hacks.

## Task D3 — References guidance

After A6:

- [ ] document `referenceslide`;
- [ ] distinguish short provenance/source lines from full bibliographic references;
- [ ] advise continuation slides rather than microscopic type.

## Task D4 — Machine-readable capability drift

If the repo's registry/docs checks derive public contracts from `<reportkit-contract>` blocks, run the existing docs/registry drift checks and update generated documentation through the repository's supported command rather than hand-editing generated files.

## Workstream D report contract

Return:

- status;
- commits;
- docs changed;
- exact guidance added;
- docs drift-check result;
- confirmation that no implementation files were modified.

---

# Workstream E — Integration and release gate

**Starts after:** A-D complete.

**Purpose:** Combine all streams, run full validation, and make final visual decisions. This workstream should not invent new APIs.

**Files:** ideally none beyond status/docs updates; `scripts/acceptance_check.sh` may be modified only if the new density fixture is not already covered by an existing presentation acceptance path.

## Task E1 — Verify interfaces after merge

- [ ] Read final A-D commits rather than relying on this plan's provisional syntax.
- [ ] Verify constrained authoring emits exactly the implemented LaTeX API.
- [ ] Verify density fixture uses semantic grid/reference APIs, not stale manual P0 layouts.
- [ ] Verify docs use the implemented names.

## Task E2 — Run targeted tests

At minimum:

```bash
pytest tests/test_executive_theme.py -q
pytest tests/test_authoring_ir.py -q
pytest tests/test_presentation_density_fixture.py -q
```

Also run any presentation-specific test modules created by A-C.

## Task E3 — Full repository gate

- [ ] Run the repository's canonical test suite.
- [ ] Run `bash scripts/acceptance_check.sh`.
- [ ] Run `reportkit docs --check --json` if that remains the documented drift gate.
- [ ] Native-build both canonical and density executive presentations.
- [ ] Ensure no new blocking diagnostics appear in the agent contract.

## Task E4 — Final 140-DPI visual review

Review every density slide at 140 DPI and answer:

1. Does an ordinary assertion orient rather than dominate?
2. Does evidence occupy the majority of the useful canvas?
3. Are one-line and two-line assertion states visibly coherent?
4. Does compact fit look deliberate rather than squeezed?
5. Do 2×2, 2×3, 3-column, and 4-step layouts remain readable without local font hacks?
6. Are sources/references readable at normal presentation scale?
7. Does the canonical hero closing slide still feel intentionally stronger than normal assertions?
8. Are title/divider slides still appropriately distinct?

If a visual issue remains, route the fix back to its owning workstream rather than patching across ownership boundaries in E.

## Task E5 — Release decision

The implementation is complete only if all spec Definition of Done items are satisfied, especially:

- hero and standard assertion roles are distinct;
- standard/compact/invalid fit is deterministic;
- evidence canvas is materially larger on working slides;
- supported dense layouts need no local size hacks;
- references are readable;
- native density fixture has no overlap/clipping/safe-area violation;
- canonical executive fixture still builds without hero-message regression.

**Integration report contract:**

- merged commit list by workstream;
- full pytest summary;
- acceptance-check result;
- docs drift result;
- canonical fixture result;
- density fixture result;
- 140-DPI visual review;
- final token values;
- any deferred P2 item and explicit reason.

---

## 3. Recommended execution waves

### Wave 1 — serial foundation

Run A1 → A2 → A3 only.

Do not start B-D until the P0 composition API and fit diagnostic are frozen.

### Wave 2 — parallel proof and integration surfaces

Run in parallel:

- B1-B2: typed authoring + advisory preflight;
- C1-C2: native density fixture + mechanical envelope inspection;
- D1: composition-selection documentation;
- A4-A5: supporting typography and dense layout implementation.

These are file-disjoint.

### Wave 3 — parallel polish

Run in parallel:

- B3: dense-grid/reference authoring integration;
- C3-C4: semantic dense fixture + references acceptance;
- D2-D3: dense/reference documentation;
- A6-A7: references composition + independent title/divider review.

These remain file-disjoint because A owns LaTeX, B owns authoring Python, C owns fixtures/inspection, and D owns docs.

### Wave 4 — integration

Run E1-E5 serially on the merged result.

---

## 4. Commit / PR structure

Recommended PR sequence:

### PR 1 — P0 presentation hierarchy

Owned by A.

Includes:

- assertion tokens;
- `assertionslide`;
- deterministic fit;
- LaTeX contract tests.

This is the load-bearing PR.

### PR 2A — Authoring integration

Owned by B; branch from PR 1/main after P0 lands.

### PR 2B — Native density acceptance

Owned by C; branch from PR 1/main.

### PR 2C — Presentation authoring guidance

Owned by D; branch from PR 1/main.

### PR 2D — Dense presentation semantics

Owned by A; branch from PR 1/main. It may run concurrently with PRs 2A-2C because its files do not overlap them.

### PR 3A — Dense/reference authoring

Owned by B after A's dense/reference interfaces are available.

### PR 3B — Density fixture finalization

Owned by C.

### PR 3C — Docs finalization

Owned by D.

### Final integration PR

Only if needed for acceptance wiring/status updates. Avoid a "mega cleanup" PR that rewrites implementation files from multiple streams.

---

## 5. Merge-conflict matrix

| File / area | A | B | C | D | E |
| --- | :---: | :---: | :---: | :---: | :---: |
| `reportkit-core.sty` | owner | — | — | — | read |
| `reportkit-theme-executive-slides.sty` | owner | — | — | — | read |
| `reportkit-presentation.sty` | owner | — | — | — | read |
| authoring IR/directives/rendering | — | owner | — | — | read |
| density fixture | — | — | owner | — | read |
| `inspect_pdf.py` presentation checks | — | — | owner | — | read |
| `SKILL.md` / presentation docs | — | — | — | owner | read |
| `scripts/acceptance_check.sh` | — | — | — | — | conditional owner |

This matrix is normative for parallel execution.

---

## 6. Risks and mitigations

### Risk 1 — TeX headline measurement becomes fragile

**Mitigation:** keep the fit state discrete and bounded. Use boxes/dimensions already available in TeX; do not implement generalized responsive typography.

### Risk 2 — P1 layout work destabilizes P0 hierarchy

**Mitigation:** PR 1 freezes P0 first. Dense layout work consumes those roles rather than changing them.

### Risk 3 — Markdown preflight disagrees with TeX

**Mitigation:** Python preflight is advisory only. Native TeX measurement is authoritative.

### Risk 4 — visual acceptance becomes screenshot-only

**Mitigation:** C mechanizes safe-area, clipping, page/text, and envelope checks where reliable, while retaining a 140-DPI human visual gate for hierarchy and balance.

### Risk 5 — documentation drifts from actual API

**Mitigation:** D starts only after the API checkpoint and re-runs the repository's documentation/registry drift checks.

### Risk 6 — future themes are forced to inherit executive values

**Mitigation:** new semantic roles live in the shared token contract; only the executive adapter chooses current numeric values. No composition branches on theme name.

---

## 7. Definition of plan completion

The plan itself is successfully executed when:

- all A-D workstream reports are complete;
- no parallel workstream violated file ownership;
- P0 interface is stable and documented;
- native density fixture builds through ReportKit;
- constrained authoring emits the new API;
- presentation docs guide composition selection correctly;
- canonical and density fixtures pass the full release gate;
- the final visual review confirms ordinary assertion slides are materially less title-heavy while hero slides retain deliberate emphasis.
