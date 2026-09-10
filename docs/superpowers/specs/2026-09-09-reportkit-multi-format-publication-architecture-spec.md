# ReportKit — Multi-Format Publication Architecture

**Status:** Draft / not started. Supersedes nothing; extends the architecture
introduced by
[2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md](2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md)
(Steps 1–5 implemented, `reportkit.cls` v1.8.0).
**Last updated:** 2026-09-09
**Current-state claims:** verified against the working tree at `7d8c0fe`
(see [Current state](#1-current-state-verified-2026-09-09)). Every premise below
carries a `file:line` anchor so the implementer does not re-derive it.
**Priority:** P2 — architectural hardening, ahead of any new theme.
**Companion:** [2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md](2026-09-10-reportkit-agent-interface-and-platform-contract-spec.md)
covers the agent-facing contract (capability discovery, authoring input,
diagnostics, reproducibility, vendor-neutral packaging) and amends §9, §17,
§18, §19, §20 and §21 of this document — see its §18.

---

## Framing: generalize before extending

ReportKit v1.8 proved the theme/publication-type split *once*, with one theme
pair and one publication-type pair. This phase does not add a visual family. It
converts a two-case proof into an N-case architecture, then adds exactly one new
axis — the renderer — because slides are the first format the current article
backend genuinely cannot express.

The sequencing matters more than the content. Executive, venture and editorial
each introduce a fresh opportunity for special-case coupling; if they land
before the abstraction hardens, ReportKit acquires four more generations of the
`\ifdefstring{\rk@theme}{...}` pattern that
[§3.2](#32-semantic-modules-branch-on-theme-name) exists to remove.

So the next implementation task is **not** "build the executive theme". It is:

> Generalize the v1.8 institutional/equity implementation into a renderer- and
> theme-safe architecture, prove backward compatibility, then add the slide
> renderer.

### The design model

Four concerns, kept orthogonal:

```
content  ×  publication type  ×  renderer  ×  theme
```

- **Content** is the author's material. It knows nothing about the other three.
- **Publication type** owns *structural semantics* — what parts a document has.
- **Renderer** owns *output mechanics* — pages versus frames.
- **Theme** owns *appearance* — type, color, spacing, geometry, styling.

A change along one axis must not require an edit along another. That is the
whole specification; everything below is its consequences.

---

## 1. Current state (verified 2026-09-09)

### 1.1 What exists — do not reimplement

| Component | Location |
| --- | --- |
| Core class with theme/publication-type options | `latex_templates/reportkit.cls` (v1.8.0) |
| Shared core | `latex_templates/reportkit-core.sty` |
| `theme=default` | `latex_templates/themes/reportkit-theme-default.sty` |
| `theme=institutional-research` | `latex_templates/themes/reportkit-theme-institutional-research.sty` |
| `publication-type=technical-report` | implicit — loads no extra file |
| `publication-type=equity-research` | `latex_templates/publication_types/reportkit-equity-research.sty` |
| Python theme objects | `python_scripts/reportkit/themes/` (`Theme` dataclass, `get_theme()`) |
| Theme-aware visualization | `python_scripts/reportkit_viz.py` (`apply_theme()`, `new_figure()`) |
| Config resolution + engine gating | `python_scripts/reportkit/config.py` |
| Fixtures | `latex_templates/examples/career_guide_en/`, `latex_templates/examples/equity-research/` |

### 1.2 Verified premises

| Premise | Verified at |
| --- | --- |
| Class enumerates themes as fixed `\DeclareOption` lines | `reportkit.cls:42-43` |
| Class enumerates publication types the same way | `reportkit.cls:44-45` |
| Unknown options are forwarded to `article` | `reportkit.cls:46` — `\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}` |
| Theme name reaches modules as a bare macro | `reportkit.cls:40` — `\newcommand{\rk@theme}{default}` |
| Publication type loads by literal name substitution | `reportkit.cls:70-72` |
| `reportkit-boxes.sty` branches on theme name | `reportkit-boxes.sty:20` — `\ifdefstring{\rk@theme}{institutional-research}` |
| Core loads paged-only packages | `reportkit-core.sty:18-22` — `titlesec`, `fancyhdr`, `needspace`, `caption`, `geometry` |
| Diagram styling is hardcoded in the semantic module | `reportkit-diagrams.sty:22-39` — node font/corners/dimensions, edge widths and colors, label typography |
| Further hardcoded diagram typography | `reportkit-diagrams.sty:195-307` — matrix axes, swimlanes, layers, timeline nodes |
| Pipeline template hardcodes the class and long-form package | `publication_pipeline/templates/publication-template.tex:1,4` |
| That template is the pipeline's only template | `publication_pipeline/scripts/publication_build.py:28` — `TEMPLATE = PIPELINE_ROOT / "templates" / "publication-template.tex"` |
| Config resolves `document.theme` / `.publication_type` / `.paper` | `config.py:resolve_document()` |
| Theme→engine requirements are enforced | `config.py:THEME_ENGINE_REQUIREMENTS`, `theme_engine_conflict()` |

### 1.3 Corrections to the source draft

Four premises in the source draft are stale or understate the problem. The
requirements below are written against the verified state, not the draft.

**(a) Unknown themes do not fail — they silently fall back.** The draft calls
the current enumerated-option chain "acceptable for the current
implementation". It is worse than that. Because `reportkit.cls:46` forwards
unrecognized options to `article`, `\documentclass[theme=venture]{reportkit}`
does not error: `article` ignores the option, LaTeX emits a
`Unused global option(s)` **warning** at `\begin{document}`, and the document
compiles to completion under `theme=default`. A typo'd or not-yet-implemented
theme therefore produces a plausible-looking PDF in the wrong design system.
[§3.1](#31-the-class-does-not-scale-and-fails-open)'s hard-failure requirement
is a bug fix, not only a scalability improvement.

**(b) The pipeline never passes the theme to LaTeX at all.** The draft frames
§7 as "the pipeline hardcodes a single long-form template". The deeper defect
is that `document.theme` and `document.publication_type` are resolved and
validated in Python (`publication_build.py:268-274`) but **never reach
`\documentclass`** — the template's line 1 is an unparameterized
`\documentclass{reportkit}`. A `publication.yaml` requesting
`theme: institutional-research` passes engine validation and then builds a
default-theme PDF. The repository already knows this: see the comment block at
`latex_templates/examples/equity-research/publication.yaml:1-8`, which records
that the equity fixture is compiled directly *because* pipeline-driven theme
selection does not exist. Template selection and option plumbing are one work
item, and the plumbing is the load-bearing half.

**(c) The figure-size slots the draft proposes mostly already exist.** The
draft's §10 asks to "extend toward" `full / wide / compact / square / half /
sidebar`. All six already ship, plus `dominant`; verified by resolving both
themes:

```
default                  ['compact','dominant','full','half','sidebar','square','wide']
institutional-research   ['compact','dominant','full','half','sidebar','square','wide']
```

Only the `slide-*` slots are new. [§10](#10-visualization-layer) is scoped
accordingly.

**(d) `registry.py` is taken.** `python_scripts/reportkit/registry.py` already
exists and means something else — a machine-readable inventory of public
visual primitives (figures, callouts, charts, commands) used for SKILL.md
drift detection. The new publication registry must not reuse that name; see
[§6](#6-publication-registry).

---

## 2. Normative vocabulary

These definitions are binding. Where a requirement below says a concern
"belongs to" one of these, code placing it elsewhere is a defect.

### 2.1 Theme — appearance only

A theme owns: typography; color; spacing; rules; visual density; geometry;
table styling; callout styling; diagram styling; chart styling; running
furniture; and presentation visual language.

A theme **must not** define content structures specific to a domain — finance,
startup, academic, technology or otherwise. A theme that mentions "rating" or
"traction" in anything but a color name has crossed the line.

### 2.2 Publication type — structure only

A publication type owns structural semantics: which parts exist and what they
mean.

| Publication type | Owns |
| --- | --- |
| `equity-research` | research headline, rating strip, analyst rail, what-changed, exhibit, valuation, risk/reward, financial model |
| `presentation` | title slide, section slide, message slide, chart slide, comparison slide, closing slide, appendix |
| `feature-article` | deck, byline, opening visual, pull quote, sidebar, feature exhibit |

A publication type **must not** hardcode appearance. Sizes, weights, rules and
colors come from theme hooks.

### 2.3 Renderer — output mechanics

New in this phase. Two renderers, no more:

```
paged   → technical-report, equity-research, executive-brief, feature-article, book
slides  → presentation
```

A separate `book` renderer is explicitly **not** introduced now. It becomes
justified only when a real publication needs true chapters, recto/verso layout,
trim sizes, indexing, or print production. See [§16](#16-book-support).

### 2.4 Target matrix

```
Themes                          Publication types
├── default / technical         ├── technical-report
├── institutional-research      ├── equity-research
├── executive                   ├── executive-brief
├── editorial                   ├── feature-article
└── venture                     ├── presentation
                                └── book
```

---

## 3. Architectural problems to address

### 3.1 The class does not scale, and fails open

`reportkit.cls:40-46` enumerates every theme and publication type as a literal
`\DeclareOption`, then forwards anything else to `article`. At five themes and
six publication types this is a 13-line chain whose failure mode is a silent
wrong-theme build (see [§1.3(a)](#13-corrections-to-the-source-draft)).

Replace the chain with a systematic registry/loading mechanism. The exact
mechanism is the implementer's choice — `\IfFileExists` probing on the
convention-derived filename, an explicit manifest file, or `expl3` key
handling all qualify.

**Requirements (all hard failures — `\ClassError`, not `\ClassWarning`):**

| Condition | Behavior |
| --- | --- |
| Unknown theme name | hard failure naming the requested theme and listing valid ones |
| Unknown publication type | hard failure, same shape |
| Unsupported theme × publication-type pair | hard failure naming both |
| Any of the above | **never** a silent fallback to `default` |

**Backward compatibility (non-negotiable):**

```latex
\documentclass{reportkit}
```

must continue to mean exactly `theme=default`, `publication-type=technical-report`,
`renderer=paged`, and must produce byte-comparable output to v1.8 for the
existing technical fixtures.

### 3.2 Semantic modules branch on theme name

`reportkit-boxes.sty:20` branches on `\rk@theme` to render institutional
callouts. The module's own comment defends this as "a deliberate, narrow
exception… `\newtcolorbox` bakes its options in at definition time, after the
theme file has already loaded, so there is no later hook a theme file could use
to restyle this itself."

That reasoning is sound for one theme and fails for five. The exception must
not become:

```latex
\ifdefstring{\rk@theme}{institutional-research}{...}{%
  \ifdefstring{\rk@theme}{executive}{...}{%
    \ifdefstring{\rk@theme}{editorial}{...}{%
      \ifdefstring{\rk@theme}{venture}{...}{...}}}}
```

**Requirement:** invert the dependency. The semantic module declares *what a
callout is*; the theme supplies *how it looks*, through a hook the theme file
sets before the semantic module defines its environments. This directly
resolves the definition-time objection: the module reads hook values at
`\newtcolorbox` time, and the theme has already populated them.

Conceptual API — exact form is the implementer's choice:

```latex
\RKCalloutBegin{principle}{Title}
...
\RKCalloutEnd
```

or a style-application hook:

```latex
\RKApplyCalloutStyle{principle}
```

The rule to satisfy: **semantic modules own meaning; themes own rendering.**

**Preserve every existing public environment unchanged:**

```latex
\begin{principle}{...}
\begin{decisionpoint}{...}
\begin{metric}{...}
```

No consumer publication may need rewriting.

### 3.3 Diagram styling is embedded in semantic primitives

`reportkit-diagrams.sty:22-39` fixes node fonts, rounded corners, dimensions,
edge widths, fills and label typography; `:195-307` repeats hardcoded
typography for matrix axes, swimlanes, layers and timelines.

**Requirement:** move these into theme-overridable TikZ styles or token hooks.
At minimum these styles receive theme-defined defaults:

```
rk node          rk edge          rk edge label
rk layer         rk matrix axis   rk timeline
```

**Do not fork diagram implementations per theme.** The same authored
`reportarchitecture` must render appropriately as a technical-report figure, an
institutional exhibit, an executive slide object and a venture slide object,
with identical authoring syntax.

---

## 4. Renderer architecture

### 4.1 Keep the paged renderer

The existing article-based `reportkit.cls` remains the paged backend, serving
`technical-report`, `equity-research`, `executive-brief`, `feature-article` and
`book`.

Move only what is necessary to let a slide renderer exist alongside it. Do not
restructure the paged renderer for its own sake.

### 4.2 Add the slide renderer

Create `latex_templates/reportkit-slides.cls`. Use Beamer unless a strong
implementation reason argues otherwise; record the reason if you deviate.

**Shares with the paged renderer:** metadata; color token names; semantic
diagrams; chart assets; common utilities; provenance/source helpers; the theme
registry.

**Must not inherit paged-only behavior:** `geometry` page margins; `fancyhdr`;
`Needspace` pagination logic; `article` section formatting; long-form caption
assumptions.

Presentations must not be forced through article pages.

---

## 5. Split shared versus paged-only core

`reportkit-core.sty:18-22` loads `titlesec`, `fancyhdr`, `needspace`, `caption`
and `geometry` — all paged-only. A slide class cannot load today's core without
inheriting page furniture it has no use for.

Refactor toward three files:

**`reportkit-core.sty`** — genuinely shared only: `xcolor`; `graphicx`;
hyperlinks; metadata; accessibility helpers; semantic registration;
source/provenance utilities; the generic token/hook mechanism; engine
utilities.

**`reportkit-paged-core.sty`** — `geometry`; `fancyhdr`; `titlesec`;
`needspace`; page captions; article-specific layout; pagination.

**`reportkit-slides-core.sty`** — Beamer/frame setup; slide margins; frame
title mechanics; slide footer/page number; presentation-safe typography;
slide-specific figure and table handling.

**Constraint:** do not perform file movement for its own sake. If the same
separation is achievable with smaller changes, prefer them — every relocated
line is a backward-compatibility risk against [§19](#19-backward-compatibility).

---

## 6. Publication registry

Add a Python-side registry as the **canonical source of truth** for
renderer/theme/publication compatibility. LaTeX-side checks
([§3.1](#31-the-class-does-not-scale-and-fails-open)) are a backstop for
hand-written `.tex` files; the Python registry is what the pipeline consults.

**Naming:** `python_scripts/reportkit/registry.py` is already taken by the
visual-primitive inventory (see [§1.3(d)](#13-corrections-to-the-source-draft)).
Use a distinct module — `publications.py` or `publication_registry.py` — or
place it under `reportkit/publications/`. Do not extend the existing
`registry.py`; the two have different consumers and different change cadences.

Shape (exact structure may vary):

```python
PUBLICATION_TYPES = {
    "technical-report": {
        "renderer": "paged",
        "themes": ["default", "technical"],
    },
    "equity-research": {
        "renderer": "paged",
        "themes": ["institutional-research"],
    },
    "executive-brief": {
        "renderer": "paged",
        "themes": ["executive", "institutional-research"],
    },
    "feature-article": {
        "renderer": "paged",
        "themes": ["editorial"],
    },
    "presentation": {
        "renderer": "slides",
        "themes": ["executive", "venture"],
    },
    "book": {
        "renderer": "paged",
        "themes": ["default", "technical", "editorial"],
    },
}
```

The registry must resolve:

```
publication type → renderer → compatible themes → template → required engine
```

Required engine already has an owner: `config.py:THEME_ENGINE_REQUIREMENTS`.
Fold it into the registry or have the registry defer to it, but do not create a
second, divergent copy.

**Validation must fail early**, at `reportkit check` and at build start, before
any LaTeX runs:

```
ERROR: theme 'venture' does not support publication type 'technical-report'
       compatible themes: default, technical
```

---

## 7. Pipeline template selection

Two defects, one work item (see
[§1.3(b)](#13-corrections-to-the-source-draft)):

1. `publication_pipeline/templates/publication-template.tex:1` hardcodes
   `\documentclass{reportkit}` with **no options**, so the resolved theme and
   publication type never reach LaTeX.
2. `publication_build.py:28` binds a single long-form template regardless of
   publication type.

**Requirement:** template selection and class-option plumbing both become
renderer- and publication-aware, driven entirely by `publication.yaml`.

Target layout:

```
publication_pipeline/templates/
├── technical-report.tex
├── equity-research.tex
├── executive-brief.tex
├── feature-article.tex
├── presentation.tex
└── book.tex
```

**Minimize duplication.** Six fully duplicated templates is the wrong answer;
prefer a base paged template plus publication-specific fragments. The five
paged templates differ in front matter and a handful of structural blocks, not
in metadata handling, licensing, links or bookmarks.

Selection must be automatic:

```yaml
document:
  publication_type: presentation
  theme: venture
```

resolves internally to the equivalent of:

```
renderer = slides
class    = reportkit-slides
template = presentation
```

The consumer must never specify the class manually. `document.class` stays
readable for diagnostics; it stops being the thing that decides.

**Acceptance:** building
`latex_templates/examples/equity-research/publication.yaml` through the
markdown pipeline must produce an institutional-themed, equity-research PDF —
closing the gap that file's own header comment records.

---

## 8. Configuration

Retain the existing surface:

```yaml
document:
  theme:
  publication_type:
  paper:
  engine:
```

**Do not overload `profiles:`** with semantic genres such as "startup pitch" or
"technology deck". `profiles:` means build profiles (draft/final), and
conflating the two makes profile resolution
(`config.py:_profile_values`) load-bearing for design decisions.

If authoring variants later need configuration, use a separate section:

```yaml
authoring:
  genre: startup-pitch
```

This is **optional for this sprint** — do not build it speculatively.

**Theme selection stays constrained.** Do not expose font size, margins, rule
width or paragraph spacing through `publication.yaml`. Themes own their design
system. The existing `theme:` section
(`font_family`/`font_path`/`font_policy`, `config.py:THEME_KEYS`) is the
precedent for how narrow this surface should stay, and the controlled brand
overrides in [§12.2](#122-venture) are the only sanctioned addition.

---

## 9. Common theme token contract

Formalize the Python and LaTeX theme interfaces around one conceptual
vocabulary. The two sides need not share a physical config file; they must
expose a **consistent semantic token set**.

The existing `Theme` dataclass (`reportkit/themes/__init__.py`) is the starting
point — it already covers `latex_colors`, `data_colors`, `text_width_in`,
`figure_sizes`, font candidate lists, `base_font_size` and `mathtext_fontset`.
Extend it to the categories below rather than inventing a parallel structure.

| Category | Tokens |
| --- | --- |
| Typography | display, heading, body, metadata, table, chart, mono, math |
| Color | ink, muted, hairline, surface, primary, secondary, semantic colors, data series |
| Geometry | canvas/paper, text width, margins, column gutter |
| Spacing | paragraph, heading, component |
| Rules | thin, medium |
| Tables | body size, header treatment, row spacing |
| Charts | base font, tick size, label size, line width, grid style, legend style |
| Diagrams | node font, node padding, node radius, edge weight, label font |

The Diagrams row is what
[§3.3](#33-diagram-styling-is-embedded-in-semantic-primitives) consumes; the
Charts row is what `reportkit_viz.apply_theme()` already consumes. Palette
synchronization between the two sides is already checked by
`reportkit_viz.py check-theme` / `validate_palette_against_latex()` — extend
that check to new token categories rather than adding a second checker.

---

## 10. Visualization layer

The major theme-awareness work is **already implemented**.
`reportkit_viz.py:78-141` resolves theme objects, palette, fonts, figure sizes
and mathtext configuration through `get_theme()`.

**Do not rewrite this subsystem.** Extend it only where new formats require it.

Per [§1.3(c)](#13-corrections-to-the-source-draft), the current slot set is
already:

```
full   dominant   wide (compatibility alias)   compact   square   half   sidebar
```

**The new work is slide slots only:**

```
slide-main   slide-half   slide-hero
```

**Constraints:**

- Do not hardcode slot dimensions to one paper size. A theme owns or derives
  its physical figure dimensions — `text_width_in` is already derived from
  theme geometry (`themes/__init__.py`, `text_width_in` field comment), and
  slide slots derive from canvas size the same way.
- Preserve every existing public key, including the `wide` alias. It is public
  API that shipped publications call.

---

## 11. Font requirements

The institutional theme already implements the Google Sans direction, and
`reportkit_viz.py` already handles custom mathtext explicitly to stop serif
leakage into numeric axes (`Theme.mathtext_fontset`, `"stix"` vs `"custom"`).

**Generalize that discipline.** Each theme must declare:

- primary text font
- display font, if different
- mono font
- fallback chain
- math rendering strategy
- required TeX engine

Font consistency must hold across: body; headings; sidebar; tables; TikZ; chart
x ticks; chart y ticks; legends; annotations; mathtext.

The `font_policy: strict` / `fallback` mechanism
(`themes/reportkit-theme-institutional-research.sty:82`, `config.py:THEME_KEYS`)
is the existing precedent — reuse it, do not reinvent per theme.

**Licensing:** do not commit proprietary font binaries without confirmed
redistribution rights. See `metadata/licenses.yml`, `THIRD-PARTY-NOTICES.md`
and `references/licensing.md`; `tests/test_licensing.py` enforces this.

---

## 12. New themes

### 12.1 Executive

**Primary renderer:** `slides`. **Secondary use:** `executive-brief`.

Visual character: consulting/corporate strategy; assertion-evidence structure;
strong alignment and grid; moderate-to-high information density; restrained
palette; sans typography; charts and diagrams dominant; minimal decoration.

Must support especially well:

```
architecture   process    2×2       roadmap
comparison     waterfall  timeline  table   decision tree
```

Most of these already exist as primitives (`reportkit-diagrams.sty`,
`reportkit-structure.sty`, `reportkit-process.sty`, `reportkit_viz.py`'s
`waterfall_chart` / `bubble_matrix` / `timeline_chart`). Executive should
restyle them, not reimplement them.

**Do not create `tech-presentation`, `finance-presentation` or
`strategy-presentation` themes.** Those are authoring genres over one executive
theme — that is exactly the confusion
[§17](#17-authoring-skill-updates) exists to prevent.

### 12.2 Venture

**Primary renderer:** `slides`. **Publication type:** `presentation`.

Visual character: startup/VC; brand-forward; large typography; lower
information density; variable composition; strong negative space; product
imagery and screenshots; bold metrics; light and dark frames; storytelling over
consulting density.

Required compositions:

```
hero        problem       solution   product
traction    market        business model
competition team          funding ask
use of funds             closing
```

These are **semantic compositions, not rigid templates** — an author combines
them, they do not fill in fixed slots.

Controlled brand overrides are permitted, and are the only sanctioned expansion
of [§8](#8-configuration)'s constrained surface:

```yaml
brand:
  primary:
  secondary:
  logo:
  display_font:
```

Do not expose arbitrary slide styling beyond these four keys.

### 12.3 Editorial

**Renderer:** `paged`. **Publication types:** `feature-article`, `book`.

Visual character: magazine / thought leadership; strong editorial typography;
serif body permitted and preferred; complementary sans for metadata and
display; storytelling through text and visual rhythm; more variable page
composition than the technical report.

Required support:

```
cover/opening      headline           deck              byline
pullquote          sidebar            drop cap
one-column prose   two-column prose   full-width visual
image credit       large exhibit      feature opener
endnotes/references
```

**Do not make this a generic DTP system.** Editorial is a design system with
opinions, not a page-layout engine.

---

## 13. Presentation publication type

Add `latex_templates/publication_types/reportkit-presentation.sty` (or an
equivalent shared semantic layer), following the naming convention
`reportkit.cls:70-72` already derives from the publication-type name.

Shared compositions:

```
title slide          section divider      single-message slide
text + visual        visual + text        full-visual slide
two-column comparison                     three-part argument
hero metric          chart slide          table slide
architecture slide   closing slide        appendix slide
```

**Both `executive` and `venture` must use this same publication type.**

This is a **major acceptance criterion for the whole abstraction**: if venture
needs its own publication type, the theme/publication-type boundary has failed
and the design must be revisited before proceeding to
[Phase E](#phase-e--editorial).

---

## 14. Executive brief publication type

A minimal paged format targeting roughly **2–8 pages**.

Required structure:

```
title / metadata
executive recommendation
key findings
compact exhibits
decision / implication
risks
next steps
sources
```

Reuse existing semantic components wherever possible — `metric`,
`decisionpoint`, `redflag`, the exhibit system from
`publication_types/reportkit-equity-research.sty`, and the provenance/source
helpers in core all apply directly.

**Do not create a large new primitive library** unless something is genuinely
missing.

---

## 15. Feature article publication type

Add semantic compositions for:

```
headline    deck        byline      opening visual
pull quote  sidebar     feature exhibit
section opener          image credit
```

**Keep styling entirely in the editorial theme.** The test: the same article
structure must remain usable, unmodified, with a second future editorial theme.

---

## 16. Book support

**Do not create `reportkit-book.cls`** in this phase unless an implementation
constraint forces it. Use the existing long-form infrastructure
(`reportkit-longform.sty`) plus the paged renderer.

Extend only what is clearly missing:

```
title page       publication details    contents
parts/chapters (if needed)              chapter openers
bibliography     appendices             glossary hooks
```

**Defer** until a real publication requires them: recto/verso; print
signatures; indexing; trim/bleed production. These are also the trigger
conditions for a dedicated book renderer per
[§2.3](#23-renderer--output-mechanics).

---

## 17. Authoring skill updates

`SKILL.md` must choose **publication type before visuals**. Add a decision gate
approximately:

```
Need systematic explanation?              → technical-report / book
Need an investment recommendation?        → equity-research
Need a short management decision doc?     → executive-brief
Need slide-based communication?           → presentation
Need designed narrative reading?          → feature-article
```

Then select a compatible theme — compatibility comes from the registry
([§6](#6-publication-registry)), not from the agent's judgment.

The authoring agent must internalize:

> **publication type ≠ topic. theme ≠ topic.**

Worked example — "technology architecture" is a topic, and may appear as:

```
technical-report + technical
presentation     + executive
feature-article  + editorial
```

`reportkit/registry.py`'s existing SKILL.md drift check
(`check_skill_drift()`) covers figures and callouts. Extend it, or add a
sibling check, so the documented publication-type/theme matrix cannot drift
from the registry either.

---

## 18. Testing and QA

Every theme × publication-type combination needs a canonical fixture.

| Theme | Fixture | Status |
| --- | --- | --- |
| Technical | career-guide (`examples/career_guide_en/`) | exists |
| Institutional | equity-research (`examples/equity-research/`) | exists |
| Executive | 8–10 slide fictional technology/strategy deck | new |
| Venture | 10–12 slide fictional startup pitch | new |
| Editorial | 6–8 page fictional feature article | new |

**Executive deck must include:** title; assertion-evidence slide; architecture;
2×2; chart; table; roadmap; recommendation.

**Venture pitch must include:** hero; problem; product; traction; market;
competition; team; ask.

**Editorial article must include:** opening page; body prose; pullquote;
sidebar; image/figure; full-width exhibit; references.

All fixture content must be fictional and must not reproduce third-party
branding — the constraint the institutional spec already imposes.

### Required automated checks

```
compilation                      output renderer/class
paper/canvas dimensions          font resolution
theme/publication compatibility  missing assets
undefined references             overfull content
chart font consistency           palette synchronization
no unexpected default-theme leakage
```

The last one is the direct regression test for
[§1.3(a)](#13-corrections-to-the-source-draft): a build that requested a theme
and silently produced `default` must fail the suite.

Several of these already have owners — `publication_pipeline/scripts/
check_build_log.py` (overfull/undefined), `publication_validation.py` (assets),
`reportkit_viz.py check-theme` (palette). Extend them rather than adding
parallel checkers.

### Visual regression

Render canonical pages and slides to PNG and compare against stored expected
images, following the existing pattern at
`latex_templates/examples/equity-research/expected/` and
`scripts/visual_qa_equity_research.py`.

**Inspect changed layouts before accepting a baseline update.** An
auto-accepted baseline is indistinguishable from no test at all.

**Known gap to close, not inherit:** the institutional spec records that no
implementing session had a TeX Live install with `lualatex`, leaving its
LaTeX-level compiles and visual baselines unverified. This phase adds three
more themes and a second renderer; carrying that gap forward would leave the
majority of ReportKit's output unverified by compilation. Establish a real
compile environment as part of [Phase A](#phase-a--architecture-hardening),
before new themes land.

---

## 19. Backward compatibility

**Non-negotiable.**

```latex
\documentclass{reportkit}
```

must continue to work, meaning `theme=default`,
`publication-type=technical-report`, `renderer=paged`.

Every existing semantic API must continue to work:

```
principle        decisionpoint   researchproblem   assumption
redflag          evidencenote    limitationnote    tipnote
deliverablenote  metric          reportmatrix      riskheatmap
reportflow       reportswimlane  reportarchitecture
reportroadmap    ...
```

The authoritative list is generated, not hand-maintained: see
`reportkit/registry.py:generate_registry()`. Use it as the compatibility
checklist.

Existing figure size names must remain valid, including the `wide` alias
([§10](#10-visualization-layer)).

**Do not alter default-theme rendering as a side effect of this refactor**
unless an existing bug is explicitly being corrected — and if so, say which,
in the changelog.

---

## 20. Implementation phases

### Phase A — Architecture hardening

Before any new theme:

1. introduce the publication/renderer registry ([§6](#6-publication-registry));
2. validate theme/publication compatibility, failing early and hard
   ([§3.1](#31-the-class-does-not-scale-and-fails-open), [§6](#6-publication-registry));
3. separate shared from paged core, minimally ([§5](#5-split-shared-versus-paged-only-core));
4. refactor callout styling into theme hooks ([§3.2](#32-semantic-modules-branch-on-theme-name));
5. refactor diagram styling into theme hooks ([§3.3](#33-diagram-styling-is-embedded-in-semantic-primitives));
6. make pipeline template selection *and class-option plumbing* publication-aware
   ([§7](#7-pipeline-template-selection));
7. establish a working `lualatex` compile environment ([§18](#18-testing-and-qa)).

**Definition of done:** the existing technical and institutional/equity
fixtures still render correctly — verified by actual compilation, not
inspection — with **no theme-specific conditional branches remaining in any
semantic module**, and with the equity fixture building through the markdown
pipeline rather than only by direct compile.

### Phase B — Slide renderer

Implement `reportkit-slides.cls`, the `presentation` publication type, and the
slide pipeline template. Use a minimal placeholder theme if one is needed for
architecture testing.

**Definition of done:** a presentation compiles through the normal ReportKit
pipeline without touching the article renderer.

### Phase C — Executive theme

Implement executive visual tokens and presentation compositions, reusing the
existing diagram and visualization DSLs.

**Definition of done:** a credible consulting/technology deck can be authored
with no custom page coordinates and no bespoke TikZ.

### Phase D — Venture theme

Implement venture as a second presentation theme.

**Definition of done:** the same presentation semantic primitives render
materially differently under `executive` and `venture` **with no duplicated
slide implementation**.

This is the critical proof that theme versus publication type is working. If it
fails, stop and fix the abstraction rather than proceeding.

### Phase E — Editorial

Implement the editorial theme and the `feature-article` publication type.

**Definition of done:** a long-form magazine-style article can be produced
without falling back to technical-report visual grammar.

### Phase F — Brief and book polish

Implement `executive-brief` and book refinements. Prefer reuse over new
infrastructure.

---

## 21. Non-goals

Do not implement:

- generic desktop publishing
- an arbitrary slide-positioning DSL
- PowerPoint import/export
- a theme marketplace
- dozens of industry-specific themes
- separate finance/technology/strategy presentation themes
- animation-heavy Beamer features
- a full print publishing workflow
- automatic responsive HTML rendering
- a theme inheritance hierarchy, unless clearly necessary
- arbitrary YAML control over all visual parameters

---

## 22. Final architectural acceptance criterion

This phase succeeds when all of the following work through shared semantics:

**Same architecture diagram** → technical report, executive slide, venture slide.

**Same time-series chart** → institutional research, executive deck, editorial
article.

**Same evidence/metric semantics** → technical callout, institutional hairline
treatment, executive slide object.

And none of the following is required to achieve it:

- theme-specific authoring syntax
- page-specific coordinates
- duplicated chart functions
- duplicated diagram implementations
- large if/else chains inside semantic modules

Target architecture:

```
                  CONTENT
                     │
             PUBLICATION TYPE
                     │
                  RENDERER
                     │
                   THEME
                     │
        ┌────────────┼────────────┐
        │            │            │
     semantics     charts      diagrams
        │            │            │
        └────────────┼────────────┘
                     │
                   OUTPUT
```

---

## 23. Open questions

Resolve these before or during Phase A; record resolutions in the
implementation plan, following the convention the institutional-theme spec and
plan established.

1. **`default` versus `technical`.** [§6](#6-publication-registry)'s registry
   lists both as themes for `technical-report`, but only `default` exists
   (`themes/reportkit-theme-default.sty`). Is `technical` a rename, an alias,
   or a genuinely distinct fifth theme? A rename collides with
   [§19](#19-backward-compatibility); an alias is cheap; a new theme needs its
   own fixture.

2. **Hook mechanism for callouts.** `\newtcolorbox` bakes options at definition
   time (`reportkit-boxes.sty:9-19`). Does the theme populate token macros that
   the module reads at definition time, or does the module defer definition
   until `\AtBeginDocument`? The first is simpler; the second is more flexible.
   Pick one and apply it consistently across callouts and diagrams.

3. **Registry duplication between Python and LaTeX.** The class needs
   compatibility data for hand-written `.tex` files; Python needs it for the
   pipeline. Generate the LaTeX table from the Python registry, hand-maintain
   both with a drift test, or have LaTeX validate only names and defer pairing
   to Python?

4. **Slide canvas geometry.** Do slide themes declare a canvas (16:9 at what
   physical size?) the way paged themes declare paper, and does `paper:` in
   `publication.yaml` become meaningless — or an error — under the `slides`
   renderer?

5. **Brand overrides and palette synchronization.**
   [§12.2](#122-venture)'s `brand.primary` overrides a theme color at build
   time. How does `validate_palette_against_latex()` stay meaningful when the
   palette is partly configuration-supplied?

6. **Fixture count versus build time.** Five fixtures across two renderers,
   plus visual regression, on an engine (`lualatex`) that is not fast. Does the
   full suite still run per-commit, or does visual regression move to a
   separate gate?
