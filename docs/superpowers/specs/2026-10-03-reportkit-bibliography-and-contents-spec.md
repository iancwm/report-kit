# BibTeX bibliography and themed contents pages

**Status:** Approved design · implementation not started · 3 October 2026
**Scope:** Reusable ReportKit engine (TeX packages, build pipeline, validation, context contracts, docs). Consumer `.bib` files and manuscripts stay in consumer projects.

## Problem and evidence

- No ReportKit path reads a `.bib` file. Each publication type hand-writes its own reference list: `bookreferences` (a `thebibliography` wrapper), `featurereferences` (an `\item` list), `briefsources` (an `\item` list) and `referenceslide` (at most eight `\referenceitem`s, then a hard `PRESENTATION_REFERENCES_OVERFLOW` error). `equity-research` has no reference list.
- `publication_build.py::_compile_tex_passes` runs exactly two TeX passes and no bibliography tool. Markdown is converted with `pandoc -f markdown-raw_tex` and no `--natbib`/`--citeproc`, so `[@key]` is not a citation.
- `diagnostics.py` already defines `undefined_citation` and `bibliography_warning`; `reportkit_doctor.py` already probes `bibtex`/`biber`.
- Contents pages exist only in `reportkit-longform.sty` (`\RKContents`, used by `technical-report` and `book`) and the label-only `\RKCompactContents`. Feature articles, executive briefs, equity research and presentations have no contents/agenda primitive.
- Toolchain: `bibtex` and `natbib` (`plainnat`, `unsrtnat`) are present on the local TinyTeX host and in the pinned image (`texlive-latex-extra`, `texlive-bibtex-extra`). `biber` is in neither; `biblatex` is absent locally. A BibTeX + natbib design therefore needs no toolchain, lock or image change.

## Decisions

| ID | Decision |
| --- | --- |
| B1 | Use classic BibTeX + `natbib`. biblatex/biber and CSL/citeproc are out of scope. |
| B2 | Two citation styles: `numeric` (`unsrtnat`, `natbib` `numbers,sort&compress`) and `author-year` (`plainnat`, `natbib` `authoryear,round`). Named styles (APA, Chicago, IEEE) are out of scope. |
| B3 | Each publication type declares a default style; `publication.yaml` may override it. |
| B4 | One authoring entry point per feature (`\RKBibliography`, `\RKContents`); the layout is a per-publication-type *skin* built from theme tokens only. |
| B5 | Existing manual environments (`bookreferences`, `featurereferences`, `briefsources`, `referenceslide`/`\referenceitem`) remain supported as the no-`.bib` path. No breaking change. |
| B6 | Documents without a configured bibliography keep today's two-pass build exactly; existing baselines must not change. |

## 1. Configuration

New optional `bibliography` section in `publication.yaml`, accepted by `config.py` (`_known_for`/`_validate_and_normalize`) and profile-overridable like other sections:

```yaml
bibliography:
  file: references.bib          # required when the section is present; relative to source root
  style: numeric                # optional: numeric | author-year; default from the publication type
  title: References             # optional heading; default from the publication type
  include_uncited: false        # optional; true emits \nocite{*}
```

`resolve_bibliography(config, profile)` returns the normalized record or `None`. Per-type defaults live in `PUBLICATION_TYPES` (new keys `bibliography_style`, `bibliography_title`, `contents_title`):

| Type | `bibliography_style` | `bibliography_title` | `contents_title` |
| --- | --- | --- | --- |
| technical-report | numeric | References | Contents |
| book | author-year | References | Contents |
| feature-article | author-year | References | In this issue |
| executive-brief | numeric | Sources | Contents |
| equity-research | author-year | Sources | In this report |
| presentation | numeric | References | Agenda |

## 2. TeX packages

### 2.1 `reportkit-bibliography.sty` (new, engine-wide)

Loaded by `reportkit.cls` and `reportkit-slides.cls` after the publication-type package. Publication-type packages define their skin hooks with `\newcommand`; this package supplies the neutral defaults with `\providecommand`, so a type's skin always wins and a type without one gets the default.

- Reads `\RKBibStyle` (`numeric`/`author-year`), `\RKBibFile`, `\RKBibTitle`, `\RKBibIncludeUncited` from generated `reportkit-options.tex`. Defaults when absent: `numeric`, no file, `References`, false.
- Loads `natbib` with the options in B2. Under `author-year`, `\cite` behaves as `\citet`.
- `\RKBibliography[title]`: errors with `RK_BIBLIOGRAPHY_UNCONFIGURED` if no file is configured; otherwise sets `\bibliographystyle`, applies `\nocite{*}` if requested, and calls `\bibliography{\RKBibFile}` with `thebibliography` routed through the skin hooks below.
- Skin hooks, each with a neutral default (an unnumbered sans `\section*` listed in the contents, hanging-indent list in the body size, `Ink` text):
  - `\RKBibSkinBegin{title}` / `\RKBibSkinEnd` — wrap the whole list.
  - `\RKBibSkinItemFont` — font/colour applied to entries.
  - `\RKBibSkinPerFrame` — entries per frame (slides only; `0` means unpaginated).
- Implementation: redefine natbib's `thebibliography` (via `\renewenvironment` after `natbib` loads) so it calls the skin hooks instead of `\section*{\refname}`; keep `\bibitem`, `\NAT@` label handling and hanging indent intact.
- Contract blocks: `\RKBibliography` (command), plus documentation of `\citep`, `\citet`, `\citealp` as allowed primitives for every target.

### 2.2 `\RKContents` dispatcher

Move the generic `\RKContents` from `reportkit-longform.sty` into a small shared definition that calls `\RKContentsSkin[title]`. The longform package defines `\RKContentsSkin` with exactly today's body (clear page, PDF bookmark, sans `\tableofcontents`, clear page), so `technical-report` and `book` output is unchanged. `\RKCompactContents` is unchanged.

### 2.3 Per-type skins

Every skin uses only existing theme tokens (no literal `\fontsize`/`\definecolor`), matching each publication package's "structure, not style" rule.

| Type (package) | References skin | Contents skin |
| --- | --- | --- |
| technical-report (longform) | Default skin: unnumbered `References` section, TOC-listed | Existing `\RKContents` page (unchanged) |
| book (`reportkit-book.sty`) | Reuse the `bookreferences` chapter opener (unnumbered, TOC-listed) around the generated list | Existing page; parts and appendices already listed |
| feature-article | `featurereferences` look: one-column, `outside_columns`, feature source size | Inline “In this issue” strip built from the `.toc` (section titles + page numbers), no page break; first pass prints nothing rather than erroring |
| executive-brief | `briefsources` look: compact, `\rksourcesize`, `Muted` | One-line compact contents under the masthead; **only when `\RKContents` is called** (no automatic insertion) |
| equity-research | `Sources` section in exhibit/source type, placed before disclosures | “In this report” list with page numbers, for use inside the sidebar |
| presentation | `referenceslide` look; automatic pagination at `\RKBibSkinPerFrame=8` with a “(cont.)” title on continuation frames | New `agendaslide` composition listing sections registered by `sectiondivider`; optional `[current=<n>]` highlights one entry |

Presentation note: `\RKBibliography` in slides is a frame-producing command used **outside** any `frame`. It typesets the list into a box and splits it into frames of at most eight entries. The manual `referenceslide` keeps its eight-item hard error.

## 3. Markdown authoring

- When a bibliography is configured, `run_pandoc` adds `--natbib`, so `[@key]` → `\citep{key}` and `@key` → `\citet{key}`. Without a bibliography, the pandoc command is unchanged.
- A new safe directive `::: references` (optional `title:`) emits `\RKBibliography[...]`. If a manuscript cites keys and contains no `references` directive, the renderer appends `\RKBibliography` after the last segment and records `bibliography.auto_placed: true` in the build report.
- A new safe directive `::: contents` (optional `title:`) emits `\RKContents[...]`; for `presentation` it emits an `agendaslide` frame.
- Directives are registered in `markdown_directives.py` with the same validation as existing directives; raw TeX remains disabled.

## 4. Build pipeline

In `publication_build.py`:

1. Stage the configured `.bib` file into the output directory (same containment checks as other staged sources). Write `\RKBibStyle`, `\RKBibFile`, `\RKBibTitle`, `\RKBibIncludeUncited` into the generated options.
2. In `_compile_tex_passes`, after pass 1, run `bibtex <jobname>` **only if** a bibliography is configured **and** the pass-1 `.aux` contains `\citation` or `\bibdata`. Then run two more TeX passes (three total). Otherwise run today's second pass only.
3. `bibtex` runs through `run_limited` with the same timeout, memory limit and env as TeX (`openout_any=p`, `LC_ALL=C`, `SOURCE_DATE_EPOCH=1`, `TZ=UTC`), `cwd=output`, and `BIBINPUTS`/`BSTINPUTS` restricted to the output directory plus the TeX tree default.
4. Failures: missing `bibtex` → `RK_BIBTEX_MISSING` (exit 5, environment); non-zero bibtex exit → `RK_BIBTEX_FAILURE` (exit 4) with `.blg` diagnostics; timeout → `RK_COMPILE_TIMEOUT`.
5. Build report (and `schemas/reportkit-build-report.schema.json`) gains:
   ```json
   "bibliography": {"file": "references.bib", "style": "numeric", "entries_cited": 12,
                    "bibtex_exit": 0, "auto_placed": false}
   ```
   `bibliography` is `null` when not configured. The bibtex command is appended to `commands` and `exit_codes`.

The container path needs no change: `container_build.py` invokes the same build script and the pinned image already contains `bibtex` and `natbib`.

## 5. Validation and diagnostics

`reportkit check` (before any TeX run):

| Code | Severity | Condition |
| --- | --- | --- |
| `RK_BIBLIOGRAPHY_FILE_MISSING` | error | `bibliography.file` absent or outside the source root |
| `RK_BIBLIOGRAPHY_STYLE_INVALID` | error | `style` not `numeric`/`author-year` |
| `RK_BIBLIOGRAPHY_DUPLICATE_KEY` | error | Same entry key twice in the `.bib` |
| `RK_CITATION_UNDEFINED` | error | A cited key (Markdown `[@key]`/`@key`, TeX `\cite*{...}`) is not in the `.bib` |
| `RK_CITATION_WITHOUT_BIBLIOGRAPHY` | error | Citations present but no `bibliography` section configured |
| `RK_BIBLIOGRAPHY_NOT_PLACED` | warning | TeX source cites keys but never calls `\RKBibliography` (Markdown auto-places instead) |

The `.bib` key scan is a regex over `@type{key,` headers (comments and `@string`/`@preamble`/`@comment` ignored); no new Python dependency. Markdown key extraction ignores code spans/blocks and e-mail addresses.

After the build: parse `<jobname>.blg` for `Warning--` and `I couldn't open` lines into the existing `bibliography_warning` kind; natbib's `Citation ... undefined` on the final pass maps to the existing `undefined_citation` kind. `reportkit doctor --require full-build` reports `bibtex` as required (not a NOTE) when the project configures a bibliography.

## 6. Context, docs and skill

- `reportkit context --slice primitives` lists `\RKBibliography`, `\citep`/`\citet`/`\citealp`, `\RKContents` and (presentation) `agendaslide` for every target, via contract blocks; regenerate reference docs with `reportkit docs`.
- `SKILL.md` “Write for the decision”: replace “put full citations in the publication’s source section” with the `.bib` workflow and the rule *never invent bibliography entries*; one row in the References table pointing to a new `references/bibliography-and-contents.md`.
- Each per-type authoring guide (book, feature, brief, presentation, institutional-research, technical) gets a short “References and contents” subsection naming its default style and skin, and marks the manual environment as the fallback.
- `TODOS.md` gains this spec in the outstanding table.

## 7. Testing

Static/unit (no TeX):

- `config.py`: section accepted, defaults per type, override, invalid style, profile override.
- `.bib` key scanner: normal entries, `@string`/`@comment` ignored, duplicate key detected, case handling.
- Citation extraction: Markdown `[@a; @b]`, `@a`, code spans ignored, e-mail ignored; TeX `\citep[p.~3]{a,b}`, `\citet*{a}`.
- `check` diagnostics table in §5, one test per code.
- Pandoc command: `--natbib` present only when configured.
- Directive rendering for `references`/`contents`, including auto-placement.
- Build-report schema validates with and without `bibliography`.
- `_compile_tex_passes` sequencing with a fake runner: unconfigured → 2 TeX calls, no bibtex; configured with citations → TeX, bibtex, TeX, TeX; configured without citations → 2 TeX calls; bibtex missing/failing/timeout → the codes in §4.

Compile tests (marked like existing TeX-dependent tests; skipped when the engine is unavailable):

- One minimal fixture per publication type × default theme, each with a 3-entry `.bib`, one `\citep`, one `\citet`, `\RKContents` and `\RKBibliography`: assert zero errors, no `undefined_citation`, and that extracted PDF text contains the skin's title, every cited entry's title, and correctly formatted labels for its style (`[1]` vs `(Author, 2024)`).
- Presentation: a 10-entry `.bib` with `include_uncited: true` produces two reference frames (8 + 2) with the “(cont.)” title; `agendaslide` lists every `sectiondivider` title.
- Regression: existing technical-report and book fixtures without a bibliography produce the same pass count and an unchanged `\RKContents` page (existing tests and baselines continue to pass).
- Markdown end-to-end: one Markdown fixture with `[@key]` builds and lists the entry.

Visual: render page images for each new fixture and record a human review in the build report. Pinned-baseline promotion follows the existing per-format visual-review process and is not a condition of this spec.

## Acceptance criteria

| ID | Criterion |
| --- | --- |
| AC1 | A consumer project with `bibliography.file` and `\citep` builds a PDF on both local pdfLaTeX/LuaLaTeX hosts and in the pinned container, with no new toolchain package. |
| AC2 | All six publication types render references and contents through their skins, using only theme tokens (enforced by the existing theme/composition audits). |
| AC3 | `numeric` and `author-year` produce their documented label formats; the per-type default applies when `style` is omitted. |
| AC4 | Unknown keys, duplicate keys, missing files and citations without configuration fail in `reportkit check` with the §5 codes. |
| AC5 | Documents without a bibliography keep the two-pass build; all pre-existing tests and visual baselines pass unchanged. |
| AC6 | Presentation references paginate automatically at eight entries per frame. |
| AC7 | Markdown `[@key]` citations work and the reference list is placed automatically when no `references` directive is given. |
| AC8 | `build-report.json` records the bibliography block; the schema validates. |

## Out of scope

biblatex/biber, CSL/citeproc, named academic styles, per-chapter bibliographies, footnote citation styles, multiple `.bib` files (a later list form of `file` can extend this), and automatic insertion of contents pages.
