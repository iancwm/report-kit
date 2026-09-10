# Known fixes (historical defect record)

Read this when a compile failure looks similar to something already found
and fixed — it documents what broke, why, and how it was verified, so a
recurrence is recognized quickly rather than re-diagnosed from scratch.

## `reportkit-diagrams.sty` — decimal-times-length arithmetic (fixed in v1.2.0)

**Symptom:** any diagram using `RKMatrixCell` (2x2 matrix) or `RKLayer`
(layered architecture) failed to compile with `Illegal unit of measure (pt
inserted)`. Swimlanes and plain node/edge networks were unaffected.

**Cause:** fifteen places in the diagram macros wrote a decimal
coefficient directly against an `\rk@...` length macro with no operator
between them, e.g. `0.25\rk@matrixw`. TeX/pgfmath expands the macro and
concatenates the text (`"0.25"` + `"12.2"` → `"0.2512.2"`), which is not a
valid number.

**Fix:** inserted an explicit `*` multiplication operator at all 15 sites
(`0.25\rk@matrixw` → `0.25*\rk@matrixw`), which pgfmath parses correctly
inside coordinate expressions. The two `text width={...}` node keys don't
auto-evaluate arithmetic the way coordinates do, so those precompute the
value with `\pgfmathsetlengthmacro` into a length macro first.

**Verified:** recompiled a matrix diagram, a layered architecture, a
swimlane, and a network through two `pdflatex` passes each, rasterized
every page with `pdftoppm`, and visually inspected the output. No change
to the diagram API — existing report `.tex` source using these macros
needs no edits.

## `reportkit.cls` — `\times` glyph clobbered under lualatex (fixed in v1.2.1)

**Symptom:** under lualatex only, `\times` silently rendered as `∝`
instead of `×`. pdflatex was unaffected.

**Cause:** the class unconditionally loaded `libertinust1math` after
`libertinus`, which is correct under pdflatex but clobbers `\times`'s
glyph mapping under lualatex.

**Fix:** guarded the legacy math package load behind `\ifPDFTeX`.

**Verified:** the existing English guide (`career_guide_en`) recompiled to
a byte-identical PDF under pdflatex afterward; the lualatex path
(`career_guide_vi`) was recompiled and visually confirmed to render `×`
correctly.

## `reportkit_doctor.py` — FULL BUILD false positive (fixed)

**Symptom:** the doctor reported `MODE: FULL BUILD` (pdflatex, lualatex,
bibtex all present) even when the Libertinus fonts `reportkit.cls`
requires were missing — a real compile then failed immediately on the
first `\RequirePackage`.

**Cause:** the doctor checked for TeX *engines* being installed, not for
the specific font packages a compile actually needs.

**Fix:** the doctor now also checks via `kpsewhich` for `libertinus.sty`
and `libertinust1math.sty` specifically, and downgrades its reported mode
to `SOURCE BUILD + FIGURES` when they're missing, printing the fix
command. Always trust the doctor's printed `MODE:` line over an assumption
that "TeX is installed" implies a working build.

## Test collection — PyMuPDF/scientific-stack import order (fixed)

**Symptom:** a pandas/matplotlib-dependent test suite skips instead of
failing, or collection fails with a `libstdc++` version/import error after
PyMuPDF has already loaded.

**Cause:** some Linux wheel combinations share a process-wide C++ runtime;
loading `pymupdf` before the scientific stack can expose an ABI conflict.
The old test order also let `pytest.importorskip()` turn that environment
failure into an exit-0 skip.

**Fix:** `tests/conftest.py` imports matplotlib and pandas before PyMuPDF,
while still allowing genuinely absent optional packages to be handled by the
tests that need them.

**Verified:** the CI-order command `python -m pytest tests
publication_pipeline/tests -q` now collects the scientific-stack tests after
that deterministic import order; an installed-but-incompatible package fails
during collection instead of being silently skipped.
