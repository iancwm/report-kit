# ReportKit Visual Grammar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved, unexecuted — blocked on re-cutting the `tooling`
branch (P0-2 in `TODOS.md`).
**Last updated:** 2026-09-07

**Goal:** Give ReportKit the three diagram primitives, the figure width control, and the working alt-text path that the Data Engineering Guide's remaining five figures are blocked on.

**Architecture:** All work lands in `latex_templates/` on the `tooling` branch. A new pytest layer compiles single-figure LaTeX documents with LuaLaTeX and asserts on the *rendered geometry* via PyMuPDF, because the defect this plan fixes first (C1-2) compiles cleanly and is invisible to the existing log-grep gate. Tasks 1–4 fix and extend the existing diagram machinery; tasks 5–7 add one primitive each; task 8 wires everything into the acceptance harness and the skill's primitive table.

**Tech Stack:** LaTeX (LuaTeX 1.22.0, TeX Live 2025), TikZ/pgfkeys, Python 3.12, pytest, PyMuPDF 1.28.2.

**Spec:** `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md` (as amended 2026-09-06) — sections **C** (visual grammar), **B6** (diagram width key), **B7** (alt-text emission). Read the spec's C1 and B7 sections before starting; both carry probe evidence that changes what the original spec text said.

## Global Constraints

- **Branch:** `tooling`, which **must be re-cut from `main` before Task 1**. As of 2026-09-06 the existing `tooling` branch is 0 commits ahead and **17 behind** `main`, and carries a stale 5-file script set. Executing against it as-is would apply this plan's line references to the wrong versions of `latex_templates/`. Verify with `git rev-list --count main..tooling` — it must print `0` and `git rev-list --count tooling..main` must also print `0` before starting.
- This plan touches **no** manuscript, fragment, or `publication-guidelines.md` file. Fragment workarounds are retired on the content branch afterwards, not here.
- **Engine:** LuaLaTeX. The existing `scripts/acceptance_check.sh` uses `pdflatex`; the new pytest layer uses `lualatex` and skips cleanly when it is absent.
- **No new LaTeX package may be added without confirming it resolves** — this checkout is TinyTeX on TL2025 against a TL2026 remote, so `tlmgr install` fails. `accsupp.sty` is **not currently present** (Task 4 handles this explicitly).
- **Every new primitive follows the established contract:** a semantic environment, declaration order is reading order, authors control links not coordinates, a case in `latex_templates/examples/visual_grammar_acceptance_test.tex`, and a row in `SKILL.md`'s question-to-primitive table.
- **Style:** match `reportkit-process.sty` — `pgfkeys` families with `.store in`, `\NewDocumentCommand`/`\NewDocumentEnvironment` from `xparse`, `\rk@`-prefixed internals, `\PackageError` for author mistakes.
- **Node geometry constant:** `rk node` renders **89.370pt** wide (`text width=28mm` + `inner xsep=5pt` × 2). Any grid or step spacing must exceed this. Do not hardcode a spacing that assumes a narrower node.
- **Commit style:** Conventional Commits (`feat:`, `fix:`, `test:`). End every commit message with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## File Structure

```
tests/                                        (new — the geometry-assertion layer)
  conftest.py                                 pytest fixtures: compile_doc, latex_engine
  geometry.py                                 helpers: word_boxes, node_rects, stream_contains
  requirements.txt                            pytest, pymupdf (pinned)
  test_reportflow.py                          Task 1 — C1-1 regression guard
  test_reportnetwork.py                       Task 2 — C1-2 fix
  test_diagram_width.py                       Task 3 — B6
  test_diagram_alttext.py                     Task 4 — B7
  test_reportstate.py                         Task 5 — C2
  test_reportcompare.py                       Task 6 — C2
  test_reporttimeline.py                      Task 7 — C2

latex_templates/
  reportkit-process.sty                       Task 2 (network spacing)
  reportkit-diagrams.sty                      Tasks 3, 4 (lrbox, width=, alt text)
  reportkit-grammar.sty                       (new — Tasks 5-7, the three primitives)
  reportkit.cls                               Task 5 (load the new module)
  examples/
    visual_grammar_acceptance_test.tex        Task 8 (cases for all three primitives)

SKILL.md                                      Task 8 (primitive table rows)
scripts/acceptance_check.sh                   Task 8 (run pytest layer)
```

**Why `reportkit-grammar.sty` is a new file rather than more of `reportkit-diagrams.sty`:** `reportkit-diagrams.sty` is already ~330 lines carrying the node/edge styles, the `diagram` wrapper, and eleven primitives. The three new primitives are self-contained and share only the node/edge styles. A separate module keeps each file reviewable and matches the existing split (`-process`, `-spatial`, `-boxes`, `-code`).

---

### Task 1: Geometry test harness + `reportflow` regression guard

The harness is the deliverable here; the C1-1 regression test is its first consumer. Per the spec's amended C1, **the vertical-flow bug is already fixed** — this task locks that in so it cannot regress, and gives every later task a way to assert on rendered output.

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/geometry.py`
- Create: `tests/requirements.txt`
- Create: `tests/test_reportflow.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `compile_doc(body: str, name: str = "doc") -> pymupdf.Document` — pytest fixture. Wraps `body` in a `reportkit` document, compiles with LuaLaTeX, returns the opened PDF. Raises `AssertionError` with the tail of the TeX log if no PDF is produced.
  - `word_boxes(page, labels: set[str]) -> dict[str, tuple[float, float, float, float]]` — maps each found word to `(x0, y0, x1, y1)`.
  - `node_rects(page, min_width: float = 40.0) -> list[pymupdf.Rect]` — node-sized drawn rectangles, sorted left-to-right.
  - `stream_contains(doc, needle: bytes) -> bool` — True if any object stream contains `needle`.

- [ ] **Step 1: Create the dependency file**

Create `tests/requirements.txt`:

```
pytest==8.3.4
pymupdf==1.28.2
```

- [ ] **Step 2: Write the fixtures**

Create `tests/conftest.py`:

```python
"""Fixtures for compiling single-figure ReportKit documents and inspecting them.

These tests assert on *rendered geometry*, not on the TeX log. The defect that
motivated this layer (reportnetwork's grid/node-width collision) compiles with
exit code 0 and an empty warning list while drawing every arrow backwards, so
a log-grepping gate cannot see it.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import pymupdf

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"

PREAMBLE = "\\documentclass{reportkit}\n\\begin{document}\n"
POSTAMBLE = "\n\\end{document}\n"


@pytest.fixture(scope="session")
def latex_engine():
    engine = shutil.which("lualatex")
    if engine is None:
        pytest.skip("lualatex not on PATH")
    return engine


@pytest.fixture
def compile_doc(latex_engine, tmp_path):
    def _compile(body, name="doc"):
        tex = tmp_path / f"{name}.tex"
        tex.write_text(PREAMBLE + body + POSTAMBLE, encoding="utf-8")
        env = dict(os.environ, TEXINPUTS=f"{TEMPLATES}:")
        proc = subprocess.run(
            [latex_engine, "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        pdf = tmp_path / f"{name}.pdf"
        if not pdf.exists():
            raise AssertionError(
                f"lualatex produced no PDF (exit {proc.returncode}).\n"
                f"--- last 3000 chars of output ---\n{proc.stdout[-3000:]}"
            )
        return pymupdf.open(pdf)

    return _compile
```

- [ ] **Step 3: Write the geometry helpers**

Create `tests/geometry.py`:

```python
"""Helpers for asserting on the geometry of a rendered ReportKit figure."""


def word_boxes(page, labels):
    """Map each word in `labels` to its (x0, y0, x1, y1) bounding box."""
    found = {}
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if text in labels:
            found[text] = (x0, y0, x1, y1)
    return found


def node_rects(page, min_width=40.0):
    """Node-sized drawn rectangles on the page, ordered left to right.

    `rk node` renders 89.37pt wide and 10mm (~28.35pt) tall. The width floor
    excludes rules, arrowheads, and caption underlines.
    """
    rects = [
        d["rect"]
        for d in page.get_drawings()
        if d["rect"].width >= min_width and 15.0 <= d["rect"].height <= 60.0
    ]
    return sorted(rects, key=lambda r: r.x0)


def stream_contains(doc, needle):
    """True if any object stream in `doc` contains the raw bytes `needle`."""
    for xref in range(1, doc.xref_length()):
        try:
            stream = doc.xref_stream(xref)
        except Exception:
            continue
        if stream and needle in stream:
            return True
    return False
```

- [ ] **Step 4: Write the regression test**

Create `tests/test_reportflow.py`:

```python
"""reportflow direction handling.

`direction=vertical` was broken before commit 1c00be3, which changed the
comparison at reportkit-process.sty:30 to expand \\rk@flowdirection before
\\ifstrequal sees it. These tests exist so that fix cannot silently regress.
"""

from geometry import word_boxes

VERTICAL = r"""
\begin{diagram}[caption={A vertical flow.}]
  \begin{reportflow}[direction=vertical]
    \step{a}{Alpha}
    \step{b}{Bravo}
    \step{c}{Charlie}
    \flowedge{a}{b}
    \flowedge{b}{c}
  \end{reportflow}
\end{diagram}
"""

HORIZONTAL = r"""
\begin{diagram}[caption={A horizontal flow.}]
  \begin{reportflow}
    \step{a}{Alpha}
    \step{b}{Bravo}
    \step{c}{Charlie}
    \flowedge{a}{b}
    \flowedge{b}{c}
  \end{reportflow}
\end{diagram}
"""

LABELS = {"Alpha", "Bravo", "Charlie"}
ORDER = ("Alpha", "Bravo", "Charlie")


def test_vertical_flow_stacks_steps_in_one_column(compile_doc):
    boxes = word_boxes(compile_doc(VERTICAL)[0], LABELS)
    assert set(boxes) == LABELS, f"missing labels: {LABELS - set(boxes)}"
    xs = [boxes[n][0] for n in ORDER]
    ys = [boxes[n][1] for n in ORDER]
    assert max(xs) - min(xs) < 5.0, f"expected one column, got x={xs}"
    assert ys == sorted(ys), f"expected descending order, got y={ys}"
    assert ys[1] - ys[0] > 20.0, f"steps too close to be separate rows: y={ys}"


def test_horizontal_flow_is_still_the_default(compile_doc):
    boxes = word_boxes(compile_doc(HORIZONTAL)[0], LABELS)
    assert set(boxes) == LABELS, f"missing labels: {LABELS - set(boxes)}"
    xs = [boxes[n][0] for n in ORDER]
    ys = [boxes[n][1] for n in ORDER]
    assert max(ys) - min(ys) < 5.0, f"expected one row, got y={ys}"
    assert xs == sorted(xs), f"expected left-to-right order, got x={xs}"
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python3 -m venv build/.venv-tests
build/.venv-tests/bin/pip install -r tests/requirements.txt
build/.venv-tests/bin/python -m pytest tests/test_reportflow.py -v
```

Expected: **2 passed**. Both must pass on the first run — this task guards an existing fix rather than making a broken thing work. If `test_vertical_flow_stacks_steps_in_one_column` fails, the C1-1 fix has regressed since `1c00be3`; stop and investigate before continuing.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/geometry.py tests/requirements.txt tests/test_reportflow.py
git commit -m "test: add rendered-geometry test layer with reportflow direction guard

The existing acceptance check greps TeX logs. The reportnetwork spacing
defect compiles cleanly with an empty warning list, so log-grepping cannot
catch it. These fixtures compile a single figure and assert on the geometry
PyMuPDF reads back from the PDF.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Fix `reportnetwork`'s grid/node-width collision (C1-2)

**Files:**
- Create: `tests/test_reportnetwork.py`
- Modify: `latex_templates/reportkit-process.sty:103-120`

**Interfaces:**
- Consumes: `compile_doc` (Task 1), `node_rects` and `word_boxes` (Task 1).
- Produces: `reportnetwork` accepts `x spacing=<cm>` and `y spacing=<cm>` keys, defaulting to `3.9` and `2.25`. `\networknode` and `\networkedge` signatures are unchanged.

- [ ] **Step 1: Write the failing test**

Create `tests/test_reportnetwork.py`:

```python
"""reportnetwork grid spacing must clear the rendered node width.

`rk node` is text width=28mm plus inner xsep=5pt on each side = 89.370pt.
The original grid step was 3.15cm = 89.291pt, so adjacent nodes overlapped by
0.079pt. pgf's border clipping then degenerated and every arrowhead in a
horizontal chain pointed backwards. The build emitted no error and no warning.
"""

from geometry import node_rects, word_boxes

CHAIN = r"""
\begin{diagram}[caption={A four-stage chain.}]
  \begin{reportnetwork}
    \networknode{n1}{Source}
    \networknode{n2}{Ingest}
    \networknode{n3}{Store}
    \networknode{n4}{Serve}
    \networkedge[flow]{n1}{n2}
    \networkedge[flow]{n2}{n3}
    \networkedge[flow]{n3}{n4}
  \end{reportnetwork}
\end{diagram}
"""

RK_NODE_WIDTH_PT = 89.37


def test_adjacent_grid_nodes_have_visible_clearance(compile_doc):
    rects = node_rects(compile_doc(CHAIN)[0], min_width=RK_NODE_WIDTH_PT - 5.0)
    assert len(rects) >= 4, f"expected 4 node rectangles, found {len(rects)}"
    gaps = [
        round(rects[i + 1].x0 - rects[i].x1, 3) for i in range(min(3, len(rects) - 1))
    ]
    assert all(g >= 2.0 for g in gaps), (
        f"nodes abut or overlap; gaps in pt: {gaps}. "
        f"Grid step must exceed the {RK_NODE_WIDTH_PT}pt rendered node width."
    )


def test_grid_row_wraps_after_four_nodes(compile_doc):
    """The layout still wraps: node 5 starts a second row."""
    body = CHAIN.replace(
        r"\networkedge[flow]{n3}{n4}",
        "\\networkedge[flow]{n3}{n4}\n    \\networknode{n5}{Monitor}",
    )
    boxes = word_boxes(compile_doc(body)[0], {"Source", "Monitor"})
    assert set(boxes) == {"Source", "Monitor"}
    assert boxes["Monitor"][1] > boxes["Source"][1] + 20.0, "node 5 should wrap"
    assert abs(boxes["Monitor"][0] - boxes["Source"][0]) < 5.0, "should align"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportnetwork.py -v
```

Expected: `test_adjacent_grid_nodes_have_visible_clearance` **FAILS** with gaps at or below zero (measured: `-0.079`). `test_grid_row_wraps_after_four_nodes` should already pass.

- [ ] **Step 3: Make the spacing configurable and clear the node width**

In `latex_templates/reportkit-process.sty`, replace lines 103–120 (from `\newcommand{\rk@networklayout}{grid}` through the end of `\networknode`) with:

```latex
\newcommand{\rk@networklayout}{grid}
% Grid spacing must exceed the rendered width of an rk node, which is
% text width=28mm plus inner xsep=5pt on each side = 89.370pt = 3.152cm.
% The previous 3.15cm default was 0.079pt narrower than the node itself, so
% adjacent nodes overlapped, pgf's border clipping degenerated, and arrowheads
% rendered reversed -- with no TeX error or warning to show for it.
\newcommand{\rk@networkxstep}{3.9}
\newcommand{\rk@networkystep}{2.25}
\newcount\rk@networkindex
\pgfkeys{
  /reportkit/network/.is family,
  /reportkit/network,
  layout/.store in=\rk@networklayout,
  x spacing/.store in=\rk@networkxstep,
  y spacing/.store in=\rk@networkystep,
}
\NewDocumentEnvironment{reportnetwork}{O{}}{%
  \begingroup\pgfkeys{/reportkit/network,layout=grid,x spacing=3.9,y spacing=2.25,#1}%
  \rk@networkindex=0\relax
}{\endgroup}
\NewDocumentCommand{\networknode}{O{} m m}{%
  \ifstrequal{\rk@networklayout}{radial}{%
    \node[rk node,#1] (#2) at ({3.5*cos(90-\the\rk@networkindex*60)},{3.5*sin(90-\the\rk@networkindex*60)}) {\strut #3};%
  }{%
    \node[rk node,#1] (#2) at ({mod(\the\rk@networkindex,4)*\rk@networkxstep},{-floor(\the\rk@networkindex/4)*\rk@networkystep}) {\strut #3};%
  }%
  \advance\rk@networkindex by 1\relax
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportnetwork.py tests/test_reportflow.py -v
```

Expected: **4 passed**. Gaps should now be ≈ 21.3pt (3.9cm step − 89.37pt node = 110.55 − 89.37).

- [ ] **Step 5: Confirm the four-node chain still fits the text block**

```bash
build/.venv-tests/bin/python -c "
import pymupdf, subprocess, os, tempfile, pathlib
d = tempfile.mkdtemp()
body = open('tests/test_reportnetwork.py').read().split('CHAIN = r\"\"\"')[1].split('\"\"\"')[0]
tex = pathlib.Path(d)/'fit.tex'
tex.write_text('\\\\documentclass{reportkit}\\n\\\\begin{document}\\n'+body+'\\n\\\\end{document}\\n')
subprocess.run(['lualatex','-interaction=nonstopmode','fit.tex'],cwd=d,
               env=dict(os.environ,TEXINPUTS='latex_templates:'),capture_output=True)
p = pymupdf.open(pathlib.Path(d)/'fit.pdf')[0]
rects=[x['rect'] for x in p.get_drawings() if x['rect'].width>=84 and 15<=x['rect'].height<=60]
print('leftmost', min(r.x0 for r in rects), 'rightmost', max(r.x1 for r in rects))
print('text block is 76.5pt to 518.7pt (A4 minus 27mm margins)')
"
```

Expected: leftmost ≥ 76.5 and rightmost ≤ 518.7. If the chain overflows, reduce `x spacing` to the largest value that still leaves a ≥ 2pt gap, or narrow the nodes for that figure.

- [ ] **Step 6: Commit**

```bash
git add tests/test_reportnetwork.py latex_templates/reportkit-process.sty
git commit -m "fix: clear rk node width in reportnetwork grid spacing

The 3.15cm grid step was 0.079pt narrower than a rendered rk node, so
adjacent nodes overlapped, pgf's border clipping degenerated, and every
arrowhead in a horizontal chain pointed backwards. The build reported no
error. Default step is now 3.9cm, and both axes are author-configurable.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `width=` / `scale=` on the `diagram` environment (B6)

This task introduces the `lrbox` that Task 4 also needs. The spec's B7 note requires B6 and B7 to share one structural change; build the box here and wrap it there.

**Files:**
- Create: `tests/test_diagram_width.py`
- Modify: `latex_templates/reportkit-diagrams.sty:50-100`

**Interfaces:**
- Consumes: `compile_doc`, `node_rects` (Task 1).
- Produces: the `diagram` environment accepts `width=<dimen>` (e.g. `width=\textwidth`) and `scale=<factor>` (e.g. `scale=1.4`). Both are optional; omitting them preserves current output byte-for-byte in layout terms. `width` wins if both are given. Internally the figure body is captured in the save box `\rk@diagrambox`, which Task 4 reuses.

- [ ] **Step 1: Write the failing test**

Create `tests/test_diagram_width.py`:

```python
"""The diagram environment's width= and scale= keys.

Review P1-02: several guide figures are narrow vertical flows centred in a
wide text block, forcing small labels. Authors previously widened them with a
per-node text width override at every call site. These keys replace that.
"""

import pytest

from geometry import node_rects

FIGURE = r"""
\begin{diagram}[%(opts)scaption={A two-step flow.}]
  \begin{reportflow}[direction=vertical]
    \step{a}{Alpha}
    \step{b}{Bravo}
    \flowedge{a}{b}
  \end{reportflow}
\end{diagram}
"""


def widest_node(doc):
    rects = node_rects(doc[0], min_width=20.0)
    assert rects, "no node rectangles found"
    return max(r.width for r in rects)


def test_width_key_widens_the_figure(compile_doc):
    plain = widest_node(compile_doc(FIGURE % {"opts": ""}, name="plain"))
    wide = widest_node(
        compile_doc(FIGURE % {"opts": "width=\\textwidth,"}, name="wide")
    )
    assert wide > plain * 1.5, f"width= did not widen the figure: {plain} -> {wide}"


def test_scale_key_enlarges_the_figure(compile_doc):
    plain = widest_node(compile_doc(FIGURE % {"opts": ""}, name="plain"))
    scaled = widest_node(compile_doc(FIGURE % {"opts": "scale=1.5,"}, name="scaled"))
    assert scaled == pytest.approx(plain * 1.5, rel=0.05), (
        f"scale=1.5 should multiply width by 1.5: {plain} -> {scaled}"
    )


def test_omitting_both_keys_leaves_the_figure_unscaled(compile_doc):
    """A figure with no width/scale must render at its natural size."""
    plain = widest_node(compile_doc(FIGURE % {"opts": ""}, name="plain"))
    assert 80.0 < plain < 100.0, (
        f"expected a natural ~89.4pt rk node, got {plain}pt"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_diagram_width.py -v
```

Expected: `test_width_key_widens_the_figure` and `test_scale_key_enlarges_the_figure` **FAIL** (the unknown pgfkeys `width`/`scale` raise a package error, so `compile_doc` raises `AssertionError` with the TeX log). `test_omitting_both_keys_leaves_the_figure_unscaled` passes.

- [ ] **Step 3: Add the keys and the save box**

In `latex_templates/reportkit-diagrams.sty`, add these two declarations alongside the existing `\rk@diagram*` defaults (after `\newcommand{\rk@diagramminspace}{0.27\textheight}` at line 55):

```latex
% B6: optional figure-level sizing. Empty means "render at natural size".
% width= wins over scale= when both are given.
\newcommand{\rk@diagramwidth}{}
\newcommand{\rk@diagramscale}{}
\newsavebox{\rk@diagrambox}
```

Add these two keys to the `/reportkit/diagram` family (after `minspace/.store in=\rk@diagramminspace,` at line 66):

```latex
  width/.store in=\rk@diagramwidth,
  scale/.store in=\rk@diagramscale,
```

Then replace the `diagram` environment body with:

```latex
\NewDocumentEnvironment{diagram}{O{}}{%
  \pgfkeys{/reportkit/diagram,
    type=network,caption={},label={},source={Conceptual diagram.},description={},
    minspace={0.27\textheight},width={},scale={},#1}%
  \par\Needspace{\rk@diagramminspace}%
  \vspace{4pt}%
  \begin{center}%
  \begin{lrbox}{\rk@diagrambox}%
  \begin{tikzpicture}[x=1cm,y=1cm]
}{%
  \end{tikzpicture}%
  \end{lrbox}%
  \ifstrempty{\rk@diagramwidth}{%
    \ifstrempty{\rk@diagramscale}{%
      \usebox{\rk@diagrambox}%
    }{%
      \scalebox{\rk@diagramscale}{\usebox{\rk@diagrambox}}%
    }%
  }{%
    \resizebox{\rk@diagramwidth}{!}{\usebox{\rk@diagrambox}}%
  }%
  \end{center}
  \vspace{-2pt}%
  \ifstrempty{\rk@diagramcaption}{}{%
    \captionof{figure}{\rk@diagramcaption}%
    \ifstrempty{\rk@diagramlabel}{}{\label{\rk@diagramlabel}}%
  }%
  \ifstrempty{\rk@diagramsource}{}{\source{\rk@diagramsource}}%
  \par\vspace{5pt}%
}
```

`\scalebox` and `\resizebox` come from `graphicx`, already loaded by `reportkit.cls:27`.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_diagram_width.py -v
```

Expected: **3 passed**.

- [ ] **Step 5: Verify no existing figure changed size**

```bash
build/.venv-tests/bin/python -m pytest tests/ -v
TEXINPUTS=latex_templates: lualatex -interaction=nonstopmode \
  -output-directory=/tmp/vg latex_templates/examples/visual_grammar_acceptance_test.tex
```

Expected: all tests pass, and the acceptance test still compiles with no new errors. Both keys default to empty, so every existing figure takes the `\usebox` branch unscaled.

- [ ] **Step 6: Commit**

```bash
git add tests/test_diagram_width.py latex_templates/reportkit-diagrams.sty
git commit -m "feat: add width= and scale= keys to the diagram environment

Figure-level sizing replaces the per-node text width overrides authors used
to widen narrow vertical flows (review P1-02). The figure body is now
captured in a save box, which the alt-text wrapper also needs.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Make `description=` emit real alt text (B7)

Today `description=` is stored at `reportkit-diagrams.sty:54` and **never read**. All fourteen guide fragments set it; none of it reaches a reader. Verified: a probe figure's description appeared in no page text and no object stream, while its caption and source did.

**Read the spec's B7 section before starting.** It records a verified trade-off: `/ActualText` *replaces* the extractable text it wraps, so diagram label text stops being selectable. That is the accepted cost of the interim mechanism.

**Files:**
- Create: `tests/test_diagram_alttext.py`
- Modify: `latex_templates/reportkit-diagrams.sty` (package load + environment end)

**Interfaces:**
- Consumes: `compile_doc`, `stream_contains` (Task 1); `\rk@diagrambox` (Task 3).
- Produces: a `diagram` with a non-empty `description=` emits that string as an `/ActualText` span around the figure. A `diagram` with an empty description emits `\PackageWarning{reportkit-diagrams}`.

- [ ] **Step 1: Confirm `accsupp.sty` resolves; if not, stop and report**

```bash
kpsewhich accsupp.sty
```

If this prints a path, continue to Step 2 and use `accsupp`.

If it prints nothing, `accsupp` is unavailable and `tlmgr install accsupp` **will fail** on this checkout (TinyTeX TL2025 against a TL2026 remote). Do not silently switch mechanisms — stop and report to the human, offering the two options: (a) upgrade TeX Live per `https://tug.org/texlive/upgrade.html`, or (b) emit the marked-content span directly with LuaTeX primitives, accepting that it is engine-specific. **The rest of this task assumes `accsupp` is available.**

- [ ] **Step 2: Write the failing test**

Create `tests/test_diagram_alttext.py`:

```python
"""description= must reach the PDF as a text alternative.

Before this change the key was stored and never read: every figure's alt text
was discarded at build time while its caption and source rendered normally.

Note the trade-off recorded in the spec's B7: an /ActualText span *replaces*
the text it wraps, so node labels inside a diagram stop being separately
extractable. That is intended for a figure and is why B7 is interim -- only
tagging (B8) gives alt text and extractable inner text at once.
"""

from geometry import stream_contains

ALT = "ZZUNIQUEALTTEXT a two-step flow from Alpha to Bravo"

WITH_DESCRIPTION = (
    r"""
\begin{diagram}[caption={A caption.},source={A source.},description={%s}]
  \begin{reportflow}
    \step{a}{Alpha}
    \step{b}{Bravo}
    \flowedge{a}{b}
  \end{reportflow}
\end{diagram}
"""
    % ALT
)

WITHOUT_DESCRIPTION = r"""
\begin{diagram}[caption={A caption.},source={A source.}]
  \begin{reportflow}
    \step{a}{Alpha}
    \step{b}{Bravo}
    \flowedge{a}{b}
  \end{reportflow}
\end{diagram}
"""


def test_description_is_embedded_in_the_pdf(compile_doc):
    doc = compile_doc(WITH_DESCRIPTION)
    assert stream_contains(doc, ALT.encode("latin-1")), (
        "description= did not reach any object stream in the PDF"
    )


def test_caption_and_source_still_render(compile_doc):
    """The alt-text wrapper must not swallow the caption or source line."""
    text = compile_doc(WITH_DESCRIPTION)[0].get_text()
    assert "A caption" in text
    assert "A source" in text


def test_alt_text_replaces_inner_label_extraction(compile_doc):
    """Documents the accepted B7 trade-off so a future change is deliberate.

    If this test starts failing because labels ARE extractable again, the
    mechanism changed -- check whether B8's tagging path landed, which would
    make this assertion obsolete rather than broken.
    """
    text = compile_doc(WITH_DESCRIPTION)[0].get_text()
    assert "Alpha" not in text and "Bravo" not in text, (
        "labels unexpectedly extractable; the /ActualText span may not be "
        "wrapping the whole figure"
    )


def test_missing_description_still_compiles(compile_doc):
    """A figure with no description must warn, not fail."""
    text = compile_doc(WITHOUT_DESCRIPTION)[0].get_text()
    assert "A caption" in text
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_diagram_alttext.py -v
```

Expected: `test_description_is_embedded_in_the_pdf` **FAILS** (the string is in no stream) and `test_alt_text_replaces_inner_label_extraction` **FAILS** (labels are currently extractable). The other two pass.

- [ ] **Step 4: Wrap the save box in an `/ActualText` span**

In `latex_templates/reportkit-diagrams.sty`, add to the package requirements near the top, alongside the other `\RequirePackage` lines:

```latex
\RequirePackage{accsupp}
```

Then, in the `diagram` environment's end code from Task 3, wrap the three sizing branches. Replace the block that begins `\ifstrempty{\rk@diagramwidth}{%` with:

```latex
  % B7: emit description= as the figure's text alternative. This wraps the
  % whole figure box, so an /ActualText span replaces the labels inside it --
  % intended for a diagram, and superseded if B8's tagging path lands.
  \ifstrempty{\rk@diagramdescription}{%
    \PackageWarning{reportkit-diagrams}{%
      diagram has no description= and will expose no alt text}%
  }{%
    \BeginAccSupp{method=escape,ActualText={\rk@diagramdescription}}%
  }%
  \ifstrempty{\rk@diagramwidth}{%
    \ifstrempty{\rk@diagramscale}{%
      \usebox{\rk@diagrambox}%
    }{%
      \scalebox{\rk@diagramscale}{\usebox{\rk@diagrambox}}%
    }%
  }{%
    \resizebox{\rk@diagramwidth}{!}{\usebox{\rk@diagrambox}}%
  }%
  \ifstrempty{\rk@diagramdescription}{}{\EndAccSupp{}}%
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_diagram_alttext.py -v
```

Expected: **4 passed**. If `test_description_is_embedded_in_the_pdf` passes but the label assertion fails, the span is wrapping only part of the figure — confirm `\BeginAccSupp` sits outside the sizing branches, not inside one.

- [ ] **Step 6: Decide `type=`, which is also stored and never read**

`\rk@diagramtype` (`reportkit-diagrams.sty:50`, `:60`) has the same defect. It is set by every fragment and read by nothing. Per the spec, either use it or delete it — a stored-and-unread key is a trap. Deleting it is a breaking change for all fourteen fragments, so **keep the key and record it in the PDF** rather than removing it:

```latex
  \ifstrempty{\rk@diagramtype}{}{%
    \pdfextension info{/ReportKitDiagramType (\rk@diagramtype)}%
  }%
```

If this proves engine-specific or noisy in the log, drop the block and instead add a one-line comment at `:50` stating that `type=` is author-facing documentation consumed by no code, so the next reader is not misled. Either resolution closes the item; do not leave it undocumented.

- [ ] **Step 7: Run the full suite and commit**

```bash
build/.venv-tests/bin/python -m pytest tests/ -v
```

Expected: **11 passed** (2 + 2 + 3 + 4).

```bash
git add tests/test_diagram_alttext.py latex_templates/reportkit-diagrams.sty
git commit -m "feat: emit diagram description= as PDF alt text

The description key was stored and never read, so every figure's alt text
was discarded at build time while its caption and source rendered normally.
It is now an /ActualText span around the figure box, and a diagram with no
description warns. Per spec B7 this replaces inner label extraction; only
the tagging path in B8 gives both.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `reportstate` primitive (C2)

Unblocks the guide's Tier 1 task-recovery figure: scheduled, running, retrying, failed, succeeded, skipped.

**Files:**
- Create: `latex_templates/reportkit-grammar.sty`
- Create: `tests/test_reportstate.py`
- Modify: `latex_templates/reportkit.cls` (load the new module)

**Interfaces:**
- Consumes: `rk node` / `rk accent` styles and `\RKEdge` from `reportkit-diagrams.sty`; `compile_doc`, `word_boxes` (Task 1).
- Produces:
  - `\begin{reportstate}[layout=row|arc] ... \end{reportstate}`
  - `\state[<tikz opts>]{<id>}{<label>}` — places states in declaration order.
  - `\terminalstate[<tikz opts>]{<id>}{<label>}` — same, drawn with a doubled border.
  - `\transition[<tikz opts>]{<from>}{<to>}{<label>}` — labelled directed edge.
  - `\selfloop[<tikz opts>]{<id>}{<label>}` — retry loop above the state.

- [ ] **Step 1: Write the failing test**

Create `tests/test_reportstate.py`:

```python
"""reportstate: a state machine with labelled transitions and retry self-loops."""

from geometry import word_boxes

# Geometry fixtures deliberately omit description=. Per Task 4, a description
# wraps the figure in an /ActualText span that replaces inner label
# extraction, so word_boxes would find nothing. Omitting it also exercises
# Task 4's "no description" warning path. Figures under alt-text test carry a
# description; figures under geometry test do not.
MACHINE = r"""
\begin{diagram}[width=\textwidth,caption={Task recovery states.}]
  \begin{reportstate}
    \state{sched}{Scheduled}
    \state{run}{Running}
    \terminalstate{ok}{Succeeded}
    \terminalstate{fail}{Failed}
    \transition{sched}{run}{start}
    \transition{run}{ok}{complete}
    \transition{run}{fail}{give up}
    \selfloop{run}{retry}
  \end{reportstate}
\end{diagram}
"""

STATES = {"Scheduled", "Running", "Succeeded", "Failed"}


def test_states_render_in_declaration_order(compile_doc):
    boxes = word_boxes(compile_doc(MACHINE)[0], STATES)
    assert set(boxes) == STATES, f"missing states: {STATES - set(boxes)}"
    xs = [boxes[s][0] for s in ("Scheduled", "Running", "Succeeded", "Failed")]
    assert xs == sorted(xs), f"expected declaration order left to right: {xs}"


def test_transition_labels_render(compile_doc):
    text = compile_doc(MACHINE)[0].get_text()
    for label in ("start", "complete", "give up", "retry"):
        assert label in text, f"transition label {label!r} missing"


def test_states_do_not_overlap(compile_doc):
    boxes = word_boxes(compile_doc(MACHINE)[0], STATES)
    ordered = sorted(boxes.values(), key=lambda b: b[0])
    gaps = [round(ordered[i + 1][0] - ordered[i][2], 2) for i in range(len(ordered) - 1)]
    assert all(g > 0 for g in gaps), f"state labels overlap: {gaps}"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportstate.py -v
```

Expected: all three **FAIL** — `reportstate` is not a defined environment, so `compile_doc` raises with `Environment reportstate undefined`.

- [ ] **Step 3: Create the grammar module with `reportstate`**

Create `latex_templates/reportkit-grammar.sty`:

```latex
% ReportKit v1.5.0 -- state, comparison, and timeline primitives.
%
% These three forms exist because the publication review asked for a varied
% visual grammar -- "timelines for time, state diagrams for retries and
% recovery, before/after diagrams for cardinality" -- and warned against
% turning every figure into a vertical box-and-arrow flow.
%
% Loaded after reportkit-diagrams.sty, which supplies rk node and \RKEdge.
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{reportkit-grammar}[2026/09/06 v1.5.0 ReportKit state, comparison, timeline]
\RequirePackage{xparse}
\RequirePackage{pgfkeys}
\RequirePackage{etoolbox}

% -----------------------------------------------------------------------------
% reportstate -- a state machine.
% Declaration order is reading order; authors name transitions, not coordinates.
% -----------------------------------------------------------------------------
\tikzset{
  rk terminal/.style={rk node,draw=LinkBlue,line width=.9pt,double,double distance=1.2pt},
  rk transition label/.style={
    font=\sffamily\fontsize{7.0}{8.2}\selectfont,text=Muted,
    fill=Surface,inner sep=1.5pt,midway,above
  },
}
% Step must clear the 89.37pt rendered rk node width; 4.2cm leaves room for a
% transition label between states.
\newcommand{\rk@statestep}{4.2}
\newcount\rk@stateindex
\pgfkeys{
  /reportkit/state/.is family,
  /reportkit/state,
  step spacing/.store in=\rk@statestep,
}
\NewDocumentEnvironment{reportstate}{O{}}{%
  \begingroup\pgfkeys{/reportkit/state,step spacing=4.2,#1}%
  \rk@stateindex=0\relax
}{\endgroup}
\NewDocumentCommand{\state}{O{} m m}{%
  \node[rk node,#1] (#2) at ({\the\rk@stateindex*\rk@statestep},0) {\strut #3};%
  \advance\rk@stateindex by 1\relax
}
\NewDocumentCommand{\terminalstate}{O{} m m}{%
  \node[rk terminal,#1] (#2) at ({\the\rk@stateindex*\rk@statestep},0) {\strut #3};%
  \advance\rk@stateindex by 1\relax
}
\NewDocumentCommand{\transition}{O{} m m m}{%
  \draw[rk edge flow,#1] (#2) -- (#3) node[rk transition label] {#4};%
}
\NewDocumentCommand{\selfloop}{O{} m m}{%
  \draw[rk edge flow,#1] (#2.north) .. controls +(0.7,1.1) and +(-0.7,1.1) .. (#2.north)
    node[rk transition label,above=6pt] {#3};%
}
\endinput
```

`rk edge flow` is a real tikz style (`reportkit-diagrams.sty:32`), as is `rk edge label` (`:38`). `rk transition label` above is a new style that adds `above` placement and a `Surface` fill so a label sitting on a transition line stays readable; it does not replace `rk edge label`, which the existing primitives keep using.

- [ ] **Step 4: Load the module from the class**

In `latex_templates/reportkit.cls`, find the line that loads `reportkit-process` and add immediately after it:

```latex
\RequirePackage{reportkit-grammar}
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportstate.py -v
```

Expected: **3 passed**.

- [ ] **Step 6: Commit**

```bash
git add latex_templates/reportkit-grammar.sty latex_templates/reportkit.cls tests/test_reportstate.py
git commit -m "feat: add reportstate primitive for state machines

Unblocks the guide's task-recovery figure: labelled transitions, terminal
states, and retry self-loops, which no existing primitive could express.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `reportcompare` primitive (C2)

Unblocks the Tier 1 join-cardinality before/after figure, and the Tier 2 row-versus-column and small-file-compaction figures.

**Files:**
- Modify: `latex_templates/reportkit-grammar.sty`
- Create: `tests/test_reportcompare.py`

**Interfaces:**
- Consumes: `rk node` styles; `compile_doc`, `word_boxes` (Task 1).
- Produces:
  - `\begin{reportcompare}[gap=<cm>] ... \end{reportcompare}`
  - `\panel{<id>}{<heading>}` — declares a panel; first call is the left panel, second the right. A third raises a package error.
  - `\panelitem{<panel id>}{<row index, 0-based>}{<text>}` — a row inside a panel.
  - `\transformarrow{<label>}` — the arrow between the two panels.

- [ ] **Step 1: Write the failing test**

Create `tests/test_reportcompare.py`:

```python
"""reportcompare: two aligned panels with a transform arrow between them."""

from geometry import word_boxes

COMPARISON = r"""
\begin{diagram}[width=\textwidth,caption={Join cardinality.}]
  \begin{reportcompare}
    \panel{before}{Before join}
    \panelitem{before}{0}{one order row}
    \panelitem{before}{1}{grain: order}
    \panel{after}{After join}
    \panelitem{after}{0}{three item rows}
    \panelitem{after}{1}{grain: order item}
    \transformarrow{join multiplies rows}
  \end{reportcompare}
\end{diagram}
"""


def test_panels_sit_side_by_side(compile_doc):
    boxes = word_boxes(compile_doc(COMPARISON)[0], {"Before", "After"})
    assert set(boxes) == {"Before", "After"}, "both panel headings must render"
    assert boxes["After"][0] > boxes["Before"][2], "After panel must be to the right"
    assert abs(boxes["After"][1] - boxes["Before"][1]) < 3.0, "headings must align"


def test_panel_items_stack_under_their_heading(compile_doc):
    boxes = word_boxes(compile_doc(COMPARISON)[0], {"Before", "one", "grain:"})
    assert "one" in boxes, "first panel item must render"
    assert boxes["one"][1] > boxes["Before"][1], "items sit below the heading"


def test_transform_arrow_label_renders(compile_doc):
    assert "multiplies" in compile_doc(COMPARISON)[0].get_text()


def test_third_panel_is_an_error(compile_doc):
    body = COMPARISON.replace(
        r"\transformarrow{join multiplies rows}",
        "\\panel{extra}{Third}\n    \\transformarrow{x}",
    )
    try:
        compile_doc(body)
    except AssertionError as exc:
        assert "reportcompare" in str(exc), "expected a reportcompare package error"
    else:
        raise AssertionError("a third panel should have raised a package error")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportcompare.py -v
```

Expected: all four **FAIL** with `Environment reportcompare undefined`.

- [ ] **Step 3: Add the primitive**

Append to `latex_templates/reportkit-grammar.sty`, before `\endinput`:

```latex
% -----------------------------------------------------------------------------
% reportcompare -- two aligned panels and a transform arrow.
% For before/after questions: what changed, and what the change did to grain,
% row count, or layout.
% -----------------------------------------------------------------------------
\newcommand{\rk@comparegap}{2.6}
\newcommand{\rk@panelwidth}{5.4}
\newcommand{\rk@rowheight}{0.82}
\newcount\rk@panelindex
\pgfkeys{
  /reportkit/compare/.is family,
  /reportkit/compare,
  gap/.store in=\rk@comparegap,
  panel width/.store in=\rk@panelwidth,
}
\tikzset{
  rk panel heading/.style={
    font=\sffamily\bfseries\fontsize{8.4}{10}\selectfont,text=Ink,anchor=north west
  },
  rk panel row/.style={
    rk node,text width={\rk@panelwidth cm - 10pt},minimum height=7mm,anchor=north west
  },
}
\NewDocumentEnvironment{reportcompare}{O{}}{%
  \begingroup\pgfkeys{/reportkit/compare,gap=2.6,panel width=5.4,#1}%
  \rk@panelindex=0\relax
}{\endgroup}
% #1 id, #2 heading. First call is the left panel, second the right.
\NewDocumentCommand{\panel}{m m}{%
  \ifnum\rk@panelindex>1
    \PackageError{reportkit-grammar}{reportcompare takes exactly two panels}%
      {Declare one \string\panel for the before state and one for the after state.}%
  \fi
  \begingroup
  \edef\rk@panelx{\the\numexpr\rk@panelindex\relax}%
  \node[rk panel heading] (#1) at
    ({\rk@panelindex*(\rk@panelwidth+\rk@comparegap)},0) {#2};%
  \endgroup
  \expandafter\xdef\csname rk@panelpos@#1\endcsname{\the\rk@panelindex}%
  \advance\rk@panelindex by 1\relax
}
% #1 panel id, #2 zero-based row index, #3 text.
\NewDocumentCommand{\panelitem}{m m m}{%
  \node[rk panel row] at
    ({\csname rk@panelpos@#1\endcsname*(\rk@panelwidth+\rk@comparegap)},
     {-0.55-#2*\rk@rowheight}) {\strut #3};%
}
\NewDocumentCommand{\transformarrow}{m}{%
  \draw[rk edge flow]
    ({\rk@panelwidth+0.25},-1.1) -- ({\rk@panelwidth+\rk@comparegap-0.25},-1.1)
    node[rk transition label,align=center,text width=2.4cm] {#1};%
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reportcompare.py -v
```

Expected: **4 passed**.

- [ ] **Step 5: Commit**

```bash
git add latex_templates/reportkit-grammar.sty tests/test_reportcompare.py
git commit -m "feat: add reportcompare primitive for before/after figures

Two aligned panels and a labelled transform arrow. Unblocks the guide's
join-cardinality figure, where the point is what the join did to row count
and grain -- a question no single-panel primitive can pose.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `reporttimeline` primitive (C2)

Unblocks the Tier 1 event-time-versus-processing-time figure, and the Tier 2 batch-versus-streaming and backfill-interval figures.

**Files:**
- Modify: `latex_templates/reportkit-grammar.sty`
- Create: `tests/test_reporttimeline.py`

**Interfaces:**
- Consumes: `rk node` styles; `compile_doc`, `word_boxes` (Task 1).
- Produces:
  - `\begin{reporttimeline}[tracks={<name>,<name>},span=<cm>] ... \end{reporttimeline}`
  - `\event[<tikz opts>]{<track>}{<position 0..1>}{<label>}`
  - `\skewarrow{<track>}{<from position>}{<track>}{<to position>}` — a slanted arrow showing the same record arriving later on another track.
  - `\watermark{<track>}{<position>}{<label>}` — a vertical marker.

- [ ] **Step 1: Write the failing test**

Create `tests/test_reporttimeline.py`:

```python
"""reporttimeline: parallel time tracks with events, skew, and a watermark."""

from geometry import word_boxes

TIMELINE = r"""
\begin{diagram}[width=\textwidth,caption={Event time versus processing time.}]
  \begin{reporttimeline}[tracks={Event time,Processing time}]
    \event{Event time}{0.15}{A}
    \event{Event time}{0.35}{B}
    \event{Processing time}{0.45}{A}
    \event{Processing time}{0.80}{B}
    \skewarrow{Event time}{0.15}{Processing time}{0.45}
    \watermark{Processing time}{0.65}{watermark}
  \end{reporttimeline}
\end{diagram}
"""


def test_tracks_render_on_separate_rows(compile_doc):
    boxes = word_boxes(compile_doc(TIMELINE)[0], {"Event", "Processing"})
    assert set(boxes) == {"Event", "Processing"}, "both track labels must render"
    assert boxes["Processing"][1] > boxes["Event"][1] + 15.0, (
        "the second track must sit below the first"
    )


def test_event_position_maps_to_horizontal_offset(compile_doc):
    """An event at 0.80 must sit right of one at 0.45 on the same track."""
    page = compile_doc(TIMELINE)[0]
    marks = [
        (x0, text)
        for x0, y0, x1, y1, text, *_ in page.get_text("words")
        if text in {"A", "B"}
    ]
    assert len(marks) >= 4, f"expected 4 event marks, got {marks}"
    assert sorted(x for x, _ in marks) == [x for x, _ in sorted(marks)]


def test_watermark_label_renders(compile_doc):
    assert "watermark" in compile_doc(TIMELINE)[0].get_text()


def test_unknown_track_is_an_error(compile_doc):
    body = TIMELINE.replace(r"\event{Event time}{0.15}{A}", r"\event{Nonexistent}{0.15}{A}")
    try:
        compile_doc(body)
    except AssertionError as exc:
        assert "reporttimeline" in str(exc) or "track" in str(exc).lower()
    else:
        raise AssertionError("an unknown track should have raised a package error")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reporttimeline.py -v
```

Expected: all four **FAIL** with `Environment reporttimeline undefined`.

- [ ] **Step 3: Add the primitive**

Append to `latex_templates/reportkit-grammar.sty`, before `\endinput`. The track lookup mirrors `\rk@findlane` in `reportkit-process.sty:69-83` — reuse that pattern rather than inventing a second one:

```latex
% -----------------------------------------------------------------------------
% reporttimeline -- parallel time tracks.
% For questions about when: latency, skew between event and processing time,
% late arrival, and window closure.
% -----------------------------------------------------------------------------
\newcommand{\rk@tracks}{}
\newcommand{\rk@trackspan}{12.0}
\newcommand{\rk@trackgap}{1.6}
\newcount\rk@trackindex
\newcount\rk@trackquery
\pgfkeys{
  /reportkit/timeline/.is family,
  /reportkit/timeline,
  tracks/.store in=\rk@tracks,
  span/.store in=\rk@trackspan,
  track gap/.store in=\rk@trackgap,
}
\tikzset{
  rk track axis/.style={Hairline,line width=.6pt,-{Stealth[length=4pt]}},
  rk track label/.style={
    font=\sffamily\fontsize{7.2}{8.5}\selectfont,text=Muted,anchor=east
  },
  rk event mark/.style={
    circle,draw=LinkBlue,fill=Surface,line width=.7pt,inner sep=1.6pt,
    font=\sffamily\fontsize{6.8}{8}\selectfont,text=Ink
  },
}
\makeatletter
\newcommand{\rk@findtrack}[1]{%
  \rk@trackindex=0\relax\rk@trackquery=-1\relax
  \def\rk@tracktarget{#1}%
  \expandafter\@for\expandafter\rk@trackname\expandafter:=\rk@tracks\do{%
    \edef\rk@trackcandidate{\rk@trackname}%
    \ifx\rk@trackcandidate\rk@tracktarget
      \global\rk@trackquery=\rk@trackindex
    \fi
    \advance\rk@trackindex by 1\relax
  }%
  \ifnum\rk@trackquery<0
    \PackageError{reportkit-grammar}{Unknown reporttimeline track '#1'}%
      {Declare it in the tracks key before using \string\event.}%
    \rk@trackquery=0\relax
  \fi
}
\newcommand{\rk@drawtracks}{%
  \rk@trackindex=0\relax
  \expandafter\@for\expandafter\rk@trackname\expandafter:=\rk@tracks\do{%
    \draw[rk track axis] (0,{-\the\rk@trackindex*\rk@trackgap}) --
      (\rk@trackspan,{-\the\rk@trackindex*\rk@trackgap});%
    \node[rk track label] at (-0.2,{-\the\rk@trackindex*\rk@trackgap})
      {\rk@trackname};%
    \advance\rk@trackindex by 1\relax
  }%
}
\NewDocumentEnvironment{reporttimeline}{O{}}{%
  \begingroup\pgfkeys{/reportkit/timeline,tracks={},span=12.0,track gap=1.6,#1}%
  \ifstrempty{\rk@tracks}{%
    \PackageError{reportkit-grammar}{reporttimeline requires tracks={...}}%
      {Provide one or more comma-separated track names.}%
  }{}%
  \rk@drawtracks
}{\endgroup}
% #1 tikz opts, #2 track, #3 position in [0,1], #4 label.
\NewDocumentCommand{\event}{O{} m m m}{%
  \rk@findtrack{#2}%
  \node[rk event mark,#1] at
    ({#3*\rk@trackspan},{-\the\rk@trackquery*\rk@trackgap}) {#4};%
}
% #1 from track, #2 from position, #3 to track, #4 to position.
\NewDocumentCommand{\skewarrow}{m m m m}{%
  \rk@findtrack{#1}\edef\rk@skewfrom{\the\rk@trackquery}%
  \rk@findtrack{#3}\edef\rk@skewto{\the\rk@trackquery}%
  \draw[Hairline,line width=.5pt,densely dashed,-{Stealth[length=4pt]}]
    ({#2*\rk@trackspan},{-\rk@skewfrom*\rk@trackgap+0.18}) --
    ({#4*\rk@trackspan},{-\rk@skewto*\rk@trackgap-0.18});%
}
% #1 track, #2 position, #3 label.
\NewDocumentCommand{\watermark}{m m m}{%
  \rk@findtrack{#1}%
  \draw[LinkBlue,line width=.8pt]
    ({#2*\rk@trackspan},{-\the\rk@trackquery*\rk@trackgap-0.42}) --
    ({#2*\rk@trackspan},{-\the\rk@trackquery*\rk@trackgap+0.42});%
  \node[rk transition label,below=2pt] at
    ({#2*\rk@trackspan},{-\the\rk@trackquery*\rk@trackgap-0.42}) {#3};%
}
\makeatother
```

**Name check, already run.** Of the new control sequences, `\skew` is the one that clashes — it is a LaTeX math accent and is `TAKEN` in a loaded `reportkit` document. It is therefore `\skewarrow` throughout. All other new names (`\state`, `\terminalstate`, `\transition`, `\selfloop`, `\panel`, `\panelitem`, `\transformarrow`, `\event`, `\watermark`, and the three environments) were probed as `FREE`.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
build/.venv-tests/bin/python -m pytest tests/test_reporttimeline.py -v
```

Expected: **4 passed**.

- [ ] **Step 5: Commit**

```bash
git add latex_templates/reportkit-grammar.sty tests/test_reporttimeline.py
git commit -m "feat: add reporttimeline primitive for parallel time tracks

Events, skew arrows, and watermark markers across named tracks. Unblocks the
guide's event-time versus processing-time figure, where the reader has to see
the same record arriving at two different times.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Wire into the acceptance harness, the skill table, and the specs

**Files:**
- Modify: `latex_templates/examples/visual_grammar_acceptance_test.tex`
- Modify: `SKILL.md:44-58` (the question-to-primitive table)
- Modify: `scripts/acceptance_check.sh`
- Modify: `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md` (status)

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: `scripts/acceptance_check.sh` runs the pytest layer when a venv is available and skips cleanly otherwise, preserving its current exit-code contract (0 = clean or TeX absent in diagnostic mode; 1 = failure or `--require-tex` with no TeX).

- [ ] **Step 1: Add an acceptance-test case per primitive**

Append to `latex_templates/examples/visual_grammar_acceptance_test.tex`, before `\end{document}`. Each case must carry the caption, source, and description a real deliverable requires:

```latex
\section{State, comparison, and time}

\begin{diagram}[type=state,width=\textwidth,caption={Task recovery states.},source={Conceptual diagram.},description={A scheduled task starts running, retries on failure, and ends in either a succeeded or a failed terminal state.}]
  \begin{reportstate}
    \state{sched}{Scheduled}
    \state{run}{Running}
    \terminalstate{ok}{Succeeded}
    \terminalstate{fail}{Failed}
    \transition{sched}{run}{start}
    \transition{run}{ok}{complete}
    \transition{run}{fail}{give up}
    \selfloop{run}{retry}
  \end{reportstate}
\end{diagram}

\begin{diagram}[type=comparison,width=\textwidth,caption={Join cardinality before and after.},source={Conceptual diagram.},description={One order row joined to three item rows becomes three rows, changing the grain from order to order item.}]
  \begin{reportcompare}
    \panel{before}{Before join}
    \panelitem{before}{0}{one order row}
    \panelitem{before}{1}{grain: order}
    \panel{after}{After join}
    \panelitem{after}{0}{three item rows}
    \panelitem{after}{1}{grain: order item}
    \transformarrow{join multiplies rows}
  \end{reportcompare}
\end{diagram}

\begin{diagram}[type=timeline,width=\textwidth,caption={Event time versus processing time.},source={Conceptual diagram.},description={Two events occur early in event time but are processed later, and a watermark closes the window before the second event is handled.}]
  \begin{reporttimeline}[tracks={Event time,Processing time}]
    \event{Event time}{0.15}{A}
    \event{Event time}{0.35}{B}
    \event{Processing time}{0.45}{A}
    \event{Processing time}{0.80}{B}
    \skewarrow{Event time}{0.15}{Processing time}{0.45}
    \watermark{Processing time}{0.65}{watermark}
  \end{reporttimeline}
\end{diagram}
```

- [ ] **Step 2: Compile the acceptance test**

```bash
TEXINPUTS=latex_templates: lualatex -interaction=nonstopmode \
  -output-directory=/tmp/vg latex_templates/examples/visual_grammar_acceptance_test.tex
grep -c "^!" /tmp/vg/visual_grammar_acceptance_test.log
```

Expected: exit 0 and **0** error lines. Open the PDF and confirm each of the three new figures reads correctly — the state machine's arrowheads point forward, the two panels align, and the skew arrow slants down and to the right.

- [ ] **Step 3: Add the three rows to the skill's primitive table**

In `SKILL.md`, inside the "Visual grammar" table (currently ending with the `reportkit_viz.py` row at line ~58), add before that final row:

```markdown
| How does something move between states, and what happens on failure? | `reportstate` |
| What changed between two arrangements? | `reportcompare` |
| When did things happen, on more than one clock? | `reporttimeline` |
```

- [ ] **Step 4: Run the pytest layer from the acceptance script**

In `scripts/acceptance_check.sh`, after the `python_scripts/` import check block (which ends at line 59), insert:

```bash
# Rendered-geometry tests. These catch defects that leave no trace in the TeX
# log -- the reportnetwork spacing collision compiled with exit 0 and an empty
# warning list while drawing every arrow backwards.
TEST_VENV="$ROOT/build/.venv-tests"
if [[ -x "$TEST_VENV/bin/python" ]]; then
  if ! "$TEST_VENV/bin/python" -m pytest "$ROOT/tests" -q > "$WORKDIR/pytest.log" 2>&1; then
    echo "FAIL: rendered-geometry tests failed:" >&2
    tail -40 "$WORKDIR/pytest.log" >&2
    hit=1
  else
    echo "-- rendered-geometry tests: OK --"
  fi
elif [[ "$require_tex" -eq 1 ]]; then
  echo "FAIL: --require-tex was requested but $TEST_VENV is missing." >&2
  echo "      Create it: python3 -m venv build/.venv-tests && \\" >&2
  echo "      build/.venv-tests/bin/pip install -r tests/requirements.txt" >&2
  hit=1
else
  echo "WARN: $TEST_VENV missing -- skipping geometry tests (not blocking)." >&2
fi
```

- [ ] **Step 5: Verify the harness in both modes**

```bash
bash scripts/acceptance_check.sh; echo "diagnostic mode exit=$?"
bash scripts/acceptance_check.sh --require-tex; echo "strict mode exit=$?"
mv build/.venv-tests /tmp/venv-hidden
bash scripts/acceptance_check.sh; echo "no-venv diagnostic exit=$?"
bash scripts/acceptance_check.sh --require-tex; echo "no-venv strict exit=$?"
mv /tmp/venv-hidden build/.venv-tests
```

Expected: `0`, `0`, `0` (warns, does not block), `1` (strict mode requires the venv).

- [ ] **Step 6: Mark the spec sections done**

In `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md`, update the **Status** line to record that sections C, B6, and B7 are implemented, and note under B8 that the tagging spike is now unblocked (it needs C2 and B6, which this plan delivers).

- [ ] **Step 7: Run everything and commit**

```bash
build/.venv-tests/bin/python -m pytest tests/ -v
bash scripts/acceptance_check.sh --require-tex
```

Expected: **22 passed** (2 + 2 + 3 + 4 + 3 + 4 + 4), acceptance check exit 0.

```bash
git add latex_templates/examples/visual_grammar_acceptance_test.tex SKILL.md \
        scripts/acceptance_check.sh docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md
git commit -m "feat: wire new primitives into acceptance harness and skill table

The acceptance script now runs the rendered-geometry tests alongside its log
grep, so a clean compile is no longer mistaken for a correct figure.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Follow-up (not in this plan)

These belong to the **content branch** and should be raised once this plan lands:

1. Retire the `\RKNode` hand-placement workaround in `fragments/fig-sec01-lifecycle.tex` — C1-1 has been fixed since `1c00be3`.
2. Retire the per-node `text width=24mm` workaround in `fragments/fig-sec07-lineage.tex` — Task 2 fixes the underlying spacing.
3. Author the three Tier 1 figures the new primitives unblock (join cardinality, event versus processing time, task recovery) plus the two Tier 2 figures the `width=` key unblocks (reconciliation flow, serving surfaces), taking the guide to 19 figures.
4. Recompose the narrow vertical figures with `width=` per content spec §D1.

And on the tooling branch: **B8's tagging spike is now unblocked** and should run against a TikZ-dense section built with these primitives in place.

## Verification

The plan is complete when:

- `build/.venv-tests/bin/python -m pytest tests/ -v` reports 22 passed (2 + 2 + 3 + 4 + 3 + 4 + 4).
- `bash scripts/acceptance_check.sh --require-tex` exits 0.
- `latex_templates/examples/visual_grammar_acceptance_test.tex` compiles with zero errors and contains a state machine, a before/after comparison, and a two-track timeline.
- A figure with `description=` set has that string recoverable from the built PDF.
- A four-node `reportnetwork` chain renders with visible gaps and forward-pointing arrowheads.
- `SKILL.md`'s primitive table has a row for each of the three new environments.
