# ReportKit Institutional Theme + Equity Profile — Implementation Plan

**Status:** In progress. Step 1 (theme infrastructure) implemented on
`claude/vnext-spec-execution-wppmkl`. Steps 2–4 (institutional theme, equity
publication profile, visualization integration) implemented on
`claude/institutional-template-spec-m6imf7`. Step 5 not started.
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

## Step 2 — Institutional theme (this change)

Scope per spec §27: "Letter geometry, Google Sans resolution, type scale,
spacing, rules, tables and quieter semantic callouts." Not in scope: the
equity-research publication-type primitives (`researchfrontpage`, `exhibit`,
`ratingstrip`, etc. — Step 3), `reportkit_viz.py` theme-awareness (Step 4),
and the equity-research example fixture (Step 5). A document that loads
`theme=institutional-research` alone (no `publication-type=equity-research`,
which doesn't exist yet) gets institutional typography/geometry/palette/
furniture and a plain `\maketitle`/`\section`/`execsummary` — exactly the
`theme=default` shape, restyled.

**Environment constraint, still unresolved:** this session also has no TeX
Live install (no `pdflatex`/`lualatex`/`kpsewhich`) and no PyMuPDF (installed
locally via pip for the Python-level test run below, which is a real
dependency of `tests/conftest.py`, not a substitute for compiling). Every
`.sty` change in this step is therefore, again, **unverified by
compilation**. Brace-balance was checked mechanically for every changed/new
`.sty`/`.cls` file (a rough but real check: strip `%`-comments per line,
sum `{`/`}`, confirm the file ends at depth 0) and every macro pattern used
was cross-checked against an existing, working instance of the same pattern
elsewhere in the tree (`\@setfontsize` against `\@title`/`\@empty` already in
use; `\IfFontExistsTF`/fontspec syntax against Appendix A's embedded
prototype; `\ifdefstring` against etoolbox's documented 4-argument form).
None of that substitutes for an actual `lualatex` compile. Before this lands
anywhere that matters: run `bash scripts/acceptance_check.sh --require-tex`
(still pdflatex-only — institutional-research isn't in its test list, since
it requires lualatex and there's no primitive-level acceptance fixture for
it yet; that gap is Step 5's job), and compile a minimal
`\documentclass[theme=institutional-research]{reportkit}` smoke document
with `lualatex` on a machine that has Google Sans (or accept the
`font_policy: fallback` warning path) installed.

### What was added

`latex_templates/themes/reportkit-theme-institutional-research.sty` (new) —
self-contained, like `reportkit-theme-default.sty`: nothing in it depends on
the default theme also being loaded (only one theme is ever loaded per
document). Implements:

- **Engine guard.** `\ifPDFTeX` at the top of the file raises a
  `\PackageError` naming the requirement. This is enforcement *in addition
  to*, not instead of, `config.py`'s `theme_engine_conflict()` (OQ1,
  Step 1) — defense in depth for anyone invoking `lualatex`/`pdflatex`
  directly rather than through the `reportkit` CLI.
- **Fonts (spec §4).** `fontspec` + `\IfFontExistsTF{Google Sans}`. Three
  new setter commands — `\setreportkitfontfamily`, `\setreportkitfontpath`,
  `\setreportkitfontpolicy` — mirror the naming and preamble-settable
  pattern of the existing `\setreportkitleftheader`-family macros in
  `reportkit-core.sty`. Resolution itself runs in `\AtBeginDocument` (the
  same deferral `reportkit-core.sty` already uses for the hyperref
  PDF-metadata block), so a setter call anywhere in the preamble takes
  effect regardless of where it appears relative to `\documentclass`.
  `font_policy: strict` raises `FAIL institutional-research requires
  <family>`; `font_policy: fallback` (the default) walks Inter → Noto Sans →
  TeX Gyre Heros and warns which one it used, per spec §4's diagnostic text
  almost verbatim. `font_path` is documented as a *directory* containing
  `GoogleSans-Regular.ttf`/`GoogleSans-Bold.ttf`, matching Appendix A's
  `\GoogleSansPath` convention, not an arbitrary single file — the simplest
  contract that doesn't require generic path-splitting in LaTeX.
- **Geometry (spec §6).** `\geometry{letterpaper,left=14mm,right=14mm,
  top=14mm,bottom=15mm,headsep=6mm,footskip=8mm}` — inside §6's 13–15mm/
  13–17mm ranges, looser than Appendix A's prototype margins per OQ5. The
  `a4paper` `\LoadClass` option in `reportkit.cls` is irrelevant here:
  geometry's own paper option recomputes the PDF page size regardless, the
  same fact the default theme's late `\geometry{a4paper,...}` call already
  relies on — no `reportkit.cls` change was needed for Letter to take
  effect.
- **Base font size — the plan's "harder problem", now resolved.**
  `\renewcommand{\normalsize}{\@setfontsize{\normalsize}{10.7pt}{14.6pt}}`
  then `\normalsize`, per the plan's Step 1 recommendation ("themes
  override `\normalsize` directly"). This works because every other sized
  element in both theme files already sets an explicit `\fontsize{}{}`
  rather than relying on `\small`/`\large`/etc., so `\normalsize` is the
  only class-relative size institutional body text actually depends on.
  `\small`/`\footnotesize`/etc. remain scaled off the `10pt` `\LoadClass`
  option — not re-tuned, since nothing in either theme file currently uses
  them for anything the spec constrains.
- **Full §5 type scale** as twelve named size commands (`\rkmastheadsize`
  … `\rkdisclosuresize`), not yet consumed by anything (their consumers —
  `\researchheadline`, `\ratingitem`, sidebar blocks, etc. — are Step 3).
  Exposing the token now, unused, mirrors how Step 1 exposed
  `THEME_ENGINE_REQUIREMENTS` and `resolve_document()`'s `theme`/
  `publication_type` keys ahead of anything that reads them.
- **Palette (spec §20).** Different hex values from the default theme's
  (documented inline); the nine semantic-callout colors
  (`Principle`/`Decision`/`RedFlag`/etc.) and `MetricAccent` are
  deliberately kept at the *same* hex values as the default theme — §21
  asks the institutional theme to quiet the callout **chrome**, not
  recolor each semantic category, and a reader still scans by category
  hue once the box background is gone.
- **Quieter semantic callouts (spec §21).** `reportkit-boxes.sty` (a
  semantic module, not a theme file) now branches its single
  `\newtcolorbox{rk@callout}{...}` definition on `\rk@theme` via
  `\ifdefstring` from etoolbox. This is the one place a theme reaches into
  a semantic module rather than the reverse, and it's deliberate, not
  architectural erosion: `\newtcolorbox` bakes its options in at
  *definition* time, which happens when `reportkit-boxes.sty` loads —
  strictly after the theme file, per `reportkit.cls`'s load order — so
  there is no hook a theme file could use to override this after the fact.
  The alternative (forking the whole boxes module per theme) is exactly
  what spec §13 tells Step 4 *not* to do for charts, for the same
  duplication reason. The default-theme branch is byte-for-byte the
  pre-existing definition; a new test
  (`test_reportkit_boxes_default_theme_unchanged`) pins that.
- **Running furniture, section hierarchy, `\maketitle`, `execsummary`,
  `\source`.** Same structural shape as the default theme (same core
  macros: `\rk@leftheader`/`\rk@footer`/`\rk@version`), restyled to the
  institutional type scale and palette. Section numbers are *not*
  accent-colored, unlike the default theme's `LinkBlue` section numbers —
  a deliberate difference, following §20's "do not use accent on every
  section heading."

`reportkit.cls` gained one line:
`\DeclareOption{theme=institutional-research}{...}`. No other class change
was needed — the base-size and paper-size problems Step 1 flagged as
blocking are both resolved inside the theme file itself, not in the class.

**Filename decision (new, not one of the original eight OQs, but the same
kind of decision that needed making before writing the file):** the spec's
§2 target tree names this file `reportkit-theme-institutional.sty`. It is
named `reportkit-theme-institutional-research.sty` instead, matching the
theme identifier (`institutional-research`) used everywhere else in the
spec and by Step 1's `\edef\rk@themepackage{reportkit-theme-\rk@theme}` /
`reportkit_viz.py`'s `theme_file_for()`, both of which resolve a theme name
to a filename by literal, regular substitution. Keeping the mapping regular
for every theme (present and future) was judged more valuable than matching
one filename in a tree diagram; recorded here so it isn't "fixed" back to
the irregular form later. A test
(`test_institutional_theme_file_uses_regular_naming`) pins the chosen name
and asserts the spec's literal name does *not* exist, so this can't drift
silently either way.

### Config, CLI, and build-script plumbing

- `config.py`: new top-level `theme:` section (spec §3's optional
  `font_family`/`font_path`/`font_policy`), a `resolve_theme()` alongside
  `resolve_document()`/`resolve_validation()`, and
  `theme_font_policy_conflict()` — the same "validate and fail rather than
  silently degrade" shape as `theme_engine_conflict()`, because an
  unrecognized `font_policy` value would otherwise silently take the
  `\ifdefstring` fallback branch in the `.sty` file regardless of what was
  requested. Checked in the same two places as the engine conflict:
  `reportkit check` (`cli.py`) and `reportkit build`
  (`publication_build.py`), before any compiler runs.
- `context.py`: `reportkit context` now also reports `theme_config`
  (`font_family`/`font_path`/`font_policy`), separate from
  `document.theme` (the theme *name*).
- **Known, deliberate gap, carried over from Step 1 rather than closed
  here:** neither `document.theme` (Step 1) nor `theme.font_family`/etc.
  (this step) are wired into the actual `\documentclass[...]{reportkit}`
  options or preamble of anything `publication_build.py` compiles —
  `publication_pipeline/templates/publication-template.tex` still hardcodes
  `\documentclass{reportkit}` with no options, copied verbatim (not
  templated) into every build. Every place that *does* select a theme today
  (`latex_templates/examples/*/report.tex`) sets it directly in the `.tex`
  source, the same way it already sets `\setreportkitleftheader` etc. — not
  through the markdown-driven pipeline. `theme:`/`document.theme` therefore
  exist for validation and `reportkit context`/`reportkit check` today, not
  yet for pipeline-driven theme selection. Closing this gap, if it's ever
  needed, is unstarted follow-up outside this five-step sequence, not a
  Step 2 requirement — the spec's own Definition of Done example (§28) is a
  raw `.tex` file using class options directly, which already works.

### Verification actually performed

- `python3 -m pytest tests publication_pipeline/tests -q`: 32 passed, 18
  skipped (skips are TeX/PyMuPDF-adjacent fixtures this environment can't
  exercise; `pymupdf`, `matplotlib`, `numpy`, `pandas` were installed via
  pip specifically to run the suite fully rather than skip it wholesale).
  10 of the 32 passes are new to this step.
- `python3 -c "import reportkit.cli"`, `./reportkit context --json`,
  `./reportkit check` — CLI still loads and runs; `context`'s
  `class_version` correctly reads `1.7.0` back out of the updated
  `reportkit.cls`, confirming the class file itself parses as valid text
  the registry generator expects (not a substitute for a LaTeX parse).
- `reportkit_viz.theme_file_for("institutional-research")` resolves to the
  new file and `validate_palette_against_latex()` against it fails exactly
  as OQ2's resolution predicted (Ink/Muted/Hairline/LinkBlue/MetricAccent
  all mismatch the *default* Python palette) — pinned by a new test so this
  known, honest failure doesn't get "fixed" by accident before Step 4
  actually adds a per-theme Python palette.
- Brace-balance check (see "Environment constraint" above) on every
  changed/new `.sty`/`.cls` file.
- **Not performed, and should be before merging:** an actual `lualatex`
  compile of a minimal institutional-research document — with and without
  Google Sans present, to exercise both the `font_policy: strict` failure
  path and the `fallback` warning path — plus a compile of every existing
  `theme=default` acceptance fixture to confirm `reportkit-boxes.sty`'s new
  `\ifdefstring` branch really does leave default-theme output unchanged
  under a real TeX engine, not just under the text-level test added here.

## Step 3 — Equity publication profile (this change)

Scope per spec §27: "front page, rating strip, sidebar, what-changed,
exhibit, valuation/model and risk/reward composition primitives." Not in
scope: `reportkit_viz.py` theme-awareness or chart generation (Step 4 — the
risk/reward primitive explicitly defers its chart to that), and the
equity-research example fixture (Step 5).

**Same environment constraint as Steps 1–2:** no TeX Live, no compile
verification. The same mitigations apply (brace-balance check, pattern
cross-checks against known-working code), plus one additional, deliberate
risk-reduction: **`\dimexpr` arithmetic on `\linewidth` was avoided
entirely.** `exhibitgrid`'s pane widths (spec §12) use literal fraction
constants (`0.485\linewidth` for two columns, `0.313\linewidth` for three,
matching Appendix A's own two-up ratio) selected via `\ifcase`, rather than
a computed `(\linewidth - gutters)/columns` expression — that kind of
arithmetic is exactly where a compile-blind change is most likely to hide a
subtle bug (operator precedence, a missing `\relax`, dimension-vs-integer
coercion). `columns=4+` or a non-uniform split needs an explicit `width=` on
every `\exhibitpane` instead of a computed default.

### What was added

New `latex_templates/publication_types/reportkit-equity-research.sty`,
loaded by `reportkit.cls` when `\documentclass[publication-type=
equity-research]{reportkit}` is used (spec §2's target tree names this file
`reportkit-equity-research.sty` — the identifier `equity-research` and the
regular `reportkit-\rk@publicationtype` substitution `reportkit.cls` already
uses for theme lookup happen to produce exactly that name, so no filename
special-case was needed here the way the institutional theme's Step 2
filename needed one).

**Architectural guard, not just documentation.** Every equity-research
primitive is built on the twelve `\rk...size` type-scale tokens Step 2
exposed but left unused — meaning `publication-type=equity-research` today
only actually works with `theme=institutional-research`, even though the
architecture (spec §1) is designed so a publication type and a theme can
vary independently. Rather than silently producing "Undefined control
sequence `\rkheadlinesize`" the first time a document uses e.g.
`\researchheadline` under `theme=default`, `reportkit-equity-research.sty`
checks `\@ifundefined{rkheadlinesize}` at *load* time and raises a clear
`\PackageError` naming the actual requirement. This is new, not something
spec §27 asked for by name, but it follows directly from the same
"validate and fail rather than silently degrade" principle OQ1 established
in Step 1 — applied here at the TeX level (like the institutional theme's
own `\ifPDFTeX` guard) rather than as a new Python-side config check,
because the dependency is a fact about which macros a `.sty` file defines,
not something `publication.yaml` can express more precisely than "these two
options are used together."

Primitives, grouped by spec section:

- **§7 front page / two-column body.** `researchfrontpage` (masthead
  wrapper), `\researchkicker`/`\researchheadline`/`\researchdeck`.
  `researchmain`/`researchsidebar` realize the ~68/4/28 split as two
  `\hfill`-separated, fixed-width (`0.68\linewidth`/`0.28\linewidth`)
  sibling minipage environments — not one wrapper containing both, matching
  the spec's own example where they appear as siblings, not nested. This
  requires `\end{researchmain}` and `\begin{researchsidebar}` to have no
  blank line between them in the source (a blank line starts a new
  paragraph and breaks the minipage adjacency) — documented inline in the
  `.sty` file since `SKILL.md` guidance is Step 5's job, not this step's.
- **§8 sidebar.** `analystblock`/`marketdatablock`/`estimatesblock` (quiet
  typographic contexts, hairline-separated) plus shared
  `\sidebarlabel`/`\sidebarvalue`/`\sidebarrow` helpers — the spec names
  three block *environments* but doesn't specify an internal row API beyond
  its own bare `...` placeholder, so the row helpers are this file's own
  design, reused across all three blocks rather than invented per-block.
- **§9 rating strip.** `ratingstrip`/`\ratingitem` — hairline top/bottom
  rules, thin `\vrule` separators between items (not a tabularx `|` column
  rule, to avoid depending on `xcolor`'s `[table]` option, which core
  doesn't load), one shared `\rkratingvaluesize` for every item so price
  target isn't a giant KPI. Accent coloring of the value text is left to
  the caller (`\ratingitem{Rating}{\color{Accent}Overweight}`), per §9's
  "recommendation text *may* use accent."
- **§10 what's changed.** `whatschanged`/`\change` — accent label, hairline
  top/bottom, `$\to$` (kernel math, not `textcomp`'s `\textrightarrow`,
  which isn't loaded) for the From/To arrow.
- **§11 exhibit system.** `exhibit[number=,title=,source=,label=]` via
  `pgfkeys`, matching the exact family-declaration idiom
  `reportkit-diagrams.sty` already uses five times elsewhere in this
  codebase (`/reportkit/<name>/.is family` + reset-every-invocation
  defaults) — the lowest-risk choice available, since it's a proven pattern
  in this exact codebase rather than a new dependency. Auto-numbered via
  `\refstepcounter{rkexhibit}` so `\label`/`\ref` work normally;
  `number=` overrides the *displayed* number without disturbing the
  counter other exhibits still auto-increment from (for a combined
  publication that numbers exhibits itself across independently-built
  sections). A missing `title=` produces a `\PackageWarningNoLine`, not a
  silent empty heading.
- **§12 exhibit compositions.** `fullwidthexhibit`, `exhibitgrid[columns=N]`
  (N=1/2/3 computed; N=4+ needs explicit `width=` per pane — see above),
  and `exhibitpair` as `exhibitgrid[columns=2]` under another name (calling
  `\exhibitgrid`/`\endexhibitgrid` directly — the control sequences
  `\NewDocumentEnvironment` itself defines — rather than duplicating the
  environment). "1 dominant + 2 supporting" and "2 exhibits + full-width
  table" (spec §12's other two supported layouts) are documented as
  *compositions* of `fullwidthexhibit`/`exhibitpair`/a plain `exhibit`
  containing a table, not built as separate environments — the spec's own
  "avoid generic dashboard grids" instruction argues against adding a third
  layout primitive for a shape that's already expressible by sequencing the
  first two.
- **§16 table grammar.** `financialtable` is one generic typographic
  context (institutional font/arraystretch/`siunitx` table-format), plus
  `Y`/`Z`/`C` tabularx column types matching Appendix A's convention — not
  six named table environments (financial-summary/estimate-revisions/
  valuation/sensitivity/scenario-analysis/financial-model, per §16's list).
  Building six fixed column layouts without the real fixture data Step 5
  will introduce risks shipping tables shaped for no actual publication;
  the shared grammar is the part of §16 that's the same across all six
  regardless of what Step 5's fixture turns out to need.
- **§17 dense model mode.** `financialmodelpage` locally (via the implicit
  group `\begin{}...\end{}` already provides — no explicit `\begingroup`
  needed) drops to 7.6pt/9pt table type and tighter `\arraystretch`, while
  everything outside the environment is unaffected. True landscape page
  rotation is deliberately not implemented — see the file's own comment for
  why (another `\newgeometry`/page-rotation feature this session can't
  verify); a page that needs it can wrap `financialmodelpage` in
  `pdflscape`'s `landscape` environment itself.
- **§18 risk/reward.** No `\riskrewardchart` LaTeX-side chart-drawing
  macro: spec §18 itself prefers generating the chart "through
  reportkit_viz.py" (Step 4), and drawing it here in raw TikZ/pgfplots
  would be exactly the "bespoke chart styling" spec §28's Definition of
  Done rules out — so the chart is just a Step-4-generated image dropped
  into an ordinary `exhibit`. What this step *does* add: `\rksubheading`
  (generic accent-kicker heading, reused for Investment Thesis/Key
  Debates/Catalysts/Risks rather than four separate named macros for
  section titles the spec itself only offers as examples, not a fixed
  enum) and `\bullcase`/`\basecase`/`\bearcase` (specifically because Bull/
  Base/Bear *is* a fixed triad in §18, unlike the sidebar's example
  headings) mapped to `SeriesGold`/`Accent`/`BearRed` — matching Appendix
  A's actual bull=gold/base=teal/bear=red convention exactly (not the
  `BullGreen` token Step 2 defined speculatively and left unused here; that
  color name turned out to describe the wrong scenario once this step
  needed the real one). The page composition (thesis/debates column beside
  chart/scenario column) reuses `researchmain`/`researchsidebar` rather
  than inventing a second ~68/28 split under a new name, since Appendix A's
  risk/reward page uses the identical ratio as its front page.

### Config, CLI, and build-script plumbing

Every place that flattens `latex_templates/themes/*.sty` for TEXINPUTS or a
build's template manifest (Step 1's list) now also covers
`latex_templates/publication_types/*.sty`: `tests/conftest.py`'s
`compile_doc` fixture (which also gained a `class_options=` parameter so a
future compile-based test can actually select
`theme=institutional-research,publication-type=equity-research` — unused by
any test yet, since none can run without TeX, but the hook is there),
`scripts/acceptance_check.sh`'s flatten-copy, and
`publication_pipeline/scripts/publication_build.py`'s `template_files()`.
`shell_scripts/bootstrap.sh`'s `LATEX_REQUIRED` baseline list is
deliberately *not* extended, the same call Step 2 made for the institutional
theme file: that list is the minimum "new consumer project" bootstrap set
(`theme=default`, `publication-type=technical-report`), not an exhaustive
copy of every optional theme/publication-type file.

No `config.py`/`cli.py`/`context.py` changes were needed this step — Step
1's `document.publication_type` key and its validation already exist;
`publication-type=equity-research` needed no new config-side plumbing the
way `theme:`'s `font_family`/`font_path`/`font_policy` did in Step 2.

### Verification actually performed

- `python3 -m pytest tests publication_pipeline/tests -q`: 40 passed, 18
  skipped (same TeX/PyMuPDF-adjacent skips as before). 8 of the 40 passes
  are new to this step, including one that pins every changed
  build-plumbing file actually mentions `publication_types`, one that pins
  no `\dimexpr` crept into the pane-width computation, and one confirming
  `generate_registry()`/`check_skill_drift()` (which scan
  `latex_templates/*.sty` one level deep, same as `themes/*.sty` already
  didn't reach) are unaffected by the new file sitting one directory
  deeper.
- Brace-balance check (strip `%`-comments, sum `{`/`}`, confirm depth 0) on
  the new `.sty` file and every file this step edited.
- `./reportkit context --json`, `./reportkit doctor`,
  `bash scripts/acceptance_check.sh` (no-TeX warn-and-exit-0 path) all
  still run cleanly; `context`'s `class_version` reads back `1.8.0`.
- Manually copied `latex_templates/{*.cls,*.sty,themes/*.sty,
  publication_types/*.sty}` into a scratch directory and confirmed both new
  files land there by filename, the same flattening `reportkit.cls`'s
  `\RequirePackage` resolution depends on.
- **Not performed, and should be before merging:** an actual `lualatex`
  compile of a minimal `\documentclass[theme=institutional-research,
  publication-type=equity-research]{reportkit}` document exercising every
  primitive in this file — `researchfrontpage`/`researchmain`/
  `researchsidebar` adjacency in particular, since minipage-adjacency bugs
  (an accidental blank line, a paragraph break) are exactly the class of
  defect that produces a plausible-looking but wrong page layout rather
  than a compile error, and `\vrule`'s "running dimensions" behavior in
  `\ratingitem`, which this plan is reasoning about from documented TeX
  semantics rather than an observed render.

## Step 4 — Visualization integration (this change)

Scope per spec §27: "make `reportkit_viz.py` theme-aware, remove A4
hardcoding, add Google Sans registration and eliminate serif leakage from
numeric axes/mathtext." Unlike Steps 1–3, this step's code is pure Python
with `matplotlib`/`numpy`/`pandas` installed in this session — **it is
actually executed and tested, not just pattern-matched.** Every claim below
that isn't explicitly flagged "not performed" was run and observed to
behave as described, including rendering real figures under both themes
and inspecting their resolved fonts/colors programmatically. Two sample
renders (`risk_reward_chart` under each theme) were sent to the user
directly during this step so there was something to actually look at, not
just described.

### What was added

**`python_scripts/reportkit/themes/` (new package, OQ8).** Resolves open
question 8 (theme-token import direction): `__init__.py` defines a frozen
`Theme` dataclass and `get_theme(name)`/`available_themes()`; `default.py`
and `institutional_research.py` each build and export a module-level
`THEME` constant. The dependency is one-directional
(`reportkit_viz.py → reportkit.themes`, verified — nothing in the new
package imports `reportkit_viz`) and lazy (`get_theme()` uses
`importlib.import_module()`, not an eager top-level import of both
submodules in `__init__.py`, so there's no risk of the circular-import
shape that eager submodule imports inside a package's own `__init__.py`
would create).

- `default.py` moves every one of `reportkit_viz.py`'s pre-Step-4 hardcoded
  values into a `Theme` **verbatim, not recomputed** — same hex colors,
  same `TEXT_WIDTH_IN = 156/25.4`, same absolute `FIGURE_SIZES` heights.
  Verified: `apply_theme("default")` reproduces `INK`, `TEXT_WIDTH_IN`,
  every existing `FIGURE_SIZES` entry, `mathtext.fontset`, `font.size`,
  `axes.titlesize`, and `xtick.labelsize` exactly (test
  `test_apply_theme_default_matches_pre_step4_values`).
- `institutional_research.py` builds the institutional theme's tokens:
  `latex_colors` copied 1:1 from
  `themes/reportkit-theme-institutional-research.sty`'s actual
  `\definecolor` values (not re-derived — read directly off that file,
  same as Step 2 wrote it); `TEXT_WIDTH_IN` derived from that theme's own
  geometry (215.9mm US Letter − 14mm − 14mm = 187.9mm), not an embedded
  constant unrelated to the page (spec §15's explicit ask); `sans_candidates
  = ("Google Sans", "Inter", "Noto Sans", "Arial", "DejaVu Sans")` mirroring
  the LaTeX theme's own fallback chain; `mathtext_fontset = "custom"`.
- **OQ3 (keep `wide`).** Both theme modules keep `wide` and add `dominant`
  as an alias with the identical tuple value, plus a new `half` size (sized
  for `reportkit-equity-research.sty`'s `exhibitpair`, 0.485× the theme's
  text width) — verified present and `dominant == wide` for both themes
  (`test_figure_sizes_keep_wide_and_add_dominant_and_half`).
- **OQ4 (ratio-derived heights).** `institutional_research.py`'s
  `FIGURE_SIZES` heights are computed by applying `default.py`'s own
  width:height ratios (full 0.578, wide/dominant 0.497, compact 0.415,
  square 0.790×/0.897) to the institutional theme's different text width —
  documented in that module's comments with the derivation, so a future
  theme can reuse the same ratios without recomputing them. `default.py`
  itself keeps literal absolute numbers rather than going through this
  formula, so there is zero floating-point risk to its guaranteed-stable
  output.

**`reportkit_viz.py`: `apply_theme(theme: str = "default")`.** This is the
spec §13 entry point (`rkv.apply_theme("institutional-research")`),
verified by actually calling it and inspecting the result. The
implementation choice worth recording: rather than threading a `Theme`
argument through every one of the ~20 existing chart functions (a much
larger, riskier rewrite), `apply_theme()` reassigns the same module-level
globals (`INK`, `MUTED`, `FIGURE_SIZES`, ...) those functions already read
as plain names, via `global` declarations. Because Python looks up a bare
global name at call time, not at function-definition time, every existing
chart function became theme-aware "for free" — verified by rendering a
`bar_chart` under `institutional-research` and confirming its colors match
that theme, and by round-tripping `apply_theme("institutional-research")`
→ `apply_theme("default")` and confirming state fully reverts.

**Bug found and fixed by this mechanism, not by inspection.** Actually
testing theme-switching surfaced a real latent defect:
`annotate_point(..., accent: str = PRIMARY)` and
`shade_period(..., color: str = EVIDENCE)` bound their color defaults
directly to the module globals *in the function signature*, which Python
evaluates once at function-definition (import) time — so those two
functions' default colors would have silently stayed frozen at whichever
theme was active when `reportkit_viz.py` was first imported, forever,
regardless of any later `apply_theme()` call. Fixed to resolve the default
inside the function body (`accent: str | None = None`, then
`if accent is None: accent = PRIMARY`). Grepped the rest of the file for
the same pattern (`: str = <THEME_GLOBAL>` in a signature) and found no
other instances. Regression test:
`test_annotate_point_and_shade_period_follow_theme_switches`.

**Spec §14 (mathtext serif leakage).** `apply_theme()` only sets
`mathtext.rm`/`mathtext.it`/`mathtext.bf` when the resolved theme's
`mathtext_fontset == "custom"` (institutional's) — verified both that
those keys get set to the theme's own resolved sans font under
institutional, and that switching back to `default` leaves
`mathtext.fontset == "stix"` untouched (spec's explicit ask: fix the
institutional theme's leakage without silently restyling the default
theme's existing chart output). The **mandatory regression** spec §14
lists — numeric y-ticks, categorical x-ticks, percentages, negative
values, legend, annotation, axis title, all resolving to the same font
family — is implemented as an executable pytest test
(`test_font_consistency_regression_matches_spec_section_14_checklist`),
not just a demo figure to eyeball: it renders exactly that combination and
asserts every element's `get_fontfamily()` matches. What it can't verify
is the literal rendered glyph (matplotlib's font-family config can be
correct while an actual font file still substitutes unexpectedly at
render time) — that needs Step 5's pixel-level visual regression.

**`check-theme` becomes genuinely theme-aware (closes OQ2).** Step 1
predicted, and Steps 2–3 pinned via
`test_check_theme_institutional_honestly_fails_until_step4` (deleted this
step, per its own docstring's instruction), that `check-theme --theme
institutional-research` would report every color mismatched until a real
Python-side institutional palette existed. It now does:
`validate_palette_against_latex()` gained an optional `colors` parameter
(defaulting to the current `LATEX_THEME_COLORS` global, preserving the
exact pre-Step-4 one-argument call shape for backward compatibility), and
the CLI's `check-theme` command now passes
`reportkit.themes.get_theme(args.theme).latex_colors` explicitly. Verified
end-to-end: `python3 reportkit_viz.py check-theme --theme
institutional-research` now prints "ReportKit palette synchronized" and
exits 0 (previously — and still, for any theme name with no
`reportkit.themes` module — it fails loudly with a clear message, per
OQ2's "honest failure, not a false pass" principle, extended here to
`reportkit.themes.get_theme()`'s own `ValueError` for an unregistered
theme name).

**`risk_reward_chart()` (spec §18, new function).** Spec §18 itself
prefers the risk/reward chart be "generate[d] through reportkit_viz.py"
rather than drawn as a LaTeX-side `\riskrewardchart` macro in raw
TikZ/pgfplots — Step 3's `\bullcase`/`\basecase`/`\bearcase` primitives
were written expecting exactly this. Plots a price history with three
dashed bear/base/bull reference levels, each labeled at the right edge
(matching Appendix A's exhibit exactly), reusing each theme's existing
`DATA_NEGATIVE`/`METRIC`/`DATA_WARM` color roles rather than adding
bear/base/bull-specific `Theme` fields — those three already line up with
Appendix A's actual bear=red/base=teal/bull=gold convention for the
institutional theme (verified: rendered and inspected line colors and
annotation text under both themes; added to `build_demo()`'s regression
set; two renders sent to the user directly).

### Verification actually performed

Unlike Steps 1–3, everything below was actually executed, not just
statically checked:

- `python3 -m pytest tests publication_pipeline/tests -q`: 54 passed
  (23 new to this step, across a new `tests/test_reportkit_viz_themes.py`
  and one replaced test in `test_reportkit_vnext.py`), 18 skipped
  (TeX/PyMuPDF-adjacent fixtures unrelated to this step).
- `apply_theme("default")` reproduces every pre-Step-4 hardcoded value
  exactly (colors, `TEXT_WIDTH_IN`, `FIGURE_SIZES`, `mathtext.fontset`,
  font-size rcParams) — checked by direct equality, not approximation.
- `apply_theme("institutional-research")` then `apply_theme("default")`
  round-trips correctly; an unknown theme name raises `ValueError` naming
  the two theme names that do exist.
- Rendered a `bar_chart` under both themes with numeric+categorical ticks,
  a title, a legend, and an annotation; confirmed x-tick/y-tick/title/
  legend font families all match under the institutional theme
  (spec §14's regression), and that `mathtext.rm/it/bf` equal the theme's
  resolved sans font only when `mathtext_fontset == "custom"`.
- `python3 reportkit_viz.py check-theme --theme default`,
  `--theme institutional-research`, and `--theme nonexistent` (exit 0, 0,
  2 respectively) run from the command line, not just called as functions.
- `python3 reportkit_viz.py demo --out-dir ...` runs end-to-end and
  produces a `risk_reward.{pdf,png}` pair alongside the existing demo
  figures.
- `reportkit_doctor.py`, `reportkit context --json` (`class_version`
  correctly reads `1.8.0`), and `scripts/acceptance_check.sh`'s no-TeX
  warn-and-exit-0 path all still run cleanly with the new import added to
  `reportkit_viz.py`.
- **Not performed, and cannot be from this environment:** confirming
  `sans_candidates = ("Google Sans", ...)` actually resolves to Google Sans
  on a system that has it installed (this sandbox has none of Google
  Sans/Inter/Noto Sans/Arial, so every theme's font resolution falls back
  to `DejaVu Sans` here — the fallback *mechanism* is exercised and correct,
  but not the specific font); and anything that needs an actual printed or
  rendered LaTeX page to judge (whether the institutional theme's chart
  `base_font_size` — left at the default theme's 9.0, deliberately not
  re-tuned — reads right alongside 10.7pt LaTeX body text; whether
  `risk_reward_chart`'s proportions suit a real `exhibit`-embedded width).
  Both are Step 5 fixture-and-eyeball work.

## Remaining sequence

Step 5 is not started. Per spec §27:

5. **Fixtures + QA + skill guidance** — the four-page equity-research
   example (needs OQ6 resolved first), visual regression fixtures, `SKILL.md`
   updates (including the front-page-minipage-adjacency and
   `exhibitgrid` column-count caveats Step 3's `.sty` comments carry but
   `SKILL.md` doesn't yet, and Step 4's `apply_theme(name)`/`risk_reward_chart`
   usage), and a lualatex-based acceptance fixture for the institutional
   theme and equity-research publication type (the current
   `scripts/acceptance_check.sh` is pdflatex-only and doesn't exercise
   either). This is also where the LaTeX side of Steps 1–3 finally gets a
   real compile — see each of those steps' "Not performed" notes for what
   specifically to check first.

Step 5 should get its own review-and-verify pass on a machine with TeX
Live — this plan deliberately did not attempt it in the same pass as
Step 4, and unlike Step 4, it cannot avoid the unverified-by-compilation
caveat Steps 1–3 carried: fixtures are exactly where that finally has to be
resolved.
