# ReportKit Institutional Theme + Equity Profile — Implementation Plan

**Status:** In progress. Step 1 (theme infrastructure) implemented on
`claude/vnext-spec-execution-wppmkl`. Steps 2–5 not started.
**Last updated:** 2026-09-09

**Spec:** [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](../specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md)

---

## Why this document exists

The spec is explicit that it is "Draft / awaiting approval" and that its
eight open questions "must be resolved before implementation, not during
it." This document resolves each one with a concrete decision, then records
what Step 1 of the spec's own five-step sequence (§27) actually built against
those decisions.

**Environment constraint that shapes every decision below:** this
implementation session has no TeX Live installation (`pdflatex`, `lualatex`,
`kpsewhich` are all absent) and no PyMuPDF. Every `.sty`/`.cls` change here
is therefore **unverified by compilation**. Code was moved rather than
rewritten wherever possible specifically to minimize that risk, existing
Python-level tests were extended and run, and new Python-level tests were
added for everything that doesn't require TeX. Before this lands anywhere
that matters, run `bash scripts/acceptance_check.sh --require-tex` and
`./reportkit doctor --require full-build` on a machine with TeX Live —
neither has been run against this change.

---

## Resolutions to the eight open questions

### OQ1 — Engine default conflicts with the theme requirement

**Decision: validate and fail**, per the spec's own recommendation. A theme
that requires an engine the resolved configuration doesn't provide must
refuse to build rather than silently degrade (e.g., falling back off Google
Sans).

**Implementation:** `config.py` gains a small, explicit
`THEME_ENGINE_REQUIREMENTS` map (currently just
`{"institutional-research": "lualatex"}`) and a `theme_engine_conflict()`
function. It is checked in two places for defense in depth: `reportkit
check` (static, before any compiler runs) and `reportkit build` /
`publication_build.py` (immediately after the engine is resolved, before the
first compiler pass). Both report the same message and both are covered by
new tests.

### OQ2 — `check-theme` is single-theme by construction

**Decision:** make it theme-parameterized now, in the same step that moves
the palette out of `reportkit.cls`. `reportkit_viz.py check-theme` gains a
`--theme NAME` flag that resolves to
`latex_templates/themes/reportkit-theme-<NAME>.sty` (default `default`); the
existing `--class` flag becomes an explicit path override for anyone who
wants to point elsewhere (kept for backward compatibility — it was the only
flag before). It still validates against the single Python-side
`LATEX_THEME_COLORS` dict, because that is still the only Python palette
that exists. A per-theme Python token module (`reportkit.themes.*`) is Step
4 work; until it lands, `check-theme --theme institutional-research` will
compare the institutional LaTeX palette against the *default* Python
palette and should be expected to fail — that's an honest failure, not a
false pass, which is what OQ2 asked to avoid.

### OQ3 — `FIGURE_SIZES` key rename is a breaking API change

**Decision:** not addressed in Step 1. `FIGURE_SIZES` and `TEXT_WIDTH_IN`
are untouched — they remain A4-coupled exactly as today. This is Step 4
(visualization integration) scope. Recorded here so the decision isn't lost:
when Step 4 lands, **keep `wide` as an alias** for whichever of `half` /
`dominant` it maps closest to (`wide` today is `(TEXT_WIDTH_IN, 3.05)`,
narrower than `full` at 3.55 — closest in intent to a "not-quite-full-width"
figure). Don't drop it; existing publications call `new_figure("wide")`.

### OQ4 — §15 needs an aspect-ratio policy

**Decision:** also deferred to Step 4, recorded for whoever picks it up:
heights should be **ratio-derived from width**, not per-size constants,
so a theme with a different text width (Letter vs A4, different margins)
doesn't need to hand-tune four heights. Keep one configurable aspect ratio
per named size (e.g., `full` ≈ 16:9-ish landscape figure, `compact` squarer)
rather than a fixed inch height.

### OQ5 — §6 geometry deliberately diverges from the prototype

Not a decision point — the spec already resolves this itself ("§6 governs.
Do not copy the prototype's geometry"). Recorded here only so Step 2 doesn't
re-litigate it: use §6's 13–15mm/13–17mm margins and §5's 10.7/14.6 body
size, not Appendix A's tighter numbers.

### OQ6 — the prototype's financial figures are internally inconsistent

**Not resolved in this plan.** Reconciling FY27E EBITDA/EPS across the front
page, Exhibit 4, Exhibit 5, and Exhibit 6 requires picking one internally
consistent set of fictional numbers and is inseparable from actually writing
the Step 5 example (`latex_templates/examples/equity-research/`). Doing it
now, disconnected from that fixture, would just produce a second set of
numbers to reconcile later. Flagged as a blocking prerequisite for Step 5,
not for Step 1.

### OQ7 — §2's target tree omits six existing LaTeX modules

**Decision:** confirmed — none are dropped. `reportkit-boxes.sty`,
`-code`, `-diagrams`, `-grammar`, `-longform`, `-pandoc`, `-process`,
`-spatial`, `-structure` all remain exactly where they are, at the top level
of `latex_templates/`. Step 1 only adds `reportkit-core.sty` alongside them
and `themes/reportkit-theme-default.sty` in a new subdirectory.

### OQ8 — theme-token import direction

**Decision:** theme modules live inside the `reportkit` package
(`python_scripts/reportkit/themes/`), matching §2's target tree, and
`reportkit_viz.py` — which stays outside the package, per the current-state
table — will import *from* `reportkit.themes` when Step 4 builds it. That is
a one-directional dependency (`reportkit_viz` → `reportkit.themes`) with no
cycle: `reportkit.themes` will not import `reportkit_viz`. Not built in Step
1 — there is no institutional theme yet for it to hold tokens for — but the
direction is fixed now so Step 4 doesn't have to re-litigate it.

---

## Step 1 — Theme infrastructure (this change)

Scope: extract typography, geometry, palette and running furniture out of
`reportkit.cls` into a selected theme file, add theme/publication-type
selection, and prove the default theme is the pre-existing design with
nothing new visually. Per §27 this is bounded to "preserving pixel-equivalent
legacy output" — no new theme, no equity-research primitives yet.

### What moved where

`reportkit.cls` is now a thin orchestrator: it declares a fixed, enumerated
set of `theme=`/`publication-type=` class options (not a general key=value
parser — an unrecognised theme name is deliberately a hard LaTeX failure
rather than a silent fallback), loads `article`, requires
`reportkit-core.sty`, requires the selected theme file, then requires the
four semantic modules (`reportkit-boxes`, `-code`, `-diagrams`, `-grammar`)
as before.

`latex_templates/reportkit-core.sty` (new) holds everything that is
engine-neutral mechanism, not visual identity: package loading (`iftex`,
`microtype`, `xcolor`, `graphicx`, `booktabs`, `siunitx`, `enumitem`,
`titlesec`, `fancyhdr`, `needspace`, `caption`, `geometry`, `hyperref`,
`xparse`, `etoolbox`), `\RKLink`, the `\rk@leftheader`/`\rk@footer`/etc.
metadata macros and their setters, the `AtBeginDocument` PDF-metadata /
`pdflang` block, `\RKDiagramSection`/`\RKDiagramSubsection`, and `\code`.
None of this differs by theme.

`latex_templates/themes/reportkit-theme-default.sty` (new) holds everything
that is visual identity, moved verbatim from `reportkit.cls`: font loading
(`libertinus`, the pdfTeX-only math companion guard), the full color
palette, `\color{Ink}` and the `colorlinks` `\hypersetup` call, list/caption/
siunitx defaults, running furniture (`fancyhf`, header/footer content,
`headrule`), the section/subsection `titleformat`/`titlespacing` and their
`RKSectionNeed`/`RKSubsectionNeed` lengths, `\maketitle`, `execsummary`, and
`\source`. Geometry moved from a `\usepackage[options]{geometry}` load to
`\RequirePackage{geometry}` in core plus a late `\geometry{...}` call here —
the geometry package explicitly supports both forms identically, so this is
not a behavior change, just a relocation that lets a future theme
reconfigure margins without re-loading the package.

Nothing about this split changes `theme=default`'s (i.e. no `theme=`
option's) rendered output — every moved block is copied, not rewritten.

### Config, CLI, and build-script plumbing

- `config.py`: `DOCUMENT_KEYS` gains `theme` (default `"default"`),
  `publication_type` (default `"technical-report"`), `paper` (default
  `"a4"`). `THEME_ENGINE_REQUIREMENTS` and `theme_engine_conflict()`
  implement OQ1.
- `context.py`: `reportkit context` now reports `document.theme`,
  `document.publication_type`, and `document.paper` alongside the existing
  `document.engine`.
- `cli.py`: `reportkit check` runs `theme_engine_conflict()` against the
  resolved document config and reports it as an ordinary validation error.
- `publication_build.py`: same check runs right after `engine` is resolved,
  before the first TeX pass; the copy-loop that snapshots templates into the
  build's output directory and the build manifest's template hash list both
  now also pick up `latex_templates/themes/*.sty` (previously only
  `*.cls`/top-level `*.sty`, which would have silently excluded theme files
  from both the sandboxed build and the provenance record).
- `reportkit_viz.py`: `check-theme` gains `--theme` (OQ2).
- Every place that builds a `TEXINPUTS` value or flat-copies
  `latex_templates/*.sty` into a scratch/build directory
  (`tests/conftest.py`, `scripts/acceptance_check.sh`,
  `shell_scripts/bootstrap.sh`) now also covers
  `latex_templates/themes/*.sty` — otherwise every existing compile-based
  test and the acceptance/bootstrap scripts would fail to find
  `reportkit-theme-default.sty` the moment `reportkit.cls` requires it.

### Deferred out of Step 1, on purpose

- The institutional theme file itself, Google Sans/`fontspec` handling, and
  the `publication-type=equity-research` option — Steps 2–3.
- Making the base font size (`10pt` in `\LoadClass[10pt,a4paper]{article}`)
  theme-selectable. Step 1 only ships the `default` theme, which needs
  10pt/a4 exactly as today, so the harder problem of selecting `\LoadClass`
  options from a class-option value (which must happen before the theme file
  is even readable) is deliberately not solved yet. The margins problem is
  solved (via late `\geometry{}` reconfiguration); the base-size problem is
  not, and Step 2 must solve it — either via `\LoadClass` option
  redirection before `\ProcessOptions`, or by having themes override
  `\normalsize` etc. directly rather than relying on the class's base size
  option. Recommend the latter: it composes better with `\LoadClassWithOptions`-style guarantees, and mirrors why margins were solved with late `\geometry{}` rather than a load-time option.
- Selecting `theme=institutional-research` today falls through
  `\DeclareOption*` to `article`, which will not recognise it either;
  LaTeX's behavior in that case is a soft "unused option(s)" warning at
  `\begin{document}`, not a hard failure. That's an acceptable gap for a
  theme that doesn't exist yet, but Step 2 should turn it into a clear error
  the moment the institutional theme file exists and is still misspelled.

### Verification actually performed

- `python3 -m pytest tests publication_pipeline/tests -q` (both suites; TeX-
  and PyMuPDF-dependent cases skip cleanly in this environment).
- `python3 -c "import reportkit.cli"` / `./reportkit context --json` /
  `./reportkit doctor` — CLI still loads and runs.
- Manual review of every moved LaTeX block against the original file (diff
  of extracted text against the original byte ranges) to confirm nothing was
  dropped or altered in transit.
- **Not performed, and should be before merging:** an actual `pdflatex`
  compile of `latex_templates/examples/career_guide_en/report.tex` (the
  backward-compatibility witness named in spec §26) and a diff of its output
  PDF against the pre-change PDF. This environment cannot do that. Whoever
  reviews this on a machine with TeX Live should treat that diff as the real
  acceptance gate for Step 1, not the test suite above.

---

## Remaining sequence

Steps 2–5 are not started. Per spec §27:

2. **Institutional theme** — Letter geometry, Google Sans resolution
   (`font_policy: strict`/`fallback`), the full type scale from spec §5,
   quieter semantic callouts. Needs the `\LoadClass`-time base-size question
   above resolved first.
3. **Equity publication profile** — front page, rating strip, sidebar,
   what-changed, exhibit system, valuation/model/risk-reward primitives.
4. **Visualization integration** — `reportkit.themes` package (OQ8),
   `FIGURE_SIZES`/aspect-ratio policy (OQ3/OQ4), Google Sans in Matplotlib,
   `check-theme`'s per-theme Python palette.
5. **Fixtures + QA + skill guidance** — the four-page equity-research
   example (needs OQ6 resolved first), visual regression fixtures, `SKILL.md`
   updates.

Each remaining step should get its own review-and-verify pass on a machine
with TeX Live before the next one starts — this plan deliberately did not
attempt Steps 2–5 in the same pass as Step 1 given that constraint.
