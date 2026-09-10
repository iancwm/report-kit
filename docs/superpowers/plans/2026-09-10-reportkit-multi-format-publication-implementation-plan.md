# ReportKit Multi-Format Publication Architecture — Implementation Plan

**Status:** Draft v0.1. Architecture decisions are resolved; task sizing and
visual design details should receive engineering/design review before execution.
**Last updated:** 2026-09-10
**Plans:** [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](../specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md)
**Amended by:** [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](../specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md)
**Baseline:** main at 4f2b27f, ReportKit v1.9.1.

---

## Why this document exists

The renderer spec gives the right six-phase sequence, but its Phase A baseline
predates the v1.9 agent-contract work. Starting it literally would reimplement
the capability registry, schema, diagnostics, documentation generation and
pinned toolchain that now ship.

This plan reconciles both specs with the current tree, resolves the renderer
spec's six open questions, and turns the remaining work into independently
verifiable slices. The ordering preserves the central invariant:

    content × publication type × renderer × theme

No new visual family lands until the registry, renderer boundary, theme hooks
and pipeline selection are real and tested.

## 1. Reconciliation with the current tree

### Already implemented — extend, do not rebuild

| Capability | Current owner | Plan treatment |
| --- | --- | --- |
| Python capability catalog for two themes, two publication types and the paged renderer | python_scripts/reportkit/publications.py:10-115 | Extend into the full build-target registry. |
| Early Python compatibility validation | python_scripts/reportkit/cli.py and publication_pipeline/scripts/publication_build.py:356-365 | Keep one validation path and enrich its typed diagnostics. |
| Versioned context contract and filters | python_scripts/reportkit/context.py | Extend records and filtering for new combinations/compositions. |
| Primitive metadata extraction and generated docs | python_scripts/reportkit/registry.py and documentation.py | Add publication/theme/renderer drift checks; do not replace the extractor. |
| Unified diagnostic schema | python_scripts/reportkit/diagnostics.py and schemas/reportkit-diagnostic*.json | Route new validation through it. |
| Pinned toolchain and fingerprinted baselines | toolchain/, schemas/reportkit-toolchain.schema.json, .github/workflows/contract-ci.yml | Use it for all compile and visual gates; add Beamer dependencies only if doctor proves they are missing. |
| Compile timeout, memory limit and shell-escape prohibition | publication_pipeline/scripts/publication_build.py | Preserve in both renderers. |
| Paged accessibility contract | python_scripts/reportkit/publications.py:15-22 | Use as the parity checklist for slides. |
| Theme-aware Python visualization | python_scripts/reportkit/themes/ and reportkit_viz.py | Extend the Theme contract and add slide slots. |

### Remaining verified gaps

| Gap | Evidence at baseline |
| --- | --- |
| LaTeX options are still enumerated and unknown ReportKit values can reach article | latex_templates/reportkit.cls:29-49 |
| LaTeX has no generated compatibility table | only Python publications.py knows the supported pairs |
| Core still loads titlesec, fancyhdr, needspace, caption and geometry | latex_templates/reportkit-core.sty:17-22 |
| Callout chrome still branches on the literal theme name | latex_templates/reportkit-boxes.sty:9-64 |
| Metric styling remains hardcoded in the semantic box module | latex_templates/reportkit-boxes.sty:124-141 |
| Diagram appearance remains embedded across four semantic modules | reportkit-diagrams.sty, reportkit-structure.sty, reportkit-process.sty and reportkit-spatial.sty |
| The pipeline still has one hardcoded template and no class-option plumbing | publication_build.py:34,394-396,442 and publication-template.tex:1 |
| Markdown conversion is always Pandoc latex output | publication_build.py:174 and 415-418 |
| The equity fixture documents that it is not pipeline-driven | latex_templates/examples/equity-research/publication.yaml:1-8 |
| No slide class, slide core, presentation publication type or new theme exists | no matching files under latex_templates/ |

### Baseline verification note

The pipeline-only suite passes locally:

    python3 -m pytest publication_pipeline/tests -q
    12 passed, 1 skipped

The combined suite cannot be trusted in the drafting host: collection fails
because the host mixes NumPy 2.4.4 with NumPy-1-built optional modules and does
not have PyMuPDF. This is an environment mismatch, not a product failure.
Execution must establish its baseline inside the pinned container before the
first code change.

## 2. Resolved architecture decisions

### D1 — default remains canonical; technical is an alias

The existing default theme is the technical design system and carries the
backward-compatibility promise. Renaming it would alter diagnostics, context
output, chart lookup and hand-written class options for no visual benefit.

Add technical as a declared alias of default:

- theme=default remains the no-option default and the canonical stored name;
- theme=technical resolves to the exact same LaTeX package and Python Theme
  object;
- context reports alias_of: default;
- technical does not get a duplicate theme implementation or visual baseline;
- registry-driven compatibility tests exercise both names.

This resolves open question 1 without inventing a fifth visual family.

### D2 — themes populate definition-time token macros

Themes load before semantic modules. Use that order directly:

- shared core declares the required style-token interface with unset sentinels;
- each theme renews token macros before boxes and diagrams are defined;
- class startup hard-fails if a selected theme leaves any required token unset;
- semantic modules translate those token macros into tcolorbox/TikZ styles at
  definition time;
- no AtBeginDocument deferral is used for component styling;
- no semantic module inspects the theme name.

Font resolution may continue at AtBeginDocument because its existing setters
must remain usable anywhere in the preamble. This decision applies only to
component style construction and resolves open question 2.

### D3 — Python is canonical; LaTeX consumes a generated registry

Extend python_scripts/reportkit/publications.py as the only hand-maintained
catalog. It resolves:

    publication type
      → renderer
      → compatible themes
      → class
      → template
      → Pandoc writer
      → paper or canvas
      → required engine

Generate latex_templates/reportkit-publication-registry.def from that catalog
and commit it. Both classes input the generated file and hard-fail unknown names,
unsupported pairs and renderer/class mismatches. A drift test regenerates the
file in memory and compares it byte-for-byte.

Required-engine data moves out of config.py's independent
THEME_ENGINE_REQUIREMENTS map. theme_engine_conflict() becomes a compatibility
facade over the canonical theme record so existing imports remain valid.

This gives hand-written TeX an offline backstop without creating a second
authority and resolves open question 3.

### D4 — renderer is always derived

Renderer never becomes a user-settable document option. The pipeline derives
it from publication_type. document.class remains readable as a deprecated
diagnostic field but cannot select the backend.

For hand-written TeX, the chosen class validates that the publication type maps
back to it:

- reportkit.cls accepts only paged publication types;
- reportkit-slides.cls accepts only slide publication types;
- a mismatched class/publication pair is a ClassError that names the correct
  class.

### D5 — slides use one explicit 16:9 canvas

Use Beamer with aspectratio=169 and a declared 160 mm × 90 mm canvas. Theme
geometry records safe-area margins and derives usable chart dimensions from
that canvas.

paper remains valid for paged publications. For the slides renderer:

- an explicitly configured document.paper is a configuration error;
- an omitted paper key remains omitted in the resolved target;
- context reports canvas rather than pretending A4 applies;
- PDF inspection asserts the 160 mm × 90 mm MediaBox within tolerance.

This resolves open question 4. A second slide aspect ratio requires a separate
spec because it affects every slide composition and visual baseline.

### D6 — brand overrides create one effective theme

Add exactly four brand keys: primary, secondary, logo and display_font.
They are allowed only where the theme registry says brand_overrides: true
(initially venture).

Config resolution produces one immutable effective-theme record. The build then:

1. writes reportkit-theme-overrides.tex for LaTeX;
2. exposes the same normalized overrides to reportkit_viz.apply_theme();
3. records the effective palette/font/logo hashes in build-report.json;
4. validates the generated TeX colors against the effective Python palette.

Base-theme synchronization still compares source theme files with their Python
Theme objects. Override synchronization compares generated artifacts from one
resolved record, not the unchanged base file. Colors accept canonical six-digit
hex values; logo must resolve inside the publication root; display_font obeys
the existing strict/fallback font policy. This resolves open question 5.

### D7 — use shared entrypoints plus renderer bases

Create the six required publication entrypoints:

    publication_pipeline/templates/
    ├── technical-report.tex
    ├── equity-research.tex
    ├── executive-brief.tex
    ├── feature-article.tex
    ├── presentation.tex
    └── book.tex

Each entrypoint owns only its class declaration and publication-specific front
matter hook. Shared preamble, metadata, links, licensing and body inclusion live
in private paged-base.tex and slides-base.tex files.

The builder stages the selected entrypoint as publication.tex after replacing
only explicit ReportKit placeholders for theme and class options. It never
performs unrestricted string formatting over TeX source.

### D8 — Beamer is the slide backend

No implementation constraint currently justifies a custom slide engine. Beamer
already owns frame mechanics, overlays, navigation and 16:9 geometry. ReportKit
will disable decorative navigation and animation-heavy features, then put
semantic compositions and theme hooks above Beamer.

### D9 — new visual themes require LuaLaTeX

Executive, venture and editorial use LuaLaTeX. This keeps font behavior aligned
with institutional-research, supports controlled display-font overrides, and
avoids adding another pdfTeX font packaging path. default/technical remain on
pdfLaTeX and preserve their existing output.

Use the already bundled Google Sans family for executive and venture unless
design review demonstrates a real need for another redistributable font.
Editorial starts with the already bundled Libertinus assets. Any new font still
passes tests/test_licensing.py before it enters the tree.

### D10 — CI is sharded, but all combinations remain release gates

Every relevant pull request runs:

- fast unit, schema, drift and static-validation tests;
- a compile matrix generated from every supported theme × publication pair;
- visual regression for the five showcase fixtures in parallel jobs;
- default-theme deterministic PDF hash comparison;
- contract acceptance and accessibility inspection.

Visual jobs are separate matrix shards so one slow LuaLaTeX fixture does not
serialize the suite. They are still required checks, not nightly-only tests.
Baseline updates require reviewed before/after images and a matching pinned
toolchain fingerprint. This resolves open question 6.

### D11 — theme/renderer intersections use explicit adapters

Executive is one theme that supports two renderers. Its page geometry and slide
safe area cannot live in one undifferentiated file, and the semantic packages
must not branch to compensate.

Use a systematic two-layer theme load:

    reportkit-theme-<theme>.sty
      → shared color, font and semantic appearance

    reportkit-theme-<theme>-<renderer>.sty
      → renderer-specific geometry, spacing, furniture and component tuning

Both are theme-owned. The class loads the common file and the adapter selected
by the already-resolved renderer, then asserts the full token interface before
loading semantic modules. Python Theme records mirror this with per-renderer
token sets.

Phase A splits the existing default and institutional files by moving their
paged-only blocks verbatim into -paged adapters. Neither theme gains slide
support. Executive later supplies both -paged and -slides adapters; venture
supplies only -slides; editorial supplies only -paged. Adding a theme or a
renderer never requires a conditional in a semantic module.

### Resolved target matrix

| Publication type | Renderer / class | Themes | Target |
| --- | --- | --- | --- |
| technical-report | paged / reportkit | default, technical alias | A4 |
| equity-research | paged / reportkit | institutional-research | Letter |
| executive-brief | paged / reportkit | executive, institutional-research | Letter |
| feature-article | paged / reportkit | editorial | A4 |
| presentation | slides / reportkit-slides | executive, venture | 160 × 90 mm |
| book | paged / reportkit | default, technical alias, editorial | A4 |

Required engine is resolved from the selected canonical theme, not duplicated
on these publication records.

profiles remains a build-profile mechanism only. It does not accept genres or
topic-driven theme choices. brand is a top-level, theme-constrained section and
is not profile-overridable.

## 3. Target data flow and ownership

    publication.yaml
          │
          ▼
    config.py ──► publications.py / resolve_build_target()
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           renderer     theme   publication type
              │          │          │
              └──────────┼──────────┘
                         ▼
               immutable BuildTarget
       (class, template, writer, engine, geometry)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       Markdown/directives      theme overrides
              │                     │
              ▼                     ▼
          body.tex       reportkit-theme-overrides.tex
              └──────────┬──────────┘
                         ▼
              paged class or slide class
                         │
                         ▼
                  PDF + diagnostics

Renderer interface documentation must describe capabilities, not TeX
mechanisms. A renderer provides:

- target geometry;
- publication-body conversion;
- structural placement hooks;
- figure/table placement;
- output compilation;
- diagnostics and accessibility claims.

Class names, Pandoc writers and TeX packages are backend adapter details in the
registry. Add references/renderer-contract.md and test that each registered
renderer supplies the required capability fields.

## 4. Phase A — architecture hardening

Phase A lands before any released new theme. Use small commits in the order
below; do not combine the registry, core split and pipeline rewrite into one
unreviewable diff.

### A0 — capture the compatibility baseline in the pinned toolchain

**Files:**

- toolchain/Dockerfile and toolchain/toolchain.lock.json only if doctor proves
  Beamer or a required package is absent
- latex_templates/examples/career_guide_en/expected/ (new hash/visual metadata)
- existing equity expected assets
- tests/ fixture-baseline helpers

**Work:**

1. Build the pinned image and require its fingerprint.
2. Compile career_guide_en with no class options at a stable path.
3. Store the deterministic PDF SHA-256 and representative rendered pages.
4. Compile and render the existing direct equity fixture.
5. Record class options, engine, font list, page dimensions and toolchain
   fingerprint beside each baseline.
6. Re-run the documented tagged-PDF spike and update
   references/accessibility-tagging.md with its current result.

**Gate:** no architecture code starts until both current fixtures compile in the
pinned environment and the baseline metadata is checked in.

### A1 — turn publications.py into a build-target registry

**Files:**

- python_scripts/reportkit/publications.py
- python_scripts/reportkit/config.py
- python_scripts/reportkit/context.py
- python_scripts/reportkit/registry.py
- schemas/reportkit-context.schema.json
- tests/test_agent_contract.py
- tests/test_reportkit_vnext.py
- new tests/test_publication_registry.py

**Work:**

- Add renderer records for class adapter, template base, Pandoc writer, target
  geometry and accessibility.
- Add template and default-target data to publication-type records.
- Add alias_of, required_engine, common_package, renderer_adapters,
  brand_overrides and language/script data to theme records.
- Implement resolve_build_target(publication_type, theme, explicit_paper,
  engine) returning one immutable result or one typed configuration diagnostic.
- Preserve compatibility_error() and theme_engine_conflict() as thin facades.
- Reject alias cycles, missing referenced records, empty compatible-theme lists,
  renderer/theme mismatches and templates/classes that do not exist.
- Have context build its selection and authoring template from the resolved
  target instead of reconstructing fields independently.
- Extend the context schema without removing v1 compatibility fields.

**Tests:**

- every record is internally referentially complete;
- technical resolves exactly like default except for requested_name;
- unknown names include sorted valid candidates;
- unsupported pairs include compatible themes;
- engine mismatch is identical in check and build;
- document.class cannot override the derived class;
- context filters remain correct for aliases and future multi-renderer themes.

### A2 — generate and enforce the LaTeX registry

**Files:**

- python_scripts/reportkit/publications.py
- latex_templates/reportkit-publication-registry.def (generated)
- latex_templates/reportkit-options.tex (new shared class-option parser)
- latex_templates/reportkit.cls
- publication_pipeline/scripts/publication_build.py
- scripts/acceptance_check.sh
- tests/conftest.py
- new tests/test_latex_publication_registry.py

**Work:**

- Generate name lists, aliases, renderer ownership, package names and supported
  pairs into the .def file.
- Parse theme and publication-type systematically in a shared option layer.
- Continue forwarding genuine base-class options, but intercept any unknown
  theme= or publication-type= value and issue ClassError.
- Validate the pair and the current class renderer before loading a theme.
- Keep no-option defaults byte-compatible.
- Add .def/.tex infrastructure files to staging, TEXINPUTS and manifest hashing.
- Add a generation drift test to the existing contract/docs gate.

**Compile cases:**

- no options;
- every supported pair;
- unknown theme;
- unknown publication type;
- known but unsupported pair;
- slides publication through paged class;
- paged publication through slide class once Phase B adds that class.

Failure tests assert both non-zero exit and the requested value in the error.
A warning followed by a PDF is a failing test.

### A3 — split shared and paged mechanics

**Files:**

- latex_templates/reportkit-core.sty
- latex_templates/reportkit-paged-core.sty (new)
- latex_templates/reportkit.cls
- latex_templates/reportkit-boxes.sty
- latex_templates/reportkit-code.sty
- latex_templates/reportkit-diagrams.sty
- latex_templates/reportkit-longform.sty
- relevant compile tests

**Load order for paged documents:**

    article
      → reportkit-core
      → reportkit-paged-core
      → selected common theme
      → selected theme/paged adapter
      → optional generated theme overrides
      → selected publication type
      → semantic modules

**Shared core retains:** engine detection; guarded xcolor/graphicx/hyperref
setup; xparse/etoolbox; metadata; catalog language; link helpers; semantic
registration; provenance; required style-token declarations; renderer hook
declarations. Required tokens/hooks start unset and are asserted after the
renderer core and theme load, preventing a partial theme from silently borrowing
the default appearance.

**Paged core owns:** geometry; fancyhdr; titlesec; needspace; caption;
article pagination; paged figure/table placement; section reservation.

Replace semantic-module calls to Needspace and captionof with renderer hooks,
including:

- RKReserveSpace;
- RKDiagramPlacementBegin / RKDiagramPlacementEnd;
- RKDiagramCaption;
- RKDiagramSource;
- renderer-aware section/subsection opening.

The paged implementation delegates to today's exact behavior. The slide
implementation is supplied in Phase B and must not load needspace.

**Gate:** the default fixture retains its pinned PDF hash. The institutional
fixture retains approved pixels, fonts, dimensions and diagnostics.

### A4 — move component appearance behind theme tokens

**Files:**

- latex_templates/themes/reportkit-theme-default.sty
- latex_templates/themes/reportkit-theme-default-paged.sty
- latex_templates/themes/reportkit-theme-institutional-research.sty
- latex_templates/themes/reportkit-theme-institutional-research-paged.sty
- latex_templates/reportkit-boxes.sty
- latex_templates/reportkit-diagrams.sty
- latex_templates/reportkit-structure.sty
- latex_templates/reportkit-process.sty
- latex_templates/reportkit-spatial.sty
- python_scripts/reportkit/themes/__init__.py
- python_scripts/reportkit/themes/default.py
- python_scripts/reportkit/themes/institutional_research.py
- python_scripts/reportkit_viz.py
- tests/test_reportkit_viz_themes.py
- new tests/test_theme_contract.py

**Theme/adaptor work:**

- Move paged geometry, headings, running furniture and page-specific component
  values from the two existing theme files into their -paged adapters without
  rewriting the definitions.
- Keep shared palette, font roles and renderer-neutral semantic appearance in
  the common theme files.
- Make check-theme validate both common and renderer-adapter token layers.

**Callout work:**

- Move both current rk@callout option sets into theme token macros.
- Move metric card typography, spacing, rule and color choices into the same
  contract.
- Keep principle, decisionpoint, metric and every alias signature unchanged.
- Delete all rk@theme references from reportkit-boxes.sty.

**Diagram work:**

- Make these stable TikZ styles theme-populated: rk node, rk edge, rk edge
  label, rk layer, rk matrix axis and rk timeline.
- Add subordinate tokens for node padding/radius/font, edge weights, lane
  labels, layer title/body, matrix cells, stack/funnel labels and roadmap
  elements.
- Apply them across diagrams, structure, process and spatial. The latter three
  are included because the acceptance examples named in the spec live there;
  changing only reportkit-diagrams.sty would leave reportarchitecture and
  reportroadmap theme-locked.
- Keep geometry parameters supplied by authored semantics; themes may set
  defaults but do not fork implementations.

**Python/theme-contract work:**

- Extend Theme with explicit typography, chart, geometry, rule, table, diagram
  and script-coverage records.
- Keep the current public color and figure-size accessors as compatibility
  views.
- Extend check-theme so palette, font roles, geometry and shared token presence
  are checked through one command.

**Static gate:**

    rg for rk@theme in semantic modules returns no matches
    rg for theme-name string literals in semantic modules returns no matches

Compile and pixel/hash gates from A3 remain mandatory.

### A5 — make the pipeline target-aware

**Files:**

- publication_pipeline/templates/technical-report.tex
- publication_pipeline/templates/equity-research.tex
- publication_pipeline/templates/paged-base.tex
- placeholders for the four later entrypoints only when their publication
  records land; do not select non-implemented formats
- publication_pipeline/scripts/publication_build.py
- publication_pipeline/scripts/render_visuals.py
- python_scripts/reportkit/config.py
- schemas/reportkit-build-report.schema.json
- publication_pipeline/tests/test_template_features.py
- publication_pipeline/tests/test_additive_features.py
- new publication_pipeline/tests/test_build_target_selection.py

**Work:**

- Replace the module-level TEMPLATE constant with the resolved BuildTarget.
- Select the Pandoc writer through the renderer record.
- Stage the selected entrypoint and its shared includes, recording hashes.
- Materialize class options, theme font settings and future overrides into
  generated preamble files.
- Compile a stable publication.tex filename so downstream packaging remains
  independent of the source template name.
- Record requested and canonical theme, publication type, renderer, class,
  template, writer, engine and paper/canvas in build-report.json.
- Emit a machine-readable and log-visible resolved-selection marker. PDF
  inspection uses it to detect default-theme leakage.
- Keep validation before Pandoc and TeX.

**Equity pipeline acceptance:**

Add manuscript/order.txt, Markdown source and trusted fragments under
latex_templates/examples/equity-research/ so its existing publication.yaml can
be passed directly to reportkit build. Preserve report.tex as the direct-TeX
compatibility witness. Both paths must render the same theme/publication
identity; the pipeline version need not be byte-identical if Pandoc changes
source ordering, but it must pass the same visual and semantic checks.

### Phase A definition of done

- Python and LaTeX reject unknown names and unsupported pairs before producing
  a plausible wrong-theme PDF.
- Python is the only hand-maintained compatibility source.
- No semantic module branches on a theme name.
- Shared core loads no paged-only package.
- Existing direct TeX and pipeline technical output retain the deterministic
  default baseline.
- Institutional/equity compiles through the Markdown pipeline.
- New diagnostics use the v1.9 diagnostic schema.
- The full pinned-toolchain gate passes.

## 5. Phase B — slide renderer and presentation semantics

### B1 — add reportkit-slides.cls and slides core

**Files:**

- latex_templates/reportkit-slides.cls
- latex_templates/reportkit-slides-core.sty
- latex_templates/publication_types/reportkit-presentation.sty
- latex_templates/themes/reportkit-theme-executive.sty
- latex_templates/themes/reportkit-theme-executive-slides.sty
- publication_pipeline/templates/presentation.tex
- publication_pipeline/templates/slides-base.tex
- python_scripts/reportkit/publications.py and generated LaTeX registry
- tests/test_slide_renderer.py

**Work:**

- Load Beamer at 16:9 and never load geometry, fancyhdr, titlesec, needspace or
  paged caption behavior.
- Implement slide versions of the renderer hooks from A3.
- Disable Beamer navigation symbols and overlays in the public ReportKit
  composition API; animations remain possible only through raw-TeX escape.
- Keep metadata setters, source/provenance helpers, diagrams, charts, links and
  semantic boxes available.
- Add the presentation publication record and an experimental executive theme
  shell containing a complete token set. Do not release between B and C.
- Make Pandoc use its Beamer writer with an explicit slide level. Add fixtures
  for plain Markdown frames and directive/fragment-based compositions.

### B2 — define one presentation composition API

reportkit-presentation.sty owns semantic structures, not visual values. Its
contract must cover:

- title slide and section divider;
- single-message and assertion-evidence slide;
- text + visual and visual + text;
- full visual;
- two-column comparison;
- three-part argument;
- hero metric;
- chart, table and architecture slides;
- closing and appendix slides.

Each composition has source-adjacent contract metadata, validates through the
existing registry extractor, and delegates spacing, type, alignment, rules,
background and density to theme hooks. Executive and venture use these exact
definitions.

### B3 — add slide visualization slots

Add slide-main, slide-half and slide-hero only to slide-compatible Theme
objects. Derive widths from each theme's canvas and safe margins. Preserve all
seven current paged size names and the wide alias without value changes.

Tests assert:

- slot dimensions fit the declared safe area;
- chart typography is the resolved theme font;
- generated PDFs use vector text;
- no paged theme gains accidental slide dimensions;
- unknown slot/theme combinations fail explicitly.

### B4 — prove accessibility parity

For a canonical slide PDF, inspect:

- title/author/subject metadata;
- catalog language;
- PDF outline/bookmarks;
- meaningful link annotations;
- diagram ActualText alternatives;
- truthful tagged-PDF capability status.

If the updated tagging spike succeeds, enable tagging for both renderers in a
separate reviewed change. Do not claim parity merely because Beamer compiled.

### Phase B definition of done

A presentation builds from publication.yaml through the normal pipeline, uses
reportkit-slides.cls and Pandoc's Beamer writer, has the declared canvas, carries
the paged accessibility features, and loads no paged-only mechanics.

## 6. Phase C — executive theme

**Files:**

- latex_templates/themes/reportkit-theme-executive.sty
- latex_templates/themes/reportkit-theme-executive-paged.sty
- latex_templates/themes/reportkit-theme-executive-slides.sty
- python_scripts/reportkit/themes/executive.py
- latex_templates/examples/executive-presentation/ (new)
- tests/test_executive_theme.py
- scripts/visual_qa_executive.py or a generalized fixture runner

**Work:**

- Finish the Phase B executive token shell as a consulting/strategy system.
- Tune assertion-evidence hierarchy, grid, moderate-high density, restrained
  palette, chart/table styles and diagram styles.
- Exercise existing architecture, process, matrix, roadmap, waterfall,
  timeline and table primitives without bespoke TikZ or page coordinates.
- Build an 8–10 slide fictional technology/strategy deck containing every item
  required by renderer spec §18.
- Promote executive from experimental to stable only after visual approval.

**Gate:** the same authored architecture diagram renders in the default
technical fixture and the executive deck with no theme-specific syntax.

## 7. Phase D — venture theme and controlled branding

**Files:**

- latex_templates/themes/reportkit-theme-venture.sty
- latex_templates/themes/reportkit-theme-venture-slides.sty
- python_scripts/reportkit/themes/venture.py
- python_scripts/reportkit/config.py
- python_scripts/reportkit/themes/__init__.py
- python_scripts/reportkit_viz.py
- publication pipeline preamble/override generation
- latex_templates/examples/venture-presentation/ (new)
- tests/test_brand_overrides.py
- tests/test_venture_theme.py
- generalized visual QA runner

**Work:**

- Implement venture with large type, lower density, strong whitespace, light
  and dark frames, screenshot/product-image support and bold metric treatment.
- Add strict parsing for the four brand keys decided in D6.
- Hash and stage the brand logo like every other publication asset.
- Apply overrides to TeX and charts through the same effective-theme record.
- Author the 10–12 slide fictional pitch required by the spec.
- Use only the presentation compositions from Phase B.

**Critical gate:** a single presentation-semantic smoke document must compile
under executive and venture and produce materially different reviewed pixels.
There may be no venture copy of reportkit-presentation.sty and no venture-only
composition names. If this fails, stop and repair the abstraction before
editorial work.

## 8. Phase C-prime — constrained authoring and visual feedback

This is the remaining agent-contract Phase C-prime work and starts only after
the paged and slide renderers both exist.

### C-prime 1 — constrained Markdown directives and typed IR

**Files:**

- python_scripts/reportkit/authoring_ir.py (new)
- python_scripts/reportkit/markdown_directives.py (new)
- python_scripts/reportkit/tex_renderer.py (new)
- python_scripts/reportkit/authoring.py
- publication_pipeline/scripts/publication_build.py
- schemas/reportkit-authoring.schema.json (new)
- tests/fixtures/authoring-errors/ (new)
- tests/test_authoring_ir.py (new)

Use fenced ReportKit directives embedded in ordinary Markdown. Parse only the
directive grammar in the stdlib; Pandoc continues to own ordinary Markdown.
Normalize directives into typed IR nodes, validate primitive names,
availability, arguments and constraints from the capability contract, then
render safe TeX.

Validation collects all errors in one pass, reports manuscript file/line,
expected versus supplied arguments, candidates, remediation and contract
pointers, and never invokes TeX. Raw .tex documents and trusted fragments stay
available as explicit escape hatches.

**Acceptance:** the deliberate three-error corpus returns all three structured
diagnostics in under one second with no Pandoc or TeX subprocess.

### C-prime 2 — first-class render command

Add reportkit render over render_pdf_pages.py with:

- page/range selection;
- DPI control;
- predictable atomic output;
- JSON manifest and toolchain fingerprint;
- structured environment failure when PyMuPDF is unavailable.

Keep reportkit build's automatic full render, but document the authoring loop as
check → build → render selected pages → inspect → revise. Tests verify that a
single slide can be rendered without rasterizing the rest of a deck.

## 9. Phase E — editorial theme and feature article

**Files:**

- latex_templates/themes/reportkit-theme-editorial.sty
- latex_templates/themes/reportkit-theme-editorial-paged.sty
- python_scripts/reportkit/themes/editorial.py
- latex_templates/publication_types/reportkit-feature-article.sty
- publication_pipeline/templates/feature-article.tex
- latex_templates/examples/editorial-feature/ (new)
- tests/test_editorial_theme.py
- visual baselines

**Work:**

- Implement headline, deck, byline, opening visual, pull quote, sidebar,
  feature exhibit, section opener and image credit as semantic primitives.
- Keep every style decision in the editorial theme.
- Use Libertinus serif body with a complementary sans metadata/display stack;
  declare verified Latin-script coverage and honest unsupported/metadata-only
  languages.
- Support one-column, two-column and full-width visual rhythms without becoming
  a generic positioning language.
- Build the fictional 6–8 page fixture required by the spec.

**Gate:** replace the editorial theme with a test theme and compile the same
feature structure unchanged. No feature primitive may mention editorial.

## 10. Phase F — executive brief and book polish

### F1 — executive brief

Add reportkit-executive-brief.sty and executive-brief.tex. Reuse metric,
decisionpoint, redflag, exhibits and source helpers. Register executive and
institutional-research only after both combinations compile.

The acceptance fixture is 2–8 pages and covers recommendation, findings,
compact exhibits, implication, risks, next steps and sources. Do not add a
parallel executive component library.

### F2 — book

Add reportkit-book.sty and book.tex over reportkit.cls,
reportkit-paged-core.sty and reportkit-longform.sty. Add only publication
details, contents, part/chapter-style openers, bibliography hooks, appendices
and glossary hooks that a fixture actually exercises.

Do not add reportkit-book.cls, recto/verso production, signatures, indexing,
trim/bleed or a third renderer.

Register book with default/technical and editorial. The alias pair shares one
visual baseline; editorial receives a distinct compatibility smoke.

### F3 — combination coverage

Maintain two fixture layers:

1. five showcase fixtures: technical, institutional/equity, executive deck,
   venture pitch and editorial feature;
2. registry-generated minimal compile fixtures for every other supported
   theme × publication pair.

The test parameter list is derived from publications.py. Adding a compatible
pair without either a showcase or a generated smoke case fails collection.

## 11. Phase D-prime — neutrality, progressive disclosure and i18n

Interleave this with Phases E–F, after the catalog has reached representative
size.

### D-prime 1 — progressive disclosure

- Keep unfiltered context output for contract compatibility.
- Add a compact summary slice and publish approximate token cost per slice.
- Set the host-neutral always-loaded quickstart ceiling to 2,000 estimated
  tokens, using deterministic UTF-8-bytes/4 accounting in CI.
- Keep SKILL.md as a thin host adapter and generate its capability tables.
- Ensure publication type selection criteria and theme compatibility come only
  from publications.py.

### D-prime 2 — non-Claude adapter

Generate an OpenAI-style tool-definition bundle from the existing CLI command
contract under adapters/openai/. Its tests may invoke only stable CLI JSON and
the published schemas. It must author and validate a minimal publication
without reading SKILL.md.

The adapter is proof of neutrality, not a second manually maintained API.

### D-prime 3 — language and script truthfulness

- Extend all Theme objects with script coverage and per-script font stacks.
- Load locale-aware typography only for languages marked supported.
- Make missing glyphs fatal under strict font policy.
- Expose renderer/theme language compatibility through context.
- Keep RTL explicitly unsupported.
- Preserve Vietnamese as metadata-only until an actual typography fixture
  proves more.

## 12. Cross-cutting automated acceptance

### Static and contract

- publication registry internal consistency;
- generated LaTeX registry drift;
- full primitive metadata and examples;
- generated docs drift;
- schema conformance;
- stable diagnostic codes/remediation;
- no theme-name branches in semantic modules;
- no shell-escape path;
- template and asset containment;
- context-budget ceiling.

### Compile matrix

For every registered pair:

- correct class/renderer;
- correct paper or canvas dimensions;
- expected engine;
- expected fonts;
- no missing assets or glyphs;
- no undefined references;
- no unexpected overfull content;
- resolved-selection marker matches the request;
- no default-theme leakage;
- accessibility claims match inspection.

### Visual

- render selected canonical pages/slides at the pinned 150 DPI;
- compare only under the matching toolchain fingerprint;
- report changed regions and dimensions;
- require human inspection before baseline replacement;
- compare the no-option default PDF hash before and after Phase A.

### Architectural proofs

Maintain three shared-semantics smoke cases:

1. one architecture diagram under default, executive and venture;
2. one time-series dataset under institutional-research, executive and
   editorial;
3. one metric/evidence block under default, institutional-research and
   executive.

The sources differ only in registry-selected publication/theme wrappers. Any
theme-specific body syntax fails the proof.

## 13. Recommended pull-request sequence

1. Baselines and registry resolution.
2. Generated LaTeX registry and hard-failure option handling.
3. Shared/paged core split and renderer hooks.
4. Callout/metric/diagram theme hooks.
5. Pipeline target selection and equity pipeline fixture.
6. Slide class, slides core, presentation semantics and accessibility.
7. Executive theme and fixture.
8. Venture theme, brand overrides and fixture.
9. Constrained Markdown IR and reportkit render.
10. Editorial theme, feature article and fixture.
11. Executive brief and book.
12. Progressive disclosure, neutral adapter, i18n and release documentation.

Each PR must leave main releasable. The only intentional exception is the
experimental executive shell introduced by the slide-renderer PR; it remains
marked experimental and is not included in a release until PR 7 completes it.

## 14. Risks and stop conditions

| Risk | Control / stop condition |
| --- | --- |
| Core split changes default output | Stop on deterministic hash mismatch; bisect moved lines before continuing. |
| Beamer conflicts with shared packages | Keep conditional shared loads and renderer hooks; do not pull paged packages into slides to make one compile. |
| Theme tokens become an untyped macro swamp | Require every token category in both theme contract tests and context metadata. |
| Registry becomes duplicated again | No hand-edited LaTeX pairs; drift failure is mandatory. |
| Presentation API bakes in executive layouts | Stop when venture requires copied compositions; repair the publication/theme boundary. |
| Brand overrides make chart and TeX palettes diverge | Build both from one effective-theme record and compare generated artifacts. |
| Fixture runtime weakens CI | Shard jobs; do not remove combinations or auto-accept baselines. |
| Editorial expands into arbitrary DTP | Only add structures exercised by the canonical feature fixture. |
| Book work implies a new renderer | Defer until a real recto/verso, trim, index or print-production need exists. |
| Host environment gives misleading results | Require the pinned-toolchain fingerprint for baseline and release claims. |

## 15. Final definition of done

The implementation is complete only when:

- all six publication types resolve through one Python registry;
- both classes enforce the generated LaTeX backstop;
- every supported pair builds through publication.yaml without a manual class;
- paged and slide mechanics share semantics but not page/frame infrastructure;
- executive and venture share one presentation package;
- all five showcase fixtures and every compatibility smoke pass compilation,
  inspection and visual gates;
- current default APIs and figure-size keys remain valid;
- no semantic module branches on theme names;
- agent context, diagnostics, generated docs and the neutral adapter describe
  the expanded system without drift;
- the three cross-format shared-semantics proofs pass.
