# Institutional-research theme + equity-research publication type

Full spec:
[docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](../docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md).
Working example:
[latex_templates/examples/equity-research/](../latex_templates/examples/equity-research/)
(a fictional four-page publication -- front page, analysis exhibits,
risk/reward, financial model -- built from nothing but the primitives
below; read its `report.tex` before writing a new one).

This is a **theme** (`institutional-research`: typography, geometry,
palette, chart styling) composed with a **publication type**
(`equity-research`: front page, rating strip, exhibits, financial-model
and risk/reward pages). They vary independently -- `theme=
institutional-research` alone gives quieter, denser Letter-format prose
with no stock-rating primitives; a future `publication-type=
strategy-report` could reuse this theme without exposing them either.
`publication-type=equity-research` requires a theme that defines the
type-scale tokens below (today, only `institutional-research`) and fails
at load time, not at first use, if that requirement is not met.

## Selecting it

```latex
\documentclass[
  theme=institutional-research,
  publication-type=equity-research
]{reportkit}
```

**Requires `lualatex`**, not `pdflatex` -- the theme loads Google Sans via
`fontspec`. `reportkit check`/`reportkit build` refuse to proceed if
`document.engine` isn't `lualatex` while `document.theme` is
`institutional-research` (config.py's `theme_engine_conflict()`); the
theme file repeats the same guard at the TeX level for anyone invoking
`lualatex`/`pdflatex` directly. In `publication.yaml`:

```yaml
document:
  engine: lualatex
  theme: institutional-research
  publication_type: equity-research
  paper: letter
theme:
  font_policy: fallback   # or: strict
```

`font_policy: fallback` (the default) walks Google Sans -> Inter -> Noto
Sans -> TeX Gyre Heros and warns which one it used; `strict` fails the
build if Google Sans specifically cannot be resolved. Neither
`document.theme` nor `theme.*` are wired into the markdown-driven
publication pipeline yet -- every example that uses this theme sets
`\documentclass[...]` options directly in `report.tex`, the same way it
already sets `\setreportkitleftheader` etc.

## Exhibit-led authoring

The theme is exhibit-led, not card-led. When writing for it:

- Prefer an analytical exhibit over a decorative callout when quantitative
  evidence exists.
- Exhibit titles should state the **finding** the reader should draw
  ("Platform mix is rising as a share of total revenue"), not just name a
  metric ("Revenue Mix").
- Do not place ordinary paragraphs inside boxes.
- Sidebars (`analystblock`/`marketdatablock`/`estimatesblock`) hold
  reference information, not the core thesis -- use the main column
  (`researchmain`) for the research argument.
- Do not force a visual onto every section; deliberate whitespace is
  fine.
- Avoid dashboard layouts of repeated, equally weighted cards.
- Main narrative prose is visually more prominent than metadata: body
  text is 10.7pt/14.6pt; sidebar/metadata text is 7.6pt/9.5pt
  (`\rkbodysize` vs `\rksidebarsize`) -- never make sidebar text carry the
  argument.
- Semantic callouts (`principle`, `decisionpoint`, `redflag`, ...) still
  work under this theme; they restyle to a thin left rule and a small
  uppercase label instead of a colored box, per the theme's quieter
  chrome -- use them for their existing semantic meaning, not decoration.

## Primitive reference

Source: `latex_templates/publication_types/reportkit-equity-research.sty`
(the definitive argument reference; read it before using a primitive not
covered here).

| Primitive | Purpose |
| --- | --- |
| `researchfrontpage` | Front-page wrapper (page style, top spacing) |
| `\researchkicker{sector / region}` | Small accent-colored sector/geography line |
| `\researchheadline{...}` | The main finding, in one sentence |
| `\researchdeck{...}` | One-paragraph summary below the headline |
| `ratingstrip` / `\ratingitem{label}{value}` | Horizontal rating/PT/current-price strip -- no boxed KPI; wrap a value in `\color{Accent}` for the one allowed accent use |
| `whatschanged` / `\change{label}{from}{to}` | Compact estimate-revision summary |
| `researchmain` / `researchsidebar` | ~68%/28% two-column body. **`\end{researchmain}` and `\begin{researchsidebar}` must have no blank line between them in the source** -- a blank line starts a new paragraph and breaks the sidebar out from beside the main column to below it |
| `analystblock` / `marketdatablock` / `estimatesblock` | Sidebar contexts (small font, hairline separators); use `\sidebarrow{label}{value}` for simple rows, a `tabularx` for multi-column data |
| `exhibit[title=,source=,label=,number=]` | The core primitive -- auto-numbered (`number=` overrides the *displayed* number only); warns if `title=` is missing |
| `fullwidthexhibit` | Marks one exhibit as deliberately full-width inside a page otherwise composed of `exhibitpair`/`exhibitgrid` |
| `exhibitpair` | Exactly two `\exhibitpane{...}` |
| `exhibitgrid[columns=N]` / `\exhibitpane[width=]{...}` | N equal columns; pane widths are computed only for `columns=1/2/3` -- **`columns=4` or higher (or an uneven split) needs an explicit `width=<fraction>\linewidth` on every `\exhibitpane`**, there is no computed default |
| `financialtable` | Typographic context for a table (institutional font/spacing) -- open a `tabularx`/`tabular` with `booktabs` rules and the `Y`/`Z`/`C` column types inside it |
| `financialmodelpage` | Locally drops to 7.6pt/9pt dense table type for a model page; reverts at `\end{}` |
| `\rksubheading{...}` | Generic accent-kicker heading (Investment Thesis / Key Debates / Catalysts / Risks, or any other) |
| `\bullcase{value}{text}` / `\basecase{value}{text}` / `\bearcase{value}{text}` | The fixed Bull/Base/Bear triad, colored `SeriesGold`/`Accent`/`BearRed` |

No `\riskrewardchart` LaTeX macro exists on purpose -- generate that chart
in Python (below) and embed it like any other figure:
`\begin{exhibit}[...]\includegraphics{...}\end{exhibit}`.

Twelve `\rk...size` type-scale commands (`\rkmastheadsize` ...
`\rkdisclosuresize`, spec section 5) are available directly if a
composition needs a size the primitives above don't already apply --
prefer an existing primitive first.

## Charts (`reportkit_viz.py`)

```python
import reportkit_viz as rkv

rkv.apply_theme("institutional-research")   # switches colors, fonts, TEXT_WIDTH_IN,
                                             # FIGURE_SIZES, and mathtext for every
                                             # chart drawn after this call
fig, ax = rkv.risk_reward_chart(
    price_history, bear=135, base=245, bull=310, current=182.50,
    value_formatter=rkv.currency_formatter(),
)
rkv.save_figure(fig, "figures/risk_reward")
```

`apply_theme()` reassigns this module's color/geometry globals (`INK`,
`FIGURE_SIZES`, ...), so every existing chart function
(`bar_chart`, `timeseries`, `waterfall_chart`, ...) becomes theme-aware
automatically -- there is no separate institutional-theme chart API.
`FIGURE_SIZES` gains `half` (sized for an `exhibitpair` pane) and
`dominant` (an alias of the pre-existing `wide`) under every theme.
`risk_reward_chart()` is the Python-side counterpart to the
Bull/Base/Bear primitives above; there is no dedicated stacked-bar
helper yet, so a platform-mix-style chart is ordinary Matplotlib code
built on `new_figure()`/`style_axes()`/`legend_above()`/`DATA_COLORS` --
see `latex_templates/examples/equity-research/figures.py` for a worked
example of exactly that.

`python3 reportkit_viz.py check-theme --theme institutional-research`
validates the Python and LaTeX palettes stay in sync.

## QA

```bash
python3 latex_templates/examples/equity-research/figures.py
python3 scripts/visual_qa_equity_research.py
```

Requires `lualatex`, PyMuPDF, and NumPy; warns and exits 0 (non-blocking)
if any are missing, the same convention as `scripts/acceptance_check.sh`.
It compiles the four-page example, runs ReportKit's own log diagnostics
(overfull/underfull boxes, undefined references), renders every page to
PNG, and pixel-diffs against
`latex_templates/examples/equity-research/expected/` -- see that
directory's `README.md` before running `--update-expected`.
`scripts/acceptance_check.sh` separately compiles a fast, compact
smoke-test fixture
(`latex_templates/examples/institutional_equity_acceptance_test.tex`)
with `lualatex` on every run, alongside its existing `pdflatex` fixtures.
