# ReportKit — Outstanding Work

**Last updated:** 2026-09-19

This is an index, not an audit. Each spec/plan under `docs/superpowers/`
carries its own `**Status:**` line, updated at the workflow checkpoint that
changed it (approval, execution start, merge). This file is a one-line
pointer per document plus a rollup of what's still open — edited
incrementally when a status changes, never rebuilt from scratch. See
[docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md)
for why.
The PR-time synchronization directive is in
[references/documentation-status.md](references/documentation-status.md).

## Documents

| Document | Status | Priority |
|---|---|---|
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Approved — implementation slice, original C2 primitives, additive algorithmblock, B4 audit, and F2 measurement + bounded parallelism all landed. Nothing outstanding. | Complete |
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap — reconciled; implementation phases complete; use the plan, not this | P3 |
| [2026-09-07-reportkit-vnext-implementation-plan.md](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md) | Complete — Phase 1 merged via PR #10; additive Phases 2–4 merged via PR #9 | P3 |
| [2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md) | Approved | Process |
| [2026-09-07-documentation-and-status-tracking-cleanup.md](docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md) | Done — merged via PR #7 (`965443b`) | Process |
| [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md) | Implemented (Steps 1–5); open questions resolved in the plan below | P2 |
| [2026-09-09-reportkit-institutional-theme-implementation-plan.md](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md) | Complete — Steps 1–5 implemented; local LuaLaTeX verification passes; pinned visual QA remains | P2 |
| [2026-09-09-reportkit-fix-post-implementation-findings.md](docs/superpowers/plans/2026-09-09-reportkit-fix-post-implementation-findings.md) | Complete — all 8 tasks done and reviewed clean; fixture verification complete | Complete |
| [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md) | Phase A implementation complete in the working tree: A1–A5, D7 entrypoints, constrained Markdown directives, brand override materialization, and selection-marker inspection landed; A0 is verified against the available pinned image, while pinned-toolchain/runtime gates remain | P2 |
| [2026-09-10-reportkit-multi-format-publication-implementation-plan.md](docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md) | Phase A implementation complete in the working tree; A0 is verified against the available pinned image and A3/A4 pinned/runtime verification remains; Phase B renderer/accessibility work is complete, with executive design promotion and tagging still review-gated | P2 |
| [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](docs/superpowers/specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md) | Phase A′ and B′ complete; constrained Markdown/typed-IR authoring landed in v1.9.3; standalone render command, budgets, i18n, and neutral second adapter remain | P2 |
| [2026-09-10-reportkit-fork-port-fixes-spec.md](docs/superpowers/specs/2026-09-10-reportkit-fork-port-fixes-spec.md) | Implemented in v1.9.1 via PR #19; all 11 applicable fixes landed | Complete |
| [2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md](docs/superpowers/specs/2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md) | Implemented — merged via PR #25 (`7c5fafc`); all phases (0-2) landed; all 3 open questions resolved | Complete |
| [2026-09-16-reportkit-algorithm-visualization-primitives-spec.md](docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md) | Phases 1-3 and P3 extensions implemented 2026-09-17: shared state vocabulary plus array/window/trace, linear containers, graph/grid/DAG, heap/interval/DP, keyed join, union/find, linked-list, and recursion-tree primitives | Complete |
| [2026-09-18-algorithm-visuals-fix-sprint-spec.md](docs/superpowers/specs/2026-09-18-algorithm-visuals-fix-sprint-spec.md) | Complete with concerns — Tasks 1–4 implemented; dedicated gate passes; full acceptance retains pre-existing out-of-scope failures. | Complete |

## Open work

### P0

- **P0-1 — delete `tooling`, don't re-cut it. Done.** As of 2026-09-15,
  `origin/tooling` no longer exists (`git fetch origin --prune` lists no
  `tooling` branch, local or remote) — it has already been deleted, matching
  [references/migrating-content-branches.md](references/migrating-content-branches.md)'s
  disposition. Nothing further to do; `backup/pre-split` was never confirmed
  present either and is likewise gone.

The documented quick-start remediation and the associated Phase 0 findings
are implemented in the current worktree; the spec remains the detailed
change record.

### P2

- Algorithm-visualization primitives — **Phase 1 (core state grammar)
  implemented 2026-09-17**: the shared nine-state vocabulary (`current`,
  `active`, `candidate`, `frontier`, `visited`, `resolved`, `discarded`,
  `blocked`, `unseen`) and its `RKTokAlgorithm*` style tokens (declared in
  `reportkit-core.sty`, populated by all three themes), plus `arraystate`
  (`\cell`/`\row`/`\pointer`/`\range`/`\annotation`), `windowstate`
  (`\values`/`\window`/`\entering`/`\leaving`), and `algorithmtrace`/
  `\snapshot`, all in new `latex_templates/reportkit-algorithm-viz.sty`,
  required by `reportkit.cls` right after `reportkit-diagrams`. Contract
  metadata generates cleanly (`generate_registry(strict=True)`: zero
  errors); `references/primitive-contract.md` and
  `references/institutional-research-theme.md` regenerated;
  `tests/test_theme_contract.py` extended to cover the new module and
  tokens; new `tests/test_algorithm_viz.py` compile-and-inspect suite (skips
  without a LuaLaTeX toolchain, same as the rest of the PDF-inspection
  suite); new canonical fixture
  `latex_templates/examples/algorithm_visuals_acceptance_test.tex`, wired
  into `scripts/acceptance_check.sh`; new SKILL.md "Algorithm and
  execution-state visuals" section. **Phase 2 (core algorithm structures)
  also implemented 2026-09-17**, fanned out to two parallel workstreams
  built on the Phase 1 foundation: `stackstate`/`queuestate`
  (`latex_templates/reportkit-algorithm-linear.sty`) share one internal
  linear-container renderer per spec section 7.3 and reuse `arraystate`'s
  cell/pointer chrome outright — no new theme tokens needed.
  `graphstate`/`gridstate` (`latex_templates/reportkit-algorithm-graph.sty`)
  add three new `RKTokAlgorithmGraph*` tokens (node text width, edge
  color/width — populated in all three themes) and reuse `rk algo cell`/the
  shared state overlay for nodes and grid cells; `graphstate` uses
  `reportnetwork`-style automatic grid layout and builds no dedicated
  BFS/DFS primitive (composition with `queuestate`/`stackstate` is left to
  the document author, per spec section 2.3). Both new modules are
  `\RequirePackage`d from within `reportkit-algorithm-viz.sty` itself (not
  from `reportkit.cls`), so the public import stays
  `\RequirePackage{reportkit-algorithm-viz}` per spec section 3. Two more
  fixtures added (`algorithm_visuals_linear_acceptance_test.tex`,
  `algorithm_visuals_graph_acceptance_test.tex`) and wired into
  `scripts/acceptance_check.sh`; SKILL.md and the generated contract docs
  updated. `python -m pytest tests` passes (167 passed, 73 skipped) in this
  environment, which has no LuaLaTeX/pdfLaTeX — every new fixture and
  PDF-inspection test across both phases is unverified by an actual compile
  and needs to run once somewhere with TeX installed. **Phase 3 (additional
  high-value structures) also implemented 2026-09-17**, again fanned out to
  two parallel workstreams: `intervalstate`/`heapstate`
  (`latex_templates/reportkit-algorithm-order.sty` — intervals on a shared
  axis, one per declared row; heapstate's tree view laid out purely from
  array index, no manual tree coordinates) and `dptable`/`dagstate`
  (`dptable` in new `latex_templates/reportkit-algorithm-dp.sty`, reusing
  `gridstate`'s coordinate math; `dagstate` appended to the existing
  `latex_templates/reportkit-algorithm-graph.sty`, reusing `graphstate`'s
  node layout and `reportkit-diagrams.sty`'s existing dependency-edge style
  outright — no new edge token). 9 new theme tokens total (5 for dagstate's
  indegree badge, 4 for intervalstate's axis/heapstate's tree edges),
  populated in all three themes. Several of these primitives' own spec text
  proposes state names outside the shared nine-word vocabulary
  (`overlap`/`merged`, `solved`/`dependency`/`uncomputed`,
  `ready`/`processed`); each was mapped onto the closest existing shared
  state instead, documented in-file and in SKILL.md, per the spec's own
  section 2.2 consistency requirement. Merging this phase caught and fixed a
  real bug from the merge itself: an overly-greedy regex used to resolve
  three colliding theme-file merge conflicts (`.*` under `re.DOTALL`, with
  no non-greedy qualifier before the final anchor) silently deleted each
  file's tail — including `execsummary`'s definition and
  `\rk@styletokensloadedtrue` — while leaving the file byte-count
  superficially plausible; caught by a callout-count regression (14 → 13)
  during the post-merge registry check, not by any test written for this
  feature, and fixed by rebuilding each file's tail from the pre-merge
  commit with the new token block re-inserted precisely. Three more
  fixtures added and wired into `scripts/acceptance_check.sh`; SKILL.md,
  the generated contract docs, and `tests/test_theme_contract.py` updated.
  `python -m pytest tests` passes (169 passed, 86 skipped, 0 failed) and
  `generate_registry(strict=True)` reports zero contract errors — still
  unverified by an actual LuaLaTeX/pdfLaTeX compile in this environment.
  **P3 is now complete**: `reportkit-algorithm-p3.sty` adds `joinstate`,
  `unionfindstate`, `linkedliststate`, and `recursiontree`, with contract
  metadata, generated references, documentation, and regression coverage.
  The complete algorithm-visualization feature now covers the full P0–P3
  scope in section 21 of the
  [spec](docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md).

- **Algorithm visuals and cheat-sheet fix sprint — COMPLETE WITH CONCERNS (2026-09-19).**
  Tasks 1–3 are merged and Task 4 is complete: the four-page guide fixture,
  acceptance-list wiring, mechanical release gate, and 140-DPI colour,
  grayscale, and institutional-research visual review are all landed. The
  dedicated integration gate passes (`4 passed`); the full acceptance command
  still reports only the pre-existing out-of-scope heap, PDF-extraction,
  contract-drift, and publication-pipeline failures documented in
  `.superpowers/sdd/2026-09-18-algorithm-visuals-fix-sprint/task-4-report.md`.
  The implementation plan and specification are now tracked alongside the
  fixture and test. The merged Task 1 report is preserved at
  `.superpowers/sdd/2026-09-18-algorithm-visuals-fix-sprint/task-1-report.md`.

  Landed interfaces used by the reference fixture include
  \tracetransition (the non-conflicting trace-transition name),
  \begin{codeblock}[title][keep=auto]{lang},
  \RKCompactContents{comma-separated labels}, and
  \readyqueue{clean} with a zero-indegree badge. The longform
  \section page-break contract remains unchanged; the fixture uses
  \RKSectionOpener so stack and queue share one reading unit.

  The release decision is explicit in the Task 4 report: the pointer trace
  shows `L` advancing, the window labels the entering/leaving item and index,
  and the dependency figure places `clean_orders` in READY with indegree 0.

- Institutional theme + equity-research profile — **Step 1 (theme
  infrastructure) implemented 2026-09-09**: `reportkit.cls` now delegates
  typography/geometry/palette/furniture to a selected theme file under
  `latex_templates/themes/`; `publication.yaml` gains `document.theme`,
  `.publication_type`, `.paper`; `reportkit check`/`build` refuse to build a
  theme against an engine that can't render it. **Step 2 (institutional
  theme) implemented 2026-09-09**: new
  `themes/reportkit-theme-institutional-research.sty` — Letter geometry,
  Google Sans via fontspec with `font_policy: strict`/`fallback`, the
  spec's full §5 type scale, and quieter semantic callouts
  (`reportkit-boxes.sty` now branches its box chrome on `\rk@theme`).
  `publication.yaml` gains an optional top-level `theme:` section
  (`font_family`/`font_path`/`font_policy`). **Step 3 (equity publication
  profile) implemented 2026-09-09**: new
  `publication_types/reportkit-equity-research.sty`, loaded via
  `publication-type=equity-research` — front page
  (`researchfrontpage`/`researchkicker`/`researchheadline`/`researchdeck`),
  rating strip, sidebar blocks, what's-changed, the exhibit system
  (`exhibit`/`fullwidthexhibit`/`exhibitgrid`/`exhibitpair`), table grammar,
  a dense financial-model-page mode, and bull/base/bear risk-reward
  primitives. **Step 4 (visualization integration) implemented
  2026-09-09**: new `python_scripts/reportkit/themes/` package
  (`default.py`/`institutional_research.py`); `reportkit_viz.apply_theme
  (name)` now genuinely switches theme (colors, `TEXT_WIDTH_IN`,
  `FIGURE_SIZES`, fonts, mathtext) at runtime; `check-theme` is now
  correctly theme-aware end-to-end (`--theme institutional-research`
  passes); new `risk_reward_chart()`; fixed a latent theme-switching bug in
  `annotate_point`/`shade_period`. **Step 4's Python code was actually
  executed and tested** (matplotlib/numpy/pandas installed) — not just
  statically checked. **Step 5 (fixtures, QA, skill guidance) implemented
  2026-09-09**: the four-page fictional `latex_templates/examples/
  equity-research/` publication (front page, analysis exhibits,
  risk/reward, financial model), with its financial figures reconciled to
  one internally-consistent model (open question 6) and its four
  `figures.py` charts actually rendered and visually inspected this step
  (which caught and fixed a real `risk_reward_chart()` label-overlap bug);
  a compact `institutional_equity_acceptance_test.tex` smoke fixture,
  compiled by a new `lualatex` block in `scripts/acceptance_check.sh`;
  `scripts/visual_qa_equity_research.py` (compile + `reportkit.diagnostics`
  log check + PNG render + pixel-diff against a checked-in baseline,
  spec §25), whose pure pixel-diff function is unit-tested with synthetic
  images; two new `lualatex`-compile pytest tests; and a new
  `references/institutional-research-theme.md` linked from `SKILL.md`
  covering the primitive reference, the `researchmain`/`researchsidebar`
  adjacency requirement, the `exhibitgrid` column-count limit, and
  `apply_theme`/`risk_reward_chart` usage. **Local verification on
  2026-09-10:** `bash scripts/acceptance_check.sh --require-tex` and a full
  four-page equity fixture compile both pass under the available LuaLaTeX
  toolchain. The checked-in visual baseline still requires the pinned OCI
  toolchain and a human §25 review; the current host reports
  `RK_VISUAL_TOOLCHAIN_MISMATCH`, so do not update expected pixels from this
  environment. See
  [the implementation plan](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md).

- **Multi-format publication architecture — Phase A1 implemented in v1.9.2
  (commits `db19e78`, `8efc601`); Phase A2 implemented in v1.9.3.**
  `publications.py` is now the canonical
  publication/renderer/theme registry: it resolves one immutable build target,
  preserves the `technical` alias, validates engine and compatibility choices,
  and supplies shared structured diagnostics to context, check, and build.
  The current tree also implements Phase A2: a generated LaTeX compatibility
  registry, shared hard-failing class-option parser, pair/renderer validation,
  drift coverage, and staging for the new `.def`/`.tex` infrastructure. The
  shipped capability matrix also now contains the `slides` renderer and the
  experimental `presentation` publication type (Phase B, below); there is
  still no HTML, DOCX, PPTX, or EPUB renderer in the current tree.
  **A3 (split shared/paged mechanics) is now
  implemented**: `reportkit-core.sty` is engine-neutral (no more
  geometry/fancyhdr/titlesec/needspace/caption), a new
  `reportkit-paged-core.sty` owns those plus hyperref (see the plan's A3
  section for why hyperref's require moved there, not to core — a
  measured, not stylistic, byte-hash constraint), and every semantic module's
  direct `\Needspace`/`\begin{center}`/`\captionof`/`\source` call went
  through the new renderer hooks (`RKReserveSpace`,
  `RKDiagramPlacementBegin`/`End`, `RKDiagramCaption`, `RKDiagramSource`) a
  `reportkit-slides-core.sty` implements differently. Verified byte-identical
  against the default, institutional/equity, and longform fixtures in a
  local (non-pinned) toolchain — see the plan's A3 section for the full
  verification record; the pinned-toolchain CI gate is still authoritative
  and has not run against it yet. **A4 (move component appearance behind
  theme tokens) is partially implemented**: both existing themes are now
  split per decision D11 into a renderer-neutral common package
  (`reportkit-theme-default.sty`, `reportkit-theme-institutional-research.sty`
  — fonts, palette, style tokens) and a paged adapter package
  (`reportkit-theme-default-paged.sty`,
  `reportkit-theme-institutional-research-paged.sty` — geometry, running
  furniture, section-heading placement, `\maketitle`), both loaded by
  `reportkit.cls` and resolved from the publication registry
  (`publications.py`'s `_theme()` gained a real `renderer_adapters`
  parameter). `reportkit-core.sty` gained the style-token contract decision
  D2 describes (~30 `RKTok...` sentinels plus `\RKAssertStyleTokens`), and
  `reportkit-boxes.sty`'s `\ifdefstring{\rk@theme}{institutional-research}`
  branch is gone — callout and metric chrome now read theme-populated
  tokens, with no semantic-module theme-name branch left (new
  `tests/test_theme_contract.py` enforces this statically). Verified in a
  local (non-pinned) toolchain: the default fixture is PDF-hash-identical
  before/after (with `SOURCE_DATE_EPOCH=1 TZ=UTC`, required for
  reproducibility even at baseline on this toolchain); the institutional/
  equity fixture's raw bytes are not hash-reproducible even baseline-to-
  baseline on this particular LuaLaTeX build (a toolchain quirk, confirmed
  independent of this change), so it was verified by identical extracted
  text and identical rendered-page pixel hashes instead, plus a visual check
  that the quiet vs. boxed chrome difference the migration must preserve is
  actually still there — see the plan's A4 section for the full record.
  **Diagram work implemented 2026-09-15**: the ~90 remaining hardcoded
  appearance values across `reportkit-diagrams.sty`/`-structure.sty`/
  `-process.sty`/`-spatial.sty` (node/edge/edge-label/layer/matrix-axis/
  timeline chrome, plus `reportkit-structure.sty`'s own `rk structure
  card`/`title`/`muted`/`arrow` tikzset, needed because `reportarchitecture`
  and `reportroadmap` — the plan's own motivating examples for touching
  that file — are built on it) now read theme-owned `RKTokDiagram...`
  tokens instead of hardcoding color/weight/font/rounding/padding; both
  canonical themes (plus the experimental `executive` slides theme, which
  already had to satisfy the same contract) populate them with the exact
  pre-migration values, so appearance is unchanged. `tests/
  test_theme_contract.py`'s `SEMANTIC_MODULES` now lists all four modules.
  Verified in a local (non-pinned) toolchain: `python -m pytest tests
  publication_pipeline/tests` — 225 passed, 2 failed (the same two
  pre-existing, environment-specific `pdflatex`/`microtype` font-expansion
  failures, confirmed identical via a `git stash` before/after diff of
  `scripts/acceptance_check.sh --require-tex`'s FAIL/WARN lines); and a
  direct visual-identity check — `career_guide_en` (default theme),
  `equity-research` (institutional-research theme) and
  `presentation_acceptance_test` (executive theme) compiled with `lualatex`
  at the pre-change and post-change commit are text-identical and
  pixel-identical on every page (career_guide_en is additionally raw-PDF-
  byte-identical). See the plan's A4 section for the full record, including
  the resolved risk of whether a TikZ color option macro-expands correctly
  (confirmed empirically with a standalone probe before writing the tokens).
  **Python/theme-contract work implemented 2026-09-15**: `Theme` now carries
  explicit typography, geometry, spacing, rule, table, chart, diagram and
  script-coverage records while preserving its existing compatibility views.
  `check-theme` validates those records, palette synchronization,
  semantic-module token declarations/population, and registered common/
  renderer-adapter packages. Focused pure-Python validation and bytecode
  compilation pass; this host lacks pytest, Matplotlib, and pandas, so runtime
  and pinned-toolchain verification remain outstanding. The remaining Phase A
  work is ordered in the plan: A0's pinned compatibility baseline is now
  captured and verified against the available image. A5's
  equity-research pipeline acceptance, the D7 paged-template split,
  theme/brand override plumbing, selection-marker inspection, and the
  constrained directive/fragment-based composition path are now implemented
  and verified in the worktree.
  See [the spec](docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md)
  and [the implementation plan](docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md).

- **Multi-format publication architecture — Phase B (slide renderer and
  presentation semantics) started out of the plan's own recommended order**
  (§13 puts A5 before B; Phase B was done first here at explicit request, and
  A5 followed). **B1 and B2 are essentially complete** via
  direct-TeX authoring: `reportkit-slides.cls` (mirrors `reportkit.cls`
  over `\LoadClass[aspectratio=169]{beamer}` — Beamer's own 16:9 table
  already produces the declared 160mm x 90mm canvas natively, no dimension
  override needed), `reportkit-slides-core.sty` (implements all five
  renderer hooks; `\RKReserveSpace` is a documented no-op, `\RKDiagramCaption`
  reimplements Beamer's own figure counter instead of loading the external
  `caption` package), and `reportkit-presentation.sty` (all thirteen named
  B2 compositions, plus three thin aliases, delegating to a new,
  separately-gated presentation-token contract in `reportkit-core.sty` so
  paged themes are never forced to populate slide-only tokens). An
  experimental `executive` theme (`reportkit-theme-executive(-slides).sty`,
  `python_scripts/reportkit/themes/executive.py`) exists so the renderer
  and composition API have something real to compile against — LuaLaTeX,
  Libertinus (a documented placeholder, not the eventual Google Sans),
  marked `stability: "experimental"` throughout, per D8. **B3 implemented
  for executive only**: `slide-main`/`slide-half`/`slide-hero` figure
  sizes, derived from the canvas and the slides adapter's safe margin, with
  regression coverage that no paged theme gained slide keys. **B4 now has an
  automated PDF-inspection gate** on the compiled smoke fixture (title/author/
  subject/keywords metadata, catalog language, PDF outline/bookmarks,
  meaningful link annotation, diagram ActualText, and the truthful tagged-PDF
  status). Two real bugs were found
  and fixed along the way, not just new code written: (1) A3's own semantic-
  module migration had missed `reportkit-code.sty`, which still called
  `\Needspace` directly — harmless under paged, fatal under slides, no
  fixture had ever exercised `codeblock`/`outputblock` before; fixed and
  covered. (2) An initial composition design opened Beamer's
  `\begin{frame}...\end{frame}` from inside each composition's own
  start/end code, which fails outright (`Runaway argument?`) because
  Beamer's frame environment scans the raw input stream for a literal
  `\end{frame}`, not a macro-expanded one — the shipped design makes every
  composition content-only, wrapped in an explicit frame by the author.
  (3) Beamer's own metadata setup silently locked out
  `\setreportkitsubject`/`\setreportkitkeywords` under this renderer; fixed
  via the LaTeX2e kernel's `begindocument/before` hook. A real, narrower
  correctness fix also landed in the shared config layer (not slides-only):
  `config.py` previously defaulted `document.paper` to `"a4"`
  unconditionally for every publication type, which would have silently
  broken decision D5's "an omitted paper key stays omitted" the moment a
  canvas-renderer publication type existed to default against; now
  conditional on the renderer's geometry kind, and `resolve_build_target()`
  now actually rejects an explicit paper for a canvas renderer instead of
  silently dropping it. **Update 2026-09-16: `reportkit build` can now
  produce a presentation** — see the A5 entry below; that was this entry's
  main "not done" item. B4's findings now have an automated PDF-inspection
  gate; `executive` stays experimental pending Phase C's
  design review; the constrained directive/fragment-based composition path
  is now proven through the pipeline with source-line validation and explicit
  trusted-fragment handling. See the plan's Phase B section for the full
  verification record.

- **Multi-format publication architecture — Phase A5 (make the pipeline
  target-aware) is essentially complete**, done after Phase B at explicit
  request (the plan's own recommended order puts A5 first). `publication_
  build.py`'s `build()` now resolves and keeps a real `BuildTarget`
  (`resolve_build_target(...)`, previously called only for validation, its
  result discarded) instead of a hardcoded module-level `TEMPLATE`
  constant: the entrypoint file, the Pandoc writer (`latex` vs. `beamer`),
  and the resolved engine all come from it. The staged/compiled entrypoint
  is always named `publication.tex`/`publication.pdf` now, independent of
  which entrypoint file was selected (`cli.py`'s one dependent fallback
  filter was updated to match). `build-report.json` gained a `"selection"`
  key (the full resolved target: theme/alias/renderer/class/template/
  writer/engine/paper-or-canvas/accessibility — schema-safe since
  `reportkit-build-report.schema.json` is `additionalProperties: true`),
  and a machine-readable, log-visible `REPORTKIT-SELECTED ...` marker is
  both printed and appended to `publication.log` after a successful
  compile. Class options are now staged from the resolved target through
  explicit entrypoint placeholders, so non-default theme/publication pairs
  reach LaTeX. **`reportkit build` can now build a presentation end to end** —
  verified with a real build (`publication_type: presentation, theme:
  executive, engine: lualatex`, plain Markdown manuscript): resolves
  `renderer=slides`/`class=reportkit-slides`/`template=presentation.tex`/
  `writer=beamer`, and Pandoc's Beamer writer (now invoked with
  `--slide-level=1` for the beamer writer specifically, resolving an
  otherwise content-dependent ambiguity in which heading level becomes a
  frame) converts Markdown headings straight into `\begin{frame}{...}...
  \end{frame}` blocks that compile cleanly via `\input{body.tex}` — `\input`
  is file inclusion, not macro expansion, so Phase B's "Beamer frames can't
  be opened across a macro boundary" finding doesn't apply to it (confirmed
  by it compiling, not just argued). `slides-base.tex` gained
  `\RequirePackage{reportkit-pandoc}` (the same compatibility layer the
  paged pipeline already needs; confirmed renderer-neutral). New
  `publication_pipeline/tests/test_build_target_selection.py` (every
  registered publication type has an existing entrypoint; a real paged
  build's `selection`/marker/stable-naming; a real presentation build's
  canvas/page-count; the D5 paper-rejection happens at the pipeline
  entrypoint, exit 2, before any manuscript is read). The equity-research
  pipeline-acceptance sub-item is now implemented with Markdown source and
  trusted figure fragments; static validation passes and a local LuaLaTeX
  body compile succeeds. The host's normal build stops before body
  compilation because `algorithmicx.sty` is absent; the pinned
  `texlive-science` toolchain supplies it. **Follow-up implemented
  2026-09-16:** the D7 paged split now provides `paged-base.tex`,
  `technical-report.tex`, and `equity-research.tex`; the constrained
  Markdown directive/typed-IR path supports presentation compositions with
  source-line diagnostics and explicit trusted fragments; D6/A5 now has
  registry-gated brand parsing plus deterministic TeX/chart effective-theme
  materialization and build-report hashes; and PDF inspection consumes the
  adjacent `REPORTKIT-SELECTED` marker to detect missing, malformed,
  mismatched, or default-theme-leaking selections.

  **Remaining:** pinned/runtime verification for the new slices, and promotion
  of a reviewed venture/editorial visual system.

  **Post-rebase focused verification on 2026-09-16:** slide accessibility,
  slide-renderer, and non-compiling target-selection checks report 23 passed
  and 5 skipped; three toolchain-dependent target-selection build tests were
  deselected because this host lacks `algorithmicx.sty` (the pinned
  `texlive-science` toolchain supplies it). `reportkit docs --check --json`,
  static equity `reportkit check`, shell syntax, Ruff, and `git diff --check`
  pass. The full pinned build/test gate remains authoritative.
  See the plan's A5 section for the full record.

- **Agent interface & platform contract — Phase A′ and B′ are complete for
  the shipped non-tagged accessibility contract; constrained authoring is
  also implemented in v1.9.3.** The canonical contract is now in
  [references/agent-contract.md](references/agent-contract.md), and the
  spec's eight open questions are resolved. Remaining work is the standalone
  `reportkit render` command and visual feedback loop, then
  progressive-disclosure context budgets, a neutral non-Claude adapter, and
  i18n extensions. Tagged PDF remains explicitly unsupported pending the
  separate toolchain-gated tagging spike.
  See
  [the spec](docs/superpowers/specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md).

### P3

- vNext — **Phase 1 merged 2026-09-08 via PR #10; additive Phases 2–4 merged
  via PR #9**. PR #9 intentionally inherits the Phase 1 package,
  config, diagnostics, registry, CLI, manifest, and test-wiring work from PR
  #10 rather than duplicating it. Its additive capabilities are deeper PDF QA,
  source/manuscript and link-registry validation, `\RKLink` rendering, and
  `reportkit analyse-history`.
- Plan record — **reconciled 2026-09-07**; the overlap with the tooling spec is
  audited section by section in
  [the implementation plan](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md).
- Backlog: a Copier template for consumer projects — deliberately deferred until vNext §4 settles `publication.yaml`'s schema and there's more than one content repo to keep in sync.

## Environment notes

Sessions run in fresh, ephemeral containers — what's pre-installed (TinyTeX
vs. system TeX Live, whether poppler-utils/pandoc/pytest/matplotlib are
already present, network egress policy) varies session to session and is
not itself durable information. What is durable: a from-scratch Ubuntu/
Debian-family container with outbound network access can reliably reach a
fully working toolchain (real `lualatex`/`pdflatex` compiles, the full
pytest suite, and a clean `acceptance_check.sh --require-tex`) with:

- `apt-get install -y --no-install-recommends texlive-luatex
  texlive-latex-extra texlive-latex-recommended texlive-fonts-recommended
  texlive-science texlive-plain-generic pandoc poppler-utils` (add
  `texlive-fonts-extra` too if Libertinus doesn't already resolve via
  `kpsewhich libertinus.sty`).
- The documented `LinBiolinum_K.otf` stub
  (`font_data/LinBiolinum_K_stub_README.md`) — `libertinus-otf.sty`
  unconditionally requires it under `lualatex`, and Debian's TeX Live
  packaging doesn't ship it.
- `python3 -m venv build/.venv-tests && build/.venv-tests/bin/pip install -r
  tests/requirements.txt -r publication_pipeline/requirements.txt
  matplotlib numpy pandas` for the pytest suite (`build/.venv-tests` is the
  path `acceptance_check.sh` auto-detects). `jsonschema` is used by some
  tests via `importorskip` but isn't in `tests/requirements.txt`; install it
  too (venv or system) to stop those tests from skipping.
- `acceptance_check.sh`'s own `python_scripts/` import check
  (`reportkit_viz`/`reportkit_doctor`) runs under plain system `python3`,
  not the venv — `pip install matplotlib numpy pandas pymupdf` there too
  (`--break-system-packages` on Debian-family systems) or that one check
  fails even with a correct venv.

Verified end-to-end this way on 2026-09-15: `python -m pytest tests
publication_pipeline/tests` — 233 passed, 12 skipped, zero failures (no
`pdflatex`/`microtype` font-expansion failures either, unlike every prior
session recorded in this file — apparently an artifact of an
incompletely-provisioned host, not something inherent to the suite).
Ambient system-font fallback lookup and the pinned visual-comparison
toolchain (exact byte/pixel-hash baselines) remain a separate concern this
recipe does not address — a freshly-`apt`-installed TeX Live is not the
pinned CI toolchain, so treat any hash-level (not just text/render-level)
comparison against a checked-in baseline as informative, not authoritative,
from a session provisioned this way.

## History

- 2026-09-19: completed the algorithm visuals and cheat-sheet fix sprint.
  Merged Task 1's nine-commit implementation, added the four-page integration
  guide and mechanical release gate, wired it into acceptance compilation, and
  completed default/grayscale/institutional-research 140-DPI visual review.
  The dedicated gate passes; the full acceptance command remains nonzero only
  for pre-existing out-of-scope failures documented in the Task 4 report.

- 2026-09-16: fixed a real documentation/reality mismatch found while doing a
  status-report pass on the repo: `SKILL.md`'s frontmatter `description` and
  opening paragraph still told callers not to use ReportKit "for ... a
  presentation," left over from before Phase B/A5 landed the experimental
  slides renderer. Updated the description, removed the stale prohibition,
  and added a "Presentations (experimental)" subsection covering
  `publication_type: presentation`/`theme: executive`, the Beamer
  `--slide-level=1` heading-to-frame conversion, the thirteen named slide
  compositions, and the caveats already recorded elsewhere in this file
  (only `executive` has a slide adapter; it's a placeholder-font theme;
  tagged PDF is unsupported). `reportkit docs --check --json` still passes
  (prose-only change, no primitive-contract drift). No code changes; this is
  a documentation-only entry, not a new History checkpoint for the
  multi-format work itself.

- 2026-09-15: closed out P1-1, the tooling-hardening spec's last open item
  (B4 contrast/grayscale audit, then F2's measure-before-optimising), on
  `claude/todos-outstanding-work-dwlrpl`, on top of `main` at `7ba4f55`.
  **B4** (`references`/spec §B4): computed WCAG contrast ratios for all
  three themes' `Muted` header/footer and `codeblock`/`outputblock` syntax
  colors against their actual backgrounds, plus a grayscale-luminance
  redundancy check — all pairs pass AA (4.5:1), two margins are thin enough
  to flag (default `Muted`/`Surface` 4.51:1, institutional-research
  `LinkBlue`/`Surface` 4.62:1) but not failing, and no code change was
  needed. **F2**: built an 8-section synthetic fixture and measured
  `publication_build.py --mode sections` — serial ~25.2s (~3.1s/section,
  confirmed strictly sequential from each section's own timestamps),
  matching finding 10's hypothesis that section builds are dominated by
  external subprocess time (Pandoc, TeX ×2, PDF render, PDF inspect), not
  interpreter CPU. Implemented bounded parallel workers on that basis:
  `--workers` (declared since vNext Phase 1 but previously inert) now
  bounds a `ThreadPoolExecutor` over the sections loop, wired through the
  public `reportkit build --mode sections --workers N` CLI (registry/
  contract updated to match) as well as the internal script; `--workers 1`
  (default) is byte-for-byte the prior serial path; `--workers 0`/negative
  is now a structured `exit 2`. Measured parallel wall time with
  `--workers 4` on the same 8-section fixture: ~6.6s (~3.8x speedup,
  matching the 4-core host). Making sections concurrent surfaced a real
  latent bug along the way, not just new code: build IDs keyed on
  mode+timestamp alone collide when two sections resolve within the same
  wall-clock second (routine under concurrency, latent but possible even
  serially) — fixed by keying on the manuscript stem too, which one-shot
  wires up this item's own "deterministic aggregate reporting" requirement
  (a `REPORTKIT-SECTION <entry>: exit <code>` summary printed in manuscript
  order via `ThreadPoolExecutor.map`, which preserves submission order
  regardless of completion order). Input-hash incremental builds (F2's other
  half) were not implemented — the measured ~4x parallelism win covers the
  motivating case with no correctness risk, and every section already
  builds into its own isolated output directory, so there was no
  fresh-vs-stale input tracking to reuse; left open for a future pass.
  New `publication_pipeline/tests/test_sections_parallel_build.py` verifies
  serial and `--workers 3` runs on a 3-section fixture produce identical
  pass/fail outcomes with no history-file (build-ID) collisions, and that
  the parallel run's printed summary is in manuscript order regardless of
  completion order. Verified in a from-scratch toolchain built this session
  (`apt-get install texlive-luatex texlive-latex-extra
  texlive-latex-recommended texlive-fonts-recommended texlive-science
  texlive-plain-generic pandoc poppler-utils`, the documented
  `LinBiolinum_K.otf` stub, and a fresh `build/.venv-tests` plus
  matplotlib/numpy/pandas/pymupdf/jsonschema on the system Python for
  `acceptance_check.sh`'s own import check): `python -m pytest tests
  publication_pipeline/tests` — 233 passed, 12 skipped (all
  `jsonschema`-optional), zero failures — better than every previously
  recorded baseline in this file, which always carried two pre-existing
  `pdflatex`/`microtype` font-expansion failures; those don't reproduce in
  this fully-provisioned environment. `bash scripts/acceptance_check.sh
  --require-tex`, `reportkit docs --check --json`, and `scripts/
  contract_acceptance.py --json` all pass. See the spec's own B4/F2 sections
  for the full record, including the exact contrast/grayscale figures.
  Removed P1-1 and the now-empty P1 heading from the open-work list.

- 2026-09-15: synchronized this index against `main` at `1ec3918` (this
  local checkout's `main` ref was stale at `3cdbb47`/PR #11; `origin/main`
  was already 21 merges ahead, through PR #32). Two documentation-only
  corrections, no code changes:
  - **P0-1 (delete `tooling`) is done.** `origin/tooling` and
    `origin/backup/pre-split` no longer exist on the remote — already
    deleted, presumably by the same PR-time cleanup that removed
    `shell_scripts/`. Removed from the P0 open-work list.
  - **The code-quality-and-dependency-remediation spec (P1-2) was already
    fully implemented and merged** via PR #25 (`7c5fafc`, closed
    2026-09-12) — every Phase 0/1/2 item (§A–§Q) and all three open
    questions, not just the "Phase 0 + concrete Phase 1" this index
    previously credited. Verified by direct file inspection in this
    session (no pinned toolchain available here to re-run PR #25's own
    186-test verification): `LICENSE` and `pyproject.toml` exist;
    `shell_scripts/` and the four pipeline `.sh` wrappers are gone;
    `toolchain/requirements.in` is gone; `python_scripts/reportkit/viz/`
    exists with `reportkit_viz.py` reduced to a 21-line re-exporting shim;
    `publication_pipeline/scripts/_bootstrap.py` provides the shared
    import helper standalone scripts use (resolving open question 2);
    `reportkit init --install-fonts` is a separate opt-in flag from
    `reportkit init` (open question 1); `CONTRACT_VERSION = "1.1.0"` (open
    question 3); the duplicate `career_guide_en_make_figures.py` and the
    dead `_declared_python_primitives` are both gone;
    `.github/workflows/contract-ci.yml` runs a non-blocking `pip-audit`
    step alongside the existing Dependabot config. The spec's own
    `**Status:**` line and open questions are updated to record this;
    it is now a closed execution record. Removed P1-2 from the open-work
    list.

- 2026-09-15: added the standalone `algorithmblock` language-neutral
  pseudocode primitive in `reportkit-algorithms.sty`, with
  `\AlgorithmInput`/`\AlgorithmOutput`, optional captions/labels and opt-in
  line numbers. The primitive is deliberately separate from executable
  `codeblock` and process diagrams, remains non-floating, uses the renderer
  hook contract, and is loaded by the paged `reportkit.cls`. A dedicated
  acceptance fixture is wired into `scripts/acceptance_check.sh`, rendered
  regressions live in `tests/test_algorithmblock.py`, and the generated
  primitive references and agent-contract counts are synchronized. This is an
  additive primitive; it does not claim slide-renderer availability. See the
  tooling-hardening and agent-interface specs for the status records.

- 2026-09-15: multi-format Phase A4's remaining diagram work (theme-populated
  TikZ styles across `reportkit-diagrams.sty`, `reportkit-structure.sty`,
  `reportkit-process.sty` and `reportkit-spatial.sty`) implemented on
  `claude/multi-format-framework-oqereh`, on top of `main` at `74197e6`
  (Phase A5 and the algorithm-block primitive both merged). ~90 new
  `RKTokDiagram...` style tokens added to `reportkit-core.sty`'s contract
  and populated identically (pre-migration values, appearance unchanged) by
  the default, institutional-research and executive themes; new `rk edge`,
  `rk matrix axis`/`rk matrix axis label`/`rk matrix cell` and `rk timeline`
  tikz styles, matching the plan's own naming; `reportkit-structure.sty`'s
  own `rk structure card`/`title`/`muted`/`arrow` tikzset migrated too
  (`reportarchitecture`/`reportroadmap`, the plan's motivating examples,
  are built on it). A real risk (whether a TikZ color option correctly
  macro-expands a token standing in for a color name) was resolved with a
  standalone probe before applying the pattern ~90 times, not assumed.
  `python -m pytest tests publication_pipeline/tests`: 225 passed, 2 failed
  (the same two pre-existing, environment-specific `pdflatex`/`microtype`
  font-expansion failures, confirmed identical before/after via `git
  stash`). Direct visual-identity verification: `career_guide_en`,
  `equity-research`, and `presentation_acceptance_test` compiled with
  `lualatex` before and after are text- and pixel-identical on every page.
  `bash scripts/acceptance_check.sh --require-tex`, `reportkit docs --check
  --json` and `scripts/contract_acceptance.py --json` show the same
  pre-existing failure and nothing new. See the plan's A4 section for the
  full record. Not attempted: the Python/theme-contract extension (a
  separately-scoped remaining piece of A4), the strategicpillars/
  maturitymodel/continuum/riskheatmap accent literals left un-tokenized
  (outside the plan's explicitly named styles), and A0/the equity pipeline
  acceptance sub-item.

- 2026-09-16: reconciled the retained multi-format follow-up with `main` at
  `f45ab86` and rebased the branch cleanly. Kept the target-aware entrypoint,
  writer, engine, and class-option staging; the equity-research Markdown and
  trusted-fragment acceptance fixture; and the automated B4 slide PDF
  accessibility profile and gate. Mainline tooling-hardening changes,
  including bounded parallel section builds, remain in the rebased base.
  Focused post-rebase checks and the documentation/status records were
  refreshed; the pinned full-build gate remains open because this host lacks
  `algorithmicx.sty`.

- 2026-09-15: completed multi-format Phase A4's Python/theme-contract slice.
  Theme now exposes explicit typography, geometry, spacing, rule, table, chart,
  diagram and script-coverage records while preserving the existing
  compatibility views. The visualization adapter consumes chart tokens, and
  check-theme validates Python records, palette synchronization, semantic
  LaTeX token population, and common/renderer-adapter package presence.
  Focused pure-Python validation and bytecode compilation pass; pytest,
  Matplotlib, and pandas are unavailable on the host, so runtime and
  pinned-toolchain verification remain outstanding.

- 2026-09-15: completed the deferred equity-research pipeline acceptance
  slice from Phase A5. The existing equity publication now includes
  `manuscript/order.txt`, ordinary Markdown source, and three trusted
  `diagram` fragments that embed its generated exhibits. The pipeline
  entrypoints now expose explicit theme/publication/class placeholders and
  `publication_build.py` stages them from the resolved `BuildTarget`, closing
  the previous default-theme leakage risk. Static `reportkit check` and
  publication validation pass; a local LuaLaTeX compile produced a six-page
  PDF using a disposable stub only because this host lacks `algorithmicx.sty`,
  which is supplied by the pinned `texlive-science` toolchain. The pinned
  full-build gate remains outstanding.

- 2026-09-15: automated Phase B4's slide accessibility findings. The
  canonical presentation fixture now carries explicit subject/keyword
  metadata and a visible-text external link; `inspect_pdf.py` exposes a
  reusable slide-accessibility profile that verifies metadata, catalog
  language, outline entries, meaningful links, decompressed diagram
  `/ActualText`, and the registry's explicitly unsupported tagged-PDF status.
  `tests/test_slide_accessibility.py` and `scripts/acceptance_check.sh` run
  the profile against the compiled fixture. The tagging spike itself remains
  out of scope until the TeX format supports `\DocumentMetadata`.

- 2026-09-14: multi-format Phase A5 (make the pipeline target-aware)
  implemented on `claude/multi-format-publication-ur4n82`, on top of the
  Phase B commit, following Phase B at explicit request (the plan's own
  recommended order puts A5 first). `publication_build.py` now resolves
  and uses a real `BuildTarget` instead of a hardcoded `TEMPLATE` constant;
  stages/compiles a stable `publication.tex`/`publication.pdf` regardless
  of which entrypoint was selected; records the full resolved selection in
  `build-report.json` and a log-visible marker. `reportkit build` can now
  build a presentation end to end for the first time — verified with a
  real build using Pandoc's Beamer writer (`--slide-level=1`) against
  plain Markdown headings, compiling through `reportkit-slides.cls` at the
  declared 160mm x 90mm canvas (verified via PyMuPDF). New
  `publication_pipeline/tests/test_build_target_selection.py` (6 tests,
  including two real end-to-end builds). `python -m pytest tests
  publication_pipeline/tests`: 222 passed, 2 pre-existing/environment-
  dependent failures (unchanged from the prior checkpoint).
  `bash scripts/acceptance_check.sh --require-tex` (both compile blocks
  exit 0), `reportkit docs --check --json`, and
  `scripts/contract_acceptance.py --json` all pass. Not attempted: the
  equity-research pipeline-acceptance fixture, the full D7 paged-base.tex
  split (judged too high-risk given existing pipeline-test dependence on
  `publication-template.tex`'s current combined/section/cover-page
  branching), and directive/fragment-based presentation authoring from
  Markdown. See the plan's A5 section for the full record.

- 2026-09-14: multi-format Phase B (slide renderer and presentation
  semantics) implemented on `claude/multi-format-publication-ur4n82`, on top
  of the A4 commit, at the user's explicit request to work Phase B next
  (out of the plan's own recommended sequence, which puts A5 first — noted
  plainly in the plan rather than silently reordered). `reportkit-slides.cls`
  + `reportkit-slides-core.sty` + `reportkit-presentation.sty` (B1/B2, all
  thirteen named compositions) + an experimental `executive` theme + B3's
  slide-figure-size Python extension + B4 verified by direct PDF inspection;
  the reusable B4 accessibility gate was added on 2026-09-15.
  Two real pre-existing/found-along-the-way bugs fixed: `reportkit-code.sty`
  still called `\Needspace` directly (A3 had missed it); Beamer's frame
  environment cannot be opened/closed across a custom environment's
  start/end code (composition design corrected to content-only, wrapped by
  an explicit author-written frame) — both documented at length in the
  plan's Phase B section so they don't get rediscovered. A real (not
  slides-specific) correctness fix landed in `config.py`'s paper-defaulting
  and `resolve_build_target()`'s D5 enforcement. `python -m pytest tests
  publication_pipeline/tests`: 216 passed, 2 pre-existing/environment-
  dependent failures (confirmed against the unmodified prior commit with
  matching `PATH`). `bash scripts/acceptance_check.sh --require-tex`,
  `reportkit docs --check --json`, `scripts/contract_acceptance.py --json`
  all pass. `reportkit build` now produces a presentation through A5's
  target-aware path; directive/fragment-based composition authoring from
  Markdown remains open. See the plan's Phase B section for the full record.

- 2026-09-13: multi-format A4's theme/adapter split (decision D11) and
  callout/metric style-token work (decision D2) implemented on
  `claude/multi-format-publication-ur4n82`, on top of `main` at `70f0aba`
  (A3 merged via PR #27). New `tests/test_theme_contract.py`; updated
  `tests/test_agent_contract.py` and `tests/test_reportkit_vnext.py` for the
  new adapter package names and the removed `\rk@theme` branch. Verified in
  a local (non-pinned, but this session's sandbox has direct network access,
  unlike the session that wrote A3's own verification) toolchain: the
  default fixture is PDF-hash-identical before/after; the institutional/
  equity fixture is verified by identical text and pixel-identical renders
  instead, because this toolchain's LuaLaTeX turned out not to be
  byte-reproducible even baseline-to-baseline (a toolchain quirk unrelated
  to this change, confirmed before concluding that). `python -m pytest
  tests publication_pipeline/tests`: 195 passed, 2 failed (both pre-existing
  and environment-specific, confirmed against the unmodified tree in the
  same venv). `bash scripts/acceptance_check.sh --require-tex`, `reportkit
  docs --check --json`, and `scripts/contract_acceptance.py --json` all
  pass. Diagram-token work and the Python `Theme` contract extension (the
  rest of A4) remain open; see the plan's A4 section.

- 2026-09-13: synchronized this index against `main` at `bb15d05`. Since the
  previous checkpoint, `911db87` cleaned empty title-page metadata and added
  regression coverage, `e1d55be` made publication dates configurable as
  literal or build-time values, and `bb15d05` made `acceptance_check.sh`
  auto-detect `build/.venv-tests` with regression coverage. The focused
  registry/LaTeX/pipeline checks pass (50 tests), and
  `bash scripts/acceptance_check.sh --require-tex` passes. Multi-format A1/A2
  remain complete; A0 and A3–A5, plus the slide phases, remain open.

- 2026-09-12: synchronized this index with the post-v1.9.3 tree. The
  code-quality remediation's user-facing Phase 0 and concrete Phase 1 changes
  are landed; its dependency-audit and structural follow-up remain open. The
  local `tooling` branch still has no commits unique to it and is now 107
  commits behind `main`. The multi-format registry remains paged-PDF-only;
  the planned slide renderer has not started.

- 2026-09-11: synchronized this index with the v1.9.2 publication-registry
  commits and shipped Phase A2 in v1.9.3: a generated LaTeX compatibility
  registry plus hard-failing theme/publication class-option validation. The
  `technical` compatibility alias is documented in the contract and README;
  A0 and Phase A3–A5 remain open.

- 2026-09-10: fixed the contract acceptance gate. Diagram metadata now expands
  empty PGF-stored options before testing them, preventing duplicate empty
  labels; the continuum's default natural width now includes its endpoint
  labels. The gate passes with zero blocking diagnostics, and the full suite is
  green at 129 passed, 12 skipped.
- 2026-09-10: synchronized this index with `main` at v1.9.1. The v1.9.0
  agent contract and v1.9.1 fork-port fixes are merged; strict acceptance and
  the full equity fixture compile locally. Pinned visual QA remains blocked by
  the locked toolchain fingerprint.
- 2026-09-09: institutional-theme spec's Step 5 (fixtures, QA, skill
  guidance) implemented on `claude/institutional-theme-step-5-gi0ptf` --
  the four-page `examples/equity-research/` fixture (financial figures
  reconciled per open question 6), a compact lualatex acceptance-test
  fixture wired into `scripts/acceptance_check.sh`, `scripts/
  visual_qa_equity_research.py` (spec §25's compile/diagnose/render/
  pixel-diff tooling), and `references/institutional-research-theme.md`.
  `figures.py`'s four charts were actually rendered and inspected this
  step (matplotlib/numpy/pandas/PyMuPDF installed), which caught and fixed
  a real `risk_reward_chart()` label-overlap bug; the LaTeX compile itself
  still was not, and neither could `scripts/visual_qa_equity_research.py`
  actually run its render/compare path -- no TeX Live in this session
  either. See the plan's own Step 5 section for exactly what was and
  wasn't run.
- 2026-09-09: institutional-theme spec's Step 4 (visualization integration)
  implemented on `claude/institutional-template-spec-m6imf7` -- a new
  `reportkit.themes` Python package, a genuinely theme-switching
  `reportkit_viz.apply_theme(name)`, a theme-aware `check-theme` CLI, and a
  new `risk_reward_chart()`. Actually executed and tested in this session
  (matplotlib/numpy/pandas installed) -- unlike Steps 1-3, not blind. See
  the plan's own Step 4 section for what was run.
- 2026-09-09: institutional-theme spec's Step 3 (equity publication profile)
  implemented on `claude/institutional-template-spec-m6imf7` -- front page,
  rating strip, sidebar, what's-changed, exhibit system, table grammar,
  dense financial-model mode, and bull/base/bear risk-reward primitives.
  Not compiled -- no TeX Live in the implementing session; see the P2 entry
  above and the plan's own verification section.
- 2026-09-09: institutional-theme spec's Step 2 (institutional theme)
  implemented on `claude/institutional-template-spec-m6imf7` -- Letter
  geometry, Google Sans resolution, the spec's §5 type scale, and quieter
  semantic callouts. Not compiled -- no TeX Live in the implementing
  session either; see the P2 entry above and the plan's own verification
  section.
- 2026-09-09: institutional-theme spec's Step 1 (theme infrastructure)
  implemented on `claude/vnext-spec-execution-wppmkl`, with the spec's eight
  open questions resolved in a companion implementation plan first, as the
  spec itself required. Not compiled — no TeX Live in the implementing
  session; see the P2 entry above.
- 2026-09-08: vNext Phase 1 implemented on `feat/reportkit-vnext-phase1` —
  W1–W7 delivered the package/CLI, nested config, diagnostics attribution,
  capability registry, manifest history, and test wiring. Phases 2–4 were
  deferred to the additive follow-up recorded below.
- 2026-09-09: PR #9 was aligned with merged PR #10; duplicate Phase 1 files
  were removed from its effective diff, and the additive Phase 2–4 capabilities
  were completed on `vnext-release`.
- 2026-09-07: docs-cleanup plan completed and merged to `main` via PR #7 (`965443b`); status flipped to Done per the plan's own completion rule (none of its 26 checklist items were ever checked off inline, but the doc's explicit "Flips to Done when this branch merges" criterion was satisfied).
- 2026-09-06: five stale spec/plan documents verified implemented and deleted (four untracked, one tracked — recoverable from git history at the parent of `49af053`).
- `docs/tooling-improvement-spec-draft.md` was lost permanently in 2026-09-06 while `docs/` was gitignored and untracked — the reason specs/plans are tracked in git from 2026-09-07 onward.
