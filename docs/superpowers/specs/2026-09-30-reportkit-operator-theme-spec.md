# ReportKit Operator Theme Spec

**Status:** Implementation merged to `main` via PR #79; pinned acceptance and visual release review remain. The theme stays experimental until those gates pass.
**Last updated:** 2026-09-30
**Implementation plan:** [2026-09-30-reportkit-operator-theme-implementation-plan.md](../plans/2026-09-30-reportkit-operator-theme-implementation-plan.md)

This spec restates the author's *Operator Theme — Reusable .sty Primitives
Spec* (Appendix A) and its reference implementation `operator.sty` v5
(Appendix B) as a registered ReportKit theme. The design intent is unchanged:
a tech-industry look that gives every product a visible identity, replaces
monotone D/U letter matrices with a visual encoding, and treats terminal and
diff output as first-class execution surfaces. What changes is *where* each
piece lives, so that it follows the theme/primitive split every other
ReportKit theme obeys.

Where this document and Appendix A disagree, this document wins. §9 lists
every departure and the reason.

---

## 1. Decisions

| ID | Decision | Consequence |
| --- | --- | --- |
| **O1** | **Track B.** `operator` is a registered theme in `publications.py` `THEMES`, not a standalone `themes/operator/operator.sty`. | It loads through `reportkit.cls` like every other theme and inherits the class, core, paged core and semantic modules. |
| **O2** | **pdfLaTeX, Latin Modern.** `required_engine="pdflatex"`, body Latin Modern Roman, sans Latin Modern Sans, mono Latin Modern Mono, all through `lmodern` + `T1`. | A recorded exception to D9 ("new visual themes require LuaLaTeX"). Justification: the author's hard requirement, and Latin Modern ships with every TeX Live, so the D9 font-packaging concern does not arise. `default`/`technical` are the precedent pdfLaTeX themes. |
| **O3** | **Current TeX Live is the target.** The pinned toolchain image (TeX Live 2024) is the gate; TeX Live 2020 compatibility is not tested. | Appendix A's "stock TeXLive 2020" constraint is dropped. |
| **O4** | **The package whitelist is dropped.** `reportkit.cls` already loads `tcolorbox`, `listings`, `fancyvrb`, `xparse`, `etoolbox`, `graphicx`, `hyperref`, `caption`, `titlesec`, `fancyhdr`, `geometry`. | The theme files load only what they add (`lmodern`, `fontenc`). They never reload a package the paged core loads with options (§8, caption option clash). |
| **O5** | **Themes own appearance; primitives own structure (D2/D11).** Primitives are theme-neutral semantic modules that read style tokens. The operator theme populates those tokens. No module branches on `\rk@theme` (`tests/test_theme_contract.py`). | New primitives do **not** carry an `rk` or `operator` prefix and work under every paged theme. |
| **O6** | **No duplicate callouts.** The existing `limitation`, `assumption`, `redflag` and `decisionpoint` environments are restyled by the operator tokens. `rklimitation`/`rkassumption`/`rkredflag`/`rkdecision` are not added. | Callouts stay `breakable` tcolorboxes, which removes Appendix A's TikZ-node page-overflow risk. |
| **O7** | **Line-macro API for execution surfaces.** Terminal and diff bodies are one macro per line (`\termline`, `\diffadd`, …). The Markdown directive renderer emits the same macros, one per source line, through `tex_escape`. | Authors never hand-escape `$`/`_`/`%`/`#`/`&` in Markdown. TeX authors write the same macros the renderer writes. No `\obeylines`, no verbatim catcode tricks, and the block can break across pages. |
| **O8** | **Analytical charts use the Python chart layer.** Figures 3, 5 and 6 are produced by `reportkit_viz` under `apply_theme("operator")`, following `references/charts.md` ("Use Python charts for measured values"). | No TikZ bar-chart code in the theme. Distinct, non-colour encodings (hatch, dash) become chart tokens. |
| **O9** | **Fictional fixture.** The canonical example uses fictional product names and fictional prices. | Consistent with the other canonical fixtures; the example is an engine fixture, not a publication. Real publications live outside the engine checkout (AGENTS.md). |
| **O10** | **Pairing and stability.** `operator` is registered for `technical-report` only, `stability="experimental"`, until its fixture passes pinned-toolchain visual review. | Book and executive-brief pairings are follow-up work (§10). |

---

## 2. Files

| Layer | File | Owns |
| --- | --- | --- |
| Theme common package | `latex_templates/themes/reportkit-theme-operator.sty` | Engine guard, fonts, palette (semantic colour names), renderer-neutral style tokens: callout, metric, diagram, algorithm, table font, identity, execution surface. |
| Theme paged adapter | `latex_templates/themes/reportkit-theme-operator-paged.sty` | `\geometry`, `\headheight`, running furniture, `\titleformat`, `\maketitle`, `\captionsetup`. |
| Python tokens | `python_scripts/reportkit/themes/operator.py` | `THEME: Theme`, palette constants that match the `.sty`, chart encodings, script coverage. |
| Identity primitives | `latex_templates/reportkit-identity.sty` | `\productchip`, `\productavatar`, `\pricepill`, `\statusdot`, `\capdocumented`, `\capunestablished`, `capabilitygrid` + `\capabilityrow`. |
| Execution primitives | `latex_templates/reportkit-execution.sty` | `terminalblock` + `\termline`/`\termprompt`/`\termcomment`; `diffblock` + `\diffadd`/`\diffdel`/`\diffctx`/`\diffhunk`. |
| Canonical fixture | `latex_templates/examples/operator-report/` | `report.tex`, `composition-brief.json`, `figures.py`, `figures/`, `expected/`. |
| Visual QA | `scripts/visual_qa_operator.py` | Compile, inspect, render, and compare the fixture, like `visual_qa_editorial.py`. |
| Theme guide | `references/operator-theme.md` | Authoring guide linked from SKILL.md's format table. |

Appendix A's `themes/operator/operator.sty` and `themes/operator/README.md` are
not created.

---

## 3. Palette and tokens

### 3.1 Colours

The operator palette defines the **semantic colour names** that
`reportkit-boxes.sty`, the diagram modules and the presentation contract
already read. The `rk*` names from Appendix A are not public.

| Appendix A token | Hex | Semantic name(s) in the theme |
| --- | --- | --- |
| `rkBg` | `FCFCF9` | `PageBg` (the adapter applies it with `\pagecolor`; §9 item 11) |
| `rkSurface` | `FFFFFF` | `Surface` |
| `rkSurface2` | `F6F6F5` | `SurfaceAlt` |
| `rkBorder` | `E8E8E3` | `Hairline` |
| `rkBorderStrong` | `111111` | `InkStrong`, `Decision` (frame) |
| `rkText` | `111111` | `Ink` |
| `rkMuted` | `6B6B68` | `Muted`, `Limitation`, `Research` |
| `rkFaint` | `9A9A97` | `Faint` |
| `rkAccent` | `5B5BD6` | `LinkBlue`, `Principle`, `Assumption`, `Accent`, `MetricAccent` |
| `rkAccent2` | `FF4D5A` | `RedFlag` |
| `rkAccent3` | `00C2A8` | `Evidence`, `Tip`, `Verified`, `Deliverable` |
| `rkGrid` | `EAEAE6` | `Grid` |

The paged modules also read `Accent`, `Principle`, `Decision`, `Assumption`,
`RedFlag`, `MetricAccent`, and `Surface`. The operator theme defines those
names as aliases of the semantic colors above: `Accent` aliases `LinkBlue`,
`Principle`/`Assumption`/`MetricAccent` alias `Accent`, `Decision` aliases
`InkStrong`, `RedFlag` aliases `Accent2`, and `Surface` aliases `rkSurface`.
The other callout names (`Research`, `Tip`, `Evidence`, `Limitation`, and
`Deliverable`) are included in the semantic-name column above. The sole
non-theme color name in the paged modules is xcolor's built-in `white`.

Wave 0 of the plan fixes the complete list by reading every colour name the
paged modules reference (`grep -o '\\color{[A-Za-z]*}'` plus tcolorbox
`colframe=`/`colback=` values) so the operator theme defines each one.

### 3.2 Contract additions (core)

All additions are **additive with no-op defaults**, so every existing theme
compiles to byte-identical output without being edited. This is the one
deliberate difference from the sentinel pattern (`\rk@styletokenerror`): these
tokens refine existing primitives, and forcing every theme to populate them
would turn a theme addition into a five-theme edit.

| Token | Default | Read by | Purpose |
| --- | --- | --- | --- |
| `\RKTokCalloutKindOptions{<category>}` | expands to nothing | `rk@callout` in `reportkit-boxes.sty`, appended after the shared keys | Per-kind frame/fill/rule (Appendix A's per-callout `draw=`/`fill=`/`line width=`). |
| `\RKTokTableFont` | empty | paged core, `\AtBeginEnvironment` on `tabular`, `tabular*`, `tabularx`, `longtable` | Sans tables everywhere, including bare `X` and Pandoc `longtable` columns (Appendix A's serif bug). |

New primitives get their **own** token families and a **use-time** gate
(`\RKAssertIdentityTokens`, `\RKAssertExecutionTokens`, run on first use of a
primitive, not at module load). Every canonical paged theme populates them
(the plan's Lane T) so the primitives are available under `default`,
`institutional-research`, `executive` and `editorial` too. Missing tokens fail
loudly naming the theme.

**Identity tokens:** `RKTokIdentityNameFont`, `RKTokIdentityTagFont`,
`RKTokIdentityTagColor`, `RKTokIdentityAvatarFill`, `RKTokIdentityAvatarDraw`,
`RKTokIdentityAvatarSize`, `RKTokIdentityAvatarFont`, `RKTokIdentityPillFill`,
`RKTokIdentityPillDraw`, `RKTokIdentityPillArc`, `RKTokIdentityPillFont`,
`RKTokIdentityDotSize`, `RKTokIdentityStateVerified`, `RKTokIdentityStateFlag`,
`RKTokIdentityStateAccent`, `RKTokIdentityStateNeutral`,
`RKTokCapabilityDocumentedFill`, `RKTokCapabilityUnestablishedDraw`,
`RKTokCapabilityGlyphRadius`, `RKTokCapabilityGlyphRule`,
`RKTokCapabilityHeaderFont`, `RKTokCapabilityRowFont`,
`RKTokCapabilityProductWidth`.

**Execution tokens:** `RKTokTerminalBack`, `RKTokTerminalText`,
`RKTokTerminalTitleColor`, `RKTokTerminalTitleFont`, `RKTokTerminalFont`,
`RKTokTerminalPromptColor`, `RKTokTerminalCommentColor`, `RKTokTerminalArc`,
`RKTokTerminalPad`, `RKTokDiffBack`, `RKTokDiffFrame`, `RKTokDiffFont`,
`RKTokDiffAddColor`, `RKTokDiffAddBack`, `RKTokDiffDelColor`,
`RKTokDiffDelBack`, `RKTokDiffCtxColor`, `RKTokDiffHunkColor`,
`RKTokDiffArc`, `RKTokDiffPad`.

The token names above are the Wave 0 proposal. Wave 0 freezes the final
list in `reportkit-core.sty` and `tests/test_theme_contract.py`; lanes may
not add tokens afterwards without going through the coordinator.

### 3.3 Python chart encodings

`ChartTokens` gains two fields with defaults so existing theme modules keep
constructing:

- `hatches: tuple[str, ...] = ()` — Matplotlib hatch patterns assigned to
  series in order (operator: `("////", "", "....", "xx")`).
- `dashes: tuple[str, ...] = ()` — line styles assigned to series in order
  (operator: `("-", "-", "--", ":")`).

An empty tuple keeps today's behaviour exactly.

---

## 4. Theme appearance (operator)

- **Geometry (paged adapter):** `a4paper, margin=20mm, top=18mm, bottom=20mm`,
  plus `headsep` and `footskip` values chosen so the head and foot clear the
  text block. `\headheight` is set explicitly (≥ 14pt; Wave 1 measures it) so
  fancyhdr emits **no** warning.
- **Running furniture:** left head `\rk@leftheader` uppercase in `Muted` sans
  small; centre foot `\rk@footer` · `\thepage`; head rule `Hairline` 0.4pt.
  No hard-coded "REPORT-KIT / OPERATOR v2" string.
- **Headings:** sans bold; the number is set in `Muted` small sans followed by
  `\enspace\textbar\enspace`, as in Appendix B. `\RKReserveSpace` guards stay
  as in the default adapter.
- **Captions:** `\captionsetup{font=small, labelfont={bf,sf}, textfont={sf,color=Muted}}`
  (not a second `\usepackage{caption}`).
- **Tables:** `\RKTokTableFont` = `\sffamily\small`. `booktabs` rules in `Ink`.
- **Callouts (restyled, §3.2):** rounded 6pt cards, 10pt padding, equal rule on
  all sides (no left-rule-only chrome), uppercase small bold title.
  Per-kind options:

  | Category | Frame | Fill | Rule |
  | --- | --- | --- | --- |
  | `Limitation` | `Hairline` | `SurfaceAlt` | 0.6pt |
  | `Assumption` | `Accent` | `SurfaceAlt` | 0.8pt |
  | `RedFlag` | `RedFlag` | `Surface` | 0.8pt |
  | `Decision` | `InkStrong` | `Surface` | 1pt |
  | others | `Hairline` | `SurfaceAlt` | 0.6pt |

- **Terminal:** `InkStrong` background, **white body text**, title in `Faint`
  (never `black!50` on black, never `white!60`, which xcolor resolves to white).
- **Unestablished capability glyph:** outline in `Faint` or `Muted`, not
  `Hairline` (`E8E8E3` on white is below any usable contrast).

---

## 5. Primitive API

All primitives are registered in the generated primitive contract through
`% <reportkit-contract>` metadata blocks next to their definitions, and in
`primitive_targets.py` `ROLE_TABLE`: native for `technical-report` and `book`,
allowed for `equity-research` and `executive-brief`, unavailable for
`presentation` and `feature-article`.

### 5.1 Product identity (`reportkit-identity.sty`)

| Primitive | Kind | Signature | Replaces (Appendix A) | Notes |
| --- | --- | --- | --- | --- |
| `\productchip` | command | `m m m` — `initial`, `name`, `tag` | `\productchip` | Text only (bold name + tiny muted `[tag]`). Safe in table cells. `initial` is accepted for API symmetry and ignored. |
| `\productavatar` | command | `m m m` | `\productchipFull` | Circle avatar with `initial`, then name and tag. Prose only; raises a package error inside a table cell (the detection method is chosen and tested in Lane I). |
| `\pricepill` | command | `m m` — `price`, `plan` | `\rkPricePill` | Rounded pill; the plan name is muted. |
| `\statusdot` | command | `m` — `state` ∈ `verified`, `flag`, `accent`, `neutral` | `\rkStatusDot{<colour>}` | Semantic state, not a raw colour; unknown states are a package error listing the valid ones. |

### 5.2 Capability grid (`reportkit-identity.sty`)

| Primitive | Kind | Signature | Notes |
| --- | --- | --- | --- |
| `\capdocumented` | command | — | Filled circle (Appendix A `\rkD`). Usable in any table. |
| `\capunestablished` | command | — | Hollow circle (Appendix A `\rkU`). |
| `capabilitygrid` | composition | `O{} m` — options (`score=auto\|none`), comma-separated column headers | Builds a `tabular` (never `tabularx`) whose column count comes from the header list. Rotated headers, product column width from `RKTokCapabilityProductWidth`. |
| `\capabilityrow` | command | `O{} m m` — optional product tag, product name, a string of `D`/`U`/`-` cells | One row. The label is set as `\productchip{}{name}{tag}` (no tag: bold name only). With `score=auto` the score column is the count of `D`. A cell string whose length does not match the header count is a package error naming the row. |

Example:

```latex
\begin{capabilitygrid}{Local,Remote,Plan,MCP,Sub-agents,Worktree,Headless,Permissions,Hooks}
\capabilityrow[first-party]{Atlas CLI}{DDDDUDDDD}
\capabilityrow[open-source]{Beacon}{DUDDUUDUU}
\end{capabilitygrid}
```

This removes Appendix A's hard-coded ten-column header and the hand-typed
`& \rkD & \rkU & … & \textbf{8}` rows, and makes the "no `\end{tabularx}` after
`\end{rkgapgrid}`" rule structurally impossible to break.

### 5.3 Execution surfaces (`reportkit-execution.sty`)

| Primitive | Kind | Signature | Notes |
| --- | --- | --- | --- |
| `terminalblock` | composition | `O{}` — title | Breakable tcolorbox, terminal tokens. Body is line macros only. |
| `\termline` | command | `m` | One output line, preserved spacing, monospace. |
| `\termprompt` | command | `m` | One command line, prefixed with a prompt glyph in `RKTokTerminalPromptColor`. |
| `\termcomment` | command | `m` | One muted line. |
| `diffblock` | composition | `O{}` — title (for example a file path) | Breakable tcolorbox, diff tokens. |
| `\diffadd` | command | `m` | `+` gutter, add colour and background band. |
| `\diffdel` | command | `m` | `−` gutter, delete colour and background band. |
| `\diffctx` | command | `m` | Space gutter, context colour. |
| `\diffhunk` | command | `m` | Hunk header (`@@ … @@`) in hunk colour. |

Each line macro sets one full-width line: an empty argument yields a blank
line of the same height; leading spaces are preserved (Wave 1 uses
`\obeyspaces`-free handling: the renderer converts leading spaces to `~`, and
TeX authors use `\ ` or `~`). Long lines wrap with a hanging indent under the
gutter rather than overflowing.

TeX form:

```latex
\begin{terminalblock}[Metered credits vs direct API]
\termcomment{invoice = F + max(0, N*c - A)}
\termprompt{atlas cost --attempts 80}
\termline{Total: \$212.40 (credit cap reached at attempt 64)}
\end{terminalblock}

\begin{diffblock}[src/auth/session.ts]
\diffhunk{@@ -12,3 +12,3 @@}
\diffdel{const token = req.headers['x-token'];}
\diffadd{const token = verifyJWT(req.headers.authorization);}
\diffctx{if (!token) return deny(res);}
\end{diffblock}
```

Markdown form. The body uses the directive dialect's existing `content: |`
multiline value, because the dialect's ordinary body parsing treats `#` lines
as comments, `key: value` lines (such as `Total: $212.40`) as arguments and
drops blank lines. Inside `content: |` every line is kept verbatim after the
two-space block indent is removed. The renderer emits exactly the TeX above,
escaping each line with `reportkit.latex.tex_escape`:

````markdown
```reportkit terminalblock
title: Metered credits vs direct API
content: |
  # invoice = F + max(0, N*c - A)
  $ atlas cost --attempts 80
  Total: $212.40 (credit cap reached at attempt 64)
```

```reportkit diffblock
title: src/auth/session.ts
content: |
  @@ -12,3 +12,3 @@
  - const token = req.headers['x-token'];
  + const token = verifyJWT(req.headers.authorization);
    if (!token) return deny(res);
```

```reportkit capabilitygrid
columns: Local,Remote,Plan,MCP,Sub-agents,Worktree,Headless,Permissions,Hooks
content: |
  Atlas CLI | first-party | DDDDUDDDD
  Beacon | open-source | DUDDUUDUU
```
````

Line classification is declared in each primitive's contract metadata as a
`line_macros` constraint and is implemented once, generically, in
`tex_renderer.py`:

```json
{"code":"line_macros","prefixes":[["$ ","termprompt"],["# ","termcomment"]],"default":"termline"}
{"code":"line_macros","prefixes":[["@@","diffhunk"],["+","diffadd"],["-","diffdel"]],"preserve_prefixes":["@@"],"default":"diffctx"}
{"code":"line_macros","split":"|","macro":"capabilityrow"}
```

For `prefixes`, entries are ordered pairs of literal prefix and macro name;
the first matching prefix wins, its text is removed, and `default` handles
unmatched lines. Multi-character prefixes such as `@@` precede their
single-character alternatives. For `split`, the renderer splits each line
on the literal separator and accepts either `name|cells` or
`name|tag|cells`, emitting `\capabilityrow{}{name}{cells}` or
`\capabilityrow[tag]{name}{cells}` respectively. In both forms, leading
spaces remaining after the prefix or separator handling become `~` before
the rest of the payload is passed through `tex_escape`.

| Primitive | Prefix → macro |
| --- | --- |
| `terminalblock` | `$ ` → `\termprompt`, `# ` → `\termcomment`, anything else → `\termline` |
| `diffblock` | `+` → `\diffadd`, `-` → `\diffdel`, `@@` → `\diffhunk`, anything else (including a leading space) → `\diffctx` |
| `capabilitygrid` | each line split on `\|` into name, tag, cells → `\capabilityrow[tag]{name}{cells}` (two fields: name and cells, no tag) |

The matched prefix is stripped before escaping, except prefixes listed in
`preserve_prefixes`; the `@@` diff-hunk marker is retained so the directive
matches the hand-written `\diffhunk{@@ … @@}` form. Leading spaces after a
stripped prefix become `~` so indentation survives.
Two existing parser behaviours must change for these primitives only (plan
Lane R): `_clean_value` strips the whole `content` value, which would drop the
first line's indentation, and `_body` escapes the content as one paragraph.
Primitives without a `line_macros` constraint render exactly as today.

---

## 6. Figures

Figures are fixture content produced by `latex_templates/examples/operator-report/figures.py`
with `reportkit_viz` under `apply_theme("operator")`. Data is fictional (O9).

| Figure | Chart | Encoding requirements (from Appendix A) |
| --- | --- | --- |
| Fig 3 — evidence status | horizontal `bar_chart` | Value labels **outside** the bar end, never inside a small bar; no label clipped by the axes. |
| Fig 5 — cost per attempt | new `stacked_bar_chart` | Review component hatched (`hatches[0]`), inference solid accent on top; y-scale so the largest stack fits with headroom and the smallest inference segment is visibly non-zero. |
| Fig 6 — conditional cost | `line_chart` (numeric x) | Three series with distinct dashes (solid ink, solid muted, dashed accent); a vertical marker and label at the credit-cap kink. |

`stacked_bar_chart` and `line_chart` are new public chart names (added to
`PUBLIC_CHART_NAMES`). If `timeseries` already handles a numeric index
cleanly, Lane F may implement `line_chart` as a thin wrapper over it; the
public name is still reserved in Wave 0.

---

## 7. Acceptance criteria

| ID | Criterion | How it is checked |
| --- | --- | --- |
| **AC1** | The canonical fixture compiles under `reportkit build` with `pdflatex`, two passes, zero errors. | `scripts/visual_qa_operator.py`, pipeline `build-report.json`. |
| **AC2** | Zero `Overfull \hbox`, zero `Overfull \vbox`, zero fancyhdr `\headheight` warnings in the fixture log. | Log parse via `reportkit.diagnostics.inspect_log`; Appendix A's "≤ 2 header overfulls allowed" is withdrawn. |
| **AC3** | Every table glyph is set in Latin Modern Sans; body prose in Latin Modern Roman; terminal/diff in Latin Modern Mono. | Per-character font names inside each table/terminal bounding box (pdfplumber), not document-wide `pdffonts`. |
| **AC4** | Terminal body text is visible: inside every terminal box, text-glyph pixels are light (luminance ≥ 0.8) on a dark background (≤ 0.15). | Render at 140 DPI; sample glyph pixels inside the box region. |
| **AC5** | Fig 3 value labels lie entirely outside their bars and inside the figure bounds. | Chart-level test on the Matplotlib artists' extents. |
| **AC6** | Fig 5: review segment hatched, inference segment solid; the smallest inference segment is ≥ 2 mm tall on the page; nothing clipped. | Chart-level test plus visual review. |
| **AC7** | Every existing theme × publication-type pair renders **pixel-identical** pages after the core additions (§3.2). | Before/after page renders of every canonical fixture (Lane C records the evidence), plus `scripts/acceptance_check.sh`'s existing pixel-diff baselines. |
| **AC8** | `operator` passes the theme contract (all sentinel tokens populated, Python theme complete, palette in sync). | `tests/test_theme_contract.py`, `reportkit_viz check-theme --theme operator`. |
| **AC9** | Markdown `terminalblock`/`diffblock` directives render to the same TeX as the hand-written form, including `$`, `_`, `%`, `#`, `&`, `\`, `{`, `}` in content. | Renderer unit test with golden output. |
| **AC10** | `capabilitygrid` rejects a row whose cell count does not match the header count, and `\statusdot` rejects an unknown state, each with a package error naming the problem. | Compile-failure tests, as in `test_editorial_theme.py::test_rhythm_misuse_fails_loudly`. |
| **AC11** | A `terminalblock` or `diffblock` longer than one page breaks across pages without overflow. | Fixture page with a long diff. |
| **AC12** | Visual review of every fixture page is recorded with `reportkit review`; if it could not be performed, that is stated, never claimed. | Review record in the PR. |

---

## 8. Audit of the reference implementation (Appendix B)

Each defect below is fixed by design in §§3–5; the plan's lanes carry
regression tests for the ones marked **(test)**.

1. **Terminal text is still black on black (test).** The v5 `rkterminal`
   never sets the body colour: `\ttfamily\footnotesize` follows the title
   group with no `\color{white}`, so the body inherits black and sits on the
   `rkBorderStrong` (#111111) background. This is the v2 bug that Appendix A
   says was fixed. The lrbox is not the cause; the missing colour is.
2. **Terminal title is `black!50` on black** (≈ #888 on #111): legible but
   low contrast, and the wrong token. Use `Faint`.
3. **`ragged2e` is required** (`\RaggedRight`, `\RaggedLeft`, `\Centering`)
   although Appendix A forbids it. Irrelevant under O4, but a sign the
   whitelist was never enforced.
4. **`\usepackage[...]{caption}` inside a package**, after `reportkit-paged-core.sty`
   has already loaded `caption` without options: under Track B this is an
   option clash. Use `\captionsetup`.
5. **Packages the paged core owns are re-required** (`geometry`, `fancyhdr`,
   `titlesec`). Harmless without options, but the adapter should configure,
   not load.
6. **`\headheight` is never set**, so fancyhdr warns on every page; Appendix A
   budgets this as "header overfulls allowed". Set it.
7. **Hard-coded running strings** ("REPORT-KIT / OPERATOR v2", "Operator v2").
8. **`rkgapgrid` hard-codes ten columns and their headers**, so it cannot be
   reused for any other capability set; scores are typed by hand.
9. **`\rkU` draws in `rkBorder` (#E8E8E3) on white**: nearly invisible.
10. **Callouts are TikZ nodes**: they cannot break across pages and silently
    overflow the page bottom. The `\bgroup…\egroup` node-content trick works
    but blocks any verbatim or `\par`-sensitive content.
11. **`rkBg` is defined but never applied.**
12. **`rkdiff` sets lines with `\obeylines` and no `+`/`−` treatment**, so a
    diff renders as plain monospace text; `$`, `_`, `%`, `#`, `&` in content
    still break it.
13. **Column type `M` (tt scriptsize) and the `L/R/C` types are global
    single-letter column types**, which can collide with user preambles. §3.2's
    `\RKTokTableFont` hook fixes the serif-column bug without new column
    types.

## 9. Departures from Appendix A

| # | Appendix A | This spec | Reason |
| --- | --- | --- | --- |
| 1 | `themes/operator/operator.sty` standalone | Theme common package + paged adapter | O1 |
| 2 | pdflatex on TeX Live 2020 | pdflatex on the pinned current TeX Live | O3 |
| 3 | Allowed-packages list | Dropped | O4 |
| 4 | `rklimitation`/`rkassumption`/`rkredflag`/`rkdecision` | Existing callouts restyled | O6 |
| 5 | `L`/`R`/`C` column types | `\RKTokTableFont` on every table environment | §8 item 13 |
| 6 | `\productchipFull`, `\rkPricePill`, `\rkStatusDot{<colour>}` | `\productavatar`, `\pricepill`, `\statusdot{<state>}` | Repo naming; semantic states instead of raw colours |
| 7 | `\rkD`/`\rkU`, `rkgapgrid` with typed rows | `\capdocumented`/`\capunestablished`, `capabilitygrid` + `\capabilityrow` | §8 item 8 |
| 8 | `rkterminal`/`rkdiff` with raw content | `terminalblock`/`diffblock` with line macros | O7 |
| 9 | TikZ `patterns` charts | `reportkit_viz` charts with hatch/dash tokens | O8 |
| 10 | "≤ 2 overfull 17pt (header only)" | Zero overfulls, zero headheight warnings | §8 item 6 |
| 11 | `pdffonts` for mixed fonts | Per-region glyph font check | `pdffonts` is document-wide |
| 12 | `grep Overfull.*tabularx` | Log parse with source line mapping | Overfull messages never name the environment |
| 13 | `\tikzset{rkstep/...}` naming rule | Kept: no new TikZ key may shadow a `/tikz/` key | — |
| 14 | Real product names and prices | Fictional fixture | O9 |

## 10. Out of scope (follow-ups)

- `operator` × `book` and `operator` × `executive-brief` pairings.
- A slides adapter.
- Brand overrides (`brand_overrides` stays `False`).
- Promotion from experimental to stable (needs the pinned visual review
  recorded in `2026-09-25-reportkit-multi-format-visual-review-plan.md`).

---

## Appendix A — Original spec (verbatim)

````markdown
# Operator Theme — Reusable .sty Primitives Spec

**Goal:** A tech-industry PDF theme for Report-Kit that replaces anonymous product lists and monotone D/U matrices with product identity chips, distinct encodings, and execution surface primitives. Must compile on stock TeXLive 2020 with `pdflatex` — no `tcolorbox`, `pgfplots`, `fontspec`, `ragged2e`, `everysel`.

## File Structure
```
themes/operator/
  operator.sty          # the only required file
  README.md             # usage examples
```

## Design Tokens

```latex
\definecolor{rkBg}{HTML}{FCFCF9}
\definecolor{rkSurface}{HTML}{FFFFFF}
\definecolor{rkSurface2}{HTML}{F6F6F5}
\definecolor{rkBorder}{HTML}{E8E8E3}
\definecolor{rkBorderStrong}{HTML}{111111}
\definecolor{rkText}{HTML}{111111}
\definecolor{rkMuted}{HTML}{6B6B68}
\definecolor{rkFaint}{HTML}{9A9A97}
\definecolor{rkAccent}{HTML}{5B5BD6}   % primary indigo
\definecolor{rkAccent2}{HTML}{FF4D5A}  % red flag
\definecolor{rkAccent3}{HTML}{00C2A8}  % teal verified
\definecolor{rkGrid}{HTML}{EAEAE6}

\newcommand{\rkHeadingFont}{\sffamily\bfseries}
\geometry{a4paper, margin=20mm, top=18mm, bottom=20mm}
```

Typography rule: **Everything in tables is sans**. No serif `X` columns. Use `\sffamily\small` or `\footnotesize` consistently.

## Allowed Packages Only
```latex
\RequirePackage{xcolor}
\RequirePackage{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{tikz}
\RequirePackage{lmodern}
\RequirePackage[T1]{fontenc}
\usetikzlibrary{patterns,positioning}
\usepackage[font=small, labelfont={bf,sf}, textfont={sf, color=rkMuted}]{caption}
```
Do NOT add `tcolorbox`, `pgfplots`, `ifxetex`, `ragged2e`.

## Column Types (Fixes serif bug)

v1 bug: `\begin{tabularx}{\linewidth}{L L X}` -> last column defaults to Computer Modern Roman, causing inconsistent font in Section 3.

Fix: Define L,R,C as sans and never use bare `X`.

```latex
\newcolumntype{L}[1]{>{\raggedright\arraybackslash\sffamily\small}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash\sffamily\small}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash\sffamily\small}p{#1}}

% Usage:
\begin{tabularx}{\linewidth}{L{3.2cm} L{4.2cm} L{7.2cm}}
\toprule
{\tiny\bfseries Product} & {\tiny\bfseries Unit} & {\tiny\bfseries Caveat} \\
\midrule
...
\bottomrule
\end{tabularx}
```

Acceptance: Run `pdflatex` and grep log for `Overfull.*tabularx` should be 0. Only header/footer overfulls (17pt) allowed.

## Primitive 1: Callouts

Purpose: Replace left-border-only callouts with rounded cards.

API:
```latex
\begin{rklimitation} ... \end{rklimitation}
\begin{rkassumption} ... \end{rkassumption}
\begin{rkredflag} ... \end{rkredflag}
\begin{rkdecision} ... \end{rkdecision}
```

Implementation (robust):
```latex
\newenvironment{rklimitation}{%
\par\vspace{8pt}\noindent
\begin{tikzpicture}
\node[draw=rkBorder, fill=rkSurface2, rounded corners=6pt, line width=0.6pt, inner sep=10pt, text width=\dimexpr\linewidth-22pt, align=left] \bgroup
\sffamily\small \textbf{LIMITATION}\par\smallskip
}{\egroup;\end{tikzpicture}\par\vspace{6pt}}
```
- `rkassumption`: `draw=rkAccent`
- `rkredflag`: `draw=rkAccent2, fill=rkSurface`
- `rkdecision`: `draw=rkBorderStrong, line width=1pt`

Use `\dimexpr\linewidth-22pt` not `\linewidth-24pt` inside node to avoid overfull.

## Primitive 2: Product Identity

Purpose: Fix anonymous product names. Every product gets chip.

API:
```latex
\productchip{C}{Codex CLI}{first-party}
\productchipFull{C}{Codex CLI}{first-party} % with circle avatar, use outside tables
\rkPricePill{\$10}{Copilot Pro}
\rkStatusDot{rkAccent3} % 5.5pt circle
```

Implementation - keep simple inside tables to avoid font mismatch:
```latex
\newcommand{\productchip}[3]{%
{\sffamily\bfseries\small #2} {\color{rkMuted}\sffamily\tiny [#3]}%
}
\newcommand{\productchipFull}[3]{%
\begin{tikzpicture}[baseline=-2pt]
\node[circle, fill=rkSurface2, draw=rkBorder, inner sep=0pt, minimum size=14pt, font=\sffamily\bfseries\tiny] {#1};
\end{tikzpicture}\hspace{3pt}{\sffamily\bfseries\small #2}\hspace{4pt}{\sffamily\tiny\color{rkMuted}[#3]}%
}
\newcommand{\rkPricePill}[2]{%
\tikz[baseline=-1pt]\node[fill=rkSurface2, draw=rkBorder, rounded corners=5pt, inner sep=4pt, font=\sffamily\small]{#1\ \color{rkMuted}#2};%
}
\newcommand{\rkStatusDot}[1]{\tikz[baseline=-2.5pt]\node[circle, fill=#1, minimum size=5.5pt, inner sep=0pt]{};}
```
Lesson: v1 used TikZ circles inside tables causing tiny font + overfull. Use simple bold+tiny for tables, full avatar outside.

## Primitive 3: Capability Grid (Fix D/U)

Purpose: Replace 144 identical `D/U` letters with visual encoding.

API:
```latex
\newcommand{\rkD}{\tikz[baseline=-2pt]\fill[rkAccent] (0,0) circle (3.2pt);} % documented
\newcommand{\rkU}{\tikz[baseline=-2pt]\draw[rkBorder, line width=0.6pt] (0,0) circle (3.2pt);} % unestablished

\begin{rkgapgrid}
Codex CLI & \rkD & \rkD & \rkU & ... & \textbf{8} \\
...
\end{rkgapgrid}
```

Implementation — MUST use tabular, not tabularx inside environment (tabularx lookahead breaks):
```latex
\newenvironment{rkgapgrid}{%
\sffamily\footnotesize
\begin{tabular}{L{3.4cm} c c c c c c c c c c}
\toprule
{\sffamily\tiny\bfseries Product} & \rotatebox{90}{\tiny Local} & ... & {\sffamily\tiny\bfseries Score} \\
\midrule
}{\bottomrule\end{tabular}}
```

Do NOT add extra `\end{tabularx}` after `\end{rkgapgrid}` — v1 had that bug.

## Primitive 4: Execution Surface

Purpose: Terminal and diff blocks — first-class execution, not screenshots.

API:
```latex
\begin{rkterminal}[Copilot credits vs direct API]
Invoice = F + max(0, N*c - A)
At 80 attempts...
\end{rkterminal}

\begin{rkdiff}
- const token = req.headers['x-token'];
+ const token = verifyJWT(...)
\end{rkdiff}
```

Implementation — critical bug fix for black-on-black:

v2 bug: Used `\begin{lrbox}{\box}\begin{minipage}...\color{white}...\end{minipage}\end{lrbox}\colorbox{black}{\usebox}` — color lost, white text became black on black invisible.

Fix: Direct `\colorbox` with minipage, no lrbox:

```latex
\newenvironment{rkterminal}[1][]{%
\par\vspace{8pt}\noindent
\colorbox{rkBorderStrong}{%
\begin{minipage}{\dimexpr\linewidth-2\fboxsep-2\fboxrule-6pt}
{\sffamily\small\color{white!60}#1\par\vspace{4pt}}%
\sffamily\footnotesize\color{white}%
}{%
\end{minipage}}%
\par\vspace{8pt}
}
```

- Content must have `$` escaped as `\$` and `_` as `\_` because inside `\ttfamily` `_` still triggers math.
- Do not use `\bgroup\egroup` trick with `$` content — causes `Missing $ inserted`.

## Primitive 5: Charts (Distinct Encodings)

Rules:
- No `pgfplots`. Use only TikZ `patterns`.
- Must have distinct visual encoding, not just color.
- Must be proportionate: define `x` and `y` scales so max fits within 0-20 or 0-300 range.

Fig 5 — Cost per attempt:
```latex
\begin{tikzpicture}[x=1.5cm, y=0.22cm]
\draw[color=rkGrid] (0,0) grid (7,20);
\foreach \i/\label/\inf in {1/Grok 0.1/0.39, ... 6/Astra/5.31} {
  \fill[pattern=north east lines, pattern color=rkMuted] (\x-0.25,0) rectangle (\x+0.25,12.5); % review
  \fill[fill=rkAccent] (\x-0.25,12.5) rectangle (\x+0.25,12.5+\inf); % inference
}
\end{tikzpicture}
```
Review = hatched 12.5, inference = solid on top. Astra 5.31 is 5x others but not blowing out.

Fig 6 — Conditional cost:
- Grid 260x260, not 300, `x=0.045cm, y=0.05cm`
- 3 lines: Direct API (solid black), Pro (solid muted), Pro+ (dashed indigo)
- Add kink line at credit cap with label.

Fig 3 — Evidence status:
- Do NOT put labels inside small bars. Put outside:
```latex
\fill[rkAccent3] (0,0.2) rectangle (10,0.9);
\node[anchor=west] at (10.3,0.55) {10 verified-commercial};
```

## Header/Footer

```latex
\pagestyle{fancy}
\fancyhead[L]{\small\sffamily\color{rkMuted} REPORT-KIT / OPERATOR v2}
\fancyfoot[C]{\small\sffamily\color{rkMuted} Operator v2 \quad \thepage}
\titleformat{\section}{\rkHeadingFont\Large}{\sffamily\small\color{rkMuted}\thesection\enspace\textbar\enspace}{0em}{}
```

## TikZ Key Naming

Bug: `\tikzset{step/.style=...}` conflicts with built-in `/tikz/step`. Use `rkstep`.

## Acceptance Checklist for Coding Agent

1. `pdflatex main.tex` twice — 0 fatal errors, <=2 overfull 17pt (header only)
2. Visual: All tables sans — run `pdffonts` should show `LMRoman` only for body text, `LMSans` for tables, no mixed row
3. Visual: Terminal boxes white text on black, visible in rendered PNG
4. Visual: Fig 3 labels outside bars, not truncated
5. Visual: Fig 5 proportionate, review dominates but Astra inference visible
6. No `\end{tabularx}` after `\end{rkgapgrid}`
7. No bare `X` column in any `tabularx`

## Deliverables

- `themes/operator/operator.sty`
- `themes/operator/README.md` with usage snippet
- Example `main.tex` using all primitives
- Compiled PDF for visual check

## Reference Implementation

See attached `operator.sty` v5 — 120 lines, compiles TeXLive 2020, 8 pages, 314KB.

````

## Appendix B — Reference implementation `operator.sty` v5 (as supplied)

Supplied by the author as a single pasted line; reflowed here to one
statement per line. No token was changed. §8 audits it.

```latex
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{operator}[2026/10/01 Operator v2 fixed]
\RequirePackage{xcolor}
\RequirePackage{geometry}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{booktabs}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{ragged2e}
\RequirePackage{tikz}
\RequirePackage{lmodern}
\RequirePackage[T1]{fontenc}
\usetikzlibrary{patterns,positioning}
\definecolor{rkBg}{HTML}{FCFCF9}
\definecolor{rkSurface}{HTML}{FFFFFF}
\definecolor{rkSurface2}{HTML}{F6F6F5}
\definecolor{rkBorder}{HTML}{E8E8E3}
\definecolor{rkBorderStrong}{HTML}{111111}
\definecolor{rkText}{HTML}{111111}
\definecolor{rkMuted}{HTML}{6B6B68}
\definecolor{rkFaint}{HTML}{9A9A97}
\definecolor{rkAccent}{HTML}{5B5BD6}
\definecolor{rkAccent2}{HTML}{FF4D5A}
\definecolor{rkAccent3}{HTML}{00C2A8}
\definecolor{rkGrid}{HTML}{EAEAE6}
\newcommand{\rkHeadingFont}{\sffamily\bfseries}
\newcommand{\rkMono}{\ttfamily}
\newcommand{\rkBody}{\sffamily}
\geometry{a4paper, margin=20mm, top=18mm, bottom=20mm}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\sffamily\color{rkMuted} REPORT-KIT / OPERATOR v2}
\fancyfoot[C]{\small\sffamily\color{rkMuted} Operator v2 \quad \thepage}
\renewcommand{\headrulewidth}{0.4pt}
\titleformat{\section}{\rkHeadingFont\Large\color{rkText}}{\sffamily\small\color{rkMuted}\thesection\enspace\textbar\enspace}{0em}{}
\titleformat{\subsection}{\rkHeadingFont\large}{\sffamily\small\color{rkMuted}\thesubsection\enspace\textbar\enspace}{0em}{}
\titleformat{\subsubsection}{\rkHeadingFont\normalsize\color{rkText}}{}{0em}{}
% column types with consistent sans
\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash\sffamily\small}p{#1}}
\newcolumntype{R}[1]{>{\RaggedLeft\arraybackslash\sffamily\small}p{#1}}
\newcolumntype{C}[1]{>{\Centering\arraybackslash\sffamily\small}p{#1}}
\newcolumntype{M}[1]{>{\RaggedRight\arraybackslash\ttfamily\scriptsize}p{#1}}
% callouts - more compact, no huge tikz text width issues
\newenvironment{rklimitation}{%
\par\vspace{8pt}\noindent
\begin{tikzpicture}
\node[draw=rkBorder, fill=rkSurface2, rounded corners=6pt, line width=0.6pt, inner sep=10pt, text width=\dimexpr\linewidth-22pt, align=left] \bgroup
\sffamily\small \textbf{LIMITATION}\par\smallskip
}{\egroup;\end{tikzpicture}\par\vspace{6pt}}
\newenvironment{rkassumption}{%
\par\vspace{8pt}\noindent
\begin{tikzpicture}
\node[draw=rkAccent, fill=rkSurface2, rounded corners=6pt, line width=0.8pt, inner sep=10pt, text width=\dimexpr\linewidth-22pt, align=left] \bgroup
\sffamily\small \textbf{ASSUMPTION}\par\smallskip
}{\egroup;\end{tikzpicture}\par\vspace{6pt}}
\newenvironment{rkredflag}{%
\par\vspace{8pt}\noindent
\begin{tikzpicture}
\node[draw=rkAccent2, fill=rkSurface, rounded corners=6pt, line width=0.8pt, inner sep=10pt, text width=\dimexpr\linewidth-22pt, align=left] \bgroup
\sffamily\small \textbf{RED FLAG}\par\smallskip
}{\egroup;\end{tikzpicture}\par\vspace{6pt}}
\newenvironment{rkdecision}{%
\par\vspace{8pt}\noindent
\begin{tikzpicture}
\node[draw=rkBorderStrong, fill=rkSurface, rounded corners=6pt, line width=1pt, inner sep=10pt, text width=\dimexpr\linewidth-22pt, align=left] \bgroup
\sffamily\small \textbf{DECISION POINT}\par\smallskip
}{\egroup;\end{tikzpicture}\par\vspace{6pt}}
\newcommand{\rkStatusDot}[1]{\tikz[baseline=-2.5pt]\node[circle, fill=#1, minimum size=5.5pt, inner sep=0pt]{};}
% simplified product chip - no tikz circles inside table to avoid font mismatch
\newcommand{\productchip}[3]{%
{\sffamily\bfseries\small #2} {\color{rkMuted}\sffamily\tiny [#3]}%
}
\newcommand{\productchipFull}[3]{%
\begin{tikzpicture}[baseline=-2pt]
\node[circle, fill=rkSurface2, draw=rkBorder, inner sep=0pt, minimum size=14pt, font=\sffamily\bfseries\tiny] {#1};
\end{tikzpicture}\hspace{3pt}{\sffamily\bfseries\small #2}\hspace{4pt}{\sffamily\tiny\color{rkMuted}[#3]}%
}
\newcommand{\rkPricePill}[2]{%
\tikz[baseline=-1pt]\node[fill=rkSurface2, draw=rkBorder, rounded corners=5pt, inner sep=4pt, font=\sffamily\small]{#1\ \color{rkMuted}#2};%
}
\newcommand{\rkD}{\tikz[baseline=-2pt]\fill[rkAccent] (0,0) circle (3.2pt);}
\newcommand{\rkU}{\tikz[baseline=-2pt]\draw[rkBorder, line width=0.6pt] (0,0) circle (3.2pt);}
% capability grid with fixed widths, sans only
\newenvironment{rkgapgrid}{%
\sffamily\footnotesize
\begin{tabular}{L{3.4cm} c c c c c c c c c c}
\toprule
{\sffamily\tiny\bfseries Product} & \rotatebox{90}{\tiny Local} & \rotatebox{90}{\tiny Remote} & \rotatebox{90}{\tiny Plan} & \rotatebox{90}{\tiny MCP} & \rotatebox{90}{\tiny Sub} & \rotatebox{90}{\tiny Worktree} & \rotatebox{90}{\tiny Headless} & \rotatebox{90}{\tiny Perms} & \rotatebox{90}{\tiny Hooks} & {\sffamily\tiny\bfseries Score} \\
\midrule
}{\bottomrule\end{tabular}}
\newsavebox{\rktermbox}
\newenvironment{rkterminal}[1][]{%
\par\vspace{8pt}\noindent
\begin{lrbox}{\rktermbox}%
\begin{minipage}{\dimexpr\linewidth-16pt}
{\sffamily\small\color{black!50}#1\par\vspace{3pt}}%
\ttfamily\footnotesize
}{%
\end{minipage}%
\end{lrbox}%
\noindent\colorbox{rkBorderStrong}{\usebox{\rktermbox}}%
\par\vspace{8pt}
}
\newsavebox{\rkdiffbox}
\newenvironment{rkdiff}{%
\par\vspace{6pt}\noindent
\begin{lrbox}{\rkdiffbox}%
\begin{minipage}{\dimexpr\linewidth-16pt}
\ttfamily\footnotesize\obeylines
}{%
\end{minipage}%
\end{lrbox}%
\fcolorbox{rkBorder}{rkSurface}{\usebox{\rkdiffbox}}%
\par\vspace{6pt}
}
\usepackage[font=small, labelfont={bf,sf}, textfont={sf, color=rkMuted}]{caption}
\setlength{\tabcolsep}{6pt}
```
