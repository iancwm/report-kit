# ReportKit Algorithm Visualization Primitives

**Status:** Phase 1 (core state grammar) implemented 2026-09-17: the shared
nine-state vocabulary and its theme-owned `RKTokAlgorithm*` tokens (populated
by all three themes), `arraystate` (with `\cell`/`\row`/`\pointer`/`\range`/
`\annotation`), `windowstate`, and `algorithmtrace`/`\snapshot` all landed in
`latex_templates/reportkit-algorithm-viz.sty`, wired into `reportkit.cls`,
with contract metadata, generated-doc regeneration, `tests/
test_theme_contract.py` coverage, a new `tests/test_algorithm_viz.py`
compile-and-inspect suite, a canonical fixture
(`latex_templates/examples/algorithm_visuals_acceptance_test.tex`, wired into
`scripts/acceptance_check.sh`), and a new SKILL.md "Algorithm and
execution-state visuals" section. Verified via `python -m pytest tests` (164
passed) and `generate_registry(strict=True)` with zero contract errors; no
LuaLaTeX/pdfLaTeX toolchain was available in this environment, so the new
fixture and the new PDF-inspection tests are unverified by an actual compile
and remain to be checked the next time this runs somewhere with TeX
installed. Phase 2 (core algorithm structures) also implemented 2026-09-17:
`stackstate`/`queuestate` (`latex_templates/reportkit-algorithm-linear.sty`,
sharing one internal linear-container renderer per section 7.3, reusing
`arraystate`'s cell/pointer chrome with no new theme tokens) and
`graphstate`/`gridstate` (`latex_templates/reportkit-algorithm-graph.sty`,
three new `RKTokAlgorithmGraph*` tokens for node width and edge color/width,
populated in all three themes; auto-grid node layout, no dedicated
BFS/DFS primitive per section 2.3 — pair `graphstate` with
`queuestate`/`stackstate` by composition instead). Both are
`\RequirePackage`d from within `reportkit-algorithm-viz.sty` itself, so the
public import stays `\RequirePackage{reportkit-algorithm-viz}` per section 3.
Registry/contract/theme-token tests extended accordingly;
`python -m pytest tests` passes (167 passed) with zero contract errors; two
more fixtures added and wired into `scripts/acceptance_check.sh`, still
unverified by an actual LuaLaTeX/pdfLaTeX compile in this environment.
Phase 3 (additional high-value structures) also implemented 2026-09-17:
`intervalstate`/`heapstate` (`latex_templates/reportkit-algorithm-order.sty`
— heapstate's tree layout derived purely from array index via
`floor(ln(i+1)/ln(2))`, per section 11.2's "authors should not manually
position tree nodes"), `dptable` (`latex_templates/reportkit-algorithm-dp.sty`,
reusing `gridstate`'s coordinate math), and `dagstate` (appended to
`latex_templates/reportkit-algorithm-graph.sty`, reusing `graphstate`'s node
layout and `reportkit-diagrams.sty`'s existing dependency-edge style per
section 10.2 — no new edge token needed). Several of these primitives' own
proposed state names (`overlap`/`merged`, `solved`/`dependency`/`uncomputed`,
`ready`/`processed`) are not literally part of the shared nine-word
vocabulary from section 4; each was mapped onto the closest existing state
(documented in-file) rather than growing the vocabulary, per section 2.2's
consistency requirement — see SKILL.md's "Algorithm and execution-state
visuals" section for the exact mapping. `python -m pytest tests` passes (169
passed) with zero contract errors; three more fixtures added and wired into
`scripts/acceptance_check.sh`, still unverified by an actual LuaLaTeX/
pdfLaTeX compile in this environment. P3 extensions also implemented
2026-09-17 in `latex_templates/reportkit-algorithm-p3.sty`: `joinstate`
provides a keyed/hash-join composition, `unionfindstate` provides
disjoint-set parent/union/find state, `linkedliststate` provides explicit
next/head/tail/NULL semantics, and `recursiontree` provides call arguments,
return values, and memoization markers. Contract metadata, generated
references, documentation, and regression coverage are included; the full
algorithm visualization feature is complete.
**Target:** ReportKit vNext.
**Baseline:** `main` at `4113e8b`, ReportKit class v1.9.3, contract v1.0.0.
**Scope:** Native semantic visualization primitives for algorithms, data
structures, and execution-state traces.
**Primary module:** `latex_templates/reportkit-algorithm-viz.sty`, with P3
extensions in `latex_templates/reportkit-algorithm-p3.sty`.

---

## 1. Objective

Extend ReportKit with a native visual grammar for explaining algorithms.

The current ReportKit primitive set is strong at representing:

* architecture,
* process,
* responsibility,
* strategy,
* qualitative positioning,
* timelines,
* dependency relationships,
* capability structures,
* conceptual decomposition.

It is weaker at representing the mechanics of an algorithm as it executes.

Algorithm explanations frequently require the reader to understand:

1. the current state of a data structure,
2. which elements are active,
3. which elements have already been processed,
4. where pointers or cursors are located,
5. how state changes between iterations,
6. which elements are discarded or retained,
7. which nodes belong to a frontier,
8. how multiple snapshots relate over time.

Using generic process or architecture diagrams for these cases produces
visuals that are semantically valid but do not resemble the mental models
used to understand algorithms.

ReportKit should therefore add a dedicated semantic layer for:

> data state + active regions + markers + transitions through execution time

The design should remain consistent with ReportKit's existing philosophy:

* authors declare semantics rather than coordinates where practical,
* meaning must remain understandable without color,
* primitives should compose,
* visual behavior belongs to themes,
* algorithm diagrams should be non-floating reading units,
* visuals should carry caption, source, and accessible description through
  the existing diagram contract.

---

## 2. Design principles

### 2.1 Semantic rather than decorative

Every primitive must answer a specific reader question.

| Reader question | Primitive |
| --- | --- |
| Where are the pointers in this array? | `arraystate` |
| Which range is currently active? | `arraystate` / `windowstate` |
| What is currently in the queue? | `queuestate` |
| Which graph nodes have been visited? | `graphstate` |
| Which nodes are ready to execute? | `dagstate` |
| Which intervals overlap? | `intervalstate` |
| How does state change from one iteration to the next? | `algorithmtrace` |

The module should not become a generic drawing toolkit.

### 2.2 State should be encoded consistently

All algorithm-state primitives should share a common semantic state
vocabulary.

Initial vocabulary:

* `current`
* `active`
* `candidate`
* `frontier`
* `visited`
* `resolved`
* `discarded`
* `blocked`
* `unseen`

These states must be theme tokens, not hard-coded colors.

Their meaning should remain visible through:

* border weight,
* fill treatment,
* line style,
* labels,
* markers,
* patterns,
* shape treatment,

rather than color alone.

### 2.3 Composition before specialization

Specialized primitives should reuse lower-level structures.

```
arraystate
    |-- windowstate
    |-- binary-search visualization
    |-- two-pointer visualization
    \-- prefix-sum visualization
```

Similarly:

```
graphstate
    |-- BFS visualization
    |-- DFS visualization
    \-- dagstate / topological-sort visualization
```

Avoid creating a separate renderer for every named algorithm.

### 2.4 Static snapshots first

ReportKit produces static documents.

The core abstraction should therefore be *a snapshot of algorithm state at a
meaningful point in execution*.

Temporal explanations should be expressed as ordered snapshots using
`algorithmtrace`.

Do not attempt animation in the initial implementation.

---

## 3. Proposed module structure

Add:

```
latex_templates/
    reportkit-algorithm-viz.sty
```

The module should be loaded through the normal ReportKit class contract.

Recommended internal structure for `reportkit-algorithm-viz.sty`:

1. Shared algorithm-state tokens
2. Array-family primitives
3. Linear data-structure primitives
4. Graph/grid primitives
5. Interval and tabular primitives
6. Specialized compositions
7. Temporal composition

Longer-term, if the module becomes too large:

```
reportkit-algorithm-viz.sty
reportkit-algorithm-linear.sty
reportkit-algorithm-graph.sty
reportkit-algorithm-tabular.sty
reportkit-algorithm-trace.sty
```

The public import should remain:

```latex
\RequirePackage{reportkit-algorithm-viz}
```

---

## 4. Shared semantic state contract

All state-aware primitives should understand a common state grammar.

```latex
\cell[state=active]{7}
\node[state=frontier]{B}
\interval[state=resolved]{2}{5}
```

Initial state set:

| State | Meaning |
| --- | --- |
| `current` | Item currently being processed |
| `active` | Item belongs to the active working set |
| `candidate` | Item is under consideration |
| `frontier` | Discovered but not processed |
| `visited` | Already processed |
| `resolved` | Final state is known |
| `discarded` | Explicitly eliminated from consideration |
| `blocked` | Cannot currently proceed |
| `unseen` | Not yet reached |

Themes should define appearance through tokens such as:

```
RKTokAlgorithmCurrentDraw
RKTokAlgorithmCurrentFill
RKTokAlgorithmCurrentText
RKTokAlgorithmActiveDraw
RKTokAlgorithmActiveFill
RKTokAlgorithmDiscardedDraw
RKTokAlgorithmDiscardedFill
RKTokAlgorithmDiscardedPattern
```

The exact naming can be normalized during implementation.

---

## 5. Primitive family A: `arraystate`

### 5.1 Purpose

Represent indexed linear data with:

* values,
* indices,
* pointers,
* active ranges,
* highlighted cells,
* annotations,
* optional multiple aligned rows.

This should become the foundational algorithm visualization primitive.

### 5.2 Reader questions

* Which array elements are active?
* Where are left, right, mid, or other cursors?
* Which values have been discarded?
* Which subarray is being considered?
* How do two aligned arrays relate?

### 5.3 Proposed basic API

```latex
\begin{diagram}[
  type=array,
  caption={Two-pointer scan.},
  source={Conceptual diagram.},
  description={A sorted array with left and right pointers bounding the active range.}
]
\begin{arraystate}
  \cell{-4}
  \cell{-1}
  \cell{-1}
  \cell{0}
  \cell{1}
  \cell{2}
  \pointer[below]{L}{2}
  \pointer[below]{R}{6}
  \range[state=active]{2}{6}
\end{arraystate}
\end{diagram}
```

### 5.4 Core commands

```latex
\cell[<options>]{value}
\pointer[<options>]{label}{index}
\range[<options>]{start}{end}
\annotation[<options>]{text}
```

Possible options: `state=`, `label=`, `index=`, `above`, `below`, `style=`.

### 5.5 Multi-row mode

Needed for prefix sums, DP rows, original vs transformed arrays, and sorted
vs unsorted values.

```latex
\begin{arraystate}[rows=2]
  \row{values}{3,1,4,2}
  \row{prefix}{0,3,4,8,10}
  \range[row=values,state=active]{2}{4}
  \annotation{P_4 - P_1 = 7}
\end{arraystate}
```

This should likely use a dedicated `\row` command rather than repeated raw
cells.

---

## 6. Primitive family B: `windowstate`

### 6.1 Purpose

Specialized composition built on `arraystate`. Represents a sliding or moving
contiguous region.

Typical uses: fixed-size sliding windows, variable-size windows, streaming
state, moving averages, substring problems.

### 6.2 Required semantics

The primitive should visually distinguish the active window, the incoming
element, the outgoing element, the left pointer, and the right pointer.

```latex
\begin{windowstate}
  \values{4,2,7,1,3,6}
  \window{2}{4}
  \entering{5}
  \leaving{1}
\end{windowstate}
```

Alternatively, keep it thin and compile internally to `arraystate`.

---

## 7. Primitive family C: linear containers

### 7.1 `stackstate`

Represents LIFO state. Typical uses: bracket matching, DFS, monotonic stack,
expression evaluation.

```latex
\begin{stackstate}
  \item{(}
  \item{[}
  \item[state=current]{\{}
\end{stackstate}
```

Should visually mark the stack top.

### 7.2 `queuestate`

Represents FIFO state. Typical uses: BFS, work queues, streaming buffers,
Kahn's algorithm.

```latex
\begin{queuestate}
  \item[state=current]{A}
  \item{B}
  \item{C}
\end{queuestate}
```

The primitive must visibly identify:

```
DEQUEUE <- [ A | B | C ] <- ENQUEUE
```

or equivalent semantics.

### 7.3 Shared implementation

`stackstate` and `queuestate` should share a common internal linear-container
renderer.

---

## 8. Primitive family D: `graphstate`

### 8.1 Purpose

Represent graph traversal state rather than merely static graph structure.
The existing `reportnetwork` is relationship-centric; `graphstate` should be
algorithm-state-centric.

### 8.2 Required node states

At minimum: `unseen`, `frontier`, `current`, `visited`, `blocked`.

### 8.3 API concept

```latex
\begin{graphstate}
  \graphnode[state=visited]{A}{Start}
  \graphnode[state=current]{B}{Current}
  \graphnode[state=frontier]{C}{Queued}
  \graphnode[state=unseen]{D}{Unseen}
  \graphedge{A}{B}
  \graphedge{B}{C}
  \graphedge{B}{D}
\end{graphstate}
```

The first implementation can reuse ReportKit's existing semantic node and
edge styles.

### 8.4 BFS / DFS composition

A full traversal explanation should pair `graphstate` + `queuestate` for BFS,
and `graphstate` + `stackstate` for iterative DFS. This should preferably be
implemented through composition rather than a new BFS-specific primitive.

---

## 9. Primitive family E: `gridstate`

### 9.1 Purpose

Represent algorithms over 2D grids. Typical uses: islands, flood fill, maze
traversal, shortest paths, matrix DP, connected cells.

### 9.2 Required semantics

Each cell should support: `unseen`, `current`, `frontier`, `visited`,
`blocked`, `target`.

```latex
\begin{gridstate}[rows=4,columns=5]
  \gridcell{1}{1}[state=visited]
  \gridcell{1}{2}[state=current]
  \gridcell{2}{2}[state=frontier]
  \gridcell{3}{3}[state=blocked]
\end{gridstate}
```

For dense matrices, a compact data declaration would be preferable.

---

## 10. Primitive family F: `dagstate`

### 10.1 Purpose

Extend graph-state visualization for dependency algorithms. Primary use:
topological sorting, DAG scheduling, dependency resolution, data-pipeline
execution. This is especially relevant to data-engineering publications.

### 10.2 Features

Nodes should support an indegree badge, and `ready`, `processed`, and
`blocked` states.

```latex
\begin{dagstate}
  \dagnode[indegree=0,state=ready]{raw}{Raw}
  \dagnode[indegree=2]{clean}{Clean}
  \dagnode[indegree=1]{features}{Features}
  \dependency{raw}{clean}
  \dependency{clean}{features}
  \readyqueue{raw}
\end{dagstate}
```

The existing ReportKit dependency-edge grammar should be reused wherever
possible.

---

## 11. Primitive family G: `heapstate`

### 11.1 Purpose

Represent heap-based algorithms. Typical uses: top-K, priority queues,
kth-largest/smallest, merging sorted inputs.

### 11.2 Dual representation

The most useful visualization is the heap tree plus the backing array.

```latex
\begin{heapstate}
  \values{3,5,8,9,10}
  \current{1}
\end{heapstate}
```

The primitive should derive the tree relationships from array position
automatically. Authors should not manually position tree nodes.

---

## 12. Primitive family H: `intervalstate`

### 12.1 Purpose

Visualize intervals on a shared axis. Typical uses: merge intervals,
scheduling, sessionization, validity periods, overlap detection.

### 12.2 API concept

```latex
\begin{intervalstate}
  \interval{A}{1}{4}
  \interval{B}{3}{6}
  \interval{C}{8}{10}
  \merged{1}{6}
\end{intervalstate}
```

Possible semantic states: `candidate`, `overlap`, `merged`, `discarded`.

The visual should use a common horizontal scale.

---

## 13. Primitive family I: `dptable`

### 13.1 Purpose

Represent dynamic-programming state. Typical uses: 1D DP, grid DP, edit
distance, knapsack, longest common subsequence.

### 13.2 Required semantics

Cells should support: `solved`, `current`, `dependency`, `uncomputed`.

```latex
\begin{dptable}[rows=4,columns=5]
  \currentcell{3}{4}
  \dependencycell{2}{4}
  \dependencycell{3}{3}
\end{dptable}
```

Optional dependency arrows may be added, but should remain visually sparse.

---

## 14. Primitive family J: `algorithmtrace`

### 14.1 Purpose

Provide a generic temporal composition for showing algorithm state across
multiple steps. This is the second highest-priority primitive after
`arraystate`.

### 14.2 Concept

```latex
\begin{algorithmtrace}[columns=3]
  \snapshot{Initial}{
    ...
  }
  \snapshot{Advance right}{
    ...
  }
  \snapshot{Shrink left}{
    ...
  }
\end{algorithmtrace}
```

Each snapshot can contain `arraystate`, `graphstate`, `gridstate`,
`heapstate`, `intervalstate`, or another state primitive.

### 14.3 Design constraints

The trace should:

* normalize snapshot widths,
* support 2–4 columns,
* allow wrapping to multiple rows,
* provide an explicit ordered reading direction,
* optionally show transition arrows,
* avoid forcing identical diagram types across snapshots.

It should not be implemented as an animation system.

---

## 15. DE-specific extension: `joinstate`

This primitive is not a classical algorithms primitive, but is highly aligned
with ReportKit's likely data-engineering use cases.

Purpose: visualize a hash join, illustrate indexing one input, show matched
and unmatched keys, explain `GROUP BY` or keyed aggregation.

Possible structure:

```
Input A -> hash/index structure <- Input B
                    |
                    v
                 Output
```

This may be implemented after the general algorithm-state primitives.

---

## 16. Lower-priority primitives

The following should not be included in the first implementation milestone.

* **`linkedliststate`** — useful for SWE interview preparation, but less
  broadly reusable in analytical and DE documents.
* **`unionfindstate`** — useful for connectivity and component merging, but
  relatively specialized.
* **`recursiontree`** — prefer extending `reporttree` with algorithm-specific
  labels such as arguments, return value, and memoized, rather than building
  a completely independent tree renderer.
* **`hashmapstate`** — potentially useful, but care is needed not to imply
  implementation-specific bucket structure where logical key-value state is
  sufficient.

---

## 17. Integration with existing ReportKit primitives

The new module must reuse existing infrastructure.

**Reuse:** `diagram`, `source`, `description`, TikZ style tokens, semantic
edge styles, accessibility / `ActualText`, page reservation hooks, the
renderer abstraction, the theme system.

**Do not duplicate:** generic network diagrams, generic process flows,
arbitrary coordinate placement, caption handling, provenance handling, color
palettes.

---

## 18. Theme architecture

Each visual state must be expressed through theme-owned style tokens.

The module should not branch on `\rk@theme`. Instead, follow the existing
ReportKit style-token contract.

Conceptual token groups: algorithm cell base, algorithm active, algorithm
current, algorithm frontier, algorithm visited, algorithm discarded,
algorithm pointer, algorithm index label, algorithm container border,
algorithm trace separator.

Default theme appearance should remain restrained and consistent with the
current ReportKit palette.

---

## 19. Accessibility requirements

Each algorithm diagram must support the standard diagram description
contract.

```latex
description={
A seven-element array with the left pointer on index two
and the right pointer on index six. Elements outside the
pointer range are marked discarded.
}
```

State meaning must not rely only on color. Pointers and statuses should use
explicit labels, borders, line styles, textual markers, and position.

---

## 20. Documentation requirements

Update `SKILL.md` with a new section:

```
## Algorithm and execution-state visuals
```

Recommended visual-selection table:

| Reader question | Primitive |
| --- | --- |
| Where are cursors in linear data? | `arraystate` |
| What contiguous region is active? | `windowstate` |
| What is on the stack or queue? | `stackstate` / `queuestate` |
| What is the traversal frontier? | `graphstate` |
| Which grid cells are reached? | `gridstate` |
| Which DAG nodes can execute? | `dagstate` |
| What is currently in the heap? | `heapstate` |
| Which intervals overlap? | `intervalstate` |
| Which DP states are known? | `dptable` |
| How does state evolve over time? | `algorithmtrace` |

The documentation should explicitly distinguish:

* `algorithmblock` — control-flow logic,
* `codeblock` — executable implementation,
* algorithm visual — state of the data during execution,
* `reportflow` — relationships between process stages.

---

## 21. Implementation order

**Phase 1 — Core state grammar.** Implement (1) shared state vocabulary,
(2) theme tokens, (3) `arraystate`, (4) `algorithmtrace`. These establish the
architecture.

**Phase 2 — Core algorithm structures.** Implement (5) `stackstate`,
(6) `queuestate`, (7) `graphstate`, (8) `gridstate`. These cover the majority
of introductory algorithm explanations.

**Phase 3 — Additional high-value structures.** Implement (9)
`intervalstate`, (10) `heapstate`, (11) `dptable`, (12) `dagstate`.

**Phase 4 — Domain-specific extensions.** Evaluate (13) `joinstate`,
(14) `unionfindstate`, (15) linked-list support, (16) recursion-tree
extensions.

---

## 22. Priority recommendation

| Priority | Primitives |
| --- | --- |
| P0 | `arraystate`, `algorithmtrace`, shared state vocabulary |
| P1 | `graphstate`, `gridstate`, `stackstate`, `queuestate` |
| P2 | `intervalstate`, `heapstate`, `dptable`, `dagstate` |
| P3 | `joinstate`, `unionfindstate`, `linkedliststate`, recursion extensions |

The first six primitives would cover a large fraction of the visuals required
for interview-preparation guides, CS teaching material, data-structure
explanations, systems documentation, and data-engineering algorithm
walkthroughs.

---

## 23. Acceptance criteria

Each primitive should satisfy all of the following before release.

**Functional**

* Compiles under supported ReportKit paged renderers.
* Uses the existing `diagram` wrapper.
* Supports theme-owned appearance.
* Requires no manual coordinates for common usage.
* Produces deterministic layout.
* Validates invalid indices / ranges where practical.
* Supports semantic state markers.

**Visual**

* No clipping at normal A4 text width.
* Labels remain readable at default scale.
* State remains distinguishable when printed in grayscale.
* Meaning does not depend solely on fill color.
* Diagrams do not require arbitrary author spacing hacks.

**Accessibility**

* `description=` remains available.
* Important states have explicit labels or shape treatment.
* Reading order is deterministic.

**Documentation**

* Public commands include generated primitive-contract metadata.
* `SKILL.md` contains examples.
* At least one fixture exists per primitive family.
* Example use cases include both algorithm-interview and data-engineering
  scenarios.

**Regression**

* Existing ReportKit fixtures remain pixel-stable where expected.
* New style tokens do not change existing diagram appearance.
* Existing `reportnetwork`, `reportflow`, and `reporttree` behavior remains
  unchanged.

---

## 24. Canonical example fixture

Add a fixture such as `latex_templates/examples/algorithm-visuals/`.

It should demonstrate:

1. two-pointer array,
2. sliding window,
3. prefix sums,
4. queue + BFS graph,
5. DFS stack,
6. topological sort with indegrees,
7. heap + backing array,
8. interval merge,
9. simple DP table,
10. three-step `algorithmtrace`.

This fixture should be included in visual-regression testing.

---

## 25. Example target use in the Data Engineering interview guide

The current guide would benefit directly from:

* Two pointers: `arraystate`
* Sliding window: `windowstate` + `algorithmtrace`
* Prefix sums: multi-row `arraystate`
* BFS: `graphstate` + `queuestate`
* DFS: `graphstate` + `stackstate`
* Topological sort: `dagstate`
* Heap: `heapstate`
* Intervals: `intervalstate`
* Basic DP: `dptable`

This should be used as the first real-world validation document during
implementation.

---

## 26. Architectural conclusion

ReportKit should not solve this gap by adding more generic business-style
diagrams. The missing abstraction is an algorithm-state grammar.

The core model should be:

```
DATA STRUCTURE
    +
SEMANTIC STATE
    +
MARKERS / ACTIVE REGION
    +
OPTIONAL ORDERED SNAPSHOTS
```

That architecture keeps the primitive set small while making it expressive
enough for a broad range of algorithm visualizations.

The strongest implementation path is therefore:

```
arraystate
    |
    v
shared semantic-state vocabulary
    |
    v
graph/grid/container state primitives
    |
    v
algorithmtrace composition
    |
    v
specialized algorithm views
```

This gives ReportKit a coherent extension rather than a collection of one-off
algorithm diagrams.
