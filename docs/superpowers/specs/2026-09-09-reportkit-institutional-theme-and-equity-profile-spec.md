# ReportKit — Institutional Research Theme + Equity Research Profile

**Status:** Implemented (Steps 1-5). Current-state claims verified against the
working tree on 2026-09-09 (see [Current state](#current-state-verified-2026-09-09)).
The eight open questions below are resolved — see
[2026-09-09-reportkit-institutional-theme-implementation-plan.md](../plans/2026-09-09-reportkit-institutional-theme-implementation-plan.md),
which also tracks execution. That plan's Step 1 (theme infrastructure),
Step 2 (the institutional theme itself), Step 3 (the equity-research
publication profile), Step 4 (visualization integration), and Step 5
(fixtures, QA, and skill guidance) are all implemented. No implementing
session had a TeX Live install with `lualatex`, so the LaTeX-level
compile of Steps 1-3 and the visual-regression baseline Step 5 sets up
are both still genuinely unverified by compilation — see the plan's Step
5 section, "Not performed", before treating this as compile-clean.
**This gap is not hypothetical:** the first real compile against this spec
(the ACN initiation-of-coverage report, 9 September 2026) surfaced three
defects that only show up when `lualatex` actually runs the templates —
see [§29, Post-implementation findings](#29-post-implementation-findings-first-production-report-2026-09-09).
**Last updated:** 2026-09-09
**Visual reference:** Appendix A — the `meridian_equity_research_mockup_v3`
prototype, embedded verbatim. The prototype is a hand-coded proof of the target
visual language; it is **not** the target implementation (see §28, Definition of
done).

---

## Framing: two abstractions, not one clone

This should be implemented as **two separate abstractions**, not as a one-off
Morgan Stanley clone:

- **Theme:** `institutional-research` — typography, spacing, color, rules,
  tables, chart styling.
- **Publication type:** `equity-research` — rating strip, analyst rail, "what
  changed", exhibits, valuation/risk-reward pages, model pages.

That distinction is the point of the sprint. The current class hardcodes A4,
10pt Libertinus, margins, palette, headings and running furniture, while
`reportkit_viz.py` separately hardcodes its own typography and A4-derived figure
dimensions. This work should introduce a real theme boundary rather than bolt
more conditionals onto the existing class.

---

## Objective

Add a publication-ready institutional research design system inspired by
high-end sell-side research, using the approved mockup as the visual reference.

The output should feel:

- editorial rather than dashboard-like;
- analytically dense without making prose visually dense;
- driven by typography, alignment, whitespace and exhibits rather than cards;
- suitable for equity research, investment strategy, sector notes and other
  institutional analytical publications;
- visually consistent between LaTeX text, tables, diagrams and Python-generated
  charts.

The implementation must **not** copy Morgan Stanley branding, logos, proprietary
marks or exact branded layouts. The reference informs visual grammar only.

---

## Current state (verified 2026-09-09)

Every current-state premise in the source draft was checked against the tree.
All of them hold. Exact anchors, so the implementer does not have to re-derive
them:

| Premise | Verified at |
| --- | --- |
| Class hardcodes 10pt / A4 | `latex_templates/reportkit.cls:7` — `\LoadClass[10pt,a4paper]{article}` |
| Class hardcodes 27 mm side margins | `latex_templates/reportkit.cls:9` |
| Class hardcodes Libertinus | `latex_templates/reportkit.cls:24` |
| Class owns the palette | `latex_templates/reportkit.cls:44+` (`Ink`, `Muted`, `Hairline`, semantic callout colors, `Surface`) |
| Class owns running furniture | `fancyhdr` required at `latex_templates/reportkit.cls:34` |
| Viz layer hardcodes A4 text width | `python_scripts/reportkit_viz.py:98-99` — `# A4 ReportKit text width: 210mm - 2*27mm = 156mm.` / `TEXT_WIDTH_IN = 156 / 25.4` |
| Viz layer hardcodes figure sizes | `python_scripts/reportkit_viz.py:100-103` — keys `full` / `wide` / `compact`, each with a hardcoded height |
| Viz layer selects its own font families | `python_scripts/reportkit_viz.py:147-151` |
| Viz layer uses a serif mathtext set | `python_scripts/reportkit_viz.py:184` — `"mathtext.fontset": "stix"` |
| Config understands only `main`/`class`/`engine` | `python_scripts/reportkit/config.py:14` — `DOCUMENT_KEYS = ("main", "class", "engine")` |
| Config top-level sections | `python_scripts/reportkit/config.py:22` — `SECTIONS = ("publication", "document", "profiles", "validation", "output")` |
| Default engine is pdfTeX, not LuaTeX | `python_scripts/reportkit/config.py:323` — `document.setdefault("engine", "pdflatex")` |

Structural facts the target trees in §2 must accommodate:

- `latex_templates/` is currently **flat**. There is no `reportkit-core.sty`.
  The existing modules are `reportkit-boxes`, `-code`, `-diagrams`, `-grammar`,
  `-longform`, `-pandoc`, `-process`, `-spatial`, `-structure`.
- `python_scripts/reportkit/` has no `themes/`. Existing modules: `analysis`,
  `authoring`, `cli`, `config`, `context`, `diagnostics`, `manifest`,
  `registry`.
- `reportkit_viz.py` sits at `python_scripts/reportkit_viz.py` — **outside** the
  `reportkit` package.
- `latex_templates/examples/` currently contains one example, `career_guide_en`.
- `reportkit_viz.py` exposes a `check-theme` CLI command
  (`python_scripts/reportkit_viz.py:1428`) that validates the Python palette
  against a single `reportkit.cls` path.

---

## Open questions and discrepancies

These are unresolved. They are not objections to the design; they are decisions
the design leaves open, found while verifying it.

1. **Engine default conflicts with the theme requirement.** §4 requires
   LuaLaTeX for the high-fidelity profile, but the config default is `pdflatex`
   (`config.py:323`). Selecting `theme: institutional-research` without setting
   `engine: lualatex` must not silently produce a degraded PDF. Decide: does
   theme selection force the engine, validate and fail, or warn? Recommend
   *validate and fail*, consistent with §4's `font_policy: strict` behaviour.

2. **`check-theme` is single-theme by construction.** It compares the Python
   palette against one `.cls` file. Once palettes live per theme, this command
   either false-passes (checking the default palette while the institutional
   theme is active) or false-fails. It must become theme-aware in the same step
   that introduces theme palettes. §13 now carries a pointer to this item, but
   the intended behaviour is still undecided.

3. **`FIGURE_SIZES` key change is a breaking API change.** Current keys are
   `full` / `wide` / `compact` (`reportkit_viz.py:100-103`). §15 proposes
   `full` / `half` / `dominant` / `compact`, dropping `wide`. `wide` is public
   API and is used by existing publications. Keep it, or alias it, and say
   which in the implementation plan.

4. **§15 needs an aspect-ratio policy, not just a width.** The current sizes
   hardcode *height* alongside the A4-derived width. Deriving width from
   paper/margins/columns leaves height undefined. Specify whether heights are
   fixed, ratio-derived, or per-size constants.

5. **§6 geometry deliberately diverges from the prototype.** Appendix A uses
   `top=0.42in, bottom=0.42in, left=0.48in, right=0.48in` (≈ 10.7 mm /
   12.2 mm). §6 specifies 13–15 mm sides and 13–17 mm top/bottom — looser than
   the prototype, consistent with §5's instruction that body text be *more*
   readable than the mockup. **§6 governs. Do not copy the prototype's
   geometry.** The same applies to type sizes: the prototype's 9.85/13.55 body
   and 6.25–6.85 pt sidebar are superseded by §5's 10.7/14.6 and 7.6/9.5.

6. **The prototype's numbers are internally inconsistent, and §24–25 make it
   the regression fixture.** Three self-consistent islands that disagree with
   each other:
   - Front page and Exhibit 4 agree on FY27E EBITDA **691** and EPS **2.95**
     (and the sidebar P/E of 62 is consistent with 2.95 at $182.50).
   - Exhibit 5 is internally consistent on 2027E Adjusted EBITDA **917**
     (647 operating income + 112 D&A + 158 SBC) and EPS **2.27**
     (547 net income ÷ 241 diluted shares) — both disagree with the above.
   - Exhibit 6 requires **122** diluted shares to reach the $245 target
     (29,901 ÷ 122), against the model's **241**; and its Value/Share column
     sums to **$233**, not $245.

   The segment EV build does reconcile (16,260 + 10,665 + 1,116 = 28,041). Fix
   the fixture's arithmetic before it becomes a QA baseline — a fixture that
   ships with contradictory estimates teaches the authoring agent the wrong
   lesson, even with the "figures are fictional" disclaimer.

7. **§2's target tree omits six existing LaTeX modules.** `-grammar`,
   `-longform`, `-pandoc`, `-process`, `-spatial` and `-structure` are elided
   behind the `...` in §2. They must be preserved.

8. **Theme-token import direction is undecided.** §2 places theme modules in
   `python_scripts/reportkit/themes/`, inside the package, while their consumer
   (`reportkit_viz.py`) sits outside it. Either move the viz layer into the
   package or expose tokens through a boundary the outside module can import
   without a circular dependency.

---

# 1. Architectural principle

Do **not** create:

```text
reportkit-morgan-stanley.cls
```

or place equity-specific commands directly into `reportkit.cls`.

Instead introduce:

```text
ReportKit Core
│
├── Publication Type
│   └── equity-research
│
└── Theme
    ├── default
    └── institutional-research
```

Conceptually:

```text
content semantics × publication structure × visual theme
```

For example:

```yaml
document:
  publication_type: equity-research
  theme: institutional-research
```

A future combination could therefore be:

```yaml
document:
  publication_type: equity-research
  theme: modern-minimal
```

without rewriting the research document.

Conversely:

```yaml
document:
  publication_type: strategy-report
  theme: institutional-research
```

should reuse the typography and exhibit treatment without exposing stock-rating
primitives.

This preserves the homogeneous semantic feature set across themes.

---

# 2. Required repository restructuring

The current `reportkit.cls` owns typography, paper geometry, palette, headings,
title construction, headers/footers and metadata in one file. Extract
theme-controlled presentation from the core.

Target structure:

```text
latex_templates/
├── reportkit.cls
├── reportkit-core.sty
│
├── themes/
│   ├── reportkit-theme-default.sty
│   └── reportkit-theme-institutional.sty
│
├── publication_types/
│   └── reportkit-equity-research.sty
│
├── reportkit-boxes.sty
├── reportkit-code.sty
├── reportkit-diagrams.sty
├── reportkit-grammar.sty
├── reportkit-longform.sty
├── reportkit-pandoc.sty
├── reportkit-process.sty
├── reportkit-spatial.sty
├── reportkit-structure.sty
│
└── examples/
    ├── career_guide_en/
    └── equity-research/
        ├── report.tex
        ├── publication.yaml
        ├── figures.py
        └── expected/
```

The nine existing `.sty` modules are listed explicitly here because the source
draft elided them; none may be dropped (see
[Open questions](#open-questions-and-discrepancies) #7).

Python:

```text
python_scripts/reportkit/
├── themes/
│   ├── __init__.py
│   ├── default.py
│   └── institutional_research.py
└── ...
```

Do **not** duplicate chart functions by theme. Theme objects should supply
tokens to the existing visualization API. Resolve the import-direction question
([Open questions](#open-questions-and-discrepancies) #8) before writing these
modules.

---

# 3. Theme configuration contract

Extend `publication.yaml`. The current config only recognizes `publication`,
`document`, `profiles`, `validation` and `output`
(`python_scripts/reportkit/config.py:22`), and the `document` section
understands only `main`, `class` and `engine`
(`python_scripts/reportkit/config.py:14`).

Add:

```yaml
document:
  main: report.tex
  class: reportkit
  engine: lualatex
  publication_type: equity-research
  theme: institutional-research
  paper: letter
```

Optional:

```yaml
theme:
  font_family: Google Sans
  font_path: assets/fonts/GoogleSans.ttf
  font_policy: strict
```

Supported values:

```text
font_policy:
  strict    fail if requested font cannot be resolved
  fallback  use theme fallback and issue warning
```

Do not allow arbitrary design values to proliferate through `publication.yaml`.

The theme itself owns:

- margins;
- type scale;
- leading;
- colors;
- rule widths;
- sidebar proportions;
- exhibit spacing;
- table grammar;
- figure dimensions.

Configuration selects themes; it does not redesign them.

---

# 4. Google Sans font handling

The institutional theme uses **Google Sans as both the principal document face
and the visualization face**.

LuaLaTeX is therefore required for the high-fidelity profile. Because the config
default is `pdflatex`, theme selection must validate the engine rather than
degrade silently — see [Open questions](#open-questions-and-discrepancies) #1.

LaTeX should resolve the font through `fontspec`:

```latex
\setmainfont{Google Sans}
\setsansfont{Google Sans}
```

with support for an explicit local path when necessary.

Do not commit or redistribute the supplied font file unless redistribution
rights have been verified. ReportKit should support:

1. system-installed Google Sans;
2. publication-local font path;
3. configurable fallback.

Recommended fallback:

```text
Inter
→ Noto Sans
→ TeX Gyre Heros
```

The diagnostic system should report:

```text
PASS  institutional-research font: Google Sans
```

or:

```text
WARN  Google Sans unavailable; using Inter
```

Under `font_policy: strict`:

```text
FAIL  institutional-research requires Google Sans
```

---

# 5. Typography specification

This is one of the main design requirements.

## Main narrative

Main text should be intentionally more readable than the prototype in
Appendix A.

Target:

```text
Body size:        10.5–11 pt
Leading:          14–15 pt
Paragraph space:  5–6 pt
Paragraph indent: none
```

Initial implementation:

```text
10.7 pt / 14.6 pt
```

Main narrative should never inherit sidebar sizing.

## Sidebar / metadata

Target:

```text
7.2–8 pt
9–10 pt leading
```

Use for:

- analysts;
- contact details;
- market statistics;
- consensus/model estimates;
- rating metadata;
- source notes;
- disclosure furniture.

The visual hierarchy should clearly make the main research argument dominant.

## Recommended scale

```text
Masthead              8 pt / 10
Sector kicker         9 pt / 11
Main headline        23 pt / 26
Deck                 11.5 pt / 15
Rating value         12 pt / 14
Section heading      15 pt / 18
Subsection           12 pt / 15
Body                 10.7 pt / 14.6
Exhibit headline      9.5 pt / 12
Sidebar               7.6 pt / 9.5
Table body            8.0 pt / 10
Source / footnote     7.0 pt / 8.5
Disclosure            6.5–7 pt
```

Use weight and size before color or boxes to establish hierarchy.

---

# 6. Page geometry

Theme default:

```text
Paper: US Letter
```

Allow explicit A4 override later, but the canonical equity-research example
should use Letter.

Approximate geometry:

```text
Left/right margin:   13–15 mm
Top:                 13–16 mm
Bottom:              14–17 mm
```

This theme should be noticeably more spatially efficient than the current
ReportKit A4 layout, which presently uses 27 mm side margins
(`latex_templates/reportkit.cls:9`).

However, increased usable width must **not** be used simply to create longer
prose lines. Page composition should control readable line length.

These values supersede the prototype's tighter margins — see
[Open questions](#open-questions-and-discrepancies) #5.

---

# 7. Core layout primitives

Implement semantic layout primitives rather than hand-written `minipage`
coordinates.

## Research front page

Example API:

```latex
\begin{researchfrontpage}
  ...
\end{researchfrontpage}
```

Internally composed from:

```latex
\researchkicker{Enterprise Software / United States}

\researchheadline{
  Platform Mix Is Rising as AI Orchestration Becomes the
  Primary Driver of Incremental Growth
}

\researchdeck{
  We raise FY27 estimates...
}

\begin{ratingstrip}
  \ratingitem{Rating}{Overweight}
  \ratingitem{Price Target}{\$245}
  \ratingitem{Current Price}{\$182.50}
\end{ratingstrip}
```

Then:

```latex
\begin{researchmain}
...
\end{researchmain}

\begin{researchsidebar}
...
\end{researchsidebar}
```

Canonical width:

```text
Main:     ~68%
Gutter:    ~4%
Sidebar:  ~28%
```

Do not draw an outer border around either column.

---

# 8. Sidebar primitives

Provide:

```latex
\begin{analystblock}
...
\end{analystblock}

\begin{marketdatablock}
...
\end{marketdatablock}

\begin{estimatesblock}
...
\end{estimatesblock}
```

Styling:

- small font;
- thin horizontal separators;
- compact row spacing;
- no rounded boxes;
- no colored background by default;
- labels may use muted gray;
- values use Ink;
- accent only for important state.

Sidebar should visually recede.

---

# 9. Rating strip

Replace the old large BUY card. The existing equity mockup used a
dashboard-style framed rating box. The new implementation should use a simple
horizontal informational strip.

Example:

```text
STOCK RATING       INDUSTRY VIEW       PRICE TARGET
Overweight         Attractive          $245
```

Characteristics:

- no rounded rectangle;
- thin rules;
- strong baseline alignment;
- maximum one accent color;
- recommendation text may use accent;
- price target should not be rendered as a giant KPI.

## Supported item count

A rating strip must render correctly with 3 or 4 items without any item
wrapping to a second line. Item width must therefore be computed from
the actual item count, not fixed at a constant sized for one specific
count.

---

# 10. "What Changed?" primitive

Implement:

```latex
\begin{whatschanged}
  \change{Price Target}{\$253}{\$236}
  \change{FY27 EPS}{\$4.90}{\$4.62}
\end{whatschanged}
```

Visual style:

- small accent label;
- simple From / To columns;
- minimal rules;
- no card container.

This becomes a reusable research primitive rather than equity-specific hand
formatting.

---

# 11. Exhibit system

This should be the most important new primitive.

API:

```latex
\begin{exhibit}[
  number=2,
  title={Platform mix is rising as a share of total revenue},
  source={Company data; Meridian Research estimates.},
  label={fig:platform-mix}
]
  \includegraphics[width=\linewidth]{figures/platform-mix.pdf}
\end{exhibit}
```

Rendered hierarchy:

```text
Exhibit 2: Platform mix is rising as a share of total revenue

[visual]

Source: Company data; Meridian Research estimates.
```

### Exhibit title rule

Titles should preferably state a **finding**, not simply identify a metric.

Preferred:

> Platform mix is rising as a share of total revenue

Avoid:

> Revenue Mix

The skill should instruct the agent accordingly. This extends the current
ReportKit principle that visuals answer reader questions rather than decorate
pages.

---

# 12. Exhibit page compositions

Add composition primitives:

```latex
\begin{fullwidthexhibit}
...
\end{fullwidthexhibit}
```

```latex
\begin{exhibitpair}
  ...
\end{exhibitpair}
```

```latex
\begin{exhibitgrid}
...
\end{exhibitgrid}
```

Supported layouts initially:

```text
1 × full width
2 × half width
1 dominant + 2 supporting
2 exhibits + full-width table
```

Avoid generic dashboard grids. The layout engine should permit deliberate
whitespace instead of stretching all objects to fill the page.

---

# 13. Chart theme

This needs a first-class implementation rather than local chart tweaking.

`reportkit_viz.py` already provides a matched Matplotlib layer and explicitly
states that it owns quantitative visuals. Keep that architecture.

Add:

```python
rkv.apply_theme("institutional-research")
```

or allow theme resolution from publication context.

## Institutional chart tokens

```text
Background:      white
Primary:         restrained teal
Secondary:       blue / dark gray
Grid:            very light gray
Axis text:       muted charcoal
Chart text:      Google Sans
Borders:         minimal
Top/right spine: hidden
Legend frame:    none
```

Colors should be scarce. A rough accent target:

```text
<5% of visible page area
```

The `check-theme` palette-sync command must become theme-aware as part of this
step — see [Open questions](#open-questions-and-discrepancies) #2.

---

# 14. Fix font consistency in charts explicitly

This should have an automated regression test, because the issue has already
been found manually.

The current chart layer selects its own sans/serif/mono families
(`python_scripts/reportkit_viz.py:147-151`) and uses
`mathtext.fontset = "stix"` (`python_scripts/reportkit_viz.py:184`). Under the
institutional theme, eliminate sources of accidental serif rendering.

The theme must explicitly set:

```python
font.family
axes.label
axes.title
xtick
ytick
legend
annotations
figure text
```

to Google Sans.

Also configure mathtext to avoid STIX serif leakage. For example:

```python
"mathtext.fontset": "custom",
"mathtext.rm": google_sans,
"mathtext.it": google_sans,
"mathtext.bf": google_sans,
```

or another tested sans-compatible configuration.

Do not use `text.usetex=True` for the chart theme.

### Mandatory regression

Render a figure containing:

- numeric y ticks;
- categorical x ticks;
- numeric x ticks;
- percentages;
- negative values;
- legend;
- annotation;
- axis title.

QA must verify that all chart text resolves to the intended typeface.

This is specifically intended to prevent the inconsistency already observed,
where numeric vertical-axis ticks appeared serif while categorical horizontal
labels were sans.

---

# 15. Figure sizing

The existing visualization library calculates figure width from the current A4
156 mm text block (`python_scripts/reportkit_viz.py:98-99`).

Remove this hard-coded coupling. Instead expose theme geometry:

```python
theme.text_width_in
theme.figure_sizes
```

For example:

```python
FIGURE_SIZES = {
    "full": ...,
    "half": ...,
    "dominant": ...,
    "compact": ...,
}
```

The values should be calculated from:

```text
paper
margins
column layout
gutter
```

rather than embedded constants.

Two constraints the source draft did not address: the existing public key
`wide` must be retained or aliased, and heights need a stated policy since
deriving width alone leaves them undefined — see
[Open questions](#open-questions-and-discrepancies) #3 and #4.

---

# 16. Table grammar

Equity research depends heavily on tables. Introduce institutional variants
for:

```text
financial summary
estimate revisions
valuation
sensitivity
scenario analysis
financial model
```

Visual rules:

- no vertical borders;
- minimal horizontal rules;
- header weights instead of colored panels;
- optional very light row highlight;
- right-align numeric columns;
- decimal alignment where practical;
- consistent Actual/Estimate distinction;
- units clearly stated once;
- muted source line;
- avoid excessive bolding.

Use `booktabs` and `siunitx` (both already required by the class).

### Estimates

Preferred column language:

```text
2025A   2026E   2027E   2028E
```

Actual and estimate status should remain readable even in grayscale.

---

# 17. Dense model mode

Do not force the main body type scale onto financial-model pages.

Implement:

```latex
\begin{financialmodelpage}
...
\end{financialmodelpage}
```

This may temporarily switch to:

```text
7–8 pt table text
tight row spacing
landscape if required
```

while preserving:

- same font;
- same palette;
- same exhibit/title grammar;
- same headers/footers.

The principle is:

> editorial prose pages optimize reading; model pages optimize scanning.

Do not make both equally dense.

---

# 18. Risk/reward primitive

Implement:

```latex
\riskrewardchart[
  current=182.50,
  bear=135,
  base=245,
  bull=310
]
```

or preferably generate through `reportkit_viz.py`.

The page composition should support:

```text
Investment Thesis       Risk / Reward chart
Key Debates             Bull assumptions
Catalysts               Base assumptions
Risks                   Bear assumptions
```

Again, avoid large colored cards.

---

# 19. Running furniture

Institutional theme:

### Header

Left:

```text
REPORTKIT | RESEARCH
```

or publication brand.

Right:

```text
Company / Sector
```

Very small muted type.

### Footer

- publication identity;
- date/version if needed;
- page number.

Use hairlines rather than boxed regions.

---

# 20. Color system

Base:

```text
Ink        #202124 or equivalent
Muted      #6B7075
Hairline   #D9DDE1
Surface    #F7F8F8
Accent     restrained teal
```

Use accent primarily for:

- kicker;
- recommendation;
- "What Changed?";
- one major chart series;
- selected structural markers.

Do not use accent on every section heading. Avoid extensive tinted boxes.

Note that these differ from the core palette in `reportkit.cls:44+`
(`Ink #24272D`, `Muted #687386`, `Hairline #D9DEE5`, `Surface #F7F8FA`). Both
palettes must coexist per theme, which is the reason
[Open questions](#open-questions-and-discrepancies) #2 exists.

---

# 21. Semantic compatibility with existing ReportKit

Existing semantic structures such as:

```text
principle
decisionpoint
researchproblem
assumption
redflag
evidencenote
limitationnote
tipnote
deliverablenote
metric
```

remain part of the ReportKit contract. `SKILL.md` currently tells agents to use
them semantically rather than decoratively.

The institutional theme should restyle them more quietly. For example, replace:

```text
colored tcolorbox
```

with:

```text
thin left rule
small uppercase semantic label
minimal background or none
```

except where strong warning semantics justify more emphasis.

---

# 22. AI authoring guidance

Update `SKILL.md` with a section for this theme. The agent should understand
that the theme is **exhibit-led**.

Add rules such as:

> For `institutional-research`, prefer an analytical exhibit over a decorative
> callout when quantitative evidence exists.

> Exhibit titles should communicate the conclusion the reader should draw.

> Do not place ordinary paragraphs inside boxes.

> Sidebars contain reference information, not the core thesis.

> Use the main column for the research argument.

> Do not force a visual onto every section. A page may contain deliberate
> whitespace.

> Avoid dashboard layouts composed of repeated equally weighted cards.

> Main narrative prose should be visually more prominent than metadata.

This fits naturally with ReportKit's existing reader-question visual grammar.

---

# 23. Required equity-research page archetypes

V1 should ship with these page patterns:

| Archetype | Purpose |
| --- | --- |
| Research front page | Headline, deck, rating, thesis, sidebar |
| Narrative analysis | Main argument + sidebar or exhibit |
| Exhibit page | 1–3 analytical figures |
| Estimate revisions | Changed estimates + commentary |
| Valuation page | Method + SOTP/DCF tables |
| Risk/reward | Bear/base/bull |
| Financial model | Dense tabular model |
| Risks | Material investment risks |
| Disclosures | Analyst certification and legal text |

Not every equity report has to use every page. The primitives exist
consistently even when omitted.

---

# 24. Example deliverable

Ship a fictional sample:

```text
latex_templates/examples/equity-research/
```

using the Nexa/Meridian content from the Appendix A prototype.

The sample should contain at least:

```text
Page 1  research front page
Page 2  analysis + 3 exhibits
Page 3  risk/reward + debates
Page 4  financial model
```

This becomes the visual regression fixture.

Do not use Morgan Stanley or Apple content as the canonical test fixture.

**Reconcile the fixture's arithmetic first.** The prototype's estimates
contradict each other across pages; see
[Open questions](#open-questions-and-discrepancies) #6 for the specific
conflicts.

---

# 25. Visual regression testing

This feature is design-heavy, so compilation tests are insufficient. Generate
PNG previews of canonical pages and compare them in CI or the QA workflow.

At minimum test:

- page geometry;
- headline wrapping;
- sidebar alignment;
- exhibit positioning;
- chart fonts;
- table overflow;
- source alignment;
- excessive blank pages;
- overfull boxes.

Add targeted font QA:

```text
FAIL if chart y-tick font != chart x-tick font
FAIL if requested Google Sans silently falls back
```

Where programmatic font detection is unreliable, the render should still be
included in visual QA.

---

# 26. Backward compatibility

Critical requirement:

```yaml
document:
  class: reportkit
```

with no theme specified must continue to render the existing ReportKit design.

Default:

```text
theme = default
publication_type = technical-report
paper = a4
```

Do **not** silently restyle existing publications. The institutional theme is
opt-in.

The existing `career_guide_en` example is the backward-compatibility witness:
its output must remain pixel-equivalent after step 1 of §27.

---

# 27. Implementation sequence

Five bounded implementation steps:

1. **Theme infrastructure** — extract current typography, geometry, palette and
   furniture from `reportkit.cls` into `reportkit-theme-default.sty`; add theme
   selection/config while preserving pixel-equivalent legacy output.
2. **Institutional theme** — implement Letter geometry, Google Sans resolution,
   type scale, spacing, rules, tables and quieter semantic callouts.
3. **Equity publication profile** — implement front page, rating strip,
   sidebar, what-changed, exhibit, valuation/model and risk/reward composition
   primitives.
4. **Visualization integration** — make `reportkit_viz.py` theme-aware, remove
   A4 hardcoding, add Google Sans registration and eliminate serif leakage from
   numeric axes/mathtext.
5. **Fixtures + QA + skill guidance** — rebuild the four-page fictional mockup
   using only public ReportKit APIs, add visual regression fixtures, and update
   `SKILL.md`.

Do **not** start by copying the prototype into another giant `.sty` file. The
valuable outcome of this sprint is that the mockup becomes the first proof that
ReportKit has a genuine theme/profile architecture.

---

# 28. Definition of done

The sprint is complete when this minimal source:

```latex
\documentclass[
  theme=institutional-research,
  publication-type=equity-research
]{reportkit}

\begin{document}

\researchheadline{Platform mix is rising as AI becomes the primary growth driver}

...

\begin{exhibit}[
  title={Platform mix is rising as a share of total revenue},
  source={Company data; ReportKit Research estimates.}
]
  \includegraphics{figures/platform-mix.pdf}
\end{exhibit}

\end{document}
```

reproduces the visual language of the Appendix A prototype **without
page-specific coordinates, local font patches, bespoke chart styling, or raw
`minipage` layouts**.

That is the architectural bar for vNext.

---

# 29. Post-implementation findings (first production report, 2026-09-09)

Steps 1-5 were verified by inspection, not by compilation (no implementing
session had `lualatex` available — see the Status line above). The first
real document built against this spec — an equity-research initiation
report for Accenture (ACN), compiled the same day — surfaced three defects
that inspection missed because each one only manifests once real content
(a 4-item rating strip, categorical mix data, a populated sidebar) runs
through the templates. All three are traced to specific files/lines below.
They are implementation bugs, not disagreements with the design in §1-§28,
but two of them expose gaps in the spec itself (§9 and §5) that let the bug
happen in the first place, so both the spec text and the implementation
need a fix.

## 29.1 Rating strip has no defined item count, and the shipped width overflows at 4

**Symptom:** On the front page, the fourth `\ratingitem` ("Implied Upside")
wraps to a second line instead of sitting on the same horizontal strip as
the other three, breaking the "strong baseline alignment" characteristic
§9 requires.

**Root cause:** §9's examples only ever show **three** items (`STOCK
RATING / INDUSTRY VIEW / PRICE TARGET`), and the spec never states how many
items a rating strip must support. The implementation
(`latex_templates/publication_types/reportkit-equity-research.sty:113`)
picked a fixed width sized for exactly three:

```latex
\begin{minipage}[t]{0.29\linewidth}%
```

The ACN report uses four (`Stock Rating`, `Price Target`, `Reference
Price`, `Implied Upside` — a natural set for an initiation report, which
needs to show the reference price and the resulting upside alongside the
rating and target). Four fixed-width items plus three inter-item rules
exceed 100% of the line:

```text
4 × 0.29\linewidth = 1.16\linewidth   (before separators)
```

**Suggested spec fix:** §9 should state a supported item-count range (3-4
is enough for every archetype in §23) rather than illustrating only the
one count that happens to fit the hardcoded width. Add to §9:

> A rating strip must render correctly with 3 or 4 items without any item
> wrapping to a second line. Item width must therefore be computed from
> the actual item count, not fixed at a constant sized for one specific
> count.

**Suggested implementation fix:** in `\ratingitem`
(`reportkit-equity-research.sty:110-117`), replace the hardcoded
`0.29\linewidth` with a width derived at `\end{ratingstrip}` time from a
counted first pass (mirroring the two-pass counting `reportkit-structure.sty`
already uses for `reportarchitecture`/`capabilitymap`), or — more simply,
since `ratingstrip` items are homogeneous single-line boxes — replace the
minipage-per-item layout with a `tabularx` row of `C` columns sized
`1/N\linewidth` each. Either way, add a 4-item case to the visual
regression fixture (§25) alongside the existing 3-item case so this
class of regression cannot ship silently again.

## 29.2 Sidebar has one type-scale step, so subheadings cannot outrank body text by size

**Symptom:** In the sidebar, `\rksubheading{Near-term read-through}` reads
at the same size as the "Supportive:" / "Concerning:" body text beneath
it. The only things distinguishing it are weight and color, not size —
which directly contradicts §5's closing instruction: *"Use weight and size
before color or boxes to establish hierarchy."*

**Root cause:** §5's recommended scale (the table under "Recommended
scale") has exactly **one** sidebar-family entry — `Sidebar 7.6 pt / 9.5`
— covering labels, values, and prose uniformly. It has no separate,
smaller step for a sidebar-internal subheading the way the main column has
one (`Section heading 15pt` vs. `Subsection 12pt` vs. `Body 10.7pt` are
three distinct steps; the sidebar has zero). The implementation inherited
this gap faithfully:

- `\rksidebarsize` is defined once, at `7.6pt/9.5pt`
  (`latex_templates/themes/reportkit-theme-institutional-research.sty:223`).
- `\rksubheading` (`reportkit-equity-research.sty:349`) sets `\bfseries`
  and `\color{Accent}` but reuses that same `\rksidebarsize` — there is no
  smaller size for it to use even if the author wanted one.

Every sidebar subheading in the ACN report (`Business mix`,
`Near-term read-through`, `Catalysts`, `Key falsifier`, `Risks`, `View
change`) inherits the same flat hierarchy, not just the one flagged in the
example.

**Suggested spec fix:** add a fourth sidebar-family row to §5's scale
table, below `Sidebar`:

```text
Sidebar subheading    6.6-6.8 pt / 8-8.2
```

and add a sentence to §8 (Sidebar primitives) noting that sidebar
subheadings are a distinct, smaller type step from sidebar body text —
the same size-establishes-hierarchy principle §5 already states for the
main column, applied to the sidebar's own internal hierarchy.

**Suggested implementation fix:** add
`\rksidebarsubheadingsize` (`\fontsize{6.7pt}{8.1pt}\selectfont`) next to
`\rksidebarsize` in the theme file, and change
`reportkit-equity-research.sty:349`'s `\rksubheading` to use it instead of
`\rksidebarsize`. One macro, one call site — every sidebar subheading in
every existing and future document picks up the fix automatically.

## 29.3 No sanctioned way to render small proportional/categorical data in a sidebar

**Symptom:** The ACN report's "Business mix" sidebar block renders five
`\sidebarrow` label/value pairs — two dollar figures (Consulting vs.
Managed Services revenue) and three percentages that sum to 100%
(Americas/EMEA/Asia-Pacific revenue split). Both groups are proportional
compositions of a whole, which is exactly the data shape a small pie or
donut chart communicates at a glance and five stacked text rows do not —
the reader has to do the arithmetic in their head to see that Consulting
and Managed Services are roughly balanced, or that Americas is barely
half of revenue.

**Root cause:** this is not a one-off authoring miss; the toolchain gives
an author no better option today:

- §22's authoring guidance tells the agent to "prefer an analytical
  exhibit over a decorative callout when quantitative evidence exists,"
  but every example of an exhibit in §11/§12 assumes the ~68%-wide main
  column. Nothing in §22 or §8 tells the author what to do when the
  quantitative evidence belongs in the ~28%-wide sidebar instead — so the
  fallback is `\sidebarrow` text, every time.
- Even an author who wanted to embed a chart in the sidebar has no sized
  figure preset to put it in: `figure_sizes`
  (`python_scripts/reportkit/themes/institutional_research.py:95-102`)
  defines `full` / `wide` / `dominant` / `compact` / `square` / `half`,
  and the narrowest of those (`half`, 3.588in) is sized for a two-up
  `exhibitpair` pane at 0.485\linewidth of the ~7.2in main-column text
  width — nearly double the sidebar's own ~0.28\linewidth (≈2.0in on
  Letter). Every existing preset overflows the sidebar.
- `reportkit_viz.py` has no pie or donut chart function at all (its chart
  functions are `timeseries`, `bar_chart`, `distribution`, `scatter_plot`,
  `heatmap`, `drawdown_chart`, `risk_reward_chart`, `waterfall_chart`,
  `treemap_chart`, `tornado_chart`, `bubble_matrix`, `timeline_chart`).
  Even with a correctly sized figure preset, there is no themed primitive
  to render a 2-3-slice composition, which is exactly what would push an
  author toward hand-rolled matplotlib — the "bespoke chart styling" §28's
  Definition of Done rules out.

**Suggested spec fix:** add to §22 (AI authoring guidance):

> A sidebar composition of 2-4 values (a segment split, a geographic mix,
> a channel mix) is a chart, not a `\sidebarrow` list — render it as a
> small themed donut or pie chart sized for the sidebar column, with the
> underlying values still available in the source as a caption or
> `\source{}` line. Reserve `\sidebarrow` for point metrics and estimates
> that are not proportions of a common whole.

and add a `sidebar` entry to §15's figure-sizing discussion sized for the
~0.28\linewidth sidebar column (≈2.0in on Letter, vs. `half`'s 3.588in),
plus a new pie/donut chart function to §13's chart-theme scope, using the
same restrained-teal/blue/gold/muted palette §13 already specifies for
every other chart type.

**Suggested implementation fix:**
1. Add `"sidebar": (2.05, 2.05)` (or similar, ratio-derived per the
   existing convention) to `figure_sizes` in both theme modules.
2. Add a `donut_chart()` (or `pie_chart()`) function to `reportkit_viz.py`
   following the existing function signature convention (`size=`, themed
   colors via `series_style()`, `save_figure()`).
3. Add a 4th QA fixture page (or extend an existing sidebar) to §24/§25's
   example deliverable exercising this primitive, so "sidebar chart
   overflows its column" joins the checklist in §25 the same way "table
   overflow" already does.

---

# Appendix A — Visual reference prototype

`meridian_equity_research_mockup_v3.tex`, embedded verbatim. This is the
approved visual reference, preserved here because the standalone prototype file
was removed once this spec absorbed it.

**Read it as a target appearance, not a target implementation.** It is
hand-coded with raw `minipage` coordinates, a local `fontspec` patch and
inline `pgfplots` styling — precisely the three things §28 requires the finished
implementation to eliminate. Its geometry and type sizes are superseded by §6
and §5 respectively, and its financial figures need reconciling before reuse as
a fixture ([Open questions](#open-questions-and-discrepancies) #5 and #6).

```latex
\documentclass[9pt,letterpaper]{article}

% Google Sans is the sole publication typeface. The rendered PDF uses
% static Regular/Medium/Bold instances derived from the user-supplied variable font.
% For local compilation, either install Google Sans system-wide or place the three
% static faces in \GoogleSansPath.
\usepackage{fontspec}
\newcommand{\GoogleSansPath}{./fonts/}
\IfFontExistsTF{Google Sans}{%
  \setmainfont{Google Sans}[Ligatures=TeX]
  \setsansfont{Google Sans}[Ligatures=TeX]
  \IfFontExistsTF{Google Sans Medium}{%
    \newfontfamily\gsmedium{Google Sans Medium}[Ligatures=TeX]
  }{\newfontfamily\gsmedium{Google Sans}[Ligatures=TeX]}
}{%
  \setmainfont[Path=\GoogleSansPath,UprightFont=GoogleSans-Regular.ttf,BoldFont=GoogleSans-Bold.ttf]{GoogleSans-Regular.ttf}
  \setsansfont[Path=\GoogleSansPath,UprightFont=GoogleSans-Regular.ttf,BoldFont=GoogleSans-Bold.ttf]{GoogleSans-Regular.ttf}
  \newfontfamily\gsmedium[Path=\GoogleSansPath]{GoogleSans-Medium.ttf}
}
\newcommand{\gsregular}{\normalfont}
\usepackage{microtype}
\usepackage[letterpaper,top=0.42in,bottom=0.42in,left=0.48in,right=0.48in,headheight=14pt,headsep=8pt,footskip=14pt]{geometry}
\usepackage[table]{xcolor}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{multirow}
\usepackage{enumitem}
\usepackage{ragged2e}
\usepackage{fancyhdr}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\pgfplotsset{
  every axis/.append style={
    tick label style={font=\gsregular\scriptsize,text=Muted},
    label style={font=\gsregular\scriptsize,text=Muted},
    title style={font=\gsmedium\scriptsize}
  },
  every axis legend/.append style={font=\gsregular\fontsize{5.8}{6.8}\selectfont}
}
\usepackage[hidelinks]{hyperref}

% -----------------------------------------------------------------------------
% Typography
% Google Sans is used consistently for narrative, metadata, tables, and charts.
% Hierarchy comes from size, leading, weight, and column placement rather than
% switching type families. Main narrative is deliberately larger and airier;
% sidebars remain compact so they read as reference detail.
% -----------------------------------------------------------------------------

% -----------------------------------------------------------------------------
% Palette: restrained institutional research aesthetic
% -----------------------------------------------------------------------------
\definecolor{Ink}{HTML}{202124}
\definecolor{Muted}{HTML}{6B6F72}
\definecolor{Rule}{HTML}{B9BEC1}
\definecolor{LightRule}{HTML}{DADDE0}
\definecolor{Accent}{HTML}{18A999}
\definecolor{AccentPale}{HTML}{E8F7F4}
\definecolor{Blue}{HTML}{2477A7}
\definecolor{Gold}{HTML}{D6A84B}
\definecolor{SoftGray}{HTML}{F3F4F4}
\definecolor{ModelBlue}{HTML}{173A8A}
\definecolor{ModelPale}{HTML}{EAF0FF}
\definecolor{BearRed}{HTML}{A94343}

\color{Ink}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4.6pt}
\setlist[itemize]{leftmargin=10pt,itemsep=1pt,topsep=1.5pt,parsep=0pt}
\setlist[enumerate]{leftmargin=13pt,itemsep=1pt,topsep=1.5pt,parsep=0pt}
\renewcommand{\arraystretch}{1.05}

% -----------------------------------------------------------------------------
% Header/footer
% -----------------------------------------------------------------------------
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyhead[L]{\gsmedium\footnotesize Meridian Research\hspace{5pt}{\color{Rule}|}\hspace{5pt}\fontsize{7.2}{8.2}\selectfont RESEARCH}
\fancyhead[R]{\sffamily\footnotesize\textcolor{Accent}{\textbf{UPDATE}}}
\fancyfoot[R]{\sffamily\scriptsize\textcolor{Muted}{\thepage}}

% -----------------------------------------------------------------------------
% Helpers
% -----------------------------------------------------------------------------
\newcommand{\datekicker}{{\sffamily\scriptsize\textcolor{Muted}{September 8, 2026 \; 08:30 PM SGT}\par}}
\newcommand{\kicker}[1]{{\gsmedium\textcolor{Accent}{\small #1}}}
\newcommand{\headline}[1]{{\gsmedium\fontsize{22}{25.2}\selectfont #1}}
\newcommand{\deck}[1]{{\fontsize{11.5}{15.5}\selectfont\RaggedRight #1}}
\newcommand{\sectiontitle}[1]{\vspace{2pt}{\gsmedium\fontsize{13.5}{16.2}\selectfont #1}\par\vspace{7pt}}
\newcommand{\subhead}[1]{{\gsmedium\fontsize{10.5}{12.8}\selectfont #1}}
\newcommand{\exhibit}[2]{%
  \vspace{2pt}\noindent{\gsmedium\fontsize{8.7}{10.6}\selectfont Exhibit #1: #2}\par\vspace{3pt}}
\newcommand{\source}[1]{\vspace{1pt}{\gsregular\fontsize{6.1}{7.4}\selectfont\textcolor{Muted}{Source: #1}}}
\newcommand{\tinycaps}[1]{{\sffamily\fontsize{6.5}{7}\selectfont\bfseries\MakeUppercase{#1}}}
\newcommand{\metric}[2]{\begin{minipage}[t]{0.31\linewidth}\tinycaps{#1}\\[-1pt]{\sffamily\fontsize{10}{11.5}\selectfont #2}\end{minipage}}
\newcommand{\sidebarlabel}[1]{{\sffamily\fontsize{6.1}{7}\selectfont\textcolor{Muted}{\MakeUppercase{#1}}}}
\newcommand{\sidebarvalue}[1]{{\sffamily\fontsize{7.4}{8.8}\selectfont\textbf{#1}}}
\newcommand{\changedlabel}{%
  \colorbox{Accent}{\parbox[c][0.34in][c]{0.70in}{\centering\color{white}\sffamily\fontsize{7}{8}\selectfont\bfseries WHAT'S\\CHANGED?}}}
\newcommand{\ruleline}{\par\vspace{2pt}{\color{Rule}\hrule height 0.45pt}\vspace{4pt}}
\newcommand{\tealrule}{\par\vspace{2pt}{\color{Accent}\hrule height 1.2pt}\vspace{4pt}}

\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}
\newcolumntype{Z}{>{\RaggedLeft\arraybackslash}X}
\newcolumntype{C}{>{\centering\arraybackslash}X}

\begin{document}

% =============================================================================
% PAGE 1 - FRONT PAGE
% =============================================================================
\datekicker
\vspace{7pt}

\begin{minipage}[t]{0.665\textwidth}
\vspace{0pt}
\kicker{Nexa Cloud Solutions, Inc. \;|\; North America}
\vspace{7pt}

\headline{AI Infrastructure Demand Is Holding Up Better Than Feared; Services Mix Provides an Offset}
\vspace{8pt}

\begin{tabularx}{\linewidth}{@{}Y|Y|Y@{}}
\metric{Stock Rating}{Overweight} &
\metric{Industry View}{Attractive} &
\metric{Price Target}{\$245.00} \\
\end{tabularx}

\vspace{10pt}
\deck{We trim FY27 infrastructure growth assumptions after channel checks point to slower enterprise deployments, but raise our services estimates as AI orchestration usage remains resilient. Lower hardware contribution is more than offset by recurring platform revenue, keeping our price target at \$245.}

\vspace{8pt}
\begin{minipage}[t]{0.18\linewidth}
\changedlabel
\end{minipage}\hfill
\begin{minipage}[t]{0.79\linewidth}
\vspace{0pt}
{\sffamily\fontsize{6.8}{8}\selectfont
\begin{tabularx}{\linewidth}{@{}Yrr@{}}
\toprule
\textbf{Nexa Cloud (NXCL)} & \textbf{From:} & \textbf{To:}\\
\midrule
FY27 Revenue (\$M) & 2,610 & 2,540\\
FY27 EPS (\$) & 3.05 & 2.95\\
Price Target & \$245 & \$245\\
\bottomrule
\end{tabularx}}
\end{minipage}

\vspace{9pt}
{\fontsize{9.85}{13.55}\selectfont\RaggedRight\setlength{\parskip}{6.3pt}
\textbf{Enterprise AI demand is slowing, not breaking.} Our channel work indicates large customers are extending deployment timelines by one to two quarters, but the underlying pipeline remains intact. Importantly, usage-based orchestration revenue continues to grow faster than subscription seats, suggesting customers are consolidating workloads rather than abandoning AI projects.

\textbf{Services and platform mix now matter more than unit growth.} We forecast AI Orchestration and Token Routing to rise to 28\% of revenue by FY28 from 21\% in FY25. That mix shift supports gross margin expansion even with a more conservative infrastructure outlook, and reduces the sensitivity of earnings to quarterly deployment volatility.

\textbf{We see limited downside to estimates from current checks.} Our FY27 revenue estimate falls 3\%, but EBITDA declines only 1\% as lower-margin hardware-linked activity accounts for most of the revision. We maintain our \$245 target, derived from a sum-of-the-parts framework that applies a premium multiple to recurring services revenue.

\textbf{The key debate is duration, not direction.} Investors appear to be discounting a full normalization in enterprise AI spending. Our work suggests the more likely path is a slower but longer adoption cycle, with services, security and inference routing becoming the primary value drivers over the next 24 months.
}
\end{minipage}
\hfill
\begin{minipage}[t]{0.305\textwidth}
\vspace{0pt}
{\sffamily\fontsize{6.45}{7.9}\selectfont
\sidebarlabel{Meridian Research LLC}\\
\sidebarvalue{Alexander Vance, CFA}\\
\textcolor{Muted}{Equity Analyst}\\
alexander.vance@meridian.example\\
+65 6123 4567\\[5pt]
\sidebarvalue{Sarah Jenkins}\\
\textcolor{Muted}{Research Associate}\\
sarah.jenkins@meridian.example\\
+65 6123 4568
}

\vspace{7pt}
\tealrule
{\sffamily\fontsize{6.55}{7.9}\selectfont
\begin{tabularx}{\linewidth}{@{}Y Z@{}}
\rowcolor{AccentPale}\multicolumn{2}{@{}l@{}}{\textbf{Nexa Cloud Solutions (NXCL)}}\\
Stock Rating & \textbf{Overweight}\\
Industry View & Attractive\\
Price Target & \$245.00\\
Share Price & \$182.50\\
Market Cap (\$M) & 42,850\\
52-Week Range & 195.40--124.10\\
\end{tabularx}
}

\vspace{7pt}
{\sffamily\fontsize{6.25}{7.5}\selectfont
\begin{tabularx}{\linewidth}{@{}Yrrrr@{}}
\rowcolor{AccentPale}\multicolumn{5}{@{}l@{}}{\textbf{Fiscal Year Ending}}\\
 & 2024A & 2025E & 2026E & 2027E\\
\midrule
EPS (\$) & 0.78 & 1.35 & 2.10 & 2.95\\
P/E (x) & 234 & 135 & 87 & 62\\
Revenue (\$M) & 1,141 & 1,520 & 1,985 & 2,540\\
EBITDA (\$M) & 205 & 335 & 496 & 691\\
\end{tabularx}
}

\vspace{7pt}
{\sffamily\fontsize{6.25}{7.5}\selectfont
\begin{tabularx}{\linewidth}{@{}Yrrrr@{}}
\rowcolor{AccentPale}\multicolumn{5}{@{}l@{}}{\textbf{Quarterly EPS (\$)}}\\
 & 1Q26E & 2Q26E & 3Q26E & 4Q26E\\
\midrule
Prior & 0.40 & 0.46 & 0.56 & 0.70\\
Current & 0.41 & 0.45 & 0.55 & 0.69\\
\end{tabularx}
}

\vfill
{\sffamily\fontsize{5.65}{7.0}\selectfont\textcolor{Muted}{Meridian Research does and seeks to do business with companies covered in its research reports. Investors should consider this report as only a single factor in making an investment decision. For analyst certification and important disclosures, refer to the end of this mock report.}}
\end{minipage}

\newpage

% =============================================================================
% PAGE 2 - ANALYSIS / EXHIBITS
% =============================================================================
\datekicker
\sectiontitle{Analysis}

\exhibit{1}{Enterprise AI usage remains resilient even as deployment cycles lengthen}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
  width=0.62\textwidth,height=2.10in,
  xmin=0,xmax=24,ymin=40,ymax=105,
  xtick={0,6,12,18,24}, ytick={40,50,60,70,80,90,100},
  axis line style={draw=Rule}, tick style={draw=Rule},
  tick label style={font=\gsregular\scriptsize,text=Muted},
  ylabel={Index}, xlabel={Weeks Since Launch},
  label style={font=\gsregular\scriptsize,text=Muted},
  grid=major, grid style={draw=LightRule,line width=0.25pt},
  legend style={font=\gsregular\fontsize{5.8}{6.8}\selectfont,draw=none,at={(0.5,-0.25)},anchor=north,legend columns=4},
]
\addplot[Blue,thick,smooth] coordinates {(0,58)(3,81)(6,71)(9,65)(12,66)(15,78)(18,62)(21,57)(24,55)};
\addplot[Accent,thick,smooth] coordinates {(0,62)(3,96)(6,83)(9,71)(12,70)(15,87)(18,64)(21,59)(24,56)};
\addplot[Gold,thick,dashed,smooth] coordinates {(0,55)(3,73)(6,66)(9,63)(12,62)(15,72)(18,60)(21,56)(24,54)};
\addplot[Muted,thick,densely dotted,smooth] coordinates {(0,59)(3,87)(6,78)(9,68)(12,68)(15,82)(18,63)(21,58)(24,55)};
\legend{FY23 launch,FY24 launch,FY25 launch,FY26 launch}
\end{axis}
\end{tikzpicture}
\end{center}
\source{Company data, Meridian Research estimates}

\vspace{8pt}
\begin{minipage}[t]{0.485\textwidth}
\exhibit{2}{Platform mix is rising as a share of total revenue}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
  width=\linewidth,height=1.65in,
  ybar stacked, bar width=12pt,
  symbolic x coords={FY24A,FY25E,FY26E,FY27E}, xtick=data,
  ymin=0,ymax=100, ytick={0,20,40,60,80,100},
  axis line style={draw=Rule}, tick style={draw=Rule},
  tick label style={font=\gsregular\scriptsize,text=Muted},
  grid=major, grid style={draw=LightRule,line width=0.25pt},
  legend style={font=\gsregular\fontsize{5.6}{6.4}\selectfont,draw=none,at={(0.5,-0.22)},anchor=north,legend columns=3},
]
\addplot[fill=Blue,draw=none] coordinates {(FY24A,76)(FY25E,72)(FY26E,68)(FY27E,64)};
\addplot[fill=Accent,draw=none] coordinates {(FY24A,17)(FY25E,21)(FY26E,25)(FY27E,28)};
\addplot[fill=Gold,draw=none] coordinates {(FY24A,7)(FY25E,7)(FY26E,7)(FY27E,8)};
\legend{Subscription,AI Orchestration,Services}
\end{axis}
\end{tikzpicture}
\end{center}
\source{Company data, Meridian Research estimates}
\end{minipage}
\hfill
\begin{minipage}[t]{0.485\textwidth}
\exhibit{3}{Gross margin expands despite slower infrastructure growth}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
  width=\linewidth,height=1.65in,
  ymin=70,ymax=82, ytick={70,72,74,76,78,80,82},
  symbolic x coords={FY24A,FY25E,FY26E,FY27E,FY28E}, xtick=data,
  axis line style={draw=Rule}, tick style={draw=Rule},
  tick label style={font=\gsregular\scriptsize,text=Muted},
  grid=major, grid style={draw=LightRule,line width=0.25pt},
]
\addplot[Accent,very thick,mark=*] coordinates {(FY24A,75.8)(FY25E,78.0)(FY26E,79.0)(FY27E,80.0)(FY28E,80.5)};
\end{axis}
\end{tikzpicture}
\end{center}
\source{Company data, Meridian Research estimates}
\end{minipage}

\vspace{10pt}
\exhibit{4}{Estimate revisions are concentrated in lower-margin infrastructure activity}
{\sffamily\fontsize{6.7}{7.8}\selectfont
\begin{tabularx}{\textwidth}{@{}Yrrrrrrrrr@{}}
\toprule
 & \multicolumn{3}{c}{\textbf{FY26E}} & \multicolumn{3}{c}{\textbf{FY27E}} & \multicolumn{3}{c}{\textbf{FY28E}}\\
\cmidrule(lr){2-4}\cmidrule(lr){5-7}\cmidrule(lr){8-10}
\textbf{Metric} & New & Old & \% Chg & New & Old & \% Chg & New & Old & \% Chg\\
\midrule
Revenue (\$M) & 1,985 & 2,010 & -1.2\% & 2,540 & 2,610 & -2.7\% & 3,165 & 3,250 & -2.6\%\\
Subscription & 1,350 & 1,360 & -0.7\% & 1,626 & 1,650 & -1.5\% & 1,940 & 1,970 & -1.5\%\\
AI Orchestration & 496 & 490 & +1.2\% & 711 & 690 & +3.0\% & 950 & 920 & +3.3\%\\
Services & 139 & 160 & -13.1\% & 203 & 270 & -24.8\% & 275 & 360 & -23.6\%\\
EBITDA (\$M) & 496 & 492 & +0.8\% & 691 & 698 & -1.0\% & 918 & 930 & -1.3\%\\
EPS (\$) & 2.10 & 2.12 & -0.9\% & 2.95 & 3.05 & -3.3\% & 4.02 & 4.15 & -3.1\%\\
\bottomrule
\end{tabularx}}
\source{Meridian Research estimates}

\newpage

% =============================================================================
% PAGE 3 - RISK / REWARD
% =============================================================================
\datekicker
\sectiontitle{NXCL Risk Reward}

\begin{minipage}[t]{0.665\textwidth}
\vspace{0pt}
\subhead{Services Mix Is Underappreciated by Investors}
\vspace{4pt}
\begin{center}
\begin{tikzpicture}
\begin{axis}[
  width=\linewidth,height=2.05in,
  xmin=0,xmax=24,ymin=100,ymax=320,
  xtick={0,6,12,18,24}, xticklabels={Sep-24,Mar-25,Sep-25,Mar-26,Sep-26},
  ytick={100,150,200,250,300},
  axis line style={draw=Rule}, tick style={draw=Rule},
  tick label style={font=\gsregular\scriptsize,text=Muted},
  grid=major, grid style={draw=LightRule,line width=0.25pt},
]
\addplot[Blue,thick] coordinates {(0,128)(2,136)(4,150)(6,148)(8,162)(10,171)(12,181)(14,176)(16,189)(18,201)(20,195)(22,188)(24,182.5)};
\addplot[Accent,dashed,thick] coordinates {(0,245)(24,245)};
\addplot[BearRed,dashed,thick] coordinates {(0,135)(24,135)};
\addplot[Gold,dashed,thick] coordinates {(0,310)(24,310)};
\node[anchor=west,font=\gsregular\scriptsize,text=Accent] at (axis cs:18,247) {Base \$245};
\node[anchor=west,font=\gsregular\scriptsize,text=BearRed] at (axis cs:18,137) {Bear \$135};
\node[anchor=west,font=\gsregular\scriptsize,text=Gold] at (axis cs:18,312) {Bull \$310};
\end{axis}
\end{tikzpicture}
\end{center}
\source{Company filings, Meridian Research estimates}

\vspace{5pt}
{\fontsize{9.45}{12.9}\selectfont\RaggedRight
\textbf{Price Target \hfill \textcolor{Accent}{\$245}}\\[-1pt]
Derived from base-case scenario.\\[5pt]

\textbf{Bull \hfill \textcolor{Gold}{\$310}}\\[-1pt]
\textbf{18.0x CY28E EV/EBITDA on \$1.1B EBITDA.} Platform adoption accelerates, AI orchestration becomes the primary workload-control layer for large enterprises, and net retention stabilizes above 135\%. Gross margin exceeds 81\% as usage scales with limited incremental infrastructure cost.\\[6pt]

\textbf{Base \hfill \textcolor{Accent}{\$245}}\\[-1pt]
\textbf{14.5x CY28E EV/EBITDA on \$918M EBITDA.} Enterprise deployments remain slower than the 2024--25 pace, but recurring platform revenue and usage-based routing support high-teens growth with steady margin expansion. We use a sum-of-the-parts framework to reflect the higher quality of recurring revenue.\\[6pt]

\textbf{Bear \hfill \textcolor{BearRed}{\$135}}\\[-1pt]
\textbf{9.0x CY28E EV/EBITDA on \$720M EBITDA.} A broader IT budget slowdown delays production deployments, hyperscalers bundle competing routing software, and customers consolidate vendors. Revenue growth falls to the low teens and margin expansion stalls.}
\end{minipage}
\hfill
\begin{minipage}[t]{0.305\textwidth}
\vspace{0pt}
\kicker{Investment Thesis}
{\sffamily\fontsize{6.85}{8.35}\selectfont
\begin{itemize}
\item Nexa occupies a valuable control point between enterprise applications and multiple model providers.
\item Services mix should increase revenue visibility and reduce quarterly deployment cyclicality.
\item Improving gross margin and sales efficiency support durable free-cash-flow conversion.
\end{itemize}}

\vspace{8pt}
\kicker{Key Debates}
{\sffamily\fontsize{6.85}{8.35}\selectfont\RaggedRight
\textbf{Can AI infrastructure spending reaccelerate?} Yes, but we expect the recovery to be driven by production workloads rather than experimentation.\\[4pt]
\textbf{Can hyperscalers commoditize routing?} Partly. We think multi-cloud governance and data-security requirements preserve a role for independent control-plane software.\\[4pt]
\textbf{Is valuation already discounting the upside?} Not fully, in our view, given the market still values Nexa primarily on consolidated revenue rather than mix and cash-flow quality.}

\vspace{8pt}
\kicker{Potential Catalysts}
{\sffamily\fontsize{6.85}{8.35}\selectfont
\begin{itemize}
\item Faster enterprise migration from pilot to production.
\item Expanded co-sell agreements with major cloud providers.
\item AI routing attach rates above our base case.
\item Capital return once free cash flow exceeds \$700M.
\end{itemize}}

\vspace{8pt}
\kicker{Risks to Price Target}
{\sffamily\fontsize{6.85}{8.35}\selectfont
\begin{itemize}
\item Hyperscaler bundling and pricing pressure.
\item Customer concentration and delayed renewals.
\item Higher specialized engineering costs.
\item Regulatory constraints on enterprise AI deployment.
\end{itemize}}
\end{minipage}

\newpage

% =============================================================================
% PAGE 4 - FINANCIAL MODEL
% =============================================================================
\datekicker
\sectiontitle{NXCL Financial Model}
\exhibit{5}{Income statement and key operating metrics}

\sffamily\scriptsize
\setlength{\tabcolsep}{2.05pt}
\renewcommand{\arraystretch}{1.03}
\begin{tabular}{@{}lrrrrrrrrrrrr@{}}
\toprule
\rowcolor{ModelBlue}\color{white}\textbf{\$M except per share data} &
\color{white}\textbf{1Q25A}&\color{white}\textbf{2Q25A}&\color{white}\textbf{3Q25A}&\color{white}\textbf{4Q25A}&
\color{white}\textbf{1Q26A}&\color{white}\textbf{2Q26E}&\color{white}\textbf{3Q26E}&\color{white}\textbf{4Q26E}&
\color{white}\textbf{2025A}&\color{white}\textbf{2026E}&\color{white}\textbf{2027E}&\color{white}\textbf{2028E}\\
\midrule
\rowcolor{ModelPale}\textbf{Revenue} & 342&366&391&421&442&478&510&555&1,520&1,985&2,540&3,165\\
Subscription & 251&265&278&300&307&326&341&376&1,094&1,350&1,626&1,940\\
AI Orchestration & 69&78&85&87&103&116&131&146&319&496&711&950\\
Services & 22&23&28&34&32&36&38&33&107&139&203&275\\
Revenue Growth & 34\%&33\%&32\%&34\%&29\%&31\%&30\%&32\%&33\%&31\%&28\%&25\%\\
\midrule
Cost of Revenue & 78&82&86&89&94&101&107&115&335&417&508&617\\
\rowcolor{SoftGray}\textbf{Gross Profit} & 264&284&305&332&348&377&403&440&1,186&1,568&2,032&2,548\\
Gross Margin & 77.2\%&77.6\%&78.0\%&78.8\%&78.7\%&78.9\%&79.0\%&79.3\%&78.0\%&79.0\%&80.0\%&80.5\%\\
\midrule
R\&D & 96&99&102&113&111&116&121&128&410&476&559&665\\
Sales \& Marketing & 113&118&123&132&128&133&139&145&486&545&635&728\\
G\&A & 34&35&37&41&39&40&41&43&147&163&191&228\\
\rowcolor{SoftGray}\textbf{Operating Income} & 21&32&43&46&70&88&102&124&143&384&647&927\\
Operating Margin & 6.1\%&8.7\%&11.0\%&10.9\%&15.8\%&18.4\%&20.0\%&22.3\%&9.4\%&19.3\%&25.5\%&29.3\%\\
\midrule
D\&A & 20&22&23&24&24&25&26&27&89&102&112&121\\
Stock Compensation & 31&33&35&36&36&37&38&39&135&150&158&169\\
\rowcolor{ModelPale}\textbf{Adjusted EBITDA} & 72&87&101&106&130&150&166&190&366&636&917&1,217\\
EBITDA Margin & 21.1\%&23.8\%&25.8\%&25.2\%&29.4\%&31.4\%&32.5\%&34.2\%&24.1\%&32.0\%&36.1\%&38.5\%\\
\midrule
Interest \& Other & 5&5&6&6&7&7&8&8&22&30&36&42\\
Pretax Income & 26&37&49&52&77&95&110&132&165&414&683&969\\
Taxes & 5&7&10&10&15&19&22&26&32&82&136&194\\
\rowcolor{SoftGray}\textbf{Net Income} & 21&30&39&42&62&76&88&106&133&332&547&775\\
Diluted Shares (M) & 235&236&236&237&237&238&238&239&236&238&241&244\\
\rowcolor{ModelPale}\textbf{EPS (\$)} & 0.09&0.13&0.17&0.18&0.26&0.32&0.37&0.44&0.57&1.39&2.27&3.18\\
\bottomrule
\end{tabular}

\vspace{8pt}
\exhibit{6}{Valuation framework}
\begin{tabularx}{\textwidth}{@{}Yrrrrr@{}}
\toprule
\rowcolor{AccentPale}\textbf{Segment / Metric} & \textbf{2027E} & \textbf{Multiple} & \textbf{EV} & \textbf{Weight} & \textbf{Value / Share}\\
\midrule
Core Subscription Revenue & 1,626 & 10.0x EV/Sales & 16,260 & 55\% & \$135\\
AI Orchestration Revenue & 711 & 15.0x EV/Sales & 10,665 & 35\% & \$89\\
Services EBITDA & 62 & 18.0x EV/EBITDA & 1,116 & 10\% & \$9\\
\midrule
\textbf{Enterprise Value} & & & \textbf{28,041} & & \\
(+) Net Cash & & & 1,860 & & \\
\textbf{Equity Value} & & & \textbf{29,901} & & \\
Diluted Shares (M) & & & 122 & & \\
\rowcolor{AccentPale}\textbf{Price Target} & & & & & \textbf{\$245}\\
\bottomrule
\end{tabularx}
\source{Company data, Meridian Research estimates. Figures are fictional and for design demonstration only.}

\vfill
{\sffamily\fontsize{5.8}{7}\selectfont\textcolor{Muted}{\textbf{ANALYST CERTIFICATION AND IMPORTANT DISCLOSURES:} The analyst(s) responsible for the preparation of this mock report certify that the views expressed accurately reflect their personal views about the subject company. This document is a fictional design prototype created to demonstrate an institutional equity-research publication system and is not investment advice.}}

\end{document}
```
