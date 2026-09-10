# ReportKit Fork Port: Verified Fixes

**Status:** Proposed — verified against `main` at `299b933`, not yet
implemented.
**Source:** a port record describing 11 changes (9 defects, 2 features) made
on another fork of this repository, commits `5d1b3c9..eaa80f9`. That range
does not exist in this repository's history — the fork diverged before this
tree's current state — so every item below was independently re-verified
against this codebase rather than assumed to transfer as-is.
**Scope of this document:** confirms which of the fork's 11 items still
describe a real defect or gap in this repository, in which form, and what to
change. It changes no manuscript prose.

## How to read this

For each item: **Evidence** is what was found in this tree (file:line, or a
command run), **Verdict** is whether the fork's fix still applies here and in
what shape, and **Fix** is the concrete change. Two items are not straight
ports — §B (swimlanes) is already fixed here by different code, and §K
(environment docs) is already covered except for one gap — both are called
out rather than silently dropped.

## Summary

| # | Area | Verdict |
|---|---|---|
| 1 | Test harness import order | Applies — reproducible import-order hazard, confirmed present in this suite and its CI invocation |
| 2 | Swimlane column math | **Does not apply** — already fixed here by different code (see §B). Test coverage gap remains. |
| 3 | Dated roadmap milestone anchoring | Applies — confirmed overlap-prone geometry, no rendering test exists |
| 4 | Pandoc figure `keepaspectratio` | Applies — global default is missing; not yet triggered by tracked content |
| 5 | Diagram label validation scope | Applies — confirmed false-positive via existing `label=` edge-option syntax |
| 6 | Publication asset staging | Applies — confirmed: `figures/`/`assets/` are never staged or added to `TEXINPUTS` |
| 7 | pandas `M`/`ME` compatibility | Applies — repo hardcodes `ME`, pandas is unpinned outside the CI lockfile |
| 8 | Bubble-matrix markers | Applies — confirmed groups differ by color only |
| 9 | Per-project license metadata | Applies as a **feature gap** — only a single global license file exists |
| 10 | License URL LaTeX-escaping | Applies — confirmed unescaped interpolation, ship with §9 |
| 11 | Environment/toolchain docs | Mostly already covered; one addition ties to §1 |

---

## A. Test harness: import order can turn a real failure into a silent skip

**Evidence.** `tests/conftest.py:9` does `import pymupdf` at module scope.
Conftest modules load before sibling test modules in a directory, so this
import happens before anything in `tests/` imports `matplotlib`/`pandas`.
`tests/test_reportkit_viz_themes.py:19-21` gates its own body on
`pytest.importorskip("matplotlib")` / `"pandas"` — if that import fails for
any reason, the test **skips**, not fails, and the suite exits 0.

The actual invocations both order `tests` ahead of
`publication_pipeline/tests`, so `tests/conftest.py` is the first thing
pytest imports in the session:
- `scripts/acceptance_check.sh:75` — `pytest "$ROOT/tests"
  "$ROOT/publication_pipeline/tests" -q`
- `.github/workflows/contract-ci.yml:38` — `python -m pytest tests
  publication_pipeline/tests -q`, run inside the pinned Docker toolchain.

`toolchain/requirements.lock` pins `pymupdf==1.28.2`, `matplotlib==3.10.6`,
`pandas==2.3.2`, `numpy==2.3.3` together — exactly the combination PyMuPDF's
manylinux wheel (which bundles its own `libmupdf`/C++ runtime) has a known
history of colliding with when a scientific-stack package that also ships
compiled extensions loads afterward, depending on the base image's system
`libstdc++`. This sandbox has neither package installed, so the collision
itself could not be reproduced here — the import-order hazard is
structural and verifiable independent of that: **whatever the failure mode,
`importorskip` converts it into a silent, exit-0 skip**, which is the
defect worth closing regardless of whether the specific libstdc++ symptom
reproduces on a given CI image.

**Fix.** In `tests/conftest.py`, import `matplotlib` and `pandas` (each
guarded, since they're optional for suites that don't need them) *before*
`import pymupdf`, so any environment-level incompatibility surfaces as an
import error in the packages that actually need to succeed, at the point
pytest can still report it — not as a downstream `importorskip` in an
unrelated test file. Equivalently, move the `pymupdf` import in
`tests/conftest.py` into the `compile_doc`/fixture functions that actually
need it, so it no longer runs at collection time ahead of every other test
module. Either change should ship with a comment recording why the order
matters, so a future edit doesn't silently reorder it back.

**Verify.** Run `python -m pytest tests publication_pipeline/tests -q` (the
CI order) with the pinned lockfile installed, before and after, and confirm
`test_reportkit_viz_themes.py`'s tests report `passed`, not `skipped`, in
both the old and new order — this is the regression check, since the fix
should be a no-op when the environment is healthy and a hard failure (not a
skip) when it isn't.

**Priority.** P0 — per the port record's own framing, this should land
first because every other fix in this document is validated by this same
test suite.

---

## B. Swimlanes: already fixed, differently — strengthen the test instead

**Fork's claim.** Multi-column swimlanes could collapse onto column 1 with
exit 0 and no warning; recommends fixing the column-position pgfmath and
adding an overlap guard, plus a test that verifies actual pitch.

**Evidence.** `latex_templates/reportkit-process.sty:196-210` already
computes column position from an explicit pitch:
```
\rk@lanestepwidth = (\rk@lanewidth - \rk@laneouterwidth/1cm) / (\rk@lanecolumns - 1)
% node center at 0.5*outerwidth + (col-1)*stepwidth
```
This is derived, not hardcoded, and spans the full declared `width=`
symmetrically (first/last node centers sit half a node-width in from each
edge). It also already errors — not warns — when a step's column exceeds
`columns=` (`:194-195`) or when `column spacing=` doesn't fit the declared
width (`:207-208`). None of that reads as the collapsed-to-column-1 defect
the fork describes; this file's column math looks like it was already
rewritten since the fork's base commit.

`tests/test_primitive_additions.py:11-33` is the fork's exact port target —
a rendered-PDF geometry test for a 5-column swimlane — but it only checks
that label x-positions are non-decreasing and stay within the process
rails, not that consecutive columns are actually spaced apart. A near-total
collapse that still produced a strictly increasing (if tiny) sequence of
x-coordinates would pass this test today.

**Verdict.** No code fix to port — the defect as described does not exist
in this tree. The fork's test-strengthening recommendation still stands on
its own merits.

**Fix.** Extend `test_five_column_swimlane_stays_inside_its_declared_process_width`
(or add a sibling test) to assert the pitch directly: compute consecutive
gaps between the five node x-centers and assert each is within a tolerance
of `(process_right - process_left - node_width) / (columns - 1)`, so a
future regression that compresses spacing — even one that keeps ordering
correct — fails loudly.

**Priority.** P2 — test-only, no production defect to block on.

---

## C. Dated roadmaps: below-side milestone arrows can draw through the period label

**Evidence.** `latex_templates/reportkit-structure.sty:249` draws each
period label as an **unnamed** node, `anchor=north`, at a fixed
`(\rk@roadx,-.22)`, `text width=2.55cm`, in the `rk structure muted` style
(`:40`, 6.8pt font / 8.1pt leading). Two lines of that style extend roughly
0.57cm below the anchor — to about `y=-0.79` — for any period label that
wraps (anything past roughly 15-18 characters at that width, e.g. a
quarter label with a short description appended).

The below-side milestone branch (`:259-262`, odd milestone index) draws its
connector from `y=-.10` to `y=-.63` and places its card at `y=-.68`,
independent of how much the period label actually occupies:
```
\draw[rk structure arrow] (\rk@roadx,-.10) -- (\rk@roadx,-.63);
\node[rk structure card,anchor=north,...] at (\rk@roadx,-.68) {...};
```
`-0.63` sits inside the ~`-0.22` to `-0.79` band a two-line period label can
occupy — so a below-side milestone on a period whose label wraps draws its
arrow directly through the label text. There is no rendering test for
`reportroadmap`'s `mode=dated` at all — `tests/*.py` has no reference to it
(only `latex_templates/examples/visual_grammar_acceptance_test.tex`, which
this repo's `compile_doc`-based geometry suite does not exercise), so this
would not currently be caught even if it reproduced in a fixture.

**Fix.** Give the period-label node a name (e.g.
`roadperiod\the\rk@i`) when it is drawn, then anchor the below-side arrow's
start/end and the milestone card's position off that node's `.south` (with
a fixed gap), instead of the current hardcoded absolute y-offsets. This
makes the geometry correct regardless of how many lines a period label
wraps to, matching how the above-side branch already has slack (period
labels never extend upward, so that branch is not at risk).

**Test.** Add a `reportroadmap` `mode=dated` case to the rendered-PDF
geometry suite (same `compile_doc`/`geometry.py` pattern as
`tests/test_primitive_additions.py`) with a period label long enough to
wrap to two lines and a milestone on the below side. Assert no overlap
between the milestone arrow's bounding path and the period label's word
boxes, and that the arrow is still present and drawn (i.e., the fix doesn't
silently drop the connector) — the fork's stated intent for this test.

**Priority.** P1 — silent visual defect with no compile-time signal, same
class as the C1 bug the tooling-hardening spec already fixed and
regression-tested (`docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md`,
§C1).

---

## D. Pandoc figures: missing global `keepaspectratio`

**Evidence.** `latex_templates/reportkit-core.sty:14` loads `graphicx` with
no accompanying `\setkeys{Gin}{...}` default — grepping the whole
`latex_templates/` and `publication_pipeline/templates/` tree finds exactly
one `keepaspectratio` use, hand-written for the cover image
(`publication_pipeline/templates/publication-template.tex:31`). Nothing
sets it as a default for `\includegraphics` calls Pandoc itself emits from
manuscript Markdown image syntax.

Pandoc's LaTeX writer, when an image carries a percentage width but no
explicit height (`![caption](fig.png){width=60%}`), emits both `width=` and
a `height=\textheight`-style fallback in the generated `\includegraphics`
call — precisely so an image can never overflow the page — and relies on
`keepaspectratio` to keep that pair from distorting the image. Pandoc's own
default LaTeX template carries a `\setkeys{Gin}{width=\maxwidth,
height=\maxheight,keepaspectratio}` block for exactly this reason;
`reportkit-pandoc.sty` (the file that centralizes the rest of ReportKit's
Pandoc-compatibility preamble per the tooling-hardening spec's §B1) does
not carry it.

No tracked fixture currently uses a percentage-width Markdown image — a
repo-wide grep for `!\[.*\]\(.*\)\{.*\}` finds nothing — so this has not yet
visibly broken a build here, but the missing default is real and the first
manuscript author who writes `{width=NN%}` (an ordinary, documented Pandoc
image-sizing idiom) will get a stretched figure with a clean exit code.

**Fix.** Add a `\setkeys{Gin}{width=\maxwidth,height=\maxheight,
keepaspectratio}` block (with the accompanying `\maxwidth`/`\maxheight`
`\Gin@nat@width`-based macros Pandoc's own template defines) to
`reportkit-pandoc.sty`, since this is specifically about Pandoc-sourced
figures. This is additive and does not change the one existing explicit
`keepaspectratio` call.

**Test.** Add a Pandoc-feature fixture (natural home:
`publication_pipeline/tests/`, alongside the D5 fixture work the
tooling-hardening spec calls for) — a small image with a `{width=NN%}`
attribute and a non-square aspect ratio, rendered end to end, with the
built PDF's image bounding box asserted proportional to the source image
rather than stretched.

**Priority.** P1 — silent output defect, same "exit 0 with wrong output"
class as §C.

---

## E. Diagram label validation counts edge `label=` as a diagram label

**Evidence.** `publication_pipeline/scripts/publication_validation.py:20`:
```python
OPTION_LABEL_RE = re.compile(r"(?<![\\A-Za-z])label\s*=\s*\{\s*([^{}]+?)\s*\}")
```
applied at `:163` to the **entire fragment file's text**, not scoped to the
`\begin{diagram}[...]` options group. `reportkit-process.sty:26` declares
`label/.store in=\rk@flowlabel` as a real, documented per-edge key for
`reportflow` edges (its own `.unknown` error message at `:29` lists `label=`
as a supported edge option), used as `label={...}` — the same brace syntax
`OPTION_LABEL_RE` matches. Any fragment that pairs a `\begin{diagram}[...,
label={fig:foo}, ...]` with an edge like `\flowedge[label={Approve}]{a}{b}`
has two `label={...}` matches in the file, so `publication_validation.py:165`
raises `expected exactly one diagram label` on a fragment that is correct.

`publication_pipeline/tests/test_validation.py:18-19` only ever writes a
single `label=` per fixture file (the diagram's own), so this false
positive is not covered — and no tracked fragment currently uses an edge
label, so it hasn't fired yet, matching the port record's description of a
latent defect rather than an active build break.

**Fix.** Scope the label count to the `\begin{diagram}[...]` options group
specifically: extract that bracketed option string first (handling nested
braces inside option values and an unterminated/malformed option group as
an explicit diagnostic rather than a silent no-match), then run `LABEL_RE`
(for `\label{...}`, if ReportKit diagrams ever emit one) and a
diagram-options-scoped label match only within that substring. Edge-level
`label=` outside the `diagram` options must not contribute to the count.

**Test.** Add a fixture fragment with `\begin{diagram}[label={fig:x}, ...]`
containing a `\flowedge[label={Approve}]{a}{b}` (or equivalent
`\handoff[label={...}]`) and assert `validate_publication` reports it
valid. Add a companion fixture with a malformed/unterminated option group
(e.g. an unclosed `[` before `label=`) and assert it produces a clear
diagnostic rather than either a false pass or an unhandled exception.

**Priority.** P1 — blocks legitimate manuscript content the diagram grammar
already supports.

---

## F. Publication assets: `figures/`/`assets/` are never staged into the build

**Evidence.** `publication_pipeline/scripts/publication_build.py:369-370`
copies only `template_files()` (ReportKit's own `.cls`/`.sty` files) and the
document template into `output/`; the loop building `body-NN.tex` per
manuscript (`:378-390`) and `write_metadata`/`render_links_tex` afterward
never touch a `figures/` or `assets/` directory in `source_root`. The
compiled `TEXINPUTS` at `:434`:
```python
texinputs = f"{output}:{REPO_ROOT / 'latex_templates'}//:"
```
contains `output` and the *engine's* `latex_templates/` tree — it does not
contain `source_root` (the publication project directory) at all, and the
TeX engine is invoked with `cwd=output` (`:449`), not `cwd=source_root`.
So a manuscript image reference such as `![Chart](figures/revenue.png)`,
which resolves fine when an author compiles by hand from inside the
publication project (where `cwd == source_root` and the image is a sibling
path), cannot resolve inside a pipeline build: neither the working
directory nor `TEXINPUTS` gives the TeX engine any path back to
`source_root`. This matches the port record's description precisely —
"manuscript images working manually but failing in pipeline builds" — and
is a build-time image-resolution failure, not silent, but the fork's
staging fix and the `build-report.json` recording of staged assets are
still worth porting for reproducibility and observability, not just to fix
the missing-file error.

**Fix.** In `build()`, after computing `output`, copy `source_root /
"figures"` and `source_root / "assets"` into `output/` (each optional —
only if the directory exists), before rendering the manuscript. Record what
was staged (paths and a hash per file, same shape as the existing
`"templates"` entries) in `build-report.json` so a build's provenance shows
which project assets it actually used, per the fork's note that "staged
assets are also recorded in build-report.json."

**Test.** Add a fixture publication project (or extend the existing
`publication_pipeline/tests/` fixtures) with a `figures/` directory
containing one image referenced from a manuscript fragment or Markdown
body, build it through `publication_build.build()`, and assert both that
the build succeeds and that `build-report.json` lists the staged asset.

**Priority.** P1 — currently a hard build failure for any project that uses
local image assets outside the fragment/diagram pipeline, which is a
reasonable and likely-common way to include a manuscript figure Pandoc
converts directly (a screenshot, a pre-rendered chart export, a logo).

---

## G. pandas `M` vs `ME` frequency alias

**Evidence.** Every date-frequency call in this tree already uses the
pandas 2.2+ alias unconditionally:
- `python_scripts/reportkit_doctor.py:102` — `freq="ME"`
- `python_scripts/reportkit_viz.py:1569` — `freq="ME"`
- `latex_templates/examples/equity-research/figures.py:113` — `freq="ME"`

pandas is **not** listed in `tests/requirements.txt` or
`publication_pipeline/requirements.txt` (both pin only `pytest` and
`PyMuPDF`) — it is only pinned in `toolchain/requirements.lock`
(`pandas==2.3.2`), which is exclusively the CI Docker image
(`toolchain/Dockerfile`). Any local development, doctor run, or example
script execution outside that image uses whatever pandas is installed, with
no floor. `"ME"` was introduced in pandas 2.2 and does not exist on earlier
versions — it raises rather than degrades gracefully — so
`reportkit_doctor.py:96-111`'s `check_vector_export()` (which itself
depends on `freq="ME"` at `:102`) reports a false failure on any pandas
before 2.2, exactly the port record's "false doctor failures."

**Fix.** Add a small `month_end_freq()` helper (natural home:
`python_scripts/reportkit/context.py`, which already imports pandas and is
shared infrastructure) that inspects the installed pandas version and
returns `"ME"` on 2.2+, `"M"` otherwise. Replace the three hardcoded
`freq="ME"` call sites above with it.

**Test.** A unit test asserting the helper returns the version-appropriate
alias is sufficient given the current sandbox cannot install multiple
pandas versions to exercise both branches directly; if CI can matrix a
pre-2.2 pandas job cheaply, add that as a stronger check, but it is not a
blocker for landing the fix.

**Priority.** P2 — real, but only manifests outside the pinned CI image,
where behavior has no other floor today.

---

## H. Bubble matrix: groups differ only by color

**Evidence.** `python_scripts/reportkit_viz.py:1277-1286` (`bubble_matrix`,
grouped branch):
```python
for index, group in enumerate(groups):
    mask = frame[group_column].astype(str) == group
    ax.scatter(frame.loc[mask, x], frame.loc[mask, y], s=areas[mask.to_numpy()],
               color=DATA_COLORS[index], alpha=0.72, linewidths=0.45, edgecolors=WHITE, label=group)
```
No `marker=` argument varies per group — every group renders as
matplotlib's default circle. `reportkit_viz.py` already defines a `MARKERS`
sequence used the same way for line-series differentiation
(`:317`, `"marker": MARKERS[i % len(MARKERS)]`), so the same pattern is
directly reusable here, not a new design.

**Fix.** In the grouped branch, pass `marker=MARKERS[index % len(MARKERS)]`
alongside the existing `color=DATA_COLORS[index]`, matching the existing
line-series convention. Leave the single-series (no `group_column`) branch
unchanged — it has no groups to distinguish.

**Test.** Extend the existing viz theme test suite
(`tests/test_reportkit_viz_themes.py`, which already imports and exercises
`reportkit_viz` under real matplotlib) with a case that builds a grouped
`bubble_matrix` and asserts the resulting `PathCollection`s use distinct
marker paths per group, not just distinct facecolors.

**Priority.** P2 — accessibility correctness, no build failure.

---

## I & J. Per-project license metadata, and escaping its URL — ship together

**I. Evidence (feature gap).** `publication_pipeline/scripts/
publication_build.py:313` loads exactly one license source:
```python
license_values = load_license_metadata(LICENSE_FILE)   # metadata/licenses.yml, repo-root, global
```
`python_scripts/reportkit/config.py`'s `IDENTITY_KEYS`/`DOCUMENT_KEYS`/
`VALIDATION_KEYS`/`THEME_KEYS`/`SECTIONS` (`:9-38`) have no license or
classification section at all — a publication project's `publication.yaml`
has no field that can override `content_license`, `content_license_url`, or
declare a `classification`. Every publication built through this pipeline
therefore inherits the single engine-wide claim in `metadata/licenses.yml`
(currently `CC-BY-4.0`), with no way for a confidential or otherwise
non-CC-licensed project to say so.

**Fix.** Add a `license` section to `publication.yaml` (`content_license`,
`content_license_url`, `classification`, all optional) and a resolver
(mirroring `resolve_identity`'s override pattern) that starts from the
engine's `metadata/licenses.yml` values and overrides only the fields the
project sets — so existing projects that set nothing keep exactly today's
behavior, matching the fork's stated compatibility requirement. Pass the
resolved values into `write_metadata` in place of the always-global
`license_values`, and surface `classification` as a new `\RKPubClassification`
macro (or fold it into the existing disclaimer/rights-notice text) so a
non-CC project's cover/footer can say so.

**J. Evidence (the injection path this feature opens).**
`publication_build.py:242`:
```python
f"\\newcommand{{\\RKPubContentLicenseURL}}{{{license_values['content_license_url']}}}",
```
is the **only** identity field in `write_metadata` not passed through
`tex_escape()` (compare `:238-241`, `:244`, every other field). `tex_escape`
itself is defined at `:116` and already used for every other user-supplied
string in this function. `content_license_url`'s only validation today,
`license_metadata.py:28-30`, is `urlparse(...).scheme == "https"` and a
non-empty `netloc` — it does not reject LaTeX metacharacters anywhere in
the path, query, or fragment (`#`, `&`, `%`, `_`, `{`, `}`, `\` are all
legal in a URL and all meaningful to LaTeX). Today this is a low-severity
gap: `metadata/licenses.yml` is a single repo-root file only a maintainer
with commit access edits. §I turns `content_license_url` into a value each
publication project can set independently in its own `publication.yaml` —
at that point the same unescaped interpolation becomes a real LaTeX-
injection path from a much larger and less trusted set of editors, which is
exactly why the fork ships these two together.

**Fix.** In `license_metadata.py`'s validation (reused by both the global
loader and §I's per-project resolver), reject a `content_license_url`
containing any of `\ { } $ & # ^ _ ~ %` outside of standard URL percent-
encoding — i.e., require it to already be a well-formed URL with those
characters either absent or properly percent-encoded, since a license URL
has no legitimate reason to carry a literal brace or backslash. Then, in
`publication_build.py:242`, wrap the (now validated) value in `tex_escape()`
like every other field, consistent with `\RKPubProjectURL`
(`:238`, currently also unescaped, if this repo's URL fields — plural — are
what a fresh guest actually meant when they inspected them: adjacent gap,
worth fixing at the same time, not just the license URL) — pending
confirmation neither macro is meant to carry raw TeX for a `\url{}` wrapper
at the point of use; if it is, escape at the point of typesetting instead
of at definition, and add a comment recording that choice so the asymmetry
with the other fields isn't mistaken for an oversight later.

**Test.** Extend `tests/test_licensing.py` with: (1) a per-project
`publication.yaml` override producing a resolved `license_values` distinct
from the global metadata, with an unset project falling back to today's
global value unchanged; (2) a `content_license_url` containing a brace or
backslash rejected by validation; (3) a legitimate URL with `%`/`&`/`#`
(ordinary URL characters) accepted and, once run through `write_metadata`,
appearing `tex_escape`d in the generated `metadata.tex`.

**Priority.** P1 for §J once §I lands (the injection surface doesn't exist
without it); P2 for §I alone as a feature. Land them in the same change, as
the fork did.

---

## K. Environment/toolchain documentation

**Evidence.** This repository's environment documentation is already
substantially more thorough than the port record's checklist implies:
`references/font-setup.md` covers the Libertinus install (bundled tarball
+ `TEXMFLOCAL` rationale, apt-get fallback, the `luaotfload` requirement,
and the `LinBiolinum_K.otf` stub gap) in detail; `references/known-fixes.md`
documents the `reportkit_doctor.py` FULL BUILD false positive (engines
present but fonts missing) and two prior silent-rendering defects with
symptom/cause/fix/verification; `references/troubleshooting.md` documents
the standard task flow, the doctor's `MODE:` line, and (`:59-61`) that
Python/matplotlib/numpy/pandas are expected preinstalled with `biber`
notably absent. Required TeX packages are documented as apt package names
(`texlive-fonts-extra`, `texlive-luatex`) rather than `tlmgr` package names,
which is consistent with this repo's Debian/Ubuntu-first tooling elsewhere
(`toolchain/Dockerfile`) — not a gap.

The one thing this documentation set does not mention anywhere is a
library-path/import-order trap of the kind §A fixes: nothing tells a future
contributor that `pymupdf` importing before `matplotlib`/`pandas` in the
same process is a known-risky order, so a recurrence would currently be
re-diagnosed from scratch rather than recognized — the exact failure mode
`references/known-fixes.md`'s own stated purpose exists to prevent.

**Fix.** Add one entry to `references/known-fixes.md` (or a new "silent
import-order hazard" note cross-referenced from `references/
troubleshooting.md`'s Environment notes) once §A lands, recording: the
symptom (a pandas/matplotlib-dependent test skips instead of failing, or
fails with a `libstdc++` version error), the cause (import order across
`pymupdf` and the scientific stack), and the fix (§A's reordering) — mirror
the existing entries' symptom/cause/fix/verified structure.

**Priority.** P3 — documentation only, and only meaningful once §A exists
to document.

---

## Sequencing

```
A (test harness)         ─┐ first — every other fix here is verified by this suite
E (diagram label parse)   │
F (asset staging)         │ independent defects, safe to land in any order after A
C (roadmap anchoring)     │
D (Pandoc keepaspectratio)┘
G (pandas M/ME)          ── independent, any time
H (bubble matrix markers)── independent, any time
I + J (license metadata + escaping) ── ship together, any time after A
B (swimlane test only)   ── no code fix; land whenever convenient
K (docs)                  ── after A, records what A fixed
```

## Acceptance criteria

- `python -m pytest tests publication_pipeline/tests -q`, run in the CI
  order, reports `test_reportkit_viz_themes.py`'s tests as passed (not
  skipped) with the pinned toolchain installed (§A).
- The 5-column swimlane test asserts a minimum inter-column pitch, not just
  monotonic ordering (§B).
- A rendered-PDF test for `reportroadmap` `mode=dated` with a wrapping
  period label and a below-side milestone shows no overlap between the
  milestone arrow and the period label's word boxes, and the arrow is still
  present (§C).
- A percentage-width Pandoc image fixture renders at its source aspect
  ratio, not stretched to the declared height (§D).
- `validate_publication` accepts a fragment combining a diagram label and
  an edge `label=` option, and reports a clear diagnostic (not a crash) on
  a malformed/unterminated diagram option group (§E).
- A fixture publication with a `figures/` directory referenced from
  Markdown builds successfully through `publication_build.build()`, and the
  staged asset appears in `build-report.json` (§F).
- `month_end_freq()` returns `"ME"` on pandas 2.2+ and `"M"` before it, and
  the three hardcoded call sites use it (§G).
- A grouped `bubble_matrix` renders a distinct marker per group in addition
  to distinct colors (§H).
- A publication project's `publication.yaml` can override
  `content_license`/`content_license_url`/`classification`; an unset
  project is byte-for-byte unchanged from current output (§I).
- A `content_license_url` containing a LaTeX metacharacter outside percent-
  encoding is rejected by validation; a legitimate URL survives
  `write_metadata` correctly `tex_escape`d (§J).
- `references/known-fixes.md` records the import-order hazard once §A
  lands (§K).
