# ReportKit — Outstanding Work

**Last updated:** 2026-09-19

This is the current-work index, not an audit. The front of the document contains
only work that is still actionable. Completed implementation records and dated
history are kept at the back. Each spec/plan remains the authoritative execution
record for its own scope; this file is the rollup. See
[docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md)
and [references/documentation-status.md](references/documentation-status.md).

## Outstanding documents

| Document | Current status | Priority |
|---|---|---|
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Reconciled roadmap; implementation phases are complete in the companion plan. Only the deferred consumer-project template remains. | P3 |
| [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md) | Steps 1–5 and pinned visual baseline comparison passed; human §25 review remains. | P2 |
| [2026-09-09-reportkit-institutional-theme-implementation-plan.md](docs/superpowers/plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md) | Same state: pinned baseline passed; human §25 visual release review remains. | P2 |
| [2026-09-09-reportkit-multi-format-publication-architecture-spec.md](docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md) | A0–A5, Phase B, and constrained-authoring item C′1 are implemented; focused pinned A3/A4 checks passed, full acceptance and future visual phases remain. | P2 |
| [2026-09-10-reportkit-multi-format-publication-implementation-plan.md](docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md) | Same implementation state as the spec; remaining work is release verification and later visual phases. | P2 |
| [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](docs/superpowers/specs/2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md) | A′/B′, constrained authoring, and standalone render are implemented; budget, neutrality, i18n, and tagging work remain deferred. | P2 |

## Open work

### P2

- **Institutional theme — human visual release review.** The four-page equity
  fixture and checked-in baseline passed the pinned OCI comparison on
  2026-09-19 with zero diagnostics. Complete the spec §25 human visual review;
  do not update expected pixels from a non-pinned host.

- **Multi-format A3/A4 — complete the acceptance matrix.** The pinned OCI
  image/doctor and 53 focused A3/A4 checks passed on 2026-09-19. Finish the
  interrupted full acceptance matrix and record its result; focused status
  records are synchronized.

- **Multi-format Phase C — promote the executive theme.** Complete the
  consulting/strategy visual system, 8–10 slide fixture, and visual approval
  required to move `executive` from experimental to stable. Keep the existing
  presentation composition API unchanged.


### P3

- **Multi-format Phase D — venture theme and controlled branding.** Add the
  venture theme and strict four-key brand override path, including hashed logo
  staging, cross-renderer effective-theme materialization, and a reviewed
  10–12 slide fixture.

- **Multi-format Phase E — editorial feature article.** Add the editorial theme,
  feature-article publication type, semantic feature primitives, and the
  required 6–8 page fixture without introducing feature-specific positioning
  APIs.

- **Multi-format Phase F — executive brief, book, and combination coverage.**
  Add only the publication details and fixtures named in the implementation
  plan, then derive minimal compatibility coverage from the publication
  registry.

- **Agent contract — progressive disclosure budgets.** Add compact context
  slices with deterministic token-cost reporting while preserving the
  unfiltered compatibility output and the 2,000-token host-neutral quickstart
  ceiling.

- **Agent contract — neutral adapter.** Generate the OpenAI-style tool bundle
  from the stable CLI contract and prove it can author and validate a minimal
  publication without reading `SKILL.md`.

- **Agent contract — language and script truthfulness.** Add per-script font
  stacks and renderer/theme language compatibility; keep RTL unsupported and
  Vietnamese metadata-only until a real typography fixture proves otherwise.

- **Agent contract — tagged-PDF spike.** Revisit tagged PDF only through the
  separate toolchain-gated `\DocumentMetadata` investigation; the current
  contract must continue to state that tagging is unsupported.

- **vNext consumer-project template.** Add a Copier template only after
  `publication.yaml` settles and there is more than one consumer content
  repository to keep synchronized.

## Completed work

The following records are complete. Their implementation details and dated
verification notes are retained in `History` below.

### Completed specifications and plans

| Document | Status |
|---|---|
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Implementation slice, `algorithmblock`, B4 contrast/grayscale audit, and F2 bounded parallel workers complete. |
| [2026-09-07-reportkit-vnext-implementation-plan.md](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md) | Phase 1 and additive Phases 2–4 complete. |
| [2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md) | Approved design implemented by the companion plan. |
| [2026-09-07-documentation-and-status-tracking-cleanup.md](docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md) | Done and merged to `main`. |
| [2026-09-09-reportkit-fix-post-implementation-findings.md](docs/superpowers/plans/2026-09-09-reportkit-fix-post-implementation-findings.md) | All eight tasks complete and reviewed clean. |
| [2026-09-10-reportkit-fork-port-fixes-spec.md](docs/superpowers/specs/2026-09-10-reportkit-fork-port-fixes-spec.md) | All 11 applicable fixes landed and covered. |
| [2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md](docs/superpowers/specs/2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md) | Phases 0–2 and all three open questions complete. |
| [2026-09-16-reportkit-algorithm-visualization-primitives-spec.md](docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md) | Full P0–P3 algorithm-visualization scope complete. |
| [2026-09-18-algorithm-visuals-fix-sprint-spec.md](docs/superpowers/specs/2026-09-18-algorithm-visuals-fix-sprint-spec.md) | Tasks 1–4 complete; dedicated gate passes, with only documented pre-existing acceptance failures. |
| [2026-09-18-algorithm-visuals-fix-sprint.md](docs/superpowers/plans/2026-09-18-algorithm-visuals-fix-sprint.md) | Tasks 1–4 complete and synchronized with the sprint spec. |

### Completed implementation slices

- Tooling hardening, the vNext CLI/diagnostics/registry phases, source/link
  validation, PDF inspection, `\RKLink`, history analysis, `algorithmblock`,
  and bounded parallel section builds are shipped.
- The documentation/status-tracking cleanup is shipped; specs and plans are
  tracked, status headers exist, and `TODOS.md` is an index rather than an
  audit.
- Institutional theme and equity-research Steps 1–5 are implemented and the
  local LuaLaTeX fixtures compile. The pinned visual gate is listed above.
- The fork-port fixes, code-quality/dependency remediation, and all applicable
  structural follow-up are shipped.
- Algorithm visualization primitives P0–P3 are implemented, documented, and
  covered by generated-contract and regression tests.
- The algorithm visuals fix sprint is implemented: repaired linear-state
  geometry, readable traces, dependency-layout/ready-queue rendering,
  code-unit pagination protection, the four-page guide fixture, acceptance
  wiring, and default/grayscale/institutional-research visual review are
  complete. The dedicated gate passes; the full acceptance command retains
  only the pre-existing out-of-scope failures recorded by the sprint plan.
- Multi-format A0–A5, Phase B, and constrained-authoring C′1 are implemented
  for the currently registered targets. The remaining pinned/runtime gates
  and future visual phases are listed above.
- The agent-facing A′/B′ contract, constrained Markdown/typed-IR authoring
  path, and standalone render loop are implemented. The deferred budget,
  neutrality, i18n, and tagging slices are listed above.
- The standalone `reportkit render` authoring-loop command is implemented with
  page/range selection, DPI control, atomic output, a JSON manifest, a
  toolchain fingerprint, structured missing-PyMuPDF failure, focused tests,
  and contract/skill documentation.


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

- 2026-09-19: split the active P2 work across four parallel implementation
  tracks. The standalone `reportkit render` command is now implemented with
  selected-page/DPI rendering, atomic output, a JSON manifest, a toolchain
  fingerprint, and structured missing-PyMuPDF handling; its focused tests pass
  in both the host and pinned environments. The institutional four-page visual
  baseline comparison passed in the pinned OCI toolchain (human §25 review is
  still open). Focused pinned A3/A4 checks passed; the broader acceptance suite
  retains documented pre-existing failures and was not treated as a release
  pass. Phase C remains intentionally open because no reviewed executive deck
  fixture exists yet.

- 2026-09-19: reorganized this index so only active, scoped work appears before the completed implementation record; synchronized the document rows with the current spec and plan status lines.

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
