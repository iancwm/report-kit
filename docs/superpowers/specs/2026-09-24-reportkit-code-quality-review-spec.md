# ReportKit Code Quality Review — September 2026

**Status:** Two items (§A, §B) landed in this same change; §C and §D are open,
unscheduled cleanup; §E is a documentation-only note. No phase gate blocks
anything else in the repository.
**Baseline:** `main` at `b8766fd` (branch `claude/code-quality-review-pzqcft`).
**Source:** a targeted re-audit of the repository's Python surface
(`python_scripts/`, `publication_pipeline/`, `scripts/`, `adapters/`,
`tests/`) following up on
[2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md](2026-09-12-reportkit-code-quality-and-dependency-remediation-spec.md).
That document is closed and its Phase 0–2 items are still landed and verified
below. This pass exists to check whether they held, and to find what changed
since. It is not a full re-audit of `latex_templates/` or the publication
pipeline's LaTeX-facing behavior — scope is engine-internal Python quality
only, matching the prior document's stated scope.
**Method:** every item below was verified in this tree by running the tool
that finds it (`ruff`, `pytest`, `ast`, `grep`), not by inspection alone. The
full test suite (`python3 -m pytest tests publication_pipeline/tests`) passes
at 368 passed / 139 skipped both before and after the fixes in §A/§B (the
skips are TeX-toolchain-gated tests; no TeX engine is available in this
review environment).

## What's still good

The 2026-09-12 remediation held up well on re-inspection:

- The single shared `tex_escape` (`reportkit/latex.py`) that ended the
  "four disagreeing escapers" defect is still the one every documented call
  site uses, and `tests/test_code_quality_remediation.py` still asserts
  identity across `authoring.py`, `publication_build.py`, and
  `reportkit/latex.py` at import time — a real regression guard, not just a
  comment. (§B below is exactly this guard having one blind spot.)
- `reportkit_viz.py` is a 93-line compatibility shim as promised, not the
  1716-line original.
- Version-probe duplication is gone: `reportkit/toolchain.py:version_line` is
  the one implementation `reportkit_doctor.py` and `publication_build.py`
  both import.
- Docstring coverage on the modules called out as gaps
  (`toolchain.py`, `documentation.py`, `manifest.py`) is complete, and it
  extends to code added since — `reportkit/latex.py`, `reportkit/viz/theme.py`,
  `reportkit/viz/figure.py`, `authoring_ir.py`, and `context_budget.py` all
  have docstrings on every public definition.
- `shell_scripts/bootstrap.sh` and the four pipeline wrapper scripts it
  documented alongside are gone; `reportkit init` and the `./reportkit`
  facade are the only paths now.
- Error handling at process boundaries (`except Exception` in
  `reportkit_doctor.py`, `publication_build.py`, `inspect_pdf.py`,
  `render_pdf_pages.py`, `contract_acceptance.py`) uniformly converts to a
  diagnostic envelope rather than swallowing the error or leaking a raw
  traceback. No bare `except:` anywhere in the tree.

## Summary

| § | Item | Verdict | Status |
|---|---|---|---|
| A | CI's ruff gate silently excludes the two directories where the repo's one lint violation lived | **Defect** — verified by execution | Landed |
| B | A second, private `_tex_escape` reappeared outside the shared escaper the last remediation created for this exact reason | **Defect-class regression** — verified by execution | Landed |
| C | `publication_build.build()` grew past its last remediation (318 → 424 lines) despite the `_fail()` helper landing | Acceptable-but-costly | Open |
| D | The `reportkit_viz` → `reportkit/viz/` package split is a re-export shim over one 1512-line `core.py` | Acceptable-but-costly | Open |
| E | `pyproject.toml` declares `line-length = 120` but globally ignores `E501`, so nothing enforces it | Cleanup | Open |

---

## A. CI's ruff invocation has a blind spot, and it is exactly where the one lint violation in the repository lives

**Evidence.** `.github/workflows/contract-ci.yml`'s only lint step was:

```
ruff check python_scripts publication_pipeline/scripts scripts tests
```

Four positional paths. Two real source trees are absent: `adapters/` (the
OpenAI tool-generation adapter) and `publication_pipeline/tests/` — note the
CI command names `publication_pipeline/scripts` but not
`publication_pipeline/tests`, even though `python -m pytest tests
publication_pipeline/tests` two lines above runs that directory's tests.

Running `ruff check .` (respecting `pyproject.toml`'s `extend-exclude`, no
custom paths) against this tree before this change found exactly one
violation in the entire repository:

```
F401 [*] `pathlib.Path` imported but unused
 --> publication_pipeline/tests/test_log_gate.py:1:21
```

Running the CI command verbatim against that same tree reported
`All checks passed!` — the gate cannot see the file the violation is in.
`adapters/` was clean, but nothing was checking it either.

**Verdict.** Defect. A lint gate that does not cover a directory whose tests
CI itself runs is not exercising what it appears to guard, and this is not
hypothetical — it is demonstrated by the one violation that slipped through
it.

**Fix (landed in this change).**
- Removed the unused `from pathlib import Path` in
  `publication_pipeline/tests/test_log_gate.py` (confirmed unused: no other
  reference to `Path` in the file).
- Widened the CI ruff invocation to
  `ruff check python_scripts publication_pipeline scripts tests adapters`
  (`publication_pipeline` covers both `scripts/` and `tests/` under it).
  Verified `ruff check python_scripts publication_pipeline scripts tests
  adapters` and `ruff check .` both report `All checks passed!` after the fix.

**Verification.** The widened command is what CI now runs; re-introducing an
unused import in `publication_pipeline/tests/` or `adapters/` will fail the
existing `pinned-toolchain` job with no further change needed.

## B. The shared `tex_escape` regression guard has a blind spot, and a second private copy reappeared behind it

**Evidence.** `reportkit/theme_overrides.py:448` defined its own
`_tex_escape`, byte-for-byte the same ten-character replacement table as
`reportkit/latex.py:19 tex_escape` — the function the 2026-09-12 remediation
(§B in that document) created specifically to end having more than one LaTeX
text escaper in the tree, after a previous divergence between escapers
produced both a silently-wrong render (`~` swallowed as a non-breaking space)
and a hard TeX build failure (`^` reaching text mode). Four call sites used
`_tex_escape` to render brand font names and policy strings into
`reportkit-theme-overrides.tex` (lines 484, 485, 494, 495).

`tests/test_code_quality_remediation.py` already asserts, at import time,
that `publication_build.tex_escape`, `authoring.tex_escape`, and
`reportkit.latex.tex_escape` are the same object — the regression guard the
last remediation added. It does not import or check
`theme_overrides._tex_escape`, so a second private copy could exist beside it
undetected. It currently agreed with the shared table character-for-character
(verified: both cover exactly the same ten metacharacters with the same TeX
output), so this is not a live rendering defect today — but nothing enforced
that agreement, which is the exact condition that produced the original
defect.

**Verdict.** Defect-class regression. The fix for "N escapers that can
diverge" was "one escaper," and a new private copy of it was added anyway in
code that postdates the remediation (the brand-overrides / venture theme
work). The identity-assertion pattern the tests already use for the other
three call sites is the correct guard; it just didn't cover this one.

**Fix (landed in this change).**
- Deleted `theme_overrides._tex_escape` and its four call sites now call the
  shared `reportkit.latex.tex_escape`, imported as `_tex_escape` to keep the
  four call sites unchanged (`from .latex import tex_escape as _tex_escape`).
- Extended `test_all_latex_text_callers_share_the_same_escaper` in
  `tests/test_code_quality_remediation.py` to also assert
  `theme_overrides_tex_escape is tex_escape`, so a future private copy in
  this module fails the same guard the other three call sites already have.

**Verification.** `python3 -m pytest tests/test_code_quality_remediation.py
tests/test_brand_overrides.py publication_pipeline/tests/test_log_gate.py`
passes (43 tests); full suite still 368 passed / 139 skipped, unchanged from
before the fix.

## C. `publication_build.build()` grew past its last remediation

**Evidence.** The 2026-09-12 document flagged `build()` at 318 lines (item M)
and prescribed a `_fail(report, diagnostics, code)` helper to collapse nine
repeated five-line failure epilogues. That helper exists today at
`publication_build.py:434` and is used throughout. Despite it landing,
`build()` (`publication_build.py:475`) is now **424 lines** — measured by AST
span (`ast.FunctionDef.lineno` to `end_lineno`), up from 318. It remains the
longest function in the repository by roughly a factor of two over the next
candidate (`scripts/visual_qa_equity_research.py:main`, 180 lines).

The helper solved the specific duplication it targeted; it did not bound the
function's growth, because the Phase D–F multi-format work (venture,
editorial, executive-brief, book publication types — all landed since
2026-09-12 per `TODOS.md`) added new target-specific branches to the same
function rather than to an extracted stage.

**Verdict.** Acceptable-but-costly, same class as before, now larger. The
cost named in the original item — the gate-failure path is only exercisable
by running an entire build — still holds, and now covers more branches.

**Fix (not applied in this pass; scoping only).** The original prescription
still applies: split preflight (validate → config → resolve target) from the
compile stages (Pandoc, TeX passes, log gate, page rendering, PDF
inspection), so each multi-format branch is independently testable. This is
a larger, behavior-preserving refactor of the repository's most
build-critical function and deserves its own reviewed change with the full
acceptance/visual-QA gate run against it, not a quick edit bundled into a
review pass. Flagging it here keeps it from being re-discovered as new next
time.

**Verification (when done).** A test exercising each preflight failure branch
directly, without a full build — the gap the original item named — passing
for every multi-format target added since.

## D. The `reportkit_viz` → `reportkit/viz/` package split is a re-export shim over one 1512-line `core.py`

**Evidence.** The 2026-09-12 document (item N) prescribed splitting the
1716-line `reportkit_viz.py` into `reportkit/viz/{theme,figure,formatters,
charts/,cli}.py`. `theme.py` (134 lines) and `figure.py` (151 lines) are
genuine, independent implementations — `apply_theme` and `new_figure` live
there and nowhere else. `charts/__init__.py`, however, is a 12-line re-export:

```python
from ..core import (
    bar_chart, bubble_matrix, distribution, donut_chart, drawdown_chart, heatmap,
    risk_reward_chart, scatter_plot, timeline_chart, timeseries, tornado_chart,
    treemap_chart, waterfall_chart,
)
```

All thirteen chart constructors are still implemented in `core.py`
(1512 lines), alongside palette validation, `build_demo` (107 lines), and the
module's CLI. `core.py` imports cleanly from `theme.py` and `figure.py` (no
duplication — this is not a repeat of §B), so the split is directionally
correct and not a regression; it is simply incomplete relative to what item N
proposed. The package is functionally fine — `reportkit_viz.py` as a
93-line shim was the primary deliverable and it is correct — this is a
secondary structural note.

**Verdict.** Acceptable-but-costly, lower priority than when first raised:
the highest-value part of the split (getting `reportkit_viz.py` down from
1716 lines to a compatibility shim) is done. What remains is moving each
chart family (or groups of related charts) into `charts/` as real modules
rather than a re-export, which is optional polish, not a defect.

**Fix (not applied; scoping only).** If pursued, group the thirteen chart
functions by shared helpers (e.g. `_treemap_*` with `treemap_chart`,
`_bubble_areas` with `bubble_matrix`) into 3–4 files under `charts/`, moving
`validate_palette_against_latex` / `validate_theme_contract_against_latex`
and `build_demo` to their own modules. Low priority — no defect motivates it,
only the original structural goal being half-realized.

## E. `line-length = 120` in `pyproject.toml` is dead configuration

**Evidence.** `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
...
[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]
ignore = ["E402", "E501"]
```

`E501` (line-too-long) is the only ruff rule that reads `line-length`, and it
is globally ignored. No `ruff format` step exists in CI or as a documented
local command. A line-length count in this tree found 241 lines over 120
characters across the core Python modules checked — a mix of legitimate
tabular data (e.g. `reportkit/registry.py`'s one-line-per-command contract
dicts, which read better as single lines) and ordinary prose that would wrap
under the declared limit if it were ever enforced.

**Verdict.** Cleanup, not a defect — nothing is broken, and several of the
long lines are better left unwrapped. The problem is narrower: the setting
in the config file currently does nothing, which could mislead a contributor
who reads `line-length = 120` as an active constraint.

**Fix (not applied; a decision, not a mechanical change).** Either drop the
now-inert `E501` from `ignore` and accept the churn of wrapping genuine prose
violations (while adding a per-file or per-line `noqa` for the tabular data
that's better unwrapped), or remove the unused `line-length` key and record
in a comment that width is deliberately unenforced. Either resolves the
inconsistency; picking one is a judgment call about the tabular-data
tradeoff above, not something to decide inside a review pass.

---

## Non-goals

- No change to `latex_templates/`, publication content, diagram DSL, or
  visual output.
- No re-litigation of the 2026-09-12 document's resolved decisions
  (packaging model, `bootstrap.sh` retirement, directory layout) — this pass
  only checked whether they held.
- §C and §D are recorded, not scheduled; neither blocks a release and
  neither is a defect. They belong in `TODOS.md` as open structural notes,
  not as a gate.

## Acceptance criteria

§A and §B are done as of this change: `ruff check .` reports zero violations,
the widened CI command matches it, and the escaper identity test covers all
four call sites including `theme_overrides`. §C, §D, and §E are open and
unscheduled; picking any of them up should update this document's status
table rather than rediscover the finding.
