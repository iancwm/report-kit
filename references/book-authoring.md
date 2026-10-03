# Book authoring

> Scope: `book` structure × `default`, `technical`, or `editorial` look. TeX and Markdown are supported. Default and technical use pdfLaTeX; editorial uses LuaLaTeX.

Use this type for a multi-chapter handbook, guide, or book. The structure provides front matter, chapters, parts, appendices, references, and a glossary. The [canonical example](../latex_templates/examples/book/) shows the complete flow under the supported themes.

For Markdown source, each top-level heading starts a numbered chapter after the title, publication details, and contents pages. TeX source uses the book-specific semantic roles shown in the target-scoped context. Keep chapter depth and front matter clear; the type does not add print production, recto/verso handling, or an index.

The book's structure is independent of its look. Select a supported theme explicitly and let `reportkit build` choose its engine. Use the canonical [`composition-brief.json`](../latex_templates/examples/book/composition-brief.json) as a reference, adapt it to the publication, then run `reportkit check --source-root <project> --json` and review rendered pages for chapter openings, contents, appendices, references, and page breaks.

## References and contents

Books default to author-year citations with a References list and the
longform Contents page: declare `bibliography.file` in `publication.yaml`,
cite with `\citep`/`\citet` or `[@key]`, and place `\RKBibliography` and
`\RKContents` where they belong. The generated list reuses the
`bookreferences` chapter opener and type. A book with no `bibliography`
section keeps compiling identically; without a `.bib` file, use the manual
`bookreferences` environment instead. See [bibliography and
contents](bibliography-and-contents.md).
