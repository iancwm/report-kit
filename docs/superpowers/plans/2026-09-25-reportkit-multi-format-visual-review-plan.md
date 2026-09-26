# ReportKit venture and other-format visual review plan

**Status:** Phase E editorial review complete; D/F1/F2 remain · 26 September 2026
**Spec:** [docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md](../specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md) (Phases D, E, F)
**Companion plan:** [docs/superpowers/plans/2026-09-10-reportkit-multi-format-publication-implementation-plan.md](2026-09-10-reportkit-multi-format-publication-implementation-plan.md) (§7 Phase D, §9 Phase E, §10 Phase F1/F2)
**Goal:** Close the one item all four experimental formats share — pinned-toolchain visual review with a checked-in pixel baseline — so each can flip from `stability="experimental"` to `"stable"` in `python_scripts/reportkit/publications.py`.

This plan does not redesign anything. Venture, editorial, executive-brief and
book are implemented, registered, tested and compile cleanly on an unpinned
toolchain today. What is missing is identical across all four: a render from
the repository's pinned Docker toolchain, a human looking at the pages, and a
checked-in artifact recording that the look was approved.

## 1. Current state (from TODOS.md, verified against the tree)

| Format | Publication type / theme | Fixture | Dedicated visual QA script | Checked-in pixel baseline |
| --- | --- | --- | --- | --- |
| Venture | `presentation` / `venture` | `latex_templates/examples/venture-presentation/` (12 slides) | `scripts/visual_qa_venture.py` — exists, renders PNGs, runs the executive-vs-venture smoke gate | none |
| Editorial | `feature-article` / `editorial` | `latex_templates/examples/editorial-feature/` (6 pages) | none | none |
| Executive brief | `executive-brief` / `executive`, `institutional-research` | `latex_templates/examples/executive-brief/` (3 pages × 2 themes) | none | none |
| Book | `book` / `default`, `technical`, `editorial` | `latex_templates/examples/book/` (11 pages × 2 distinct renders; technical is byte-identical to default) | none | none |

**Phase E review, 2026-09-26:** `scripts/visual_qa_editorial.py` now builds the
three figures and six-page article in the pinned image. The reviewed PNGs and
manifest are in `latex_templates/examples/editorial-feature/expected/`. The
chart PDFs embed Libertinus Sans; the full-width exhibit leaves open space on
page 4, and the short final page is accepted. Both editorial stability flags
are now `stable`. The table above is the original planning snapshot.

For contrast, the two formats that already carry a checked-in pixel baseline
(`equity-research`/`institutional-research` and the `career_guide_en`
fixture) both have an `expected/` directory containing `baseline.json`
(toolchain fingerprint, PDF SHA-256, per-page PNG list, pixel-difference
threshold), the checked-in `page-NN.png` files themselves, and a `README.md`
documenting the refresh procedure — see
`latex_templates/examples/equity-research/expected/`. That is the mechanism
this plan extends to the other four formats, per TODOS.md's explicit bar for
Phase D–F ("Promote each to stable only after that review passes on the
pinned OCI image").

Note this is a *stricter* bar than the one `presentation`/`executive` (Phase
C) actually cleared before its own promotion to stable on 2026-09-20 — that
promotion was reviewed from rendered PNGs on an unpinned host, with no
checked-in baseline directory to this day. This plan follows the bar
currently written down in TODOS.md, not the Phase C precedent; if that's
more rigor than intended, that's a one-line scope call for whoever picks
this up, not a blocker to drafting the plan.

## 2. Definition of done (applies to each format independently)

A format is promoted to stable only when all of the following are true:

1. A dedicated `scripts/visual_qa_<format>.py` exists, staging and compiling
   the format's canonical fixture(s) the same way the equity-research and
   venture scripts already do (reuse `_template_files`/`render_pages` from
   `scripts/visual_qa_executive.py` rather than re-implementing staging).
2. The script supports `--update-expected`, writing `expected/baseline.json`
   (toolchain fingerprint, PDF SHA-256, page dimensions, page PNG list) plus
   the PNGs themselves into the fixture's own `expected/` directory, matching
   `latex_templates/examples/equity-research/expected/baseline.json`'s shape.
3. The baseline was generated inside `toolchain/Dockerfile`'s pinned image
   (`docker build -f toolchain/Dockerfile -t reportkit-pinned .`), not on an
   ad hoc host — a locally-built LuaLaTeX is not proof of anything pinned CI
   will see.
4. A human reviewed the rendered pages against the format's checklist (§4
   below) and recorded that review (a dated note in this plan's history or
   the spec's own status line — follow whatever the institutional-theme
   spec's §25 review recorded as precedent) before the PNGs were committed.
5. `python_scripts/reportkit/publications.py`'s `stability` field flips from
   `"experimental"` to `"stable"` at the exact entries in §3, and the
   corresponding LaTeX registry regenerates (`reportkit docs --write` or
   whatever the repo's generator command currently is) so Python and LaTeX
   stay in sync.
6. The spec (§7/§9/§14/§16), the companion implementation plan (§7/§9/§10),
   and `TODOS.md` are updated to record the promotion and drop the item from
   open work.

A format's automated tests already passing (`tests/test_venture_theme.py`,
`tests/test_editorial_theme.py`, `tests/test_executive_brief.py`,
`tests/test_book.py`) is a precondition, not a substitute, for this review —
those tests check structure and text identity, not whether the rendered page
actually looks good.

## 3. Exact stability flags to flip

| Format | File | Line (as of this plan) | Field |
| --- | --- | --- | --- |
| Venture | `python_scripts/reportkit/publications.py` | 277 | `THEMES["venture"].stability` |
| Editorial | `python_scripts/reportkit/publications.py` | 288 | `THEMES["editorial"].stability` |
| Editorial | `python_scripts/reportkit/publications.py` | 349 | `PUBLICATION_TYPES["feature-article"].stability` |
| Executive brief | `python_scripts/reportkit/publications.py` | 332 | `PUBLICATION_TYPES["executive-brief"].stability` |
| Book | `python_scripts/reportkit/publications.py` | 368 | `PUBLICATION_TYPES["book"].stability` |

Editorial has two flags because `feature-article` is the only publication
type the `editorial` theme serves — both gate on the same one fixture review
and should flip together. Book has only one flag because `default` and
`technical` are already stable themes; the `book` publication type's own
flag is what currently holds all three theme pairs back, including the
`editorial` pair, even though the `editorial` *theme* flag above is a
separate switch used by `feature-article`. Whoever executes this should
decide explicitly whether `book`'s promotion should wait on `editorial`'s
theme-level promotion (defensible, since `book/editorial` visually depends
on the same theme file) or can proceed independently since the registry
tracks them as unrelated flags — record the decision, don't leave it
implicit.

## 4. Per-format review checklists

Base every checklist on spec §25's institutional-theme checklist (geometry,
text wrapping, alignment, exhibit/figure positioning, chart fonts, table
overflow, blank pages, overfull boxes) plus what's format-specific:

- **Venture** — `scripts/visual_qa_venture.py` already lists its own
  checklist in `manual_review`: one idea per slide with dominant display
  type and generous negative space; opening/statement/closing frames dark,
  content frames light; brand primary/secondary and logo consistent across
  slides and the chart; product image and hero metrics read as the slide's
  subject; no clipped labels, overlaps, or leaked default-theme colors. Also
  confirm the executive-vs-venture smoke gate's pixel difference is
  comfortably above `MATERIAL_DIFFERENCE_FLOOR` (6.0) on the pinned render,
  not just the unpinned one.
- **Editorial** — drop cap renders correctly at the opening page; one- and
  two-column prose rhythm has no orphan/widow columns; both pull quotes sit
  clear of body text; sidebar doesn't collide with the main column; inset,
  column-span and full-width exhibits (including the chart and the
  `reportflow` diagram) size and caption correctly; image credits are
  legible; **check whether Libertinus Sans actually resolves in chart text
  on the pinned image** — the implementation record flags that the unpinned
  host fell back to DejaVu Sans, so this is a real unresolved risk, not a
  formality; check for a partial page left by a full-width exhibit that
  doesn't fit and decide if that's acceptable authoring or needs a fixture
  fix.
- **Executive brief** — masthead/decision-metadata strip renders under both
  `executive` and `institutional-research`; action/owner/due table in
  `briefactions` doesn't overflow; exhibits/`financialtable` columns align;
  recommendation and implication (`decisionpoint`) and risks
  (`redflag`/`assumption`) are visually distinct from body prose; sources
  list formats correctly; confirm both theme renders are visually distinct
  from each other despite sharing `brief.tex`'s body.
- **Book** — part divider and imprint page render correctly; chapter
  openers are numbered and styled consistently; the lettered appendix uses
  a visibly different numbering scheme than chapters; the table/metric in
  the subsection-bearing chapter doesn't overflow; glossary and
  `\cite`-driven reference list format correctly; confirm `technical` is
  still byte-for-byte identical to `default` after adding page images
  (only capture one baseline for the alias pair, not two;
  `tests/test_book.py` already asserts this at the text level — the
  baseline should not duplicate work, just record one rendered set); for
  `editorial`, confirm running-header/footer band and chapter-opener style
  correctly diverge from `default` while chapter body content matches.

## 5. Workstreams and sequencing

Four independent workstreams, one per format — they touch disjoint files
(each format's own script, fixture `expected/` directory, and its own lines
in `publications.py`) and can run in parallel. Suggested order if done
serially, cheapest first:

1. **Venture** — smallest remaining lift. `scripts/visual_qa_venture.py`
   already exists and already renders and checks everything except writing
   a baseline; add `--update-expected` (mirror
   `scripts/visual_qa_equity_research.py`'s implementation), run it inside
   the pinned image, review, commit, flip line 277.
2. **Editorial** — write `scripts/visual_qa_editorial.py` from the venture
   script as a template (same staging/compile/render helpers, no brand
   overrides or smoke-gate diff since editorial has no sibling theme to
   diff against — its gate is the existing theme-swap test, not a pixel
   diff). Resolve the Libertinus Sans font-fallback question before
   reviewing, since it changes what "correct" looks like.
3. **Executive brief** — write `scripts/visual_qa_executive_brief.py`
   covering *both* registered themes (`executive` and
   `institutional-research`) from the one shared `brief.tex` body; two
   baselines, one per theme, not a smoke-style diff (there's no
   "shared-body-vs-modified-body" gate to run here the way venture has).
   Consider wiring the fixture into `scripts/acceptance_check.sh`'s fast
   loop while here — the F1 implementation record notes it isn't yet, and
   `brief.tex` needs to be staged alongside `report.tex` for that to work.
4. **Book** — write `scripts/visual_qa_book.py` covering `default` and
   `editorial` renders (skip a separate `technical` baseline; it's proven
   byte-identical to `default` by `tests/test_book.py`, so re-reviewing its
   pixels is redundant — note that decision in the script's docstring so
   it isn't rediscovered as a gap later). Decide the editorial-theme
   dependency question from §3 before flipping the `book` stability flag.

## 6. Open questions to resolve before or during execution

1. Does `book/editorial`'s promotion require `editorial` theme's own
   promotion first, or are they independent registry flags that can move
   on separate schedules? (§3)
2. Is Libertinus Sans available in the pinned toolchain's font search path
   for chart text, or does the editorial chart need a documented fallback
   font the way the executive fixture already does?
3. Should `executive-brief`'s fixture join `scripts/acceptance_check.sh`'s
   fast compile loop in the same pass as its visual review, or is that a
   separate follow-up (it's noted as missing in the F1 implementation
   record, not something this plan strictly needs to fix)?
4. Do all four formats get one combined pinned Docker run (cheaper, one
   `docker build`, four `docker run` invocations) or four fully separate
   PRs? Given the workstreams touch disjoint files, one PR per format,
   sharing one locally-built pinned image across all four runs, is probably
   the lower-friction choice — but that's an execution detail for whoever
   picks this up, not fixed by this plan.

## 7. What this plan does not cover

- No new visual design work — every format's tokens, primitives and
  fixtures are implemented and already reviewed by eye on an unpinned host.
  This is a promotion gate, not a redesign.
- No engine or theme changes. If the pinned render surfaces a real visual
  defect (not just "needs a second look"), fixing it is a small follow-up
  to the owning phase's own file, not part of this plan's scope — file it
  as a new dated entry rather than silently patching mid-review.
- Tagged PDF, i18n beyond what's already declared, and the deferred
  consumer-project template remain out of scope, unchanged from the spec's
  own non-goals.
