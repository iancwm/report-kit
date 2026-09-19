# ReportKit Multi-Format Publication Architecture — Implementation Plan

**Status:** Phase A implementation complete in the working tree; its pinned
OCI verification passed the focused A3/A4 checks on 2026-09-19, while the full
acceptance matrix remains outstanding. Phase B started out of the plan's own
recommended order (see below), then A5 followed it. Architecture decisions
are resolved; A1, A2, A3 and A4 are implemented, with focused pinned
verification passed and the full acceptance matrix still outstanding;
**A4's diagram work (the last item the plan's own A4 section
named as "not started") is now implemented** -- theme/adapter split,
callout/metric token work, and diagram chrome tokens are all in the tree;
the Python/theme-contract extension is now implemented in the working tree.
A5 is complete for the currently registered targets; theme/font/brand
override materialization, the full D7 paged split, constrained directive
authoring, and selection-marker inspection are now implemented in the working
tree, and the equity pipeline acceptance is implemented; A0 is now complete
against the available pinned toolchain image, with both fixture baselines
checked in. B1 and B2 are
essentially complete, now proven through `reportkit build` itself (not
just direct-TeX authoring) for the "plain Markdown frames" authoring path;
B3 is implemented for the one existing slide theme; B4 is verified by
an automated PDF-inspection gate on the canonical slide fixture. **`reportkit build` can
now produce both a technical-report/equity-research-style paged
publication and a presentation** -- see A5's own section for the
verification record. **Note on sequencing:** §13's recommended PR sequence
puts A5 before Phase B specifically so a presentation could be built
through the normal pipeline once the renderer existed; Phase B was
implemented first here at explicit request, and A5 followed once B's own
status notes kept naming it as the biggest remaining gap. Task sizing and
visual design details should receive engineering/design review before
execution.
**Last updated:** 2026-09-19
**Plans:** [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](../specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md)
**Amended by:** [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](../specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md)
**Baseline:** planning baseline `main` at `4f2b27f`, ReportKit v1.9.1.
**Current status:** base verified against `main` at `b5807e8`, with the
Python/theme-contract, target-aware A5/equity-acceptance, automated B4
slide-accessibility changes, and pinned fixture baselines retained in this
branch, ReportKit v1.9.3, on 2026-09-17. Mainline bounded parallel
section-build tooling remains in the rebased base.

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

**Execution status (updated 2026-09-17):** A0, A1 and A2 are complete in
ReportKit v1.9.2 and v1.9.3. A3 is implemented in the working tree (see its
section below for verification detail and scope actually covered — not yet
released as a version bump, and the pinned-toolchain CI gate has not run
against it). A4 is implemented in the working tree, also not yet released;
runtime and pinned-toolchain verification remain. A5 is complete for the
currently registered targets; theme/font/brand override materialization, the
full D7 paged split, constrained directive authoring, and selection-marker
inspection are implemented in the working tree. A0 is complete against the
available pinned image: the career and equity fixtures compile reproducibly,
their metadata and representative renders are checked in, and the tagged-PDF
no-go result is recorded. The pinned-toolchain CI gate for the broader A3/A4
work remains outstanding. Phase B (slide renderer and
presentation semantics) is essentially complete too, implemented before A5
at explicit request — see its own section.

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

**Verified 2026-09-17:** the available `reportkit:toolchain` image carries
the locked fingerprint
`6e0fc8ea7889634d3c337eacc4e4f68adb10c2c968e2e7e683f5c24de07408e5`, passes
`reportkit doctor --json`, and its image history uses the pinned Debian
snapshot/package versions from `toolchain/Dockerfile`. The current `main`
career fixture produced PDF SHA-256
`acd8ebdc29028baa8d64dad18120f9719cdcbca6a2d401261110710f9392d0ba` on two
independent two-pass builds; the equity fixture produced
`2bd1060b386b05391285e3a4214a148c6fa16b7648da67178752591ff28dc4fd` on two
independent two-pass builds. Career representative pages remain within the
recorded pixel threshold, while all four equity pages are pixel-identical to
their checked-in baseline. A0 is therefore closed locally; the CI gate for
the broader un-released A3/A4 slices remains the authoritative follow-up.

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
- latex_templates/reportkit-algorithms.sty
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

**Implemented 2026-09-13, one deviation from "shared core retains ...
hyperref setup" above, recorded because it is load-bearing:** the actual
`\RequirePackage{hyperref}` call, and the scheduling (`\AtBeginDocument{...}`)
of the metadata/catalog-language block that consumes it, moved to
`reportkit-paged-core.sty`, right after that file's `geometry` require —
not into `reportkit-core.sty`. `reportkit-core.sty` still owns *what* that
block does (`\RKRegisterDocumentMetadata`, `RKLink`) — only the `\RequirePackage`
call and the one-line `\AtBeginDocument{\RKRegisterDocumentMetadata}` moved.

This was not a style choice: hyperref's own documentation asks it to be
loaded after other formatting packages, and it also registers its own
`\AtBeginDocument` hook when it loads. `\AtBeginDocument` hooks run in
registration order, so loading hyperref (and scheduling reportkit's hook)
before a paged-only package such as `geometry` — which is what "shared core
retains hyperref setup" reads as, since shared core loads before any
renderer core — measurably changes the pinned default-theme PDF: named
destination coordinates shift by tens of points, and the `/Catalog`
dictionary's key order changes, even though nothing about the visible
document changed. Verified empirically, twice (isolated single-line-reorder
repro, then the actual split), against a local LuaLaTeX/pdfLaTeX toolchain:
reordering hyperref's require earlier reproduces the hash break by itself;
requiring hyperref (and scheduling the AtBeginDocument hook) from
`reportkit-paged-core.sty` instead, immediately after `geometry`, reproduces
the original bytes exactly.

A slides core must require hyperref, and schedule
`\AtBeginDocument{\RKRegisterDocumentMetadata}`, the same way — right after
its own canvas/frame package — for the same reason (Beamer also loads
formatting machinery hyperref should follow, and a slides-core hook
registering ahead of Beamer's own `\AtBeginDocument` calls is the same class
of bug even though there is no pinned hash to catch it there yet).

**Verified 2026-09-13** against a local (non-pinned — see A0's note above)
LuaLaTeX/pdfLaTeX toolchain, not yet against the pinned-toolchain CI gate:

- `latex_templates/examples/career_guide_en/report.tex` (default theme,
  pdfLaTeX, uses `principle`/`metric`/`diagram`/`execsummary`) — PDF SHA-256
  byte-identical before/after the split.
- `latex_templates/examples/equity-research/report.tex`
  (institutional-research theme, equity-research publication type,
  LuaLaTeX) — PDF SHA-256 byte-identical before/after.
- `latex_templates/examples/longform_acceptance_test.tex`
  (`reportkit-longform`, pdfLaTeX) — PDF SHA-256 byte-identical before/after.
- `python -m pytest tests publication_pipeline/tests` — same pass/fail set
  before and after, once one real regression this change introduced was
  found and fixed: `test_toolchain_fingerprint_and_release_version_are_stable`
  checks that `reportkit.cls`'s `\ProvidesClass` version string matches
  `version.py`'s `REPORTKIT_VERSION`; an early draft of this change bumped
  the class's declared version (to document the split) without bumping
  `REPORTKIT_VERSION`, and the test caught it correctly. Fixed by leaving
  `\ProvidesClass` at `v1.9.3` — a version bump is a separate release commit
  by this project's convention, not something a feature change does on its
  own. Three failures remain and are pre-existing, unrelated to this change,
  and specific to this non-pinned sandbox (reproduce identically against the
  unmodified tree): `test_acceptance_check_uses_venv`,
  `test_every_json_capable_command_uses_the_common_envelope[arguments1-0]`,
  `test_doctor_dependency_remediation_is_present_in_text_and_json`. One
  `test_reporttimeline.py` compile test failed once, only in a combined,
  writable-mount, full-suite run, and passed cleanly both standalone and in
  every other full-suite run (read-only mount) on this same tree — treated
  as a one-off sandbox flake (resource contention under that specific run
  shape), not a regression, but called out rather than silently discarded.
- `reportkit docs --check --json`, `scripts/contract_acceptance.py --json`,
  and `scripts/acceptance_check.sh --require-tex` all pass.

The pinned-toolchain CI gate (`.github/workflows/contract-ci.yml`) has not
run against this change yet and is the authoritative check.

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

**Implemented 2026-09-13 (historical checkpoint) -- theme/adapter split and
callout/metric token work:** diagram work remained open at this checkpoint,
then landed on 2026-09-15 in the record below; the Python/theme-contract
extension remains open:

- **Theme/adapter split (D11), for both existing themes:** geometry, running
  furniture (fancyhdr), section-heading placement (titlesec), and
  `\maketitle` moved verbatim out of `reportkit-theme-default.sty` and
  `reportkit-theme-institutional-research.sty` into two new files,
  `reportkit-theme-default-paged.sty` and
  `reportkit-theme-institutional-research-paged.sty`. What remains in each
  common file is fonts, palette, typography defaults (parindent/parskip/
  setlist/sisetup/captionsetup -- judged renderer-neutral, not page-specific,
  so kept common rather than moved), the style-token contract (below),
  `execsummary` (an ordinary list environment, no page machinery), and the
  `\source` helper.
  `python_scripts/reportkit/publications.py`'s `_theme()` helper gained an
  explicit `renderer_adapters` parameter (previously always defaulted to
  `{renderer: common_package}`, i.e. the adapter was always the same file as
  the common package -- the registry's `RKThemeAdapter@name@renderer` csname
  already existed from A1/A2 but nothing populated it with a distinct value
  or read it); `default`/`technical` and `institutional-research` now pass
  their real `-paged` adapter names.
  `reportkit.cls` loads the adapter package right after the common package,
  looked up the same way (`RKThemeAdapter@\rk@theme@\rk@classrenderer` via
  `\csname`, using the same `\string @`-insertion trick
  `reportkit-options.tex`'s `RKValidateSelection` already used, to avoid the
  literal `@` being absorbed into the preceding control word under
  `\makeatletter`).
  `reportkit-publication-registry.def` regenerated (drift test passes).
- **Callout/metric token work:** `reportkit-core.sty` gained the style-token
  contract the plan's D2 describes: ~30 `RKTok...` sentinel macros (listed in
  `tests/test_theme_contract.py`'s `REQUIRED_STYLE_TOKENS`), an
  `\rk@styletokensloaded` flag, and `\RKAssertStyleTokens` -- the same
  loud-sentinel pattern A3's `\RKAssertRendererHooks` already established for
  renderer hooks. Both theme common files `\renewcommand` every token (the
  institutional-research theme's quiet chrome -- spec §21, no fill, no frame
  -- and the default theme's boxed chrome are exactly the pre-existing
  hardcoded values, just relocated) and set the loaded flag.
  `reportkit-boxes.sty`'s `\ifdefstring{\rk@theme}{institutional-research}`
  branch is gone: one `\newtcolorbox{rk@callout}` definition and one `metric`
  environment, both reading tokens (`colback=\RKTokCalloutColBack`, etc.).
  Font-role tokens (`RKTokCalloutTitleFont`, the metric card's label/value/
  subtitle/why fonts) bundle their own `\fontsize{}{}\selectfont` since they
  execute as ordinary TeX inside a tcolorbox title/body, not as a pgfkeys
  value.
  A real risk before compiling: whether tcolorbox's `colback=`/`colframe=`
  keys, which end up inside `\colorlet`, would resolve a macro standing in
  for a color name (as opposed to the literal identifier) -- confirmed empirically
  by compiling, not assumed; see the verification below.
- **New test coverage:** `tests/test_theme_contract.py` (static; no
  toolchain assumed) -- every required token has a core sentinel, every
  canonical theme's common package populates every token and sets the
  loaded flag, and `reportkit-boxes.sty` neither branches on `\rk@theme` nor
  names a theme directly (comments excluded) and asserts the tokens before
  reading them. Updated `tests/test_reportkit_vnext.py` (the old
  `test_reportkit_boxes_default_theme_unchanged`, which asserted the
  `\ifdefstring` branch existed, is replaced by
  `test_reportkit_boxes_reads_style_tokens_not_theme_name` plus two
  theme-specific token assertions; `test_institutional_theme_uses_letter_geometry_and_type_scale`
  now reads geometry from the `-paged` file) and `tests/test_agent_contract.py`
  (`renderer_adapter` for institutional-research is now
  `reportkit-theme-institutional-research-paged`, not the common package
  name).
- **Verified 2026-09-13** in a throwaway, unpinned local toolchain (this
  session's sandbox has direct network access, unlike the one that wrote
  A3's verification -- `apt-get install texlive-luatex texlive-latex-extra
  texlive-bibtex-extra texlive-fonts-recommended texlive-science pandoc` plus
  the checked-in Google Sans/Libertinus fixtures staged the same way
  `toolchain/Dockerfile` does; not the pinned image itself, same caveat as
  A0/A3's non-pinned verification):
  - `latex_templates/examples/career_guide_en/report.tex` (default theme,
    pdfLaTeX) -- PDF SHA-256 byte-identical across baseline, theme-split-only,
    and theme-split-plus-tokens, with `SOURCE_DATE_EPOCH=1 TZ=UTC` set to
    match `toolchain/Dockerfile`'s determinism environment (without it, even
    the unmodified baseline is not self-reproducible across two pdfLaTeX
    runs -- a sandbox/toolchain-version quirk, not a ReportKit determinism
    bug: SOURCE_DATE_EPOCH fixes it completely for pdfLaTeX).
  - `latex_templates/examples/equity-research/report.tex`
    (institutional-research theme, equity-research publication type,
    LuaLaTeX): raw PDF bytes are **not** hash-identical even baseline-to-baseline
    on this toolchain (confirmed: two back-to-back baseline compiles of the
    unmodified tree, both with `SOURCE_DATE_EPOCH=1 TZ=UTC`, differ near the
    end of the file -- almost certainly font-subsetting/object-ordering
    nondeterminism inside this LuaLaTeX version, not something
    `SOURCE_DATE_EPOCH` reaches). Given that, verification here is
    content-level rather than hash-level: PyMuPDF text extraction is
    identical, and 150 DPI PNG renders of all 4 pages are pixel-identical
    (SHA-256 of raw pixel samples) across baseline, theme-split-only, and
    theme-split-plus-tokens. This also means A3's own recorded
    "byte-identical" LuaLaTeX result was specific to whatever toolchain build
    wrote it; this session's toolchain does not reproduce that property for
    unrelated reasons, so later sessions on yet another local toolchain
    should expect to re-derive which comparison (hash vs. pixel) is
    trustworthy rather than assume hash-identical is always available
    off the pinned image.
  - Compiled `institutional_equity_acceptance_test.tex` (LuaLaTeX) and
    `primitive_acceptance_test.tex` (pdfLaTeX) fresh and inspected rendered
    PNGs by eye: the institutional-research callout is the quiet thin-rule
    variant with no fill; the default-theme callout and metric card keep
    their boxed chrome. Not just "it compiled" -- the actual chrome
    difference the token migration must preserve was checked visually.
  - `bash scripts/acceptance_check.sh --require-tex`,
    `reportkit docs --check --json`, and `scripts/contract_acceptance.py
    --json` all pass with no blocking diagnostics.
  - `python -m pytest tests publication_pipeline/tests`: 195 passed, 2
    failed, same two pre-existing environment-specific failures TODOS.md
    already documents (`test_full_build_emits_schema_v3_report_and_lock`,
    `test_doctor_dependency_remediation_is_present_in_text_and_json`) --
    confirmed pre-existing by running the same two tests against the
    unmodified tree in the same venv before making any change. `ruff check`
    is clean on every file this slice touched (repo-wide `ruff check` has 3
    pre-existing findings in `tests/test_acceptance_venv_detection.py`,
    untouched by this slice).

The pinned-toolchain CI gate has not run against this change yet and is
still the authoritative check, per A0.

**Diagram work implemented 2026-09-15** -- theme-populated TikZ styles/
appearance across `reportkit-diagrams.sty`, `reportkit-structure.sty`,
`reportkit-process.sty` and `reportkit-spatial.sty`, following exactly the
signal the paragraph below (kept as the historical record of what was
still open) named: `SEMANTIC_MODULES` in `tests/test_theme_contract.py` now
lists all four, and `REQUIRED_STYLE_TOKENS` gained ~90 new `RKTokDiagram...`
sentinels:

- **Scope rule (kept from D2):** only appearance -- draw/fill colors, line
  weights, fonts/text colors, corner rounding, padding -- moved behind
  tokens; authored geometry (node coordinates, widths in cm, spacing
  constants, arc angles) stayed exactly where each primitive already
  computed it. Category/semantic colors (`Hairline`, `Surface`, `Ink`,
  `Muted`, `LinkBlue`, `Evidence`, `Research`, ...) were already per-theme
  via `\definecolor` before this slice and are unaffected; these tokens
  style the chrome built on top of them.
- **New tikz styles, matching the plan's own naming:** `rk edge` is now a
  real shared base style (`rk edge flow`/`sequence`/`dependency`/`handoff`/
  `causal`/`optional` all compose it, reading a common arrow-tip token
  pair plus their own color/weight token), and `rk matrix axis`/
  `rk matrix axis label`/`rk matrix cell` and `rk timeline` are new named
  styles used by `\RKMatrix`/`\RKMatrixCell` (`reportkit-diagrams.sty`),
  `reportmatrix`/`\quadrant`/`\point` (`reportkit-spatial.sty` -- the same
  axis/cell chrome, now genuinely shared rather than independently
  hardcoded), and the dated-mode `reportroadmap` axis
  (`reportkit-structure.sty`) respectively. `rk node` and `rk layer accent`/
  `rk accent` read the remaining new node/accent tokens.
- **`reportkit-structure.sty` gained its own tikzset migration** (`rk
  structure card`/`title`/`muted`/`arrow`), not just the four styles named
  literally in the plan -- required because `reportarchitecture` and
  `reportroadmap`, the plan's own motivating examples for including this
  file, are built on it. The architecture-layer, roadmap-horizon and
  capability-map boxes (each hardcoded the identical Hairline/Surface/.5pt/
  1.2pt values as `rk structure card` before this slice, just drawn as a
  raw `\draw` rectangle instead of a node style) now read the same tokens.
  `strategicpillars`' objective-card accent, `maturitymodel`'s CURRENT
  marker, `continuum`'s axis/markers and `reportkit-spatial.sty`'s risk
  heatmap/register were deliberately left as authored literals -- outside
  the plan's explicitly named styles and subordinate-token list, and a
  reasonable place to stop this slice; a future slice can fold them in the
  same way if a theme ever needs to diverge there.
- **A real risk resolved before writing ~90 tokens, not just assumed:**
  whether a bareword TikZ color option (`\fill[\SomeTokenMacro]`,
  `\fill[\SomeTokenMacro!6]`, `draw=\SomeTokenMacro`) actually expands a
  macro standing in for a color name -- the same category of risk A4's own
  callout/metric slice flagged for tcolorbox's `colback=`. Confirmed
  empirically with a standalone TikZ probe (all three forms compile
  cleanly) before applying the pattern across four files, rather than
  discovering a compile failure 90 tokens in.
- **Executive theme (Phase B's experimental slides theme) also populated**:
  it already had to satisfy the callout/metric contract (it loads
  `reportkit-boxes.sty`/`reportkit-diagrams.sty` exactly like the two paged
  themes), so it needed the same new diagram tokens -- matching the default
  theme's values, per its own header's "not restyled, no design reason to
  diverge yet" note for the callout/metric tokens.
- **Verified 2026-09-15** in a throwaway, unpinned local toolchain (`apt-get
  install texlive-luatex texlive-latex-extra texlive-fonts-recommended
  texlive-science pandoc`, plus the checked-in Google Sans/Libertinus
  fixtures staged the same way `toolchain/Dockerfile` does -- not the
  pinned image itself, same caveat every earlier A-phase slice's
  non-pinned verification carries):
  - `python -m pytest tests publication_pipeline/tests`: 225 passed, 2
    failed -- the same two pre-existing, environment-specific failures
    (both a `pdflatex`+`microtype` "auto expansion is only possible with
    scalable fonts" error against the portable Libertinus font bundle, not
    the pinned toolchain), confirmed pre-existing and unrelated to this
    change by running the identical `scripts/acceptance_check.sh
    --require-tex` against `git stash`-ed pre-change and post-change trees
    and diffing the FAIL/WARN lines -- byte-for-byte identical in both.
  - Direct before/after visual-identity proof (not just "it compiled"):
    compiled `latex_templates/examples/career_guide_en/report.tex`
    (default theme), `latex_templates/examples/equity-research/report.tex`
    (institutional-research theme) and
    `latex_templates/examples/presentation_acceptance_test.tex` (executive
    theme) with `lualatex` at both the pre-change and post-change commit
    (`SOURCE_DATE_EPOCH=1 TZ=UTC LC_ALL=C`), then compared PyMuPDF text
    extraction and 150 DPI per-page pixel-sample SHA-256 hashes: **all
    three fixtures are text-identical and pixel-identical, every page**
    (career_guide_en is additionally raw-PDF-byte-identical). This matches
    A4's own established verification method (A3/A4's prior slices found
    this toolchain's LuaLaTeX is not byte-reproducible even baseline-to-
    baseline for the institutional/equity fixture, so pixel/text identity
    is the trustworthy comparison there, confirmed again here).
  - `bash scripts/acceptance_check.sh --require-tex`, `reportkit docs
    --check --json` (clean) and `scripts/contract_acceptance.py --json`
    all show the identical pre-existing `pdflatex`/`microtype` failure
    described above and nothing new.
  - `ruff check tests/test_theme_contract.py`: clean.

**Additive primitive checkpoint (2026-09-15):** `reportkit-algorithms.sty`
adds the non-floating `algorithmblock` pseudocode module after the A3 split.
It uses `\RKReserveSpace` and `\RKDiagramCaption`, so it follows the shared
renderer-hook boundary; its dedicated paged acceptance coverage passes. The
slides class does not load this module yet, so no slide-renderer parity claim
is added to A3 or B4.

**Python/theme-contract work implemented 2026-09-15:** `Theme` now carries
explicit typography, geometry, spacing, rule, table, chart, diagram and
script-coverage records while preserving the existing scalar and mapping
accessors as compatibility views. `apply_theme()` consumes the chart record
for font sizes, line width and the theme-default grid policy. The
`check-theme` command now validates Python record completeness, palette
synchronization, semantic-module token declarations/population, and every
registered common/renderer-adapter package. Focused pure-Python contract
validation and bytecode compilation pass. The host cannot run the focused
pytest suite or chart acceptance because pytest, Matplotlib, and pandas are
not installed; the pinned toolchain remains the authoritative runtime and
visual gate.

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

**Implemented 2026-09-14; updated 2026-09-16 after rebasing onto `main` at
`f45ab86` -- every currently applicable
"Work" item above is implemented.** Class options are materialized into the
staged entrypoint through three explicit placeholders, with values taken only
from the resolved `BuildTarget`. Theme font settings and the constrained brand
override surface now materialize through one `EffectiveTheme` record; because
no currently registered theme opts into `brand_overrides`, the venture-specific
visual and brand fixture remain future work. The equity pipeline acceptance
sub-item is implemented below.

- `publication_build.py`'s `build()` now calls `resolve_build_target(...)`
  and keeps the result (`target`) instead of discarding it after validation.
  `target.template` resolves the entrypoint file
  (`PIPELINE_ROOT / "templates" / target.template`); `target.pandoc_writer`
  is threaded into `render_markdown()`'s new `writer` parameter (`"latex"`
  for paged, unchanged; `"beamer"` for slides). `target.engine` replaces
  the local `engine` variable from that point on (decision D3: Python is
  canonical) -- same value in every case that reaches this point today,
  since `engine` is never empty when passed in, but now there is one source
  of truth instead of two variables that happened to agree.
- The staged/compiled entrypoint is always named `publication.tex`
  (`publication.pdf` once compiled), regardless of which entrypoint
  filename the registry selected -- "downstream packaging remains
  independent of the source template name," exactly as asked. The one
  place that depended on the old literal `"publication-template.pdf"` name
  (`cli.py`'s `_find_pdf()` fallback filter, used only when
  `build-report.json`'s own `pdf` field lookup fails) was updated to match.
- Per-renderer shared base files (`*-base.tex` under
  `publication_pipeline/templates/` -- today `paged-base.tex` and
  `slides-base.tex`) are staged unconditionally alongside the entrypoint, so
  every split entrypoint that `\input{}`s one finds it. The legacy
  `publication-template.tex` remains self-contained as a compatibility
  witness.
- `build-report.json` gained a `"selection"` key: `target.as_dict()`
  verbatim (publication_type, requested vs. canonical theme, alias_of,
  renderer, class, template, writer, engine, paper/canvas, accessibility,
  language_support, common_package, renderer_adapter, brand_overrides).
  The schema (`schemas/reportkit-build-report.schema.json`) is
  `additionalProperties: true` with five required keys, none of which this
  touches, so this is schema-safe by construction, not by coincidence.
- The resolved-selection marker
  (`REPORTKIT-SELECTED publication_type=... theme=... renderer=... ...`) is
  both printed to stdout (visible in non-`--json` runs) and appended to
  `publication.log` after a successful compile (so `--json` mode, whose
  stdout capture is not surfaced in the payload on success, still has a
  log-visible copy) -- appended after `shutil.copy2(pass_log, log)`, not
  written into `pass_log` itself, so it cannot affect
  `inspect_log()`/`check_build_log.py`'s diagnostic parsing.
- **`reportkit build` can now actually produce a presentation** -- the
  headline gap every prior Phase A4/B status note called out. Verified with
  a real end-to-end build (`publication_type: presentation, theme:
  executive, engine: lualatex`, plain Markdown manuscript, no
  `reportkit-presentation.sty` compositions): resolves `renderer=slides`,
  `class=reportkit-slides`, `template=presentation.tex`, `writer=beamer`;
  Pandoc's Beamer writer (`--slide-level=1`, added to `render_markdown()`
  only for the beamer writer -- without it, Pandoc's own heuristic for
  which heading level becomes a frame is ambiguous and content-dependent)
  converts each top-level Markdown heading directly into a literal
  `\begin{frame}{Title}...\end{frame}` block, which compiles cleanly
  through `\input{body.tex}` (this is `\input`, not macro expansion, so
  B1's "Beamer's frame environment cannot be opened across macro
  boundaries" finding does not apply here -- confirmed by it actually
  compiling, not just argued). This is B1's "plain Markdown frames"
  authoring path; directive/fragment-based composition authoring (the
  *other* path B1 names, using `reportkit-presentation.sty`'s compositions
  from Markdown) is now implemented by the constrained authoring IR and
  trusted-fragment path described below.
  `slides-base.tex` gained `\RequirePackage{reportkit-pandoc}` (the same
  `\tightlist`/syntax-highlighting/proportional-image compatibility layer
  the paged pipeline already requires via `reportkit-longform.sty`;
  confirmed renderer-neutral -- `\linewidth`/`\textheight`, no paged-only
  package -- so reused directly rather than duplicated) and its own header
  comment was corrected (previously said A5 had not landed yet).
- **The equity-research fixture now has a real Markdown pipeline path.**
  `latex_templates/examples/equity-research/manuscript/order.txt` and
  `01-equity-update.md` provide ordinary Markdown prose and three visual
  sentinels; matching trusted fragments under `fragments/` wrap the existing
  generated exhibit PDFs in the validated `diagram` contract and preserve
  descriptive ActualText. The direct `report.tex` witness remains untouched.
  The staged entrypoint now contains
  `theme=institutional-research,publication-type=equity-research`, so the
  pipeline cannot silently use the default theme. Static publication/check
  validation passes, and a local LuaLaTeX compile produces a six-page PDF;
  the full normal build remains pinned-toolchain gated because this host lacks
  `algorithmicx.sty`, supplied by the pinned `texlive-science` dependency.
- **New test coverage:**
  `publication_pipeline/tests/test_build_target_selection.py` -- every
  registered publication type's entrypoint file exists; the renderer
  records' writers are real Pandoc writers; `resolve_build_target()` drives
  template/writer selection for both a paged and a slides target; a real
  end-to-end paged build (`example_publication`) produces a stable
  `publication.tex`/`publication.pdf`, a correctly populated `selection`
  key, and a log-visible marker; a real end-to-end presentation build
  produces the declared 160mm x 90mm canvas (verified via PyMuPDF, not
  assumed) and the right page count; an explicit `document.paper` for
  `publication_type: presentation` is rejected at exit 2 before any
  manuscript is read (decision D5, enforced at the pipeline entrypoint, not
  just the registry function directly -- `tests/test_slide_renderer.py`
  already covers that layer).
- **Post-rebase verification 2026-09-16:** focused slide-accessibility,
  slide-renderer, and non-compiling target-selection checks report 23 passed
  and 5 skipped; three toolchain-dependent target-selection build tests were
  deselected because this host lacks `algorithmicx.sty` (the pinned
  `texlive-science` toolchain supplies it). `reportkit docs --check --json`,
  static equity `reportkit check`, shell syntax, Ruff, and `git diff --check`
  pass. The full pinned build/test gate remains authoritative.

**Follow-up implemented 2026-09-16:** the D7 paged-base.tex/
technical-report.tex/equity-research.tex split is landed; constrained
directive/fragment-based presentation authoring now validates a typed IR and
renders safe TeX with explicit trusted fragments; theme/font/brand settings
materialize through one effective-theme record and are recorded in the build
report; and PDF inspection consumes the resolved-selection marker to flag
missing, malformed, mismatched, or default-theme-leaking targets.

**Pinned verification 2026-09-19:** the pinned OCI image built successfully;
the pinned doctor reported fingerprint `6e0fc8…408e5`; and 53 focused A3/A4
static/runtime checks passed, including theme-contract and Matplotlib-dependent
coverage. The full acceptance matrix was interrupted before completion, so it
remains the release follow-up. Phase C's executive visual design/review also
remains open.

**Remaining:** complete the full pinned acceptance matrix and the future visual
design/review phases.

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

**Implemented 2026-09-14; B4 automation retained and documented 2026-09-16
after rebasing onto `main` at `f45ab86` -- B1 and B2
essentially complete via direct-TeX authoring; B3 implemented for the one
existing slide theme; B4 is now verified by a reusable PDF inspector and a
compiled-fixture pytest/acceptance gate. The constrained directive/fragment
composition path is now exposed from Markdown and covered by source-line
validation and build integration.**

- **B1 (class + slides core + registry):** `reportkit-slides.cls` mirrors
  `reportkit.cls`'s option-parsing/registry-validation/theme-and-adapter-
  loading shape over `\LoadClass[aspectratio=169]{beamer}`. Beamer's own
  16:9 aspect-ratio table already produces a 16.00cm x 9.00cm (160mm x 90mm)
  frame natively (read directly from `beamer.cls`, not assumed) -- no
  `paperwidth`/`paperheight` override was needed, simplifying D5's canvas
  requirement considerably. `reportkit-slides-core.sty` implements the same
  five renderer hooks `reportkit-paged-core.sty` does:
  `\RKReserveSpace` is a no-op (a Beamer frame is already
  `reportkit-presentation.sty`'s unit of composition; there is no page flow
  to reserve space in, and this is a deliberate, documented design choice,
  not an oversight); `\RKDiagramPlacementBegin`/`End` reuse
  `\begin{center}`/`\end{center}` (works unchanged inside a frame);
  `\RKDiagramCaption` reimplements the "Figure N. text" contract using
  Beamer's own built-in `figure` counter (`beamerbaselocalstructure.sty`)
  instead of the external `caption` package (D8: no paged caption
  behavior); `\RKDiagramSource` reuses the theme-owned `\source` macro
  unchanged. `\setbeamertemplate{navigation symbols}{}` satisfies D8's
  "disable decorative navigation" directly.
  `publications.py` gained a `"slides"` renderer record
  (`geometry: {"kind": "canvas", "canvas": {"width_mm": 160, "height_mm":
  90}}`) and a `"presentation"` publication type record (no `"paper"` key).
  **A real prerequisite bug found and fixed along the way:** A3's own
  migration (see that section above) missed `reportkit-code.sty`, which
  still `\RequirePackage{needspace}`d and called `\Needspace` directly --
  harmless under the paged renderer (identical to the hook it should have
  called) but fatal under a hypothetical slides core, since there is no
  page flow for `needspace` to measure inside a Beamer frame. Fixed to call
  `\RKReserveSpace` like every other semantic module; no fixture exercised
  `codeblock`/`outputblock` before this change, so coverage was added to
  `primitive_acceptance_test.tex` alongside the fix.
  **A second, larger bug found only by attempting to compile:** an initial
  design had every `reportkit-presentation.sty` composition open and close
  Beamer's `\begin{frame}...\end{frame}` internally (in its own start/end
  code), which fails outright -- `Runaway argument? File ended while
  scanning use of \beamer@collect@@body` -- because Beamer's frame
  environment captures its own body by a raw-input-stream scan for a
  literally-typed `\end{frame}`, not a macro-expanded one, the same
  mechanism `fragile` frames use for verbatim content (confirmed by
  removing `fragile` and reproducing the identical failure with plain-text
  content, i.e. this is not a fragile-specific issue). The fix, and the
  final shipped design: every composition is content-only; the author (or
  the front-matter hook) wraps each one in an explicit, literal
  `\begin{frame}...\end{frame}`, adding `[fragile]` only where the frame's
  own content needs it (e.g. a `codeblock}`). This is standard Beamer
  extension practice, not a workaround -- documented at length in
  `reportkit-presentation.sty`'s own header so the next session does not
  rediscover it by hitting the same wall.
  **A third bug, in PDF metadata correctness (found during B4
  verification):** Beamer's own `\title`/`\subtitle`/`\author` schedule a
  `\hypersetup{pdftitle=...}`-style call of their own (via
  `\beamer@firstminutepatches`) at the kernel's `begindocument` hook,
  registered earlier (during `\LoadClass{beamer}`) than
  `reportkit-slides-core.sty`'s own `\AtBeginDocument`-registered
  `\RKRegisterDocumentMetadata` call -- and hyperref accepts only the
  *first* `\hypersetup` call for `pdftitle`/`pdfauthor`/`pdfsubject`/
  `pdfkeywords`/`pdfdisplaydoctitle` (each later attempt is silently
  dropped with a "has already been used" warning, verified empirically).
  pdftitle/pdfauthor come out correct anyway (Beamer's own values, from
  `\title`/`\subtitle`/`\author`, are exactly what reportkit-core would
  have produced), but pdfsubject/pdfkeywords silently locked to empty,
  turning `\setreportkitsubject`/`\setreportkitkeywords` into no-ops under
  this renderer -- a real, narrow accessibility-metadata regression
  relative to the paged renderer if left unfixed. The fix uses the LaTeX2e
  kernel's newer `begindocument/before` hook (fires strictly before the
  legacy `begindocument` hook regardless of load order) to call Beamer's
  own `\subject{}`/`\keywords{}` commands early enough to win the race, but
  late enough that `\rk@subject`/`\rk@keywords` already reflect any
  preamble-time `\setreportkitsubject`/`\setreportkitkeywords` call.
  Verified: pdfsubject/pdfkeywords both come out correctly populated with
  the fix; both come out empty without it, regardless of what the setters
  were called with.
- **B2 (composition API):** `latex_templates/publication_types/
  reportkit-presentation.sty` implements all thirteen named compositions
  (title slide, section divider -- plus an appendix-divider variant --,
  single-message, assertion-evidence, visual+text -- covering both
  "text+visual" and "visual+text" via one `position=` key --, full visual,
  two-column comparison, three-part argument, hero metric, closing) plus
  chartslide/tableslide/architectureslide as thin, separately-named,
  separately-contracted aliases over the same visualtext/fullvisual
  layout mechanism (an explicit, documented simplification: the plan's
  "chart, table and architecture slides" read as discoverability/naming,
  not a fourth distinct layout system). Every composition delegates
  spacing/type to a new, separate presentation-token contract
  (reportkit-core.sty's "Presentation-composition style tokens" section --
  ~12 `RKTokPresentation...` sentinels, its own `\RKAssertPresentationTokens`
  gate, deliberately *not* merged into the callout/metric
  `\RKAssertStyleTokens` gate so paged themes are never forced to populate
  slide-only tokens) or to plain semantic color names every slides-
  compatible theme is expected to define (Ink/Muted/Hairline/Accent, the
  same pattern reportkit-boxes.sty already uses for category colors). No
  composition mentions "executive" in its code (only in comments); Phase D's
  own gate (venture must compile the same compositions unchanged) is a
  natural consequence of this, not a promise made without a mechanism.
- **The experimental executive theme (D8, D9):** `reportkit-theme-
  executive.sty` (common) + `reportkit-theme-executive-slides.sty` (slides
  adapter, D11) -- LuaLaTeX-gated the same way institutional-research is,
  Libertinus fonts (not Google Sans -- documented as a deliberate
  placeholder choice, not D9 non-compliance: it needs no font_path/
  font_policy plumbing to compile in any LuaLaTeX environment this repo
  already supports, and Phase C's design review is explicitly expected to
  replace it), a full placeholder palette, the complete callout/metric
  token set (reused from the default theme's values verbatim -- no design
  reason yet to diverge), and the complete presentation-token set (new
  placeholder values). `publications.py`'s `THEMES["executive"]` and
  `python_scripts/reportkit/themes/executive.py` (the Python chart-theme
  counterpart, `apply_theme("executive")`) both marked `stability:
  "experimental"`, matching D8's "do not release between B and C."
- **B3 (slide visualization slots), for executive only:** `themes/
  executive.py`'s `figure_sizes` carries exactly `slide-main`/`slide-half`/
  `slide-hero` (not the seven paged names -- a slide-compatible theme's
  figure_sizes is scoped to slide slots only, since no composition
  references paged names like `sidebar`/`square`), derived from the 160mm
  x 90mm canvas minus the slides adapter's 8mm safe-margin (both files'
  comments say to keep the two numbers in sync -- no cross-language token
  mechanism exists yet, the same pre-existing gap every paged theme's LaTeX
  geometry already has against its own `TEXT_WIDTH_IN`). Verified: all
  three slots fit inside the declared canvas; no paged theme
  (default/technical/institutional-research) gained slide-* keys or lost
  any of its seven existing ones (regression tests in both
  `tests/test_slide_renderer.py` and updated
  `tests/test_reportkit_viz_themes.py`, which previously assumed "every
  theme" was paged). Not yet done: verifying generated chart PDFs actually
  embed vector text under this theme specifically (the general mechanism is
  unchanged from every other theme, so this is low-risk, but genuinely
  unverified for `executive`).
- **B4 (accessibility parity), verified by the reusable inspector and
  compiled-fixture gate:** title/author/
  subject/keywords metadata all correct (subject/keywords only after the
  bug fix above); `/Lang (en-US)` present in the PDF catalog (initially
  appeared absent under a naive raw-bytes grep -- a false negative from PDF
  object-stream compression, not a real gap, confirmed by reading the
  decompressed catalog object with PyMuPDF instead); `/Outlines` and
  `/PageMode /UseOutlines` present (from `\section{}` calls inside
  sectiondivider/appendixdivider) with correct bookmark titles;
  `/ViewerPreferences <</DisplayDocTitle true>>` present (Beamer's own
  default); diagram `ActualText` alternatives present in the content stream
  of every page containing a `\begin{diagram}` (3 of 3, matching the
  fixture's 3 diagrams) -- the same mechanism, unmodified, that already
  works under the paged renderer. The fixture now contains a visible-text
  external `\href`, and the inspector verifies it as a meaningful link
  annotation. Tagged-PDF capability is declared `"unsupported"` in the slides
  renderer's registry record, the same truthful status the paged renderer
  already declares, for the same reason. `inspect_slide_accessibility()` in
  `publication_pipeline/scripts/inspect_pdf.py` checks these claims. Its
  `/ActualText` reader decodes PDF literal and hexadecimal strings, rejects
  empty alternatives, and can compare exact expected values through both the
  Python API and CLI. `tests/test_slide_accessibility.py` covers the decoder
  and canonical values, compiles and inspects this fixture, and
  `scripts/acceptance_check.sh` runs the same profile when PyMuPDF is present.
- **Compiled smoke fixture:** `latex_templates/examples/
  presentation_acceptance_test.tex` -- one frame per composition (17
  frames total), reusing `reportkit-boxes`/`reportkit-code`/
  `reportkit-diagrams` content (a `principle` callout, a `metric` card, a
  `codeblock`/`outputblock` pair, three `\begin{diagram}` calls including a
  `layer` and a `matrix` type) to prove those semantic modules compile
  *unmodified* under the slides renderer, not just that new slide-specific
  code compiles. Wired into `scripts/acceptance_check.sh`'s lualatex block
  alongside the existing institutional-research/equity-research fixtures.
- **Pipeline entrypoints, per D7, are now consumed by A5:**
  `publication_pipeline/templates/slides-base.tex` (shared preamble/body
  inclusion, consuming the same `\RKPub...` metadata macros
  `write_metadata()` already generates for the paged renderer -- those are
  renderer-neutral, so no change there was needed) and `presentation.tex`
  (entrypoint: class declaration + a `\RKFrontMatter` hook calling
  `titleslide`). A5 now selects and stages these files from the resolved
  `BuildTarget`; `reportkit build` produces a presentation through Pandoc's
  Beamer writer. Directive/fragment-based composition authoring is now
  integrated through the typed IR and safe TeX renderer, not just renderer
  selection or compilation.
- **A necessary correctness fix in the shared config/registry layer, found
  while wiring the canvas/paper split (decision D5), not scoped to slides
  only:** `config.py`'s `resolve_document()` previously defaulted
  `document.paper` to `"a4"` unconditionally, for every publication type;
  three call sites (`cli.py`, `context.py`, `publication_build.py`) then
  force-`str()`-wrapped that value before passing it to
  `resolve_build_target()`, turning a real `None` into the four-character
  string `"None"`. Both would have silently broken D5's "an omitted paper
  key stays omitted" the moment `"presentation"` became a real
  `publication_type` value to default against. Fixed: the paper default is
  now conditional on the resolved publication type's renderer having
  `geometry.kind == "paper"` (every publication type before this change,
  so zero behavior change for any of them); the three call sites now pass
  `document.get("paper")` through unmodified. `resolve_build_target()`
  itself gained the actual D5 enforcement: an explicit paper for a canvas
  renderer is now a raised `PublicationRegistryError`, not a silently
  dropped value (it already computed the right *output* --
  `BuildTarget.paper` was already forced to `None` whenever `canvas` was
  present, evidently anticipated when the canvas/paper fields were
  originally added in Phase A1 -- but never raised on bad *input*).
- **New test coverage:** `tests/test_slide_renderer.py` (registry/static
  contract: renderer/theme/publication-type records, the D5 paper-vs-canvas
  rejection, both renderer-hook and presentation-token contracts, the B3
  figure-size checks). Updated `tests/test_reportkit_viz_themes.py` (two
  tests previously iterated "every theme" assuming paged-only figure-size
  keys; now iterate a `PAGED_THEMES` tuple derived from the publication
  registry, not a hardcoded name, so a future slide-only theme is excluded
  automatically too) and `tests/test_agent_contract.py` (the publication-
  matrix and primitive-count snapshot tests, which are deliberately exact
  and meant to be updated on a real registry change like this one).
  `references/primitive-contract.md` regenerated (`reportkit docs
  --write`) to match the new composition/command primitives -- required,
  not optional: `reportkit docs --check` is itself part of the required
  gate set below and fails on any drift.
- **Verified 2026-09-14** in the same local, unpinned toolchain A4 used
  (this session reused A4's already-installed texlive-latex-extra/
  texlive-luatex/pandoc packages; no new apt packages were needed for
  Beamer specifically -- confirmed by reading dpkg's own dependency
  metadata: `texlive-latex-extra` already depends on
  `texlive-latex-recommended`, which is what actually provides
  `beamer.cls`, so the pinned `toolchain/Dockerfile`'s existing package
  list already covers Beamer transitively and needs no change for B1):
  - `presentation_acceptance_test.tex` compiles cleanly under LuaLaTeX (17
    pages, exit 0), with a correct 160mm x 90mm `MediaBox` (verified via
    PyMuPDF, not assumed from the class option). Rendered several pages to
    PNG and inspected by eye: title slide, a `visualtext` frame with a
    working `RKLayer` diagram and correct two-column split, a `comparison`
    frame, a `herometric` frame (the hero value wraps to two lines at this
    placeholder font size -- a cosmetic tuning item for Phase C, not a
    defect), and a `codeblock`/`outputblock` frame (proving
    `reportkit-code.sty`'s A3-completion fix above actually works end to
    end under Beamer). The quiet-vs-boxed distinction this session
    otherwise didn't touch (A4's callout tokens) was not re-checked here
    since nothing in this phase changed it.
  - `career_guide_en/report.tex` (default theme, pdfLaTeX) with the
    `codeblock`/`outputblock` fix applied: still compiles clean, no
    fixture existed before to hash-compare against for this specific
    primitive (see the bug-fix note above), so this is a fresh compile
    check, not a byte-identity proof.
  - `bash scripts/acceptance_check.sh --require-tex`,
    `reportkit docs --check --json`, and `scripts/contract_acceptance.py
    --json` all pass with no blocking diagnostics.
  - `python -m pytest tests publication_pipeline/tests`: 216 passed, 2
    failed. Both failures are pre-existing and environment-dependent, not
    regressions -- confirmed by reproducing each identically against the
    unmodified `94d8f0f` commit with the same `PATH` (one is
    `test_doctor_dependency_remediation_is_present_in_text_and_json`,
    already documented in TODOS.md before this session; the other,
    `test_every_json_capable_command_uses_the_common_envelope[arguments1-0]`,
    is new to this session's investigation but not to the underlying cause
    -- `reportkit doctor --json` legitimately reports
    `RK_TOOLCHAIN_MISMATCH` as blocking whenever it can actually detect the
    installed Python package versions, i.e. whenever a matplotlib-equipped
    Python is first on `PATH`, regardless of which commit is checked out;
    it exits 0 only when it can't -- an artifact of this sandbox never
    matching the pinned toolchain image, the exact condition A0 exists to
    address, not something any code change in this session touches).
    `ruff check` is clean on every file this slice touched.

**Remaining / explicitly out of scope for this slice:** the tagging spike
re-run mentioned in B4 and promoting `executive` out of `"experimental"`
(explicitly Phase C's job). The directive/fragment-based presentation path
is now proven through `reportkit build`.

### Phase B definition of done

A presentation builds from publication.yaml through the normal pipeline, uses
reportkit-slides.cls and Pandoc's Beamer writer, has the declared canvas, carries
the paged accessibility features, and loads no paged-only mechanics.

**Status (updated 2026-09-16, after A5 and the B4 gate):** canvas ✅ (verified via PDF
inspection), paged-only-mechanics-free ✅ (reportkit-slides-core.sty's own
header documents the absence), accessibility features ✅ for the ones
checked (title/author/subject/keywords/catalog language/outline/bookmarks/
meaningful links/diagram ActualText/truthful tagged-PDF status),
reportkit-slides.cls + Pandoc's Beamer writer ✅, and
**"builds from publication.yaml through the normal pipeline" ✅** -- A5
made `reportkit build` resolve and stage `presentation.tex`, select the
Beamer writer, and compile through `reportkit-slides.cls`; verified with a
real end-to-end build (see A5's own section). The constrained
directive/fragment authoring path now validates and renders the same
composition API through `reportkit build`; Phase B's definition of done is
otherwise met.

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

The paged and slide renderers now exist. C-prime 1 and C-prime 2 are
implemented in the working tree; the remaining agent-contract work is the
separate budget, neutrality, i18n, and tagging backlog.

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

**Implemented 2026-09-16 in `a7e83f9`:** fenced `reportkit` directives are
parsed into `AuthoringIR` nodes with source locations; `validate_authoring()`
and `validate_ir()` check primitive names, availability, arguments, structural
and numeric constraints, links, and trusted-fragment containment before
Pandoc or TeX. `render_ir()` escapes content-derived values and admits only an
explicit, validated `fragments/*.tex` escape hatch. `publication_build.py`
integrates the path for both the paged and slides writers, including the
literal-frame boundary required by Beamer. Coverage is in
`tests/test_authoring_ir.py`; the authoring schema is
`schemas/reportkit-authoring.schema.json`.

### C-prime 2 — first-class render command

Implemented 2026-09-19 over `render_pdf_pages.py` with:

- page/range selection;
- DPI control;
- predictable atomic output;
- JSON manifest and toolchain fingerprint;
- structured environment failure when PyMuPDF is unavailable.

Keep reportkit build's automatic full render, but document the authoring loop as
check → build → render selected pages → inspect → revise. Focused tests verify
page selection, atomic preservation of a previous output, the JSON manifest,
and the structured missing-PyMuPDF failure.

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
9. Constrained Markdown IR (implemented); the first-class `reportkit render`
   command remains open.
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
