# Algorithm Visuals and Cheat-Sheet Fix Sprint

Implementation specification from visual review · 18 September 2026

**Status:** Implemented in the working tree on 2026-09-19. Tasks 1–3 are
merged; Task 4's four-page reference fixture, mechanical release gate, and
140-DPI default/institutional-research visual review are complete. The full
repository acceptance command still reports pre-existing out-of-scope
failures documented in the Task 4 report.

## Executive summary

This sprint fixes the defects visible in the compiled Data Engineering Coding
Interview Cheatsheet rather than introducing a broad new visual language. The
first release gate is an array renderer whose indices, pointers, and active
range are readable at normal page scale. The remaining work makes traces and
pipeline DAGs explain execution state, and prevents a code example from being
split away from its heading.

The sprint deliberately defers new guide-level primitives such as pattern
maps and study cards. Those are useful follow-on work, but they should build
on reliable state geometry, responsive layout, and tested pagination.

Sprint sequence: repair array geometry → make traces readable → show DAG
execution state → protect code units during pagination.

## 1. Sprint charter

### 1.1 Objective

Make ReportKit's existing algorithm primitives suitable for a compact A4
programming guide. A reader must be able to identify a data structure's
active roles, understand the transition shown by a trace, and follow a
topological-sort example without relying on colour or a prose explanation
outside the figure.

### 1.2 Evidence from the rendered guide

| Location | Visible defect | Sprint response |
|---|---|---|
| Page 4, two-pointer trace | Index labels sit against the left border of each array cell; no readable L/R markers identify the moving pointer | Correct index anchoring and add pointer-role chrome |
| Page 4, sliding window | Two code blocks explain movement but no state view shows entering or leaving elements | Make the corrected `windowstate` usable in a guide fixture |
| Page 6, queue | A short queue example occupies an otherwise sparse page | Add a code-unit pagination guard and compact guide fixture |
| Page 8, topological sort | The one-row DAG shows relationships, but the ready queue and execution state are absent | Extend `dagstate` with dependency layout and ready-queue rendering |
| Page 9, heap | The code example continues at the top of a new page without its heading | Keep a fitting code unit together; only split when it exceeds a full text page |

### 1.3 Definition of done

The sprint is complete when the revised guide fixture renders with centered
array indices, labelled pointer roles, readable trace events, a DAG ready
queue, no detached short code fragments, and no clipped or overlapping
content at 100% zoom. The proof is a reviewed before/after spread, not a
passing source-only test.

**Scope boundary:** This is a repair sprint. It changes existing primitive
contracts only where the current documented behaviour is broken or
insufficient for a readable guide. New `patternmap`, `cheatsheetgrid`, and
`algorithmwalkthrough` environments are deferred until after these
foundations have shipped.

## 2. Workstream A: linear-state geometry (`reportkit-algorithm-viz.sty`)

### A1. Repair index anchoring

`arraystate` must attach every index label to the horizontal center of its
corresponding cell.

Required coordinate contract:
```
% For cell i with bounds (x_left, x_right, y_bottom):
index_x = (x_left + x_right) / 2
index_y = y_bottom - index_gap
% index_gap is a theme token, with a guide-scale minimum.
```

| Requirement | Acceptance rule |
|---|---|
| Horizontal anchor | The index baseline is centered under the value cell, within 0.25pt of the cell center |
| Vertical clearance | The top of an index glyph is separated from the cell border by at least 1.5pt at normal guide scale |
| Index order | Index i sits below cell i, including when a range or a pointer is present |
| Compact traces | `indices=auto` hides repeated indices after the first snapshot when retained indices would violate the minimum label size |
| Theme ownership | `RKTokAlgorithmIndex*` tokens own colour, type, and gap; primitive code owns geometry only |

### A2. Fix row lookup and range targeting

The implicit row selector must expand before lookup. A bare `\pointer` or
`\range` must target the row built from direct `\cell` declarations, while
`row=<name>` must target only the named `\row`. The fixture that currently
fails with "Unknown arraystate row " must become a release gate.

### A3. Add readable pointer roles

Introduce an opt-in `role=` key on `\pointer` with initial roles `left`,
`right`, `mid`, `head`, `tail`, `top`, and `root`. A role selects a marker
shape and a visible short label; it does not change the cell's semantic
`state=`.

Target authoring form:
```latex
\begin{arraystate}[indices=auto]
\cell[state=current]{1}\cell[state=active]{3}
\cell[state=active]{5}\cell[state=current]{9}
\pointer[role=left,below]{L}{0}
\pointer[role=right,below]{R}{3}
\range[state=active]{0}{3}
\end{arraystate}
```

Roles must survive grayscale. The left/right distinction uses a label plus
opposing arrow direction; it cannot be expressed by blue versus grey borders
alone.

### A4. Make `windowstate` a verified composition

`windowstate` must reuse the repaired array geometry. `\window{start}{end}`
draws an inclusive active band and automatically exposes left/right roles.
`\entering{index}{value}` and `\leaving{index}{value}` render visible
labelled arrows so duplicate values remain unambiguous. Reject out-of-bounds
indices with a primitive-specific error.

## 3. Workstream B: trace readability (`reportkit-algorithm-viz.sty`)

### B1. Responsive `algorithmtrace`

Add `mode=auto` with this fallback order:
1. horizontal strip when every snapshot meets the minimum cell and label size;
2. two-column grid when the strip would compress a snapshot;
3. vertical sequence when the grid would still violate the minimum.

The renderer calculates the available width after reserving snapshot titles,
event labels, captions, and an optional legend. It must reflow rather than
silently reduce labels below the configured guide minimum.

### B2. Add transition text

Add `\transition{...}` between adjacent snapshots. The transition renders a
directional arrow and short text such as "sum too small; advance L." It
belongs to the edge, not to either static state. In grid and vertical modes,
the arrow includes a step number to preserve reading order.

### B3. Legend and contrast

Add `legend=auto` to `arraystate`, `windowstate`, and `algorithmtrace`. It
lists only used states and roles. The sprint fixture uses a grayscale render
to verify that current, active, and discarded cells remain distinguishable
by border or pattern as well as fill.

## 4. Workstream C: traversal and dependency state (`reportkit-algorithm-graph.sty`)

### C1. Dependency layout for `dagstate`

Add `layout=dependency` to assign each DAG node to a column based on longest
prerequisite distance; nodes declared at the same level occupy rows in
declaration order. This replaces the guide's visually thin automatic grid
with a pipeline-oriented reading order.

### C2. Ready queue is part of the rendering

`\readyqueue{raw,clean}` must render a compact FIFO queue below or beside the
DAG, labelled "ready." Each queued node retains its zero indegree badge; the
node's state changes to `frontier`. A nonzero-indegree node passed to
`\readyqueue` is a validation error.

Target topological-sort figure:
```latex
\begin{dagstate}[layout=dependency]
\dagnode[indegree=0,state=resolved]{raw}{raw\_orders}
\dagnode[indegree=0,state=frontier]{clean}{clean\_orders}
\dagnode[indegree=1,state=unseen]{sales}{daily\_sales}
\dependency{raw}{clean}\dependency{clean}{sales}
\readyqueue{clean}
\end{dagstate}
```

### C3. Demonstrate queue and graph composition

Do not create a dedicated BFS primitive in this sprint. Add one reference
fixture that places `graphstate` beside `queuestate`; add an equivalent DFS
fixture with `stackstate`. The fixtures prove that existing primitives
compose at guide scale and expose any spacing or caption defects.

## 5. Workstream D: pagination and guide fixture (`reportkit-code.sty` and guide template)

### D1. Protect short code units

Add `keep=auto` to `codeblock`. When a code block, its title, and its
immediately introducing paragraph fit on a fresh page but not in the
remaining space, move the complete unit to the next page. When the unit
exceeds a fresh text page, permit an intentional split and repeat a minimal
continuation label.

The default remains backward-compatible until the revised guide template
opts in. The implementation may use the underlying breakable-box mechanism,
but the public contract is about reading units rather than the underlying
package.

### D2. Compact-guide template changes

The guide fixture must use a compact front matter mode: integrate the
contents list as a small navigation panel on the title page and avoid a
contents-only page. Stack and queue should occupy one reading unit. The
fixture must not force a new major section after a short fragment solely for
mechanical chapter spacing.

### D3. Required reference spread

The sprint includes a revised four-page coding-guide fixture:
1. an opening page with a grouped pattern table and compact navigation;
2. two pointers plus sliding window, each with a code unit and a readable state view;
3. stack/queue plus BFS/DFS composition;
4. topological sort with dependency layout, indegrees, and ready queue.

This fixture is a visual-regression artefact. It is not a new public
primitive and does not require a full rewrite of the eleven-page guide
during the sprint.

## 6. Implementation plan and acceptance gates

### 6.1 Sequence and ownership

| Order | Module | Deliverable |
|---|---|---|
| 1 | `reportkit-algorithm-viz.sty` | Centered indices, row-lookup repair, roles, bounds validation |
| 2 | `reportkit-algorithm-viz.sty` | Trace reflow, transition labels, automatic legend |
| 3 | `reportkit-algorithm-graph.sty` | Dependency layout, ready-queue validation, renderer |
| 4 | `reportkit-code.sty` and guide template | `keep=auto` contract and compact fixture pagination |
| 5 | Examples and CI fixtures | Colour/grayscale renders, guide-scale visual review, regression baselines |

### 6.2 Automated fixtures

Each change requires a minimal TeX fixture and an A4 guide-scale fixture.
Tests must cover direct cells and named rows, duplicate window values, a
trace that must reflow, a valid and invalid ready queue, and both code-block
paths: fit-on-next-page and genuinely oversize.

### 6.3 Visual release gate

Render default and high-contrast themes at 140 DPI, then inspect each
fixture in colour and grayscale. The gate fails if any of these occur:
- an index is visually attached to a cell edge rather than its center;
- a pointer role, active range, or transition cannot be identified without colour;
- trace labels overlap, become unreadable, or lose chronological order;
- a DAG's ready queue and indegrees contradict each other;
- a short code block begins on a page without its heading or opening prose;
- any existing primitive fixture changes unexpectedly outside the documented fix.

### 6.4 Deferred work

After this sprint, assess the guide fixture and decide whether a dedicated
`patternmap`, `cheatsheetgrid`, or code-to-state `algorithmwalkthrough`
earns its own proposal. Do not begin that work until the repaired array and
trace primitives pass their guide-scale visual gate.

**Release decision:** Ship only when a reviewer can answer three questions
from the figures alone: Which pointer moved? Which item entered or left the
window? Which pipeline node can execute next? If the guide still needs prose
to answer any of these, the sprint has not fixed the reader's problem.
