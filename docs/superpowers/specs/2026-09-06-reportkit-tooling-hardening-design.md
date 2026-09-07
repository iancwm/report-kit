# ReportKit Tooling Hardening

**Status:** Approved, implementation slice landed on `main` (not the
`tooling` branch named below — see `TODOS.md`'s P0-2 for why that branch is
stale). Guide content work in the companion spec is still pending.
**Last updated:** 2026-09-07

Amended 2026-09-06 — see Amendments below.

**Branch:** `tooling` (off `main`). Everything in this spec lands here.
`data-engineering-guide` rebases onto this branch to pick up new capability.

**Companion spec:** `2026-09-06-data-engineering-guide-content-design.md`
covers the manuscript half of the same review documents. Where an item is
split between the two, both halves name each other.

**Scope of this document:** All tooling work implied by three review
documents — `docs/tooling-improvement-spec-draft.md` (11 findings),
the tooling half of `docs/data-engineering-guide-publication-review.md`, and
`docs/licensing.md` (a superseded task brief, deleted 2026-09-07 — see the
[documentation-and-status-tracking-cleanup design
spec](2026-09-07-documentation-and-status-tracking-cleanup-design.md)).
It changes build scripts, `latex_templates/`,
`python_scripts/`, and repository metadata. It changes **no** manuscript
prose and **no** diagram fragment.

## Amendments

**2026-09-06 — accessibility and PDF-inspection dependency.** A re-read of
this spec against the working tree found two gaps. Both are additions; nothing
approved here was withdrawn.

1. **B7 (new).** The `diagram` environment stores `description=` and never
   reads it, so every figure's alt text is discarded at build time. The
   content spec's §D5 was written against the assumption that setting the key
   was sufficient. It is not, and no section owned that fix.
2. **B8 (new), replacing one sentence in B3.** P1-03 previously read "pursue
   tagged-PDF structure where the engine supports it ... best-effort", which
   named no mechanism, no risk, and no exit condition. Tagging on a
   TikZ-dense document is the riskiest item in the review; it now has a
   time-boxed spike and an explicit go/no-go.
3. **D6 (clarified).** PyMuPDF is named as the single PDF-inspection
   dependency, replacing the review's poppler/`pdfplumber` method, which is
   not installed on current development machines.
4. **C1 (corrected against a live build).** The spec's two C1 bugs were, as it
   warned, "provisional ledger testimony". Both were probed on current `main`
   with LuaTeX 1.22.0 and PyMuPDF 1.28.2:
   - **C1-1 no longer exists** — fixed by `1c00be3`. Downgraded from a fix to
     a regression test.
   - **C1-2 reproduces**, with the collision quantified to 0.079pt and a new
     finding: it emits no error or warning, so the existing log-grep gate is
     structurally incapable of catching it.

   Everything in C1 is now grounded in a reproduced build rather than
   testimony. C2 and B6 remain unprobed and keep their original status.

## The finding that shapes this spec

Most of the publication review's "P0 release blockers" are not defects in the
Data Engineering Guide. They are capabilities `reportkit.cls` does not have.
The class is `article`-based (`reportkit.cls:7`) with no table-of-contents
styling, no front-matter/page-numbering model, no page-break-before-section,
and no PDF metadata plumbing beyond the link colours at `reportkit.cls:62`.

Two consequences follow, and they set the shape of the whole spec:

1. Fixing these in the guide would produce guide-local LaTeX that every future
   ReportKit long-form document has to reinvent. They belong in the class.
2. The guide's build harness already hand-rolls what the class should
   provide. The ~90-line Pandoc compatibility preamble is duplicated verbatim
   in `build-section.sh:37-112` and `combine.sh:32-96` — a duplication the
   comments in both files openly acknowledge and justify only by the absence
   of a shared home for it.

So: give ReportKit the long-form capability, and let the guide become an
ordinary consumer of it.

## Goals

1. Make bad layout and incomplete builds fail the build, rather than being
   discovered by a human reading a 56-page PDF.
2. Give ReportKit the long-form document capability the publication review
   requires, once, in `latex_templates/`.
3. Remove the harness duplication and the undeclared local dependencies that
   make the build unreproducible.
4. Fix the visual grammar defects the guide currently works around, and add
   the primitives the content backlog needs but the grammar lacks.
5. Establish the licensing model in machine-readable form and inject it into
   generated publications.

## Non-goals

- Any change to `manuscript/`, `fragments/`, or `publication-guidelines.md`.
  Those are the content spec's territory.
- Rewriting the build system, upgrading dependencies, or adding hosted CI as
  a precondition. CI is named as the eventual home for the strict gates, but
  every gate must also run locally.
- Pixel-diff regression testing. Font rendering varies by platform; the
  review's own guidance is to reserve pixel diffs for a pinned environment.

---

## A. Build correctness gate

*Source: draft findings 1–3. Priority: P0. Blocks nothing, unblocks trust in
every later phase.*

The retained logs from the reviewed build contain **four overfull boxes and
six `ignored error: Infinite glue shrinkage` events**, and the build reported
success anyway, because `build-section.sh:107-114` checks only `pdflatex`'s
exit status. One of those overfull boxes is the clipped S3 URI the
publication review independently found by eye on page 16.

### A1. Strict log gate

Add `data_engineering_guide/scripts/check-build-log.py`, run after TeX
compilation in both the section and combined builds. Non-zero exit for:

- TeX fatal errors (any line beginning `!`);
- undefined references or citations remaining after the final pass;
- `Overfull \hbox` at any width, and `Underfull \hbox` above an agreed
  badness threshold;
- `ignored error:` lines.

Invoke TeX with `-file-line-error` so every diagnostic carries a source
location. Benign messages go in a committed allowlist with an expiry date and
a reviewed justification — never silent suppression.

**Expect this to fail on first run.** That is the point: it converts six
known-but-invisible defects into a blocking result. The content spec's
section B fixes the two clipped paths; the allowlist absorbs the rest only
after each is individually reviewed.

### A2. Commit gate covers guide paths

`.githooks/pre-commit:9` matches only `latex_templates/` and
`python_scripts/`. Guide scripts, manuscripts, and fragments pass through
ungated. Add a `data_engineering_guide/{scripts,manuscript,fragments}/` arm
that runs the fast static validator (D2) plus the affected section's build.

### A3. One canonical full-document build

`build-all.sh:6-8` covers sections 01–09 while `manuscript/order.txt` lists
00 through 11 — the build-all path has never produced the actual book.
`combine.sh` does, and it is the correct source of truth. Make it explicit:
`combine.sh` is the release build, driven entirely by `order.txt`, gated by
A1, emitting the manifest from D4. Isolated per-section builds remain, but as
an author-feedback loop, not a release artifact.

---

## B. ReportKit long-form capability

*Source: publication review P0-01, P0-02, P0-03, P1-01, P1-03, P1-05, P1-06,
P2-01, P2-02, P2-03 — the capability half of each. Priority: P0.*

Two new tracked files under `latex_templates/`, plus targeted class changes.

### B1. `reportkit-pandoc.sty` — the deduplication

Move the ~90-line Pandoc compatibility preamble into one tracked file:
`\tightlist`, `emergencystretch`/`xurl`, `hyphenat[htt]`, the
`longtable`/`booktabs`/`array`/`calc` block with its `\@noskipsec` patch and
`footnotehyper` save-notes wiring, and the full `Shaded`/`Highlighting`
environment plus per-token colour macros.

Both `build-section.sh` and `combine.sh` then reduce their heredocs to
`\usepackage{reportkit-pandoc}`. This directly closes draft finding 5, whose
root cause the workflow ledger records precisely: each compatibility gap was
discovered sequentially, in production, because nothing owned the layer.

Two refinements while it is being centralised:

- Gate the `longtable` block on document content rather than loading it
  unconditionally. The unconditional load is what produces the microtype
  footnote warning in table-free sections (e.g. `01-introduction/harness.log:1000`).
- Pin the Pandoc version the block corresponds to, and add fixtures (D5).

### B2. `reportkit-longform.sty` — the book capability

| Review item | Capability |
|---|---|
| P0-01 | `\tableofcontents` styling consistent with the class's type scale; front matter in roman numerals switching to arabic at section 1; clickable entries agreeing with the PDF outline |
| P0-02, P1-05 | `\clearpage` before every H1, with `\sectionmark` corrected so `\leftmark` (used at `reportkit.cls:83`) never names a section that has not started |
| P0-03 | A breakable path/URL macro — `\allowbreak` at `/`, `=`, `_` — as the supported way to typeset a long URI, replacing bare `\texttt` |
| P1-01 | `longtable` header repetition on continuation, caption kept with header and first rows, `tabularx` fixed-width column support |
| P1-06 | A `samepage`/minipage wrapper for short listings, and a continuation marker for unavoidable splits |
| P2-01 | A section-opener treatment that gives the recovered whitespace a purpose |
| P2-03 | A title-page/cover treatment distinct from `\maketitle`'s current running-header-bearing page |

### B3. `reportkit.cls` metadata

Extend the existing `\hypersetup` at `reportkit.cls:62` with `pdftitle`,
`pdfauthor`, `pdfsubject`, `pdfkeywords`, and `pdfdisplaydoctitle`, fed from
the same `\setreportkit*` commands already defined at `reportkit.cls:72-77`.
Declare document language. Populated metadata and preserved bookmarks are
hard requirements and land here. Figure alt text is also a hard requirement
but is not free today — see B7. Tagged-PDF structure is deliberately *not*
promised by this section; B8 replaces the earlier "best-effort where the
engine supports it" wording with an explicit spike and a go/no-go.

### B4. Contrast audit

P2-02. Check the `Muted` header/footer colour (`reportkit.cls:44`) and the
syntax-highlighting palette against contrast requirements and a grayscale
proof. Keep syntax highlighting redundant with typography so no meaning is
carried by hue alone.

### B5. Release identity out of the build script

P0-04, capability half. `combine.sh`'s heredoc hardcodes
`\setreportkitversion{draft}` and the title/author strings directly in the
generated `.tex` (`combine.sh:26-31`) — there is no way to set a release
version or cover without editing a tracked script. Add a config point
(command-line argument, environment variable, or a small metadata file
`combine.sh` reads) for version string, title, author, and an optional cover
PDF path to prepend via `\includepdf` or equivalent. The content spec's
section A supplies the actual values; this item supplies the place to put
them without editing `combine.sh` per release.

### B6. Diagram width and label-size defaults

P1-02, capability half. `rk node`'s width (28mm) and per-primitive label
font sizes are hardcoded shared-style defaults in `reportkit-diagrams.sty`
(e.g. `rk node/.style` at `reportkit-diagrams.sty:22-25`, `\RKLaneNode` at
`:150`, `\RKCycleNode` at `:219`), not fragment-level options. This is why
the guide's narrow vertical figures (review P1-02) can only be widened today
by a per-node override at each call site, the same class of workaround as
the two C1 bugs. Add a diagram-level `width=` or `scale=` key to the
`diagram` environment (`reportkit-diagrams.sty:65`) that authors can set once
per figure to stretch a flow, cycle, or architecture diagram toward full text
width, rather than overriding every node individually. The content spec's
section D1 (recompose the nine existing figures) consumes this option; it
does not need to invent per-node overrides once it exists.

### B7. Figure alt text reaches the PDF

*Added by amendment 2026-09-06 (see Amendments). P1-03, capability half.
Priority: P0 for the accessibility claim — it invalidates an assumption the
content spec is already written against.*

The `diagram` environment accepts a `description=` key and stores it in
`\rk@diagramdescription` (`reportkit-diagrams.sty:54`, `:64`). Nothing ever
reads it. The environment body (`reportkit-diagrams.sty:71-99`) emits the
tikzpicture, the caption, and the source line, and returns; `\rk@diagramtype`
is stored and unread in the same way.

The consequence is that **every alt text written so far has been discarded at
build time.** All fourteen tracked fragments set `description=`, the
guidelines mandate it (`publication-guidelines.md:377-390`), and content spec
§D5 lists it as a per-figure requirement — and none of it reaches a reader
using a screen reader. This is not a gap in the manuscript; the manuscript is
correct. The pipeline drops its input.

Emit the stored description as a text alternative on the figure. The
mechanism should be the smallest one that survives the C2 primitives and the
B6 width key:

- `accsupp`'s `\BeginAccSupp{ActualText=...}` / `\EndAccSupp` around the
  figure is the low-risk option and works on every engine already in use;
- if B8 returns a go, the tagging structure supplies the alt text instead and
  this becomes the fallback path rather than the primary one.

**Verified trade-off (probe run 2026-09-06, LuaTeX 1.22.0 + PyMuPDF 1.28.2).**
An `/ActualText` span does not *add* a text alternative — it **replaces** the
extractable text of everything it wraps. A probe wrapping a two-step
`reportflow` extracted as `ZZALTTEXT a chain of two stages` with the node
labels `Source` and `Ingest` no longer recoverable. So B7 buys screen-reader
alt text at the cost of copy-paste and search of label text inside diagrams —
which matters here because guide figures carry literal identifiers such as
`\rkcode{event_date}`.

That is the correct trade for a diagram (a reader hearing
"SourceIngestStoreServe" is worse served than one hearing the description),
and it is why B7 is explicitly interim. Only tagging gives both: a `/Figure`
structure element carries `/Alt` while leaving inner text extractable. If B8
returns a go, take that path and drop the `ActualText` wrapper.

**Implementation note.** Wrap the *saved box*, not the tikzpicture's
interior. A probe injecting the marked-content literal inside the picture
produced a correctly embedded `/ActualText` but unreliable text handling. B6
already introduces an `lrbox` around the figure for its `width=` key; B7
should reuse that same box so the wrapper sits at a clean box boundary. B6 and
B7 therefore share one structural change and should land together.

Either way `description=` becomes load-bearing: an empty or missing
`description` on a `diagram` must warn, and — once the guide's fragments are
known to be complete — fail the build under the strict mode of F1. Do the
same for `type=` or delete the key; a stored-and-unread option is a trap for
the next author.

**Acceptance:** a fixture figure with a known `description` string exposes
that string as the figure's text alternative in the built PDF, verified
programmatically rather than by eye; a `diagram` with no `description`
produces a diagnostic.

### B8. PDF accessibility — tagging spike and go/no-go

*Added by amendment 2026-09-06 (see Amendments). P1-03, the half B3 no longer
promises. Priority: P1, time-boxed.*

The review's P1-03 acceptance check asks for "tagged headings and reading
order, figures expose alt text, links have meaningful labels". Three of those
four are ordinary work and are already assigned: metadata and bookmarks to
B3, alt text to B7, link labels to the content spec's §E1. Tagged structure
and reading order are the outstanding item, and they carry real risk that the
original one-sentence treatment hid.

Tagging in current LaTeX means `\DocumentMetadata{testphase=...}` on
LuaLaTeX. This guide is TikZ-dense by construction — every one of its figures
is a tikzpicture emitted by a ReportKit primitive — and the tagging phases
have a documented history of interacting badly with heavy TikZ and with
`tcolorbox`-style callouts, both of which this class uses
(`reportkit-boxes.sty`). Committing the release to tagging before testing
that interaction would put the whole publication behind an unproven
dependency.

**Method.** Time-box a spike. Build one TikZ-dense section — Section 3 or
Section 5, whichever carries more figures at the time — under
`\DocumentMetadata{testphase=phase-III}` on LuaLaTeX, with the C2 primitives
and the B6 width key in place. Record: whether it compiles, whether figures
and callouts survive, whether the structure produced is actually useful to a
checker, and what it costs in build time.

**Go:** tagging becomes a B-series requirement with its own acceptance
criteria, and B7's `accsupp` path becomes the fallback.

**No-go:** tagging is dropped from this release and recorded as a known
limitation in the release gate, with the spike's evidence attached so the
decision is reviewable rather than re-litigated. The hard requirements —
metadata, language, bookmarks, alt text, link labels — ship regardless, and
they are what the release gate checks.

Either outcome is a success for this section. The failure mode it exists to
prevent is discovering the TikZ interaction late, with figures written and a
release date fixed.

**Acceptance:** a written go/no-go decision, with the spike's build log and
page renders as evidence, committed alongside this spec. Not "tagging works".

---

## C. Visual grammar fixes and new primitives

*Source: draft finding 9, plus the two upstream bugs documented in
`data_engineering_guide/README.md:53-77`, plus the primitive gap implied by
publication review P1-07. Priority: P0 — **this section blocks the content
spec's figure programme**.*

### C1. Fix the two documented defects

Both are currently worked around inside guide fragments, which is exactly
backwards — the guide's own README tells future maintainers not to fix them.

1. ~~**`reportflow`'s `direction=vertical` is silently ignored.**~~
   **Already fixed — do not re-fix.** *(Amendment 2026-09-06.)* The spec was
   written against pre-`1c00be3` code. That commit changed
   `reportkit-process.sty:30` from `\ifstrequal{\rk@flowdirection}{vertical}`
   to `\expandafter\ifstrequal\expandafter{\rk@flowdirection}{vertical}`,
   which resolves correctly. A probe on current `main` renders a three-step
   vertical flow at constant x (~285pt) with y stepping 84 → 170 → 257pt.
   The remaining work is to **lock the fix in with a regression test**, and to
   retire the now-unnecessary `\RKNode` workaround in
   `fragments/fig-sec01-lifecycle.tex` (a content-branch change).
2. **`reportnetwork`'s default grid spacing collides with `rk node`'s
   rendered width** on a horizontal chain, breaking pgf's border-clipping
   maths and reversing arrowheads. Workaround in
   `fragments/fig-sec07-lineage.tex` is a per-node `text width=24mm`.

   **Reproduced and quantified 2026-09-06.** `rk node` is
   `text width=28mm` + `inner xsep=5pt` either side =
   **89.370pt**; the grid step at `reportkit-process.sty:117` is 3.15cm =
   **89.291pt**. Nodes are 0.079pt *wider* than their spacing, so adjacent
   nodes abut with negative clearance. A four-node chain renders as one fused
   bar with no gaps and every arrowhead pointing backwards — declared
   `n1→n2`, drawn `n1←n2`.

   **This bug produces no TeX error and no warning: the probe exited 0 with a
   clean log.** A log-grepping gate like `scripts/acceptance_check.sh` cannot
   catch it, which is the argument for the geometry-assertion test layer this
   section's fix must introduce.

**Method, per the draft's finding 9:** add the failing case to
`latex_templates/examples/visual_grammar_acceptance_test.tex` *first*,
confirm it reproduces, then change the macro. The draft explicitly flags its
own root-cause analysis as provisional ledger testimony rather than
reproduced fact, so the regression test is what establishes it. Remove the
guide-side workarounds only after the visual gate passes — and note that
removal is a **content-branch** change, coordinated with the content spec.

### C2. New primitives

The publication review asks for varied visual grammar — "timelines for time,
state diagrams for retries and recovery, physical layouts for files and
partitions, before/after diagrams for cardinality" — and explicitly warns:
*"Do not turn every figure into a vertical box-and-arrow flow."*

The current inventory is `reportflow`, `reportswimlane`, `reportnetwork`,
`causalloop`, `reportcycle`, `reportfunnel`, `evidencestack`,
`reportarchitecture`, `reportroadmap` (horizons/dated), `strategicpillars`,
`maturitymodel`, `continuum`, `capabilitymap`, `reporttree`, `reportmatrix`,
`riskheatmap`. Three required forms have no primitive:

| Primitive | Needed by (content spec section D) | Requirement |
|---|---|---|
| **State machine** | Tier 1 task recovery | Self-loops (retry), terminal-state styling, labelled transitions |
| **Before/after pair** | Tier 1 join cardinality; Tier 2 small-file compaction, row vs column | Two aligned panels with a transform arrow, per-panel captions |
| **Two-track event timeline** | Tier 1 event vs processing time | Two parallel time axes, skew arrows, watermark marker, late-arrival events |

Partition pruning (Tier 1) and the partition directory layout can likely be
composed from the existing `reporttree`; confirm during implementation rather
than adding a fourth primitive speculatively. The backpressure rate/queue plot
(Tier 2) is measured-value geometry and belongs to `reportkit_viz.py`, not the
diagram grammar.

Each new primitive follows the established contract: a semantic environment
with declaration-order reading order, authors controlling links rather than
coordinates, a case in the visual grammar acceptance test, and an entry in
`SKILL.md`'s question-to-primitive table.

---

## D. Reproducibility and observability

*Source: draft findings 4–8. Priority: P1.*

### D1. Declared, locked toolchain

`build-section.sh:113-114` requires `build/.venv/bin/python`;
`render_pdf_pages.py:11` imports PyMuPDF; the venv is gitignored
(`.gitignore:11`); its `pyvenv.cfg` records only Python 3.12.3; no dependency
declaration or lockfile exists anywhere. A clean clone cannot build.

Track a locked guide tooling environment (`requirements.txt` plus
constraints, or `pyproject.toml` plus lockfile) and a setup command that
creates the venv. Print Python, PyMuPDF, Pandoc, and TeX versions at build
start so every log identifies its own toolchain.

### D2. Static validation before TeX

`render-visuals.sh:36-43` detects a missing fragment only when a sentinel
matches exactly, and only while rendering. It cannot report orphan fragments,
duplicate labels or slugs, unsupported sentinel spellings, or a count
mismatch.

Add `validate-guide.py`: read `order.txt`, confirm every listed input exists,
validate sentinel syntax, enforce a one-to-one sentinel ↔ fragment ↔ label
mapping, and reject orphans and duplicates — all before TeX runs. This is the
fast check A2 runs in the commit hook.

### D3. Atomic page rendering

`render_pdf_pages.py:25` writes into an existing `pages/` without clearing
it, and `build-section.sh:18-20` reuses each isolated directory. If page count
falls, stale PNGs survive and a reviewer inspects a page that no longer
exists. Render to a run-unique temporary directory, validate the page count,
then replace `pages/` atomically.

### D4. Run manifest

Emit `build-report.json`: input and template hashes, tool versions, commands,
exit codes, page counts, warning counts, and the A1 gate result. Publish it
alongside the PDF and logs.

### D5. Pandoc feature fixtures

Fixture-test every supported Markdown feature — tight lists, tables, fenced
code with a recognised language, links, footnotes — through the shared
`reportkit-pandoc.sty` against the pinned Pandoc version. This is what stops
B1's centralisation from regressing the way the original sequential
discoveries did.

### D6. Visual QA becomes a result

`render_pdf_pages.py:29-34` writes images; nothing records that anyone looked
at them. Emit a contact sheet plus an index, record reviewed pages against a
build ID, and add deterministic checks for non-empty output, expected page
count, and expected figure labels.

**Including the bounding-box check** the publication review's P0-03 acceptance
criterion requires: no glyph outside the media box. The review found the two
clipped paths with `pdfplumber`; that check belongs in the build, not in a
reviewer's notebook.

**PyMuPDF is the single PDF-inspection dependency** *(amendment 2026-09-06)*.
The review's evidence method used `pdfinfo`, `pdffonts`, `pdftotext`, `pypdf`,
and `pdfplumber`; a check of a current development machine found **none** of
them installed — no poppler binaries and no PDF Python package — so the
review's own method is not reproducible on a fresh checkout today. PyMuPDF is
already required by `render_pdf_pages.py:11` and covers every check this spec
needs in one pip wheel: page geometry, text bounding boxes, links, bookmarks,
font metadata, document metadata, and render-to-image. Adding poppler would
introduce a system-level apt dependency for capability already present. Do not
reintroduce the poppler tools; port the review's checks onto PyMuPDF and pin
it in D1's lockfile.

---

## E. Licensing

*Source: `docs/licensing.md` in full. Priority: P1.*

The repository is GPL-3.0-or-later for source. Generated publications need a
separate content licence — CC BY 4.0 for original prose and diagrams — while
code examples, fonts, third-party assets, datasets, and templates keep their
own terms.

- `metadata/licenses.yml` — machine-readable `software_license`,
  `content_license`, `content_license_url`.
- `CONTENT-LICENSE.md` — CC BY 4.0 coverage and its exclusions.
- `THIRD-PARTY-NOTICES.md` — attribution table for assets, fonts,
  dependencies, templates, datasets. The Libertinus subset in `font_data/`
  and the `LinBiolinum_K.otf` stub are the first entries.
- `README.md` — a licence-scope table distinguishing the three categories.
- `references/licensing.md` — the model, and what contributors must supply
  for a new asset.
- Build pipeline — read and validate the metadata, inject a rights notice
  into generated publications (or a clearly linked sidecar), fail with a clear
  error when required metadata is missing, and never apply the content licence
  to code blocks or third-party assets.

The existing root `LICENSE` is not replaced or modified.

**Cross-reference:** the content spec's section A supplies the licence and
disclaimer *copy* that appears in the book's front matter. This section
supplies the metadata and the injection mechanism.

---

## F. Scale and portability

*Source: draft findings 10–11. Priority: P2. Do not start before A–D land.*

### F1. Strict modes

`acceptance_check.sh:20-24` exits zero when `pdflatex` is absent;
`reportkit_doctor.py` exits zero unless it crashes. Both are correct as
diagnostics and dangerous as gates. Add `reportkit_doctor.py --require
full-build` and `acceptance_check.sh --require-tex`, and require strict mode
for release builds and any future CI job.

### F2. Measure before optimising

`build-all.sh:6-8` is serial; each section re-copies every template
(`build-section.sh:25`), runs TeX twice, and rasterises every page at 150 DPI.
The draft's finding 10 is explicitly a hypothesis, not a measurement.
Establish a baseline first. Only then consider input-hash incremental builds
and bounded parallel workers with deterministic aggregate reporting.

---

## File layout introduced

```
latex_templates/
  reportkit-pandoc.sty                      (new — replaces two heredocs)
  reportkit-longform.sty                    (new — TOC, front matter, breaks)
  reportkit.cls                             (modified — PDF metadata, language)
  reportkit-process.sty                     (modified — C1 fixes)
  reportkit-diagrams.sty  or a new module   (modified/new — C2 primitives,
                                             B6 width key, B7 alt-text emission)
  examples/
    visual_grammar_acceptance_test.tex      (modified — C1 + C2 cases)
    longform_acceptance_test.tex            (new — B2 capability)
    accessibility_acceptance_test.tex       (new — B7 alt text, B8 spike input)
data_engineering_guide/
  scripts/
    check-build-log.py                      (new — A1)
    validate-guide.py                       (new — D2)
    build-section.sh, combine.sh            (modified — B1, A1, A3, D3)
    render_pdf_pages.py                     (modified — D3)
  fixtures/                                 (new — D5 + a minimal manuscript)
  requirements.txt + constraints            (new — D1)
metadata/licenses.yml                       (new — E)
CONTENT-LICENSE.md, THIRD-PARTY-NOTICES.md  (new — E)
references/licensing.md                     (new — E)
.githooks/pre-commit                        (modified — A2)
scripts/acceptance_check.sh                 (modified — F1)
python_scripts/reportkit_doctor.py          (modified — F1)
```

`data_engineering_guide/fixtures/` matters more than its size suggests. The
`tooling` branch has no manuscript — that is the whole point of the split — so
without a minimal fixture manuscript, `build-all.sh` has no input on this
branch and the A1 gate cannot be exercised where it is developed.

## Sequencing

```
A (correctness gate)  ──┐
B (longform class)    ──┼──> D (reproducibility) ──> F (scale)
C (visual grammar)    ──┘
E (licensing) — independent, any time after A

C blocks content spec section D (the figure programme).
B blocks content spec sections A and C.
B7 blocks content spec section D5's alt-text acceptance.
B8 runs after B6 + C2 land; its outcome gates nothing else.
```

B7 is small but sits on the critical path for the accessibility claim: until
it lands, content spec §D5 can be fully satisfied on paper while the built
PDF exposes no alt text at all. Sequence it with B3 rather than after C.

## Acceptance criteria

- `check-build-log.py` returns non-zero on the current retained logs, and
  zero after the four overfull boxes are fixed or explicitly allowlisted with
  a dated justification.
- The Pandoc preamble exists in exactly one tracked file; neither
  `build-section.sh` nor `combine.sh` contains a token-colour macro.
- The long-form acceptance test produces a document with a contents page whose
  page numbers match the PDF, every H1 at the top of a fresh page, and no
  running header naming a section that has not begun.
- The visual grammar acceptance test contains a vertical `reportflow` and a
  horizontal `reportnetwork` chain, both rendering correctly without
  `\RKNode` workarounds.
- Each of the three new primitives renders in the acceptance test and appears
  in `SKILL.md`'s primitive table.
- `combine.sh` accepts a version/title/author/cover configuration without
  requiring an edit to the tracked script, and the `diagram` environment
  accepts a `width=`/`scale=` key that stretches a figure without a per-node
  override.
- `validate-guide.py` rejects, in unit tests: a missing fragment, an orphan
  fragment, a duplicate slug, a duplicate label, an invalid sentinel case, and
  a missing `order.txt` entry.
- A clean clone with no pre-existing venv builds the guide end to end.
- A deliberately shortened fixture rebuild leaves no stale PNG.
- A long `s3://` fixture is rejected by the bounding-box check before the
  breakable-path macro is applied, and passes after.
- `build-report.json` is emitted by every build and records the gate result.
- A fixture figure's `description=` string is recoverable from the built PDF
  as that figure's text alternative, and a `diagram` with no `description`
  produces a diagnostic (B7).
- No build step or documented workflow invokes `pdfinfo`, `pdffonts`,
  `pdftotext`, `pdfplumber`, or `pypdf`; PyMuPDF is pinned in the lockfile and
  is the only PDF-inspection dependency (D6).
- A written tagging go/no-go decision exists with its spike evidence
  committed; if no-go, the release gate names untagged structure as a known
  limitation (B8).
- The build fails with a clear message when `metadata/licenses.yml` is absent
  or incomplete, and the generated PDF carries a content-licence notice.
- `scripts/acceptance_check.sh --require-tex` fails on a machine without TeX.
