# ReportKit — Outstanding Work

**Last updated:** 2026-09-09

This is an index, not an audit. Each spec/plan under `docs/superpowers/`
carries its own `**Status:**` line, updated at the workflow checkpoint that
changed it (approval, execution start, merge). This file is a one-line
pointer per document plus a rollup of what's still open — edited
incrementally when a status changes, never rebuilt from scratch. See
[docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md)
for why.

## Documents

| Document | Status | Priority |
|---|---|---|
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Approved, implementation slice landed; tooling follow-up remains | P1 |
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap — reconciled; implement from the plan, not this | P3 |
| [2026-09-07-reportkit-vnext-implementation-plan.md](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md) | Phase 1 in PR #10; additive Phases 2–4 in PR #9 | P3 |
| [2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md) | Approved | Process |
| [2026-09-07-documentation-and-status-tracking-cleanup.md](docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md) | Done — merged via PR #7 (`965443b`) | Process |
| [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md) | Implemented (Steps 1–5); open questions resolved in the plan below | P2 |
| [2026-09-09-reportkit-institutional-theme-implementation-plan.md](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md) | Steps 1–5 of 5 implemented (theme infrastructure, institutional theme, equity publication profile, visualization integration, fixtures/QA/skill guidance); pending real-TeX verification | P2 |

## Open work

### P0

- **P0-1 — delete `tooling`, don't re-cut it.** `git rev-list --left-right
  --count main...tooling` returns `61 0` (verified 2026-09-09): the branch has
  no unique commits, so there is nothing to preserve, and
  [references/migrating-content-branches.md](references/migrating-content-branches.md)
  already dispositions it as "Superseded and stale… then delete". Branch the
  next tooling slice fresh from `main`.

### P1

- Continue the tooling-hardening follow-up slices and reconcile them with the
  vNext roadmap; the vNext Phase 2–4 implementation slice is now complete.

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
  `apply_theme`/`risk_reward_chart` usage. **Steps 1–3's LaTeX and Step
  5's visual-regression baseline remain unverified by compilation** — no
  session so far has had a TeX Live install with `lualatex`. Before
  trusting any of it on a machine with TeX: run `bash
  scripts/acceptance_check.sh --require-tex`, diff
  `latex_templates/examples/career_guide_en/report.tex`'s compiled output
  against its pre-Step-1 PDF, and run `python3 scripts/
  visual_qa_equity_research.py --update-expected` followed by a human
  review against the printed spec §25 checklist before committing the
  resulting baseline. See
  [the implementation plan](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md).

### P3

- vNext — **Phase 1 implemented 2026-09-08 in PR #10; additive Phases 2–4 are
  implemented on PR #9**. PR #9 intentionally inherits the Phase 1 package,
  config, diagnostics, registry, CLI, manifest, and test-wiring work from PR
  #10 rather than duplicating it. Its additive capabilities are deeper PDF QA,
  source/manuscript and link-registry validation, `\RKLink` rendering, and
  `reportkit analyse-history`.
- Plan record — **reconciled 2026-09-07**; the overlap with the tooling spec is
  audited section by section in
  [the implementation plan](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md).
- Backlog: a Copier template for consumer projects — deliberately deferred until vNext §4 settles `publication.yaml`'s schema and there's more than one content repo to keep in sync.

## Environment notes

- `pdfinfo`, `pdffonts`, `pdftoppm` (poppler-utils): not installed on the current dev machine.
- `pypdf`, `pdfplumber`, system-wide PyMuPDF: not installed.
- `accsupp.sty`: not installed; `tlmgr install` fails (this checkout is TinyTeX on TL2025 against a TL2026 remote).
- Libertinus fonts: installed to `TEXMFHOME` (`~/.TinyTeX/texmf-local`) from `font_data/reportkit-libertinus-fonts.tar.gz`.

## History

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
