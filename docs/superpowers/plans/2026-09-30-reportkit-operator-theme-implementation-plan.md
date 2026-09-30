# ReportKit Operator Theme Implementation Plan (multi-agent)

**Status:** Proposed. Nothing implemented.
**Last updated:** 2026-09-30

> **For agentic workers:** this plan is built for parallel execution. One
> agent lands **Wave 0** alone. After it merges, the **Wave 1 lanes** run
> concurrently, each in its own git worktree and branch, and may edit only
> the files their lane owns. **Wave 2** is one integration agent. **Wave 3**
> is a reviewer that did not author any lane. Steps use checkbox (`- [ ]`)
> syntax for tracking.

**Goal:** Ship `operator` as an experimental, registered pdfLaTeX theme for
`technical-report`, with theme-neutral product-identity, capability-grid and
execution-surface primitives that every paged theme can render, a Markdown
path for those primitives, and chart encodings that do not rely on colour
alone.

**Spec:** [`docs/superpowers/specs/2026-09-30-reportkit-operator-theme-spec.md`](../specs/2026-09-30-reportkit-operator-theme-spec.md)
(§ numbers, decisions O1–O10 and AC1–AC12 refer to it. Appendix A is the
author's original spec; Appendix B is the supplied `operator.sty` v5.)

**Tech stack:** pdfLaTeX with `lmodern`/T1 through `reportkit.cls`; tcolorbox,
TikZ, etoolbox, xparse (already loaded by the class); Python 3.12, Matplotlib
(`reportkit.viz`), pytest, ruff; the pinned toolchain image (TeX Live 2024) for
every compiled gate (`scripts/reportkit_container.py` on hosts without TeX).

---

## 1. Why the plan is shaped this way

The work has three independent products (a theme, two primitive modules, and
a chart extension) that all converge on a small set of **hotspot files**. If
lanes edit these concurrently, most of the merge work becomes conflict
resolution:

| Hotspot | Needed by | Why it collides |
| --- | --- | --- |
| `python_scripts/reportkit/publications.py` (`THEMES`, `PUBLICATION_TYPES["technical-report"]["themes"]`) | theme, fixture, coverage tests | Registration and pairing |
| `latex_templates/reportkit-core.sty` (token contract) | theme, both primitive modules, four existing themes | New token families and gates |
| `latex_templates/reportkit-boxes.sty` (`rk@callout`) | theme | Per-kind callout hook |
| `latex_templates/reportkit-paged-core.sty` | theme | Table font hook |
| `latex_templates/reportkit.cls` (module `\RequirePackage` list, lines 102–107) | both primitive modules | Loading the new modules |
| `python_scripts/reportkit/primitive_targets.py` (`ROLE_TABLE`) | both primitive modules | Availability per publication type |
| `python_scripts/reportkit/registry.py` (`PUBLIC_CHART_NAMES`) | charts | New public chart names |
| `python_scripts/reportkit/themes/__init__.py` (`ChartTokens`) | charts, every theme module | New dataclass fields |
| `tests/test_theme_contract.py` (`REQUIRED_STYLE_TOKENS`) | theme, four existing themes | Token list |
| `references/primitive-contract.md` (generated), `SKILL.md`, `CHANGELOG.md`, `TODOS.md` | docs, everything | Generated or rolled-up text |

**The strategy is interface-first:**

1. **Wave 0 (one agent, serial).** Land every hotspot edit at once: the
   registrations, the frozen token names and gates, the two no-op core hooks
   with regression evidence, **stub** primitive modules whose contract
   metadata already carries the final signatures, a **stub** operator theme,
   and the reserved chart names. After Wave 0 every hotspot above is frozen.
2. **Wave 1 (eight lanes, parallel).** Each lane owns a disjoint set of files,
   mostly the stubs Wave 0 created. A lane never edits a file it does not own.
   A lane that needs a contract change asks the coordinator (§6).
3. **Wave 2 (one agent, serial).** Regenerate generated files, run the full
   acceptance matrix under the pinned toolchain, and write the CHANGELOG and
   TODOS entries.
4. **Wave 3 (one reviewer).** Page-by-page visual review and a bounded fix
   loop.

---

## 2. Global constraints (every lane)

- **No theme branching (O5).** No semantic module may test `\rk@theme` or
  mention `operator`. `tests/test_theme_contract.py::test_semantic_modules_do_not_branch_on_theme_name`
  enforces this.
- **Existing output is frozen (AC7).** Nothing in Waves 0–1 may change a page
  of any existing theme's fixture. Core additions have no-op defaults; the
  token blocks Lane T adds to existing themes are read only by the new
  primitives, which no existing fixture uses.
- **No package reloads with options.** Theme files configure the packages the
  paged core loads (`\geometry{}`, `\captionsetup{}`, `\titleformat`); they
  never `\RequirePackage` them again with options (spec §8 item 4).
- **No new single-letter column types, no global `\tikzset` keys that shadow
  `/tikz/` keys** (spec §9 row 13).
- **Fictional fixture content only (O9).** No real product names or prices in
  anything under `latex_templates/` or `tests/`.
- **Projects stay outside the checkout.** Only the engine fixture lives in the
  repo. Compiled PDFs and PNGs are build outputs, not commits, except the
  reviewed `expected/` baseline that `visual_qa_operator.py --update-expected`
  records in Wave 3.
- **Checks before every push:** `ruff check .`, `python3 -m pytest` on the
  lane's own test module and every module listed for it in §3.4 (TeX-backed
  tests skip themselves where no toolchain is present, so they must also be
  run in the pinned image), plus the lane's compiled smoke test in the pinned
  image.
- **Visual review honesty (AGENTS.md).** Any lane or wave that cannot render
  and look at pages says so. It never reports a visual check as done.

---

## 3. Wave 0 — contract freeze (single agent, serial)

### 3.1 Files owned

Every hotspot in §1, plus the new stub files listed in §3.3.

### 3.2 Shared contract edits

- [ ] **Registry.** Add `THEMES["operator"]`: `renderers=["paged"]`,
  `required_engine="pdflatex"`, `common_package="reportkit-theme-operator"`,
  `renderer_adapters={"paged": "reportkit-theme-operator-paged"}`,
  `stability="experimental"`, `since=` the version the `[Unreleased]`
  CHANGELOG section will ship as. Add a comment recording the D9 exception
  and its reason (spec O2). Append `"operator"` to
  `PUBLICATION_TYPES["technical-report"]["themes"]`.
- [ ] **Palette name inventory.** List every colour name the paged modules
  reference (`\color{…}`, `colframe=`, `colback=`, `draw=`, `fill=` values in
  `latex_templates/reportkit-*.sty` and `publication_types/`). Commit the
  list into spec §3.1's table so Lane O defines every one.
- [ ] **Core hooks (spec §3.2).**
  - `\RKTokCalloutKindOptions#1`, defaulting to empty, appended as the last
    key group of `rk@callout` in `reportkit-boxes.sty` (after `#1`, so a
    per-use option still wins).
  - `\RKTokTableFont`, defaulting to empty, applied with
    `\AtBeginEnvironment` to `tabular`, `tabular*`, `tabularx` and
    `longtable` in `reportkit-paged-core.sty`.
- [ ] **New token families (spec §3.2).** Declare every identity and execution
  token as a `\rk@styletokenerror` sentinel in `reportkit-core.sty`, add the
  flags `\ifrk@identitytokensloaded`/`\ifrk@executiontokensloaded`, and add
  the use-time gates `\RKAssertIdentityTokens`/`\RKAssertExecutionTokens`.
  Freeze the final names; add them to `tests/test_theme_contract.py` as two
  new lists checked against every canonical paged theme. The check stays
  `xfail(strict=True)` until Lane T and Lane O land, so it fails loudly if
  anyone forgets to remove the marker.
- [ ] **Module loading.** Add `\RequirePackage{reportkit-identity}` and
  `\RequirePackage{reportkit-execution}` after `reportkit-grammar` in
  `reportkit.cls`.
- [ ] **Availability.** Add both modules to `primitive_targets.py` `ROLE_TABLE`
  with the roles in spec §5 (native: technical-report, book; allowed:
  equity-research, executive-brief).
- [ ] **Chart contract.** Add `stacked_bar_chart` and `line_chart` to
  `PUBLIC_CHART_NAMES` (with stub functions that raise `NotImplementedError`
  naming Lane F). Add `hatches: tuple[str, ...] = ()` and
  `dashes: tuple[str, ...] = ()` to `ChartTokens`.
- [ ] **Renderer contract.** Define the `line_macros` constraint shape that
  contract metadata uses, for example
  `{"code":"line_macros","prefixes":[["$ ","termprompt"],["# ","termcomment"]],"default":"termline"}`
  and `{"code":"line_macros","split":"|","macro":"capabilityrow"}`. Write it
  into spec §5.3 as the frozen shape. Lane R implements it.

### 3.3 Stub files (the parallelism seam)

Each stub compiles, is loaded by the class, and carries **final** contract
metadata, so the registry, context and contract tests are green from Wave 0
and no lane has to edit a hotspot to register anything.

| Stub | Content | Replaced by |
| --- | --- | --- |
| `latex_templates/reportkit-identity.sty` | Every §5.1/§5.2 command and environment defined with its final xparse signature, rendering plain text (`[chip:name]`, `D`/`U`); a `% <reportkit-contract>` block per primitive with final arguments, constraints and a canonical example. | Lane I |
| `latex_templates/reportkit-execution.sty` | Every §5.3 primitive with its final signature; body lines rendered as plain `\texttt` paragraphs; contract blocks including the frozen `line_macros` constraints. | Lane X |
| `latex_templates/themes/reportkit-theme-operator.sty` | Engine guard (error unless pdfTeX), `lmodern` + T1, the operator palette under the semantic names, and a copy of the default theme's sentinel-token values so every existing primitive compiles. | Lane O |
| `latex_templates/themes/reportkit-theme-operator-paged.sty` | Copy of the default paged adapter with the operator geometry. | Lane O |
| `python_scripts/reportkit/themes/operator.py` | A complete `THEME` built from the operator palette, default metrics, `hatches`/`dashes` from spec §3.3, and Latin-script coverage (`en` verified). | Lane O (values), Lane F (chart fields) |
| `latex_templates/examples/operator-report/report.tex` | A two-page skeleton with one `\section` per primitive family and `\input` points for Lane E. | Lane E |

### 3.4 Wave 0 tests and exit criteria

- [ ] `python3 -m pytest` green, including `test_publication_registry.py`,
  `test_latex_publication_registry.py` (regenerate the LaTeX registry
  backstop), `test_theme_contract.py`, `test_agent_contract.py`,
  `test_publication_theme_coverage.py` (the new `technical-report × operator`
  pair is picked up automatically by the generated layer; it must compile).
- [ ] Regenerate `references/primitive-contract.md` from the stub metadata and
  commit it, so Wave 1 lanes do not fight over it.
- [ ] **AC7 evidence for the core hooks.** Render every canonical fixture page
  before and after the Wave 0 branch in the pinned image and record the
  pixel comparison in the Wave 0 PR. Any difference blocks the merge.
- [ ] The stub operator skeleton compiles with `reportkit build`.

---

## 4. Wave 1 — parallel lanes

Every lane:

- works in its own worktree on branch `operator/<lane-letter>-<slug>`;
- owns only the files listed for it;
- adds its own test module (new file, so there are no test-file collisions);
- runs its compiled smoke test in the pinned image and attaches the log
  summary (errors, overfull/underfull counts, warnings) to its PR;
- keeps the lane PR independent: it must merge onto post-Wave-0 `main`
  without any other lane.

Lane dependency on other lanes is **none** unless stated. Lanes E and D
consume the frozen API only.

### Lane O — Operator theme appearance

**Owns:** `reportkit-theme-operator.sty`, `reportkit-theme-operator-paged.sty`,
`python_scripts/reportkit/themes/operator.py` (except the `ChartTokens`
encodings Lane F tunes), `tests/test_operator_theme.py`.

- [ ] Palette: every semantic name from the Wave 0 inventory, with spec §3.1
  hex values; `\pagecolor{PageBg}` in the adapter.
- [ ] Every sentinel token (callout, metric, diagram, algorithm) replaced with
  operator values: rounded 6pt callouts, equal rules, `SurfaceAlt` fill,
  small uppercase sans titles.
- [ ] `\RKTokCalloutKindOptions` per spec §4's table.
- [ ] `\RKTokTableFont` = `\sffamily\small`.
- [ ] Identity and execution tokens (spec §3.2) with spec §4's contrast rules:
  terminal text white on `InkStrong`, title `Faint`, unestablished glyph
  `Faint`/`Muted`.
- [ ] Paged adapter: geometry, explicit `\headheight` measured so fancyhdr is
  silent, running furniture from `\rk@leftheader`/`\rk@footer`/`\rk@version`,
  heading formats with `\RKReserveSpace`, `\maketitle`, `\captionsetup`.
- [ ] Python theme values: palette constants matching the `.sty`; typography
  stacks "Latin Modern Sans"/"Latin Modern Roman"/"Latin Modern Mono" with a
  fallback the chart layer resolves; `reportkit_viz check-theme --theme operator`
  passes.
- [ ] `test_operator_theme.py`: registration and pairing; pdfTeX engine guard
  fails under LuaLaTeX with a clear message; palette parity between `.sty` and
  Python; no `rk*` colour names leak into public use; a compiled smoke document
  exercises headings, a booktabs table with an `X` column, a `longtable`, all
  four restyled callouts, and a caption, with zero overfull boxes and zero
  `\headheight` warnings.

### Lane I — Identity primitives

**Owns:** `latex_templates/reportkit-identity.sty`, `tests/test_identity_primitives.py`.

- [ ] Implement spec §5.1/§5.2 on the frozen signatures, reading only
  `RKTokIdentity*`/`RKTokCapability*` tokens, calling
  `\RKAssertIdentityTokens` on first use.
- [ ] `\productchip` is pure text (safe in any cell). `\productavatar` is TikZ,
  and is rejected inside alignments with a package error.
- [ ] `\statusdot{<state>}` accepts only `verified|flag|accent|neutral`.
- [ ] `capabilitygrid`: build the tabular preamble and the rotated header row
  from the comma list *before* `\begin{tabular}` (expand into a token
  register; no `&` inside loops). Plain `tabular`, never `tabularx`.
  `\capabilityrow[tag]{name}{cells}` walks the cell string, emits one glyph
  per cell, counts `D` for `score=auto`, and errors when the length differs
  from the column count.
- [ ] Tests: a compiled matrix under the stub or real operator theme **and**
  under `default` (the tokens Lane T adds; until then, a test-local token
  file); wrong-length row and unknown state fail with the named error
  (AC10); a 12-column grid fits `\linewidth` at A4 operator geometry with
  zero overfull boxes.

### Lane X — Execution surfaces

**Owns:** `latex_templates/reportkit-execution.sty`, `tests/test_execution_primitives.py`.

- [ ] `terminalblock`/`diffblock` as `breakable` tcolorboxes reading only
  `RKTokTerminal*`/`RKTokDiff*`, calling `\RKAssertExecutionTokens`.
  `colupper` (terminal) is the terminal text token, so body text can never
  inherit black (spec §8 item 1).
- [ ] Line macros: each sets one full-width line in the mono font, preserves
  `~`/`\ ` indentation, wraps long lines with a hanging indent under the
  gutter, renders an empty argument as a blank line of the same height, and
  paints the add/delete band across the full inner width.
- [ ] Line macros used outside their block raise a package error naming the
  expected environment.
- [ ] Tests: compiled blocks with every TeX-special character escaped as the
  renderer would; a 120-line diff breaks across pages with no overfull box
  (AC11); render at 140 DPI and assert terminal glyph pixels are light on a
  dark box (AC4), using the repo's existing page-render helpers
  (`publication_pipeline/scripts/render_pdf_pages.py`).

### Lane R — Markdown line-macro rendering

**Owns:** `python_scripts/reportkit/tex_renderer.py`,
`python_scripts/reportkit/markdown_directives.py`, `tests/test_line_macro_directives.py`.

- [ ] In `tex_renderer._body`, when the primitive's contract record has a
  `line_macros` constraint, render `content` one line at a time: classify by
  prefix (or split on the separator), strip the prefix, convert leading
  spaces to `~`, `tex_escape` the rest, wrap in the macro. All other
  primitives render exactly as today.
- [ ] In `markdown_directives._parse_body`, keep the raw `content: |` block
  (no whole-value `strip`) when the selected primitive declares
  `line_macros`, so first-line indentation survives. Leave behaviour
  unchanged for every other primitive.
- [ ] Validate at parse time: a `capabilitygrid` line with the wrong field
  count, or a cell string with characters other than `D`/`U`/`-`, is a
  directive diagnostic with the source line, not a TeX error later.
- [ ] Tests (AC9): golden TeX for the three spec §5.3 examples; every
  metacharacter (`$ _ % # & \ { } ~ ^`) inside terminal and diff lines; blank
  lines kept; an existing callout directive still renders byte-identical TeX.
  No TeX toolchain needed.

### Lane T — Tokens for the existing paged themes

**Owns:** one new clearly delimited block ("Identity and execution-surface
tokens") at the end of each of `reportkit-theme-default.sty`,
`reportkit-theme-institutional-research.sty`, `reportkit-theme-executive.sty`
and `reportkit-theme-editorial.sty`. It owns nothing else in those files.

- [ ] Populate every identity and execution token using each theme's
  existing palette names and type scale (terminal: its darkest ink; diff:
  its evidence/red-flag colours), then set both loaded-flags.
- [ ] Remove the `xfail` from Wave 0's token-population checks for these four
  themes.
- [ ] Evidence that existing fixtures are unchanged (the tokens are unread
  there): before/after page renders, recorded in the PR (AC7).
- [ ] One compiled smoke document per theme that uses every new primitive,
  zero errors and zero overfull boxes. (The slides-only `venture` theme is
  excluded: the primitives are unavailable for `presentation`.)

### Lane F — Chart encodings and new charts

**Owns:** `python_scripts/reportkit/viz/` (the `hatches`/`dashes` consumption,
`stacked_bar_chart`, `line_chart`, outside value labels on `bar_chart`),
the `ChartTokens` values in `themes/operator.py`, `tests/test_viz_encodings.py`.

- [ ] `apply_theme` reads `hatches`/`dashes`; an empty tuple reproduces
  today's output exactly (existing chart tests stay byte-identical).
- [ ] `stacked_bar_chart(data, *, segments, hatches=None, …)`: hatched segments
  draw the hatch in `Muted` over the surface colour; stack order bottom to top
  as given.
- [ ] `line_chart(data, *, x, series, markers=None, …)` with numeric x,
  per-series dashes, and a `markers=[(x, label)]` option for vertical
  annotations (the credit-cap kink). Wrap `timeseries` only if it handles a
  numeric index without date formatting.
- [ ] `bar_chart(..., value_labels="outside")` places labels past the bar end
  and expands the axis so none clip.
- [ ] Tests on Matplotlib artist extents: AC5 (labels outside bars, inside
  axes), AC6 (hatch present on review segments, smallest inference segment
  ≥ 2 mm at the fixture's figure size), and dash styles distinct per series.

### Lane E — Canonical fixture and visual QA tooling

**Owns:** `latex_templates/examples/operator-report/` (`report.tex`,
`composition-brief.json`, `figures.py`), `scripts/visual_qa_operator.py`,
`tests/test_visual_qa_operator.py`.

- [ ] A 6–8 page fictional report that uses every primitive at least once:
  identity chips in prose and tables, a 9-column capability grid, price
  pills, status dots, all four restyled callouts, a terminal block, a diff
  that crosses a page break, three booktabs tables (one `tabularx` with an
  `X` column, one wide), and Figures 3, 5, 6.
- [ ] `figures.py` generates Figures 3/5/6 with `apply_theme("operator")` from
  fictional data declared in the script (O9) and writes PDF + PNG, as in the
  other fixtures. Until Lane F merges, the script may fail on the stubs; the
  test marks figure generation `xfail(strict=True)` against the stub's
  `NotImplementedError`.
- [ ] `composition-brief.json` in the same schema as the other examples.
- [ ] `visual_qa_operator.py`, modelled on `visual_qa_editorial.py`: compile,
  inspect the log (AC1, AC2), per-region font check with pdfplumber (AC3),
  terminal pixel check (AC4), render pages, and compare with or update
  `expected/`.
- [ ] `test_visual_qa_operator.py`: the script's pure functions (log parsing,
  font-region classification, pixel sampling) unit-tested on synthetic inputs.

### Lane D — Documentation

**Owns:** `references/operator-theme.md`, the `SKILL.md` format-table row
and "Theme guides" row, the `AGENTS.md`-routed references index if one lists
theme guides.

- [ ] Author guide: when to pick `operator`, the pdfLaTeX requirement, each
  primitive with TeX and Markdown examples copied from the spec, the
  capability-grid legend convention, contrast rules, and known limits
  (`\productavatar` not in tables).
- [ ] `SKILL.md`: add `technical-report × operator` to the format table (TeX
  or Markdown, pdfLaTeX, canonical example path, composition brief, guide).
- [ ] Doc drift tests (`test_agent_contract.py` and any context-budget
  checks) pass.

---

## 5. Merge order and integration checkpoints

Lanes merge in any order onto `main`; each is independent after Wave 0. The
preferred order front-loads the pieces others validate against:

1. **Lane O** (real theme values) and **Lane T** (tokens elsewhere). After
   both, remove the remaining `xfail` on token population.
2. **Lanes I, X, R, F** in any order.
3. **Lane E**, then **Lane D** (so the guide can link the finished fixture).

After every merge the merging agent runs `ruff check .`, `python3 -m pytest`, and
`pytest tests/test_publication_theme_coverage.py -k operator` in the pinned
image. A red `main` stops further merges until it is fixed by the lane that
broke it.

## 6. Coordination protocol

- The coordinator is the Wave 0 agent (or the user). Contract changes after
  Wave 0 (a token rename, a signature change, a new constraint code) go
  through the coordinator as a single small PR to `main`; lanes rebase onto it.
- A lane that finds a spec defect records it in its PR description under
  "Spec questions" and continues with the most conservative reading; it does
  not silently change the API.
- Lanes do not edit `CHANGELOG.md`, `TODOS.md` or generated files; Wave 2 does.

## 7. Wave 2 — integration (single agent)

- [ ] Regenerate `references/primitive-contract.md`, the LaTeX registry
  backstop, and `adapters/openai/tools.json` if the contract changed; commit
  only generated diffs.
- [ ] Remove every remaining `xfail(strict=True)` marker introduced by this
  plan.
- [ ] Full acceptance matrix in the pinned image: `scripts/acceptance_check.sh`,
  `pytest` (full, including TeX-marked tests), `visual_qa_operator.py`, and
  `reportkit doctor --require full-build` inside a scratch consumer project
  created **outside** the checkout with
  `reportkit init <tmp>/operator-demo --publication-type technical-report --theme operator --source-mode markdown`,
  built from a Markdown manuscript that uses all three `reportkit` line-macro
  directives. Inspect `build-report.json` selection.
- [ ] AC7 across the whole matrix: every pre-existing fixture page unchanged.
- [ ] `CHANGELOG.md` `[Unreleased]` entry; `TODOS.md` row for this spec and
  plan; this plan's **Status** block updated with what was and was not run.

## 8. Wave 3 — visual review (reviewer who authored no lane)

- [ ] Render every fixture page at 140 DPI and review against spec §4 and
  AC4–AC6, plus: callout rhythm, table legibility, chip baseline alignment in
  cells, capability glyph contrast in greyscale, diff band continuity across
  the page break, figure proportion.
- [ ] File each defect against the owning lane's files; the owning lane (or
  the reviewer, for one-line token changes) fixes it. At most two review
  rounds before escalating to the user.
- [ ] Record the review with `reportkit review`, then run
  `visual_qa_operator.py --update-expected` and commit the reviewed baseline.
- [ ] If the reviewer cannot view rendered pages, the review is reported as
  **not performed**, and `operator` stays experimental with that noted in
  TODOS.

## 9. Acceptance criteria → owner

| AC | Owner | Verified in |
| --- | --- | --- |
| AC1 compiles clean | Lane E (tooling), Wave 2 (run) | `visual_qa_operator.py` |
| AC2 zero overfull / headheight warnings | Lane O (furniture), Lanes I/X (widths), Wave 2 | fixture log |
| AC3 font regions | Lane O (`\RKTokTableFont`), Lane E (check) | pdfplumber check |
| AC4 terminal contrast | Lane X (implementation + unit render), Lane E (fixture check) | pixel sampling |
| AC5 Fig 3 labels | Lane F | artist extents test |
| AC6 Fig 5 encoding | Lane F | artist extents test + Wave 3 |
| AC7 no regressions | Wave 0 (hooks), Lane T (tokens), Wave 2 (matrix) | before/after renders |
| AC8 theme contract | Lane O, Lane T | `test_theme_contract.py`, `check-theme` |
| AC9 Markdown parity | Lane R | golden TeX tests |
| AC10 loud misuse errors | Lane I | compile-failure tests |
| AC11 breakable blocks | Lane X | long-diff test |
| AC12 recorded visual review | Wave 3 | `reportkit review` record |

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| The core hooks change existing output (for example `\AtBeginEnvironment` interacting with `longtable` or a theme's table code). | No-op defaults, and AC7 evidence is a Wave 0 exit criterion. |
| `capabilitygrid` header construction breaks inside alignment (the classic `&`-in-loop problem). | Lane I builds the whole header row into a token register before the tabular opens; covered by a 12-column test. |
| Line macros cannot preserve arbitrary spacing without catcode changes. | Leading spaces become `~` in the renderer; interior runs of spaces are collapsed and documented. Anything needing exact whitespace uses `codeblock`. |
| Latin Modern is unavailable to Matplotlib, so chart and body type differ. | Lane O declares a resolvable fallback in the Python stack; `check-theme` reports the resolved family; the difference is noted in the guide if it remains. |
| Use-time token gates let a theme that lacks the tokens compile until a primitive is used. | Lane T populates every paged theme; the contract test requires the tokens for every canonical paged theme. |
| D9 exception sets a precedent for more pdfLaTeX themes. | The exception and its narrow justification (bundled Latin Modern, author requirement) are recorded in the registry comment and spec O2. |

## 11. Agent brief template

Each Wave 1 agent receives exactly this, filled in from §4:

```text
Lane <X> — <name>
Branch: operator/<x>-<slug> (worktree off post-Wave-0 main)
Read first: spec §<sections>, this plan §2 and §4 Lane <X>, AGENTS.md
You own: <files>. Do not edit any other file; ask the coordinator.
Frozen API: <signatures / tokens copied from the spec>
Pitfalls: <the spec §8 items relevant to this lane>
Done when: <the lane's checkboxes>, ruff and pytest green, compiled smoke test
green in the pinned image, log summary pasted into the PR.
Report honestly: if you could not compile or render, say so in the PR.
```
