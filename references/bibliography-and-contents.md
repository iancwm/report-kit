# Bibliography and contents

Any publication that cites external sources keeps them in a consumer `.bib`
file and renders a themed reference list plus a contents element. Never invent
a bibliography entry: every cited key must exist in the `.bib` file, and
`reportkit check` fails the build on undefined keys.

## Configure

Add a `bibliography` section to `publication.yaml`:

```yaml
bibliography:
  file: references.bib          # required when the section is present; relative to source root
  style: numeric                # optional: numeric | author-year; default from the publication type
  title: References             # optional heading; default from the publication type
  include_uncited: false        # optional; true emits \nocite{*} (lists every entry)
```

The `.bib` path must stay inside the project (letters, digits, `_`, `-`,
`.`, `/`; subdirectories such as `refs/main.bib` work). Per-type defaults:

| Publication type | Style | References title | Contents title |
| --- | --- | --- | --- |
| technical-report | numeric | References | Contents |
| book | author-year | References | Contents |
| feature-article | author-year | References | In this issue |
| executive-brief | numeric | Sources | Contents |
| equity-research | author-year | Sources | In this report |
| presentation | numeric | References | Agenda |

Documents without a `bibliography` section compile exactly as before: natbib
is never loaded and the build keeps its two TeX passes.

## Cite

TeX sources use natbib: `\citep{key}` (parenthetical), `\citet{key}`
(textual), `\citep[p.~3]{key}`, `\citealp{key}`. Markdown sources use Pandoc
citations (the build passes `--natbib` only when a bibliography is
configured): `[@key]`, `@key`, `[@a; @b, p. 3]`, `[-@key]`. E-mail addresses
and `@` inside code spans or fenced code blocks are never treated as
citations.

## Place the list

Call `\RKBibliography` where the reference list belongs, usually at the end
of the document; `\RKBibliography[Works cited]` overrides the heading.
Markdown authors write a directive fence instead:

````markdown
```reportkit references
title: Works cited
```
````

The `title:` line is optional. When a Markdown manuscript cites keys but
contains no `references` directive, the build appends `\RKBibliography` after
the last segment automatically and records `bibliography.auto_placed: true`
in the build report. A configured bibliography with `\RKBibliography` placed
but zero citations builds fine: the bibtex pass is skipped.

## Contents

`\RKContents` renders the publication type's own contents element, with an
optional heading override (`\RKContents[Contents]`); the Markdown equivalent
is a ```` ```reportkit contents ```` fence. What each type renders:

| Publication type | `\RKContents` renders |
| --- | --- |
| technical-report | Full contents page (the longform page) |
| book | Full contents page (the longform page) |
| feature-article | Inline "In this issue" strip; never breaks the page |
| executive-brief | Compact one-line contents; appears only where called |
| equity-research | "In this report" page-numbered list sized for the sidebar |
| presentation | Agenda frame listing every `sectiondivider` title |

## Presentations

In slides, `\RKBibliography` is used outside any frame: it opens an
`allowframebreaks` frame and breaks after every eighth entry, so long lists
paginate (8 + 2 for ten entries) with a `(cont.)` continuation title instead
of shrinking type. The manual `referenceslide` keeps its eight-item hard
error. For the agenda, wrap the composition in a frame:

```latex
\begin{frame}
\begin{agendaslide}
\end{agendaslide}
\end{frame}
```

`\begin{agendaslide}[Custom title]` overrides the Agenda heading.

## Diagnostics

`reportkit check` reports these before any TeX run; the build adds the last two:

| Code | Severity | Meaning |
| --- | --- | --- |
| `RK_BIBLIOGRAPHY_FILE_MISSING` | error | `bibliography.file` absent, outside the source root, or not found |
| `RK_BIBLIOGRAPHY_STYLE_INVALID` | error | `style` is not `numeric` or `author-year` |
| `RK_BIBLIOGRAPHY_DUPLICATE_KEY` | error | Same entry key twice in the `.bib` |
| `RK_CITATION_UNDEFINED` | error | A cited key is not in the `.bib`; add the entry or fix the key |
| `RK_CITATION_WITHOUT_BIBLIOGRAPHY` | error | Citations present but no `bibliography` section configured |
| `RK_BIBLIOGRAPHY_NOT_PLACED` | warning | TeX sources cite keys but never call `\RKBibliography` |
| `RK_BIBTEX_MISSING` | error (exit 5) | `bibtex` is not installed; `reportkit doctor` checks it for full builds |
| `RK_BIBTEX_FAILURE` | error (exit 4) | bibtex failed; fix the `.bib` syntax reported in the `.blg` log |

## Manual fallback

Sources with no `.bib` file keep using the existing manual environments:
`bookreferences`, `featurereferences`, `briefsources`, `referenceslide` with
`\referenceitem`. They are unchanged and compile without any `bibliography`
section (natbib is not loaded, so plain `\bibitem` entries keep working).
