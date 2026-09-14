# ReportKit — Outstanding Work

**Last updated:** 2026-09-14

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
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Approved — implementation slice and acceptance-environment fix landed; tooling follow-up remains | P1 |
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap — reconciled; implementation phases complete; use the plan, not this | P3 |
| [2026-09-07-reportkit-vnext-implementation-plan.md](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md) | Complete — Phase 1 merged via PR #10; additive Phases 2–4 merged via PR #9 | P3 |
| [2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md) | Approved | Process |
| [2026-09-07-documentation-and-status-tracking-cleanup.md](docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md) | Done — merged via PR #7 (`965443b`) | Process |
| [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md) | Implemented (Steps 1–5); open questions resolved in the plan below | P2 |
| [2026-09-09-reportkit-institutional-theme-implementation-plan.md](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md) | Complete — Steps 1–5 implemented; local LuaLaTeX verification passes; pinned visual QA remains | P2 |
| [2026-09-09-reportkit-fix-post-implementation-findings.md](docs/superpowers/plans/2026-09-09-reportkit-fix-post-implementation-findings.md) | Complete — all 8 tasks done and reviewed clean; fixture verification complete | Complete |
| [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md) | Phase A in progress — A1 landed in v1.9.2, A2 in v1.9.3; A3 implemented in the working tree, pending the pinned-toolchain CI gate; A0 and A4–A5 remain | P2 |
| [2026-09-10-reportkit-multi-format-publication-implementation-plan.md](docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md) | Phase A in progress — A1 and A2 complete; A3 implemented, pending the pinned-toolchain CI gate; A0 and A4–A5 remain | P2 |
| [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](docs/superpowers/specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md) | Implemented for v1.9.0 — Phase A′ and paged-renderer B′ complete; renderer-dependent work deferred | P2 |
| [2026-09-10-reportkit-fork-port-fixes-spec.md](docs/superpowers/specs/2026-09-10-reportkit-fork-port-fixes-spec.md) | Implemented in v1.9.1 via PR #19; all 11 applicable fixes landed | Complete |
| [2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md](docs/superpowers/specs/2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md) | Draft v0.1 — Phase 0 landed; most concrete Phase 1 fixes landed; structural Phase 2 work remains; 3 open questions | P1 |

## Open work

### P0

- **P0-1 — delete `tooling`, don't re-cut it.** `git rev-list --left-right
  --count main...tooling` returns `107 0` (verified 2026-09-12): the branch has
  no unique commits, so there is nothing to preserve, and
  [references/migrating-content-branches.md](references/migrating-content-branches.md)
  already dispositions it as "Superseded and stale… then delete". Branch the
  next tooling slice fresh from `main`.

The documented quick-start remediation and the associated Phase 0 findings
are implemented in the current worktree; the spec remains the detailed
change record.

### P1

- **P1-1 — finish the tooling-hardening follow-up.** Run and record the B4
  contrast/grayscale audit, then measure the publication build before deciding
  whether to implement bounded parallelism or incremental builds for the
  existing `--workers`/F2 hook.

- **P1-2 — close the code-quality remediation record.** The user-facing Phase 0
  fixes and the concrete Phase 1 fixes are in the current tree; the remaining
  work is to complete the dependency-audit signal (the repository has
  Dependabot configuration but no non-blocking `pip-audit` gate), resolve the
  three open questions in the spec, and either finish or explicitly defer its
  structural Phase 2 items. See
  [the remediation spec](docs/superpowers/specs/2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md).

### P2

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
  future slides core will implement differently. Verified byte-identical
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
  **Not yet done**: the diagram work (theme-populated TikZ styles across
  `reportkit-diagrams.sty`/`-structure.sty`/`-process.sty`/`-spatial.sty`)
  and the Python `Theme` contract extension (typography/chart/geometry/
  rule/table/diagram/script-coverage records; `check-theme` validating
  adapter as well as common tokens). The remaining Phase A work is ordered
  in the plan: capture the pinned compatibility baseline (A0 — attempted
  and blocked by sandbox networking, see the plan), finish A4, and make
  pipeline templates target-aware (A5). The original architecture risk
  remains in scope: the Markdown pipeline must eventually pass the resolved
  theme/publication selection to LaTeX.
  See [the spec](docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md)
  and [the implementation plan](docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md).

- **Multi-format publication architecture — Phase B (slide renderer and
  presentation semantics) started out of the plan's own recommended order**
  (§13 puts A5 before B; done first here at explicit request, with A4 and
  A5 both still incomplete). **B1 and B2 are essentially complete** via
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
  regression coverage that no paged theme gained slide keys. **B4 verified
  by direct PDF inspection** on a compiled smoke fixture (title/author/
  subject/keywords metadata, catalog language, PDF outline/bookmarks,
  diagram ActualText — not yet an automated gate). Two real bugs were found
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
  silently dropping it. **Not done**: `reportkit build` cannot produce a
  presentation yet (blocked on A5's target-aware pipeline, not attempted
  here, though `publication_pipeline/templates/slides-base.tex` and
  `presentation.tex` exist as the D7-shaped skeletons A5 will consume);
  Pandoc's Beamer writer is registered but unexercised; B4's findings are
  not yet an automated pytest gate; `executive` stays experimental pending
  Phase C's design review. See the plan's Phase B section for the full
  verification record (216 passed, 2 pre-existing/environment-dependent
  test failures, both confirmed by reproducing identically against the
  unmodified prior commit).

- **Agent interface & platform contract — Phase A′ and the
  non-renderer-dependent parts of Phase B′ implemented in v1.9.0; remaining
  work deferred.** The canonical contract is now in
  [references/agent-contract.md](references/agent-contract.md), and the
  spec's eight open questions are resolved. Upcoming work is renderer-gated:
  slide-renderer accessibility parity (B′ item 7), the authoring IR and
  constrained dialect/visual feedback loop (C′), then progressive-disclosure
  context budgets, a neutral non-Claude adapter, and i18n extensions (D′).
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

- The repository test environment is `build/.venv-tests`; it supplies
  PyMuPDF, NumPy, pandas, matplotlib, and pytest. The host Python environment
  is not authoritative for the full suite.
- TeX Live 2025 with `lualatex` is available locally; the default/paged and
  institutional strict acceptance fixtures compile using the checked-in,
  licensed Google Sans fixtures staged by the test harness. Ambient system-font
  fallback lookup is unavailable on this host; the pinned visual-comparison
  environment is also unavailable.
- `pdfinfo`, `pdffonts`, `pdftoppm` (poppler-utils): not installed on the current dev machine.
- `pypdf`, `pdfplumber`, system-wide PyMuPDF: not installed.
- `accsupp.sty`: not installed; `tlmgr install` fails (this checkout is TinyTeX on TL2025 against a TL2026 remote).
- Libertinus fonts: installed to `TEXMFHOME` (`~/.TinyTeX/texmf-local`) from `font_data/reportkit-libertinus-fonts.tar.gz`.

## History

- 2026-09-14: multi-format Phase B (slide renderer and presentation
  semantics) implemented on `claude/multi-format-publication-ur4n82`, on top
  of the A4 commit, at the user's explicit request to work Phase B next
  (out of the plan's own recommended sequence, which puts A5 first — noted
  plainly in the plan rather than silently reordered). `reportkit-slides.cls`
  + `reportkit-slides-core.sty` + `reportkit-presentation.sty` (B1/B2, all
  thirteen named compositions) + an experimental `executive` theme + B3's
  slide-figure-size Python extension + B4 verified by direct PDF inspection.
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
  all pass. `reportkit build` still cannot produce a presentation (A5
  remains open); see the plan's Phase B section for the full record.

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
