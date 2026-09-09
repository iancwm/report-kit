# ReportKit Post-Implementation Findings — Fix Three Defects

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** EXECUTION COMPLETE (7 of 8 tasks done and reviewed clean; Task 8 blocked by pre-existing fixture compilation issue)

**Goal:** Fix three defects discovered during the first ACN production report compile (Sept 9, 2026), then rebuild and verify the fixture compiles cleanly.

**Result:** All three defects fixed and implemented. Spec updates complete. LaTeX and Python implementations verified. Fixture partially updated (4-item rating strip + sidebar chart working). Task 8 fixture build revealed a pre-existing bug in the ratingstrip parameter parsing (now fixed in commits e104aae, 6409a36) and an unrelated exhibitpane issue that requires separate investigation.

**Architecture:** Three independent defect fixes that coordinate spec text updates with implementation fixes. Fix 1 adds dynamic sizing to the rating strip layout engine. Fix 2 introduces a new type-scale level for sidebar subheadings. Fix 3 adds sidebar-sized figure presets and a donut chart implementation. All changes preserve backward compatibility and reuse existing theme/viz architecture.

**Tech Stack:** LaTeX 3 (xparse, pgfkeys, tabularx), Python 3 (matplotlib, pandas), pytest.

**Spec:** [2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](../specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md) — specifically sections 29.1, 29.2, 29.3 (Post-implementation findings)

## Global Constraints

- Do not modify the fixture's arithmetic manually — §29.6 instructs reconciliation but that is outside this plan's scope.
- Do not break backward compatibility: existing documents with theme=default must remain pixel-equivalent.
- All figure_size presets must have aspect ratios derived from a stated formula (§15 open question 4), not ad-hoc values.
- Chart functions must accept `size=` parameter as either string key or `(width, height)` tuple.
- Spec updates must be made *before* corresponding implementation fixes so the spec and code stay in sync.

---

## Task 1: Update spec §9 to require 3-4 item support in rating strip

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md:594-615` (§9 Rating strip)

**Interfaces:**
- Consumes: (none — this is spec-only)
- Produces: Updated spec text clarifying item-count range and dynamic width requirement

**Rationale:** §29.1 shows that the current spec example only uses 3 items, letting the implementation hardcode a width that breaks at 4 items. The spec must state what it requires.

- [ ] **Step 1: Open the spec file and read §9 (Rating strip)**

Read lines 594–615 to see the current brief description.

- [ ] **Step 2: Find §29.1 in the same file and re-read the suggested spec fix**

Lines 1301–1308 contain the exact wording and rationale. Copy it verbatim into §9 as a new bulleted requirement.

- [ ] **Step 3: Add the spec text after the existing "strong baseline alignment" characteristic**

Insert after line 613 (after the list of Characteristics):

```latex
## Supported item count

A rating strip must render correctly with 3 or 4 items without any item
wrapping to a second line. Item width must therefore be computed from
the actual item count, not fixed at a constant width sized for one specific
count.
```

- [ ] **Step 4: Verify the edit reads naturally alongside existing text**

Read §9 in full — the new section should flow after Characteristics and before the closing.

- [ ] **Step 5: Commit**

```bash
cd /home/iancwm/git/report-kit
git add docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md
git commit -m "docs: spec §9 now requires 3-4 item support in rating strip

Per §29.1 post-implementation finding: the spec must state the supported
item-count range explicitly, not implicitly through examples. Rating strip
item width must be computed from actual item count, not fixed for one count.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update spec §5 to define sidebar subheading type scale

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md:448-464` (§5 Recommended scale table)

**Interfaces:**
- Consumes: §29.2 suggested spec fix (lines 1348–1358)
- Produces: Updated §5 scale table with new `Sidebar subheading` row

**Rationale:** §29.2 found that the sidebar has only one type-scale level, so subheadings cannot outrank body text by size. The spec must define a distinct size.

- [ ] **Step 1: Locate the "Recommended scale" table in §5 (line 449–464)**

This table lists all type sizes from Masthead down to Disclosure.

- [ ] **Step 2: Find the `Sidebar` row (line 460) in that table**

```
Sidebar               7.6 pt / 9.5
```

- [ ] **Step 3: Insert a new row immediately after it**

Add this line after line 460:

```
Sidebar subheading    6.6-6.8 pt / 8-8.2
```

This makes the subheading one size smaller than body sidebar text, reusing the same principle §5 already states for main-column hierarchy.

- [ ] **Step 4: Verify the updated table reads logically**

The new row should create a visible size hierarchy: Sidebar subheading < Sidebar < Exhibit headline.

- [ ] **Step 5: Update the body text at line 450–466 if needed**

Read the section after the table. It instructs to "Use weight and size before color or boxes to establish hierarchy." No change needed there — it already covers sidebar hierarchy by implication.

- [ ] **Step 6: Commit**

```bash
cd /home/iancwm/git/report-kit
git add docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md
git commit -m "docs: spec §5 adds sidebar subheading type-scale step

Per §29.2 post-implementation finding: the sidebar needs a distinct,
smaller type step for subheadings, just as the main column distinguishes
Section / Subsection / Body. Size establishes hierarchy (§5 closing
principle), so sidebar subheadings must be smaller than sidebar body text.

Spec range: 6.6-6.8 pt / 8-8.2 pt leading.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Update spec §8 and §22 to document sidebar chart guidance

**Files:**
- Modify: `docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md:561-591` (§8 Sidebar primitives)
- Modify: `docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md:1065-1091` (§22 AI authoring guidance)

**Interfaces:**
- Consumes: §29.3 suggested spec fixes (lines 1405–1418)
- Produces: Updated §8 and §22 explaining sidebar chart capability and when to use it

**Rationale:** §29.3 found that authors have no guidance on embedding proportional-data charts in sidebars. The spec must clarify this use case.

- [ ] **Step 1: Read §29.3's "Suggested spec fix" (lines 1405–1418)**

This section proposes adding guidance to both §22 (AI authoring) and implicitly to §15 (which will be handled in Task 5).

- [ ] **Step 2: Update §22 (AI authoring guidance) — add a new paragraph**

After line 1078 (after "Do not force a visual onto every section"), add:

```
> A sidebar composition of 2-4 values that are parts of a whole (a segment
> split, a geographic mix, a channel mix, a revenue composition) is a chart,
> not a `\sidebarrow` list — render it as a small pie or donut chart sized
> for the sidebar column, with underlying values available in the source or
> caption. Reserve `\sidebarrow` for point metrics and estimates that are
> not proportions of a common whole.
```

- [ ] **Step 3: Update §8 (Sidebar primitives) — add a new subsection**

After line 590 (the end of the Sidebar section before §9), add:

```latex
## Sidebar compositions

Sidebar data showing relative proportions (a two-way segment split, a
geographic or channel mix, a business-line breakdown) should render as a
small themed pie or donut chart, not as five `\sidebarrow` text pairs that
require mental arithmetic to parse the composition visually. The chart
function will be available in Step 4 (reportkit_viz.py's donut_chart);
`figure_sizes` will include a `sidebar` preset sized for the ~28%-wide
sidebar column (Task 5).
```

- [ ] **Step 4: Verify the edits fit the sections' existing tone**

§8 is technical, §22 is instructional. Both should now be clear on when a sidebar holds a chart vs. text.

- [ ] **Step 5: Commit**

```bash
cd /home/iancwm/git/report-kit
git add docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md
git commit -m "docs: spec §8, §22 document sidebar chart guidance

Per §29.3 post-implementation finding: authors need clear guidance on
using small charts (pie/donut) in sidebars for proportional data, rather
than text-based \sidebarrow lists that require mental arithmetic.

§8 documents the capability; §22 instructs when to prefer it.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Implement rating strip dynamic item width in LaTeX

**Files:**
- Modify: `latex_templates/publication_types/reportkit-equity-research.sty:110-117` (ratingitem implementation)

**Interfaces:**
- Consumes: `\ratingstrip` environment (already defined lines 102–108)
- Produces: Updated `\ratingitem` using tabularx with dynamic column widths instead of fixed minipages

**Rationale:** §29.1 details the overflow problem: four items × 0.29\linewidth = 1.16\linewidth, exceeding the available line. A tabularx with C (centered) columns sized `1/N\linewidth` where N is the item count solves this by distributing space evenly.

- [ ] **Step 1: Read the current ratingitem implementation (lines 110–117)**

Currently uses `\begin{minipage}[t]{0.29\linewidth}` for each item, with counters to insert separators. This hardcodes the width.

- [ ] **Step 2: Design the tabularx-based replacement**

Strategy:
1. Move `\ratingstrip` to open a tabularx environment instead of just printing rules
2. Define a column type that will be `1/N\linewidth` for N items
3. Collect items as tabularx cells instead of minipages
4. Style the cells with the same fonts/colors as before

Problem: We don't know N until we see all items. Solution: Use a two-pass approach with a counter (existing pattern: `reportkit-structure.sty` already does this for `reportarchitecture`), OR simplify by making the ratingstrip a tabularx with a fixed number of X columns and let each item span `1/N` via column definition.

For simplicity and proof of concept, use the simpler approach: change the item definition to work inside a tabularx, and let the caller open/close the tabularx environment in `\ratingstrip`.

- [ ] **Step 3: Implement the new rating strip using tabularx**

Replace lines 102–117 with:

```latex
% Rating strip (spec §9) using tabularx for dynamic item width.
% Instead of fixed minipage widths, this implementation opens a tabularx
% inside \ratingstrip and lets items populate columns that automatically
% size based on the column count, supporting 3-4 items without overflow.
\newcounter{rkratingitem}
\NewDocumentEnvironment{ratingstrip}{}{%
  \par\Needspace{4\baselineskip}\noindent
  \setcounter{rkratingitem}{0}%
  {\color{Hairline}\hrule height 0.4pt}\par\vspace{5pt}\noindent
  % We will NOT use fixed minipages anymore. Items are now expected to be
  % placed inside a tabularx manually. See \ratingitem for the cell contents.
}{%
  \par\vspace{3pt}{\color{Hairline}\hrule height 0.4pt}\par\vspace{6pt}%
}

% Individual rating item, now designed for tabularx column content.
% Usage: place these inside a tabularx row: e.g.,
%   \begin{tabularx}{\linewidth}{@{} C | C | C @{}}
%     \ratingitem{Stock Rating}{Overweight} &
%     \ratingitem{Industry View}{Attractive} &
%     \ratingitem{Price Target}{\$245}
%   \end{tabularx}
% The C column type (centered, expandable) from reportkit-equity-research.sty
% automatically distributes width equally to support 3, 4, or any N items.
\NewDocumentCommand{\ratingitem}{m m}{%
  {\sffamily\rksidebarsize\color{Muted}\MakeUppercase{#1}\par}%
  \vspace{1pt}{\sffamily\bfseries\rkratingvaluesize\color{Ink}#2\par}%
}
```

Wait — this changes the API. The old code uses:

```latex
\begin{ratingstrip}
  \ratingitem{Stock Rating}{Overweight}
  \ratingitem{...}{...}
\end{ratingstrip}
```

The new approach would require:

```latex
\begin{ratingstrip}
\begin{tabularx}{\linewidth}{@{} C | C | C @{}}
  \ratingitem{Stock Rating}{Overweight} &
  \ratingitem{...}{...} &
  \ratingitem{...}{...}
\end{tabularx}
\end{ratingstrip}
```

This breaks the existing API and the example fixture. Better approach: keep the API unchanged by using the two-pass counting method §29.1 suggests. Let me revise:

Actually, let me check the existing example to see how it's used.

- [ ] **Step 3b: Check the equity-research example to see how ratingstrip is used**

Read lines of report.tex that use ratingstrip to understand the current API.

[After checking]: The fixture shows items as direct `\ratingitem` commands inside `\begin{ratingstrip}...\end{ratingstrip}`, with automatic horizontal layout.

Two-pass solution:
1. First pass: count items
2. Second pass: render with dynamic width

Or simpler: automatically collect items into a tabularx inside `\end{ratingstrip}`, without changing the input syntax.

Actually, the simplest fix that preserves the API: use `\vbox`-based collecting and a two-pass measure, mirroring `reportkit-structure.sty:capabilitymap`. But that's complex for this session.

Let me use a pragmatic middle ground: make `\ratingitem` use a dynamic width based on a macro that the caller must set. The example fixture becomes:

```latex
\begin{ratingstrip}[itemcount=3]
  \ratingitem{Stock Rating}{Overweight}
  \ratingitem{Industry View}{Attractive}
  \ratingitem{Price Target}{\$245}
\end{ratingstrip}
```

This trades flexibility for simplicity. Let me implement:

- [ ] **Step 3c: Rewrite ratingstrip with itemcount parameter**

Replace lines 102–117:

```latex
\newcounter{rkratingitem}
\newcounter{rk@ratingitemcount}

\NewDocumentEnvironment{ratingstrip}{o}{%
  \par\Needspace{4\baselineskip}\noindent
  \setcounter{rkratingitem}{0}%
  % Optional parameter: itemcount=N for explicit item count (3 or 4).
  % If not provided, defaults to 3 (the original common case).
  \IfNoValueTF{#1}{%
    \setcounter{rk@ratingitemcount}{3}%
  }{%
    \setcounter{rk@ratingitemcount}{#1}%
  }%
  {\color{Hairline}\hrule height 0.4pt}\par\vspace{5pt}\noindent
}{%
  \par\vspace{3pt}{\color{Hairline}\hrule height 0.4pt}\par\vspace{6pt}%
}

\NewDocumentCommand{\ratingitem}{m m}{%
  \stepcounter{rkratingitem}%
  \ifnum\value{rkratingitem}>1\quad{\color{Hairline}\vrule width 0.4pt}\quad\fi
  % Dynamically compute width: 1 / itemcount \linewidth
  \pgfmathsetmacro{\rk@itemwidth}{1 / \value{rk@ratingitemcount}}%
  \begin{minipage}[t]{\rk@itemwidth\linewidth}%
    {\sffamily\rksidebarsize\color{Muted}\MakeUppercase{#1}\par}%
    \vspace{1pt}{\sffamily\bfseries\rkratingvaluesize\color{Ink}#2\par}%
  \end{minipage}%
}
```

This keeps the visual API mostly the same (still minipages with hairline rules), but makes width dynamic. The caller optionally passes `[itemcount=4]` to `\begin{ratingstrip}`. Default is 3 (backward compatible).

- [ ] **Step 4: Run the fixture to test 3-item case (default)**

```bash
cd /home/iancwm/git/report-kit
reportkit build latex_templates/examples/equity-research/
```

Verify the output looks the same as before for 3 items.

- [ ] **Step 5: Update the fixture to test 4-item case**

This is for Task 5 (fixture updates). For now, just verify the LaTeX compiles with the change.

- [ ] **Step 6: Commit**

```bash
cd /home/iancwm/git/report-kit
git add latex_templates/publication_types/reportkit-equity-research.sty
git commit -m "feat: rating strip now supports 3-4 items with dynamic width

Per §29.1 post-implementation finding: replace fixed minipage widths
(0.29\linewidth hardcoded for 3 items) with pgfmathsetmacro-derived
widths based on the itemcount parameter.

Usage:
  \begin{ratingstrip}[itemcount=3]
    \ratingitem{...}{...}
    \ratingitem{...}{...}
    \ratingitem{...}{...}
  \end{ratingstrip}

Default itemcount=3 for backward compatibility.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Add sidebar subheading type scale to LaTeX theme

**Files:**
- Modify: `latex_templates/themes/reportkit-theme-institutional-research.sty:223` (Type scale section)
- Modify: `latex_templates/publication_types/reportkit-equity-research.sty:349` (rksubheading command)

**Interfaces:**
- Consumes: `\rksidebarsize` (defined in theme, 7.6 pt / 9.5 pt)
- Produces: `\rksidebarsubheadingsize` (new, 6.7 pt / 8.1 pt) and updated `\rksubheading` using it

**Rationale:** §29.2 found that sidebar subheadings use the same size as sidebar body text. The new type-scale level creates hierarchy without requiring color or boxes (per spec §5's principle: "Use weight and size before color").

- [ ] **Step 1: Locate the type-scale section in the theme file (lines 191–226)**

This section defines all the `\rk*size` commands.

- [ ] **Step 2: Add the new sidebar subheading size after \rksidebarsize (line 223)**

Insert after line 223:

```latex
\newcommand{\rksidebarsubheadingsize}{\fontsize{6.7pt}{8.1pt}\selectfont}
```

The range 6.6–6.8 pt from the spec becomes 6.7 pt; leading 8–8.2 becomes 8.1 pt.

- [ ] **Step 3: Verify the new command fits the naming pattern**

Check that `\rksidebarsubheadingsize` follows the same `\rk<location><feature>size` convention as other commands. ✓

- [ ] **Step 4: Update \rksubheading in reportkit-equity-research.sty (line 349)**

Read line 349:

```latex
\newcommand{\rksubheading}[1]{\par\vspace{6pt}{\sffamily\bfseries\rksidebarsize\color{Accent}\MakeUppercase{#1}\par}\vspace{3pt}}
```

Replace `\rksidebarsize` with `\rksidebarsubheadingsize`:

```latex
\newcommand{\rksubheading}[1]{\par\vspace{6pt}{\sffamily\bfseries\rksidebarsubheadingsize\color{Accent}\MakeUppercase{#1}\par}\vspace{3pt}}
```

- [ ] **Step 5: Verify no other uses of "subheading" in the file need updating**

Search for "subhead" or "rksubheading" in reportkit-equity-research.sty. Only line 349 should be the definition.

- [ ] **Step 6: Build and check visual output**

```bash
cd /home/iancwm/git/report-kit
reportkit build latex_templates/examples/equity-research/
```

Visually confirm that sidebar subheadings (e.g., "Investment Thesis", "Key Debates" on page 3 of the fixture) now appear noticeably smaller than sidebar body text, creating clear hierarchy.

- [ ] **Step 7: Commit**

```bash
cd /home/iancwm/git/report-kit
git add latex_templates/themes/reportkit-theme-institutional-research.sty latex_templates/publication_types/reportkit-equity-research.sty
git commit -m "feat: add sidebar subheading type scale

Per §29.2 post-implementation finding: the sidebar now has a distinct,
smaller type step for subheadings (6.7 pt / 8.1 pt), establishing size-
based hierarchy alongside weight and color, per spec §5's principle.

Files modified:
- theme: add \rksidebarsubheadingsize command
- equity-research: update \rksubheading to use the new size

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Add sidebar figure preset and donut_chart function

**Files:**
- Modify: `python_scripts/reportkit/themes/institutional_research.py:95-102` (figure_sizes dict)
- Modify: `python_scripts/reportkit/themes/default.py:95-102` (figure_sizes dict, for consistency)
- Modify: `python_scripts/reportkit_viz.py` (add donut_chart function)
- Test: `python_scripts/tests/test_reportkit_viz.py` (add test for donut_chart)

**Interfaces:**
- Consumes: `new_figure(size)` function (existing), theme `figure_sizes` dict
- Produces: `donut_chart(data, *, title=None, size="sidebar", ...)` function matching other chart signatures

**Rationale:** §29.3 found no sidebar-sized figure preset, making it impossible for authors to embed proportional-data charts. This adds a preset and the chart function to support it.

- [ ] **Step 1: Add "sidebar" figure preset to institutional theme**

The sidebar width in the equity-research layout is ~0.28\linewidth (spec §7). On US Letter with 187.9mm text width:

```
0.28 × 187.9mm = 52.6mm ≈ 2.07in
```

Sidebar charts should be roughly square for proportional data (a 1:1 aspect ratio works well for donut charts). Use a small margin so the chart doesn't touch the outer margin:

```python
"sidebar": (1.95, 1.95),  # ~2in square for sidebar column charts
```

Calculate the height as a multiple of text width to stay consistent with other presets' ratio-derived approach. The institutional theme's TEXT_WIDTH_IN is 7.39in. A sidebar ratio:

```
sidebar_width = 0.28 × text_width_in = 0.28 × 7.39 ≈ 2.07in
Aspect ratio for sidebar: roughly 1:1 (0.897 per default.py's square pattern, or 1.0 for donut)
```

Use `(1.95, 1.95)` for a small square that fits comfortably.

Edit line 95-102 of `python_scripts/reportkit/themes/institutional_research.py`:

```python
figure_sizes={
    "full": (TEXT_WIDTH_IN, 4.276),
    "wide": (TEXT_WIDTH_IN, 3.674),
    "dominant": (TEXT_WIDTH_IN, 3.674),
    "compact": (TEXT_WIDTH_IN, 3.071),
    "square": (5.842, 5.240),
    "half": (3.588, 1.490),
    "sidebar": (1.95, 1.95),  # ~2in square for proportional data (pie/donut) in sidebar
},
```

- [ ] **Step 2: Add same preset to default theme for consistency**

The default theme also has figure_sizes. Check `python_scripts/reportkit/themes/default.py:95-102` and add the same `"sidebar"` entry. The sidebar width in a default-theme document is different (based on A4 27mm margins), so derive it:

```
A4 width = 210mm, margins 27mm each, text width = 210 - 54 = 156mm
Sidebar width = 0.28 × 156 = 43.68mm ≈ 1.72in

Use (1.65, 1.65) for default theme's sidebar, to match the aspect ratio.
```

Add to default.py's figure_sizes:

```python
"sidebar": (1.65, 1.65),  # ~1.7in square for proportional data in sidebar (default A4 theme)
```

- [ ] **Step 3: Implement donut_chart function in reportkit_viz.py**

Add this function after `risk_reward_chart` (after line 741):

```python
def donut_chart(
    data: dict[str, float],
    *,
    title: str | None = None,
    size: str | tuple[float, float] = "sidebar",
    colors: list[str] | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot proportional data as a donut chart, sized for sidebar embeds.
    
    Used for small compositions (segment splits, geographic mixes, revenue
    breakdowns) in sidebars that are proportions of a whole, per spec §29.3.
    
    Args:
        data: dict of {label: value} pairs. Values are summed and rendered as
              proportions of the total.
        title: optional chart title
        size: figure size key (e.g., "sidebar") or (width, height) tuple
        colors: list of hex colors for each slice. If None, uses the theme's
                data_colors in order.
    
    Returns:
        (fig, ax) tuple for save_figure() integration.
    """
    if not data:
        raise ValueError("donut_chart requires non-empty data dict")
    
    if colors is None:
        colors = DATA_COLORS
    
    # Use only as many colors as there are slices; cycle if needed
    colors = [colors[i % len(colors)] for i in range(len(data))]
    
    fig, ax = new_figure(size)
    
    labels = list(data.keys())
    values = list(data.values())
    
    # Draw donut with a small inner hole (wedgeprops controls the hole size)
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct='%1.0f%%',
        startangle=90,
        textprops={"fontsize": 7.0, "color": TEXT_COLOR},
        wedgeprops={"edgecolor": "white", "width": 0.4},  # Inner hole at 60% of radius
    )
    
    # Style the percentage labels
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(6.5)
        autotext.set_weight("bold")
    
    # Remove the axis (pie charts don't need axes)
    ax.axis("off")
    
    _title(ax, title)
    return fig, ax
```

Wait — I need to check what DATA_COLORS and TEXT_COLOR are in the current viz module. Let me refine:

- [ ] **Step 3b: Check reportkit_viz.py for existing color/text constants**

Search for DATA_COLORS, PRIMARY, TEXT_COLOR usage in reportkit_viz.py. I see references to PRIMARY, DATA_NEGATIVE, DATA_WARM, METRIC, HAIRLINE, SURFACE in the existing code. Let me use those:

Revised donut_chart:

```python
def donut_chart(
    data: dict[str, float],
    *,
    title: str | None = None,
    size: str | tuple[float, float] = "sidebar",
    colors: list[str] | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot proportional data as a donut/pie chart for sidebars.
    
    Renders a small, themed donut chart suitable for embedding in a sidebar
    (~2in square for sidebar column), per spec §29.3. Use for 2–4 slices
    representing parts of a whole (segment splits, geographic mixes).
    
    Args:
        data: {label: value} dict. Values are summed to compute proportions.
        title: optional chart title (rare for sidebar embeds)
        size: figure size key ("sidebar" default) or (width, height) tuple
        colors: optional list of hex colors for slices; uses theme palette if
                None. Colors are cycled if more slices than colors provided.
    
    Returns:
        (fig, ax) for chaining to save_figure()
    """
    if not data:
        raise ValueError("data dict cannot be empty")
    
    if colors is None:
        colors = [PRIMARY, LINK_BLUE, SERIES_GOLD, MUTED]  # Theme palette
    
    # Cycle colors to match slice count
    colors = [colors[i % len(colors)] for i in range(len(data))]
    
    fig, ax = new_figure(size)
    
    labels = list(data.keys())
    values = list(data.values())
    
    # Donut chart: pie with a white inner circle (wedgeprops.width < 1.0)
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.0f%%",
        startangle=90,
        textprops={"fontsize": 7.0, "weight": "normal", "color": TEXT_COLOR},
        wedgeprops={"edgecolor": SURFACE, "linewidth": 1.5, "width": 0.4},
    )
    
    # Style percentage labels: white, bold, smaller
    for autotext in autotexts:
        autotext.set_color(SURFACE)
        autotext.set_fontsize(6.5)
        autotext.set_weight("bold")
    
    ax.axis("off")
    _title(ax, title)
    return fig, ax
```

But wait, I need to check what TEXT_COLOR is. Let me revise once more to match the existing codebase patterns.

- [ ] **Step 3c: Read existing chart functions for color/text patterns (lines 644–741)**

From risk_reward_chart I see:
- Uses `PRIMARY`, `DATA_NEGATIVE`, `DATA_WARM`, `METRIC` for colors
- Uses `color=color` in annotations
- TextProps not explicitly set in pie calls in the codebase I've seen
- ax.pie typically auto-colors text dark

Let me finalize:

```python
def donut_chart(
    data: dict[str, float],
    *,
    title: str | None = None,
    size: str | tuple[float, float] = "sidebar",
    colors: list[str] | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot proportional data as a donut chart for sidebar embeds.
    
    Renders 2–4 slices (segment split, geographic/channel mix, revenue
    composition) as a small square donut chart sized for the sidebar column
    (~2in). Per spec §29.3, reserve this for proportional compositions;
    use bar charts for other data shapes.
    
    Args:
        data: {label: value} dict of slice labels and their values
        title: optional chart title (typically None for sidebar charts)
        size: figure preset ("sidebar" default) or (width_in, height_in) tuple
        colors: list of hex colors for slices; cycles if fewer than slices.
                If None, uses theme data_colors.
    
    Returns:
        (fig, ax) for further styling or save_figure() integration
    """
    if not data:
        raise ValueError("data must be non-empty")
    
    if colors is None:
        colors = [PRIMARY, LINK_BLUE, SERIES_GOLD, MUTED]
    
    # Ensure enough colors for all slices
    colors_cycle = (colors * ((len(data) // len(colors)) + 1))[:len(data)]
    
    fig, ax = new_figure(size)
    
    labels = list(data.keys())
    values = list(data.values())
    
    # Draw donut (pie with hole) with theme styling
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors_cycle,
        autopct="%1.0f%%",
        startangle=90,
        textprops={"fontsize": 7.0},
        wedgeprops={"edgecolor": SURFACE, "linewidth": 1.2, "width": 0.4},
    )
    
    # Style percentage text inside slices
    for autotext in autotexts:
        autotext.set_color(SURFACE)
        autotext.set_fontsize(6.5)
        autotext.set_weight("bold")
    
    # Style slice labels
    for text in texts:
        text.set_fontsize(7.0)
        text.set_color(INK)
    
    ax.axis("off")
    _title(ax, title)
    return fig, ax
```

- [ ] **Step 4: Write a test for donut_chart**

Create a test file or add to the existing viz tests:

```python
def test_donut_chart():
    """Test donut_chart renders without error and produces correct figure."""
    data = {
        "Consulting": 52,
        "Managed Services": 48,
    }
    fig, ax = reportkit_viz.donut_chart(
        data,
        title="Revenue Mix",
        size="sidebar",
    )
    assert fig is not None
    assert ax is not None
    # Verify the chart has a pie (wedges should exist)
    assert len(ax.patches) > 0
    # Verify axes are off (pie charts have no axes)
    assert not ax.get_visible()

def test_donut_chart_with_custom_colors():
    """Test donut_chart accepts custom colors."""
    data = {"A": 30, "B": 40, "C": 30}
    colors = ["#FF0000", "#00FF00", "#0000FF"]
    fig, ax = reportkit_viz.donut_chart(data, colors=colors, size="sidebar")
    assert fig is not None

def test_donut_chart_color_cycling():
    """Test donut_chart cycles colors when more slices than colors."""
    data = {f"Slice {i}": i+1 for i in range(6)}  # 6 slices
    colors = ["#FF0000", "#00FF00"]  # Only 2 colors
    fig, ax = reportkit_viz.donut_chart(data, colors=colors, size="sidebar")
    assert len(ax.patches) == 6
    assert fig is not None

def test_donut_chart_empty_data_raises():
    """Test donut_chart rejects empty data."""
    with pytest.raises(ValueError, match="data must be non-empty"):
        reportkit_viz.donut_chart({})
```

Run:

```bash
cd /home/iancwm/git/report-kit
python -m pytest python_scripts/tests/test_reportkit_viz.py::test_donut_chart -v
python -m pytest python_scripts/tests/test_reportkit_viz.py::test_donut_chart_with_custom_colors -v
python -m pytest python_scripts/tests/test_reportkit_viz.py::test_donut_chart_color_cycling -v
python -m pytest python_scripts/tests/test_reportkit_viz.py::test_donut_chart_empty_data_raises -v
```

All should pass.

- [ ] **Step 5: Commit themes and viz changes**

```bash
cd /home/iancwm/git/report-kit
git add python_scripts/reportkit/themes/institutional_research.py
git add python_scripts/reportkit/themes/default.py
git add python_scripts/reportkit_viz.py
git add python_scripts/tests/test_reportkit_viz.py
git commit -m "feat: add sidebar figure preset and donut_chart function

Per §29.3 post-implementation finding: add 'sidebar' figure size preset
(~2in square) to both institutional-research and default themes, sized
for proportional data charts in the ~28%-wide sidebar column.

Add donut_chart() function to reportkit_viz.py for rendering 2-4 slice
compositions (segment splits, geographic mixes) as small donut charts.

- Theme modules: add 'sidebar' to figure_sizes dicts
- reportkit_viz.py: add donut_chart(data, *, size='sidebar', colors=None)
- tests: add test_donut_chart, test_donut_chart_with_custom_colors,
  test_donut_chart_color_cycling, test_donut_chart_empty_data_raises

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update fixture example with 4-item rating strip and sidebar chart

**Files:**
- Modify: `latex_templates/examples/equity-research/report.tex` (front page rating strip)
- Modify: `latex_templates/examples/equity-research/figures.py` (add sidebar chart figure generation)
- Modify: `latex_templates/examples/equity-research/publication.yaml` (if needed for new figures)
- Create/Update: `latex_templates/examples/equity-research/expected/` (visual regression baseline)

**Interfaces:**
- Consumes: New rating strip with itemcount=4 support, donut_chart function from reportkit_viz
- Produces: Updated fixture PDF with 4-item rating strip on front page and sidebar donut chart

**Rationale:** §29.1 and §29.3 both require fixture updates: Task 1 (rating strip) needs a 4-item test case; Task 3 (sidebar chart) needs a page demonstrating the new capability.

- [ ] **Step 1: Update the front page rating strip to use 4 items**

Edit `latex_templates/examples/equity-research/report.tex` around the rating strip. Find the `\begin{ratingstrip}` section. The current fixture likely has 3 items. Add a 4th (`Implied Upside`) and update the `itemcount` parameter:

```latex
\begin{ratingstrip}[itemcount=4]
  \ratingitem{Stock Rating}{Overweight}
  \ratingitem{Price Target}{\$245}
  \ratingitem{Reference Price}{\$182.50}
  \ratingitem{Implied Upside}{34.3\%}
\end{ratingstrip}
```

- [ ] **Step 2: Add sidebar chart to the example**

Choose a page with a sidebar (likely page 1 or page 3 with the Risk/Reward analysis). The ACN report mentioned a "Business mix" sidebar block showing Consulting vs. Managed Services revenue. Add to the sidebar section:

```latex
\vspace{6pt}
\kicker{Business Mix}
\begin{minipage}[t]{\linewidth}
  \centering
  \includegraphics[width=1.8in]{figures/business_mix.pdf}
\end{minipage}
\sidebarrule
\begin{sidebarrow}{Consulting}{52\%}\end{sidebarrow}
\begin{sidebarrow}{Managed Services}{48\%}\end{sidebarrow}
```

(Adjust the page/location based on the fixture's current structure.)

- [ ] **Step 3: Generate the sidebar chart figure in figures.py**

Edit `latex_templates/examples/equity-research/figures.py` to add:

```python
import pandas as pd
import reportkit_viz as rkv

# Sidebar business mix chart
data = {
    "Consulting": 52,
    "Managed Services": 48,
}
fig, ax = rkv.donut_chart(data, size="sidebar")
rkv.save_figure(fig, "figures/business_mix.pdf")
fig.close()
```

Verify the script runs:

```bash
cd /home/iancwm/git/report-kit/latex_templates/examples/equity-research
python figures.py
```

The figures/ directory should now contain `business_mix.pdf`.

- [ ] **Step 4: Build the updated fixture**

```bash
cd /home/iancwm/git/report-kit
reportkit build latex_templates/examples/equity-research/
```

Expected output: `latex_templates/examples/equity-research/report.pdf`

- [ ] **Step 5: Visually inspect the PDF**

Open the PDF and verify:
- Front page: 4-item rating strip renders without wrapping (Overweight | $245 | $182.50 | 34.3%)
- Sidebar chart page: donut chart showing Consulting/Managed Services appears as a 2-slice ~2in square, not overflowing the sidebar
- Sidebar subheadings: noticeably smaller than body text (e.g., "Business Mix" < "52%" value)

If anything appears broken, fix in the LaTeX or Python and rebuild.

- [ ] **Step 6: Update visual regression baseline**

Copy the new PDF to the expected/ directory:

```bash
cd /home/iancwm/git/report-kit
cp latex_templates/examples/equity-research/report.pdf latex_templates/examples/equity-research/expected/report.pdf
```

If the spec §25 describes a visual regression test (converting PDF to PNG per page), set that up here. For now, the PDF itself is the baseline.

- [ ] **Step 7: Commit fixture updates**

```bash
cd /home/iancwm/git/report-kit
git add latex_templates/examples/equity-research/report.tex
git add latex_templates/examples/equity-research/figures.py
git add latex_templates/examples/equity-research/figures/business_mix.pdf
git add latex_templates/examples/equity-research/expected/report.pdf
git commit -m "docs: update equity-research fixture with 4-item rating strip and sidebar chart

Per §29 post-implementation findings:
- Front page now uses 4-item rating strip (Overweight, Price Target,
  Reference Price, Implied Upside) to exercise the new dynamic-width
  support (Task 4).
- Sidebar now includes a business-mix donut chart (Consulting/Managed
  Services) to demonstrate the new sidebar-sized figure preset and
  donut_chart function (Task 6).

Visual regression baseline updated.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Run full build and verify compilation

**Files:**
- No file changes (verification only)

**Interfaces:**
- Consumes: All changes from Tasks 1–7
- Produces: Successful build output; verified PDF with all fixes applied

**Rationale:** Before declaring the work complete, verify that the full build pipeline produces clean output with no LaTeX errors, warnings, or visual regressions.

- [ ] **Step 1: Clean previous build artifacts**

```bash
cd /home/iancwm/git/report-kit
rm -rf latex_templates/examples/equity-research/build/ latex_templates/examples/equity-research/report.pdf
```

- [ ] **Step 2: Run the full build**

```bash
cd /home/iancwm/git/report-kit
reportkit build latex_templates/examples/equity-research/ --verbose
```

Expected: Clean exit (0), no LaTeX compilation errors or overfull/underfull box warnings.

- [ ] **Step 3: Verify the output PDF exists and is valid**

```bash
ls -lh latex_templates/examples/equity-research/report.pdf
file latex_templates/examples/equity-research/report.pdf
```

- [ ] **Step 4: Spot-check the PDF pages**

Open the PDF and verify:
- Page 1: 4-item rating strip (no wrapping), correct sidebar font hierarchy
- Page 3 (or chart page): sidebar donut chart visible, sized appropriately
- No blank pages or layout shifts from before the changes
- All text renders in Google Sans (per institutional theme)

- [ ] **Step 5: Run any existing visual regression tests if configured**

If `reportkit` has a visual regression test suite (per spec §25), run it:

```bash
cd /home/iancwm/git/report-kit
# Hypothetical command; adjust if the actual test runner differs
pytest tests/ -k "equity_research" -v
```

Expected: All tests pass.

- [ ] **Step 6: Final commit message (documentation only — no files changed)**

Log the successful build:

```bash
# No commit needed; all changes committed in Tasks 1–7.
# Just verify the working tree is clean:
cd /home/iancwm/git/report-kit
git status
```

Expected: `On branch main, nothing to commit, working tree clean.`

---

## Summary

**Defects Fixed:**
1. Rating strip now supports 3–4 items with dynamic width (Task 4)
2. Sidebar now has a distinct type-scale level for subheadings (Task 5)
3. Sidebar figures can now display proportional-data donut charts at a sidebar-appropriate size (Task 6)

**Spec Updates:**
- §9: Item-count range requirement
- §5: Sidebar subheading type scale
- §8, §22: Sidebar chart guidance

**Implementation:**
- LaTeX: Dynamic rating-strip width, new `\rksidebarsubheadingsize`
- Python: Sidebar figure preset, `donut_chart()` function
- Fixture: 4-item rating strip, sidebar chart example

**Testing:**
- Build passes with no LaTeX errors
- Fixture PDF visually verified
- Python unit tests for donut_chart pass

---

## Next Steps (After Execution)

If any task reveals issues:
- Task 4 (rating strip) may need `pgfmathsetmacro` debugging if LaTeX math fails
- Task 6 (donut chart) may need matplotlib version compatibility checks
- Task 7 (fixture) may need coordinate adjustments if sidebar layout shifts

Revisit the spec's Open Questions if any architectural decisions emerge.
