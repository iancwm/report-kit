# PDF accessibility tagging spike

## Decision: no-go for this release

The time-boxed LuaLaTeX spike was run on 2026-09-06 with the ReportKit
state-machine primitive and a `tcolorbox` callout:

```text
TEXINPUTS=latex_templates: lualatex -file-line-error -interaction=nonstopmode \
  -halt-on-error reportkit-tagging-spike.tex
```

The installed TinyTeX/LaTeX format stopped before document-class loading:

```text
LaTeX Error: No support files for \DocumentMetadata found.
```

Because the format cannot enter the tagging test phase, this checkout cannot
produce meaningful tagged-PDF or reading-order evidence. Tagged structure is
therefore a known limitation of this release and is not a release gate.

The hard accessibility requirements that do ship are PDF metadata, language,
bookmarks, meaningful link text, and diagram `description=` alternatives. The
diagram alternative currently uses a PDF `/ActualText` marked-content span;
that intentionally replaces extraction of labels inside the figure. A future
tagging spike should be rerun after upgrading the TeX format and should verify
both tagged structure and preservation of inner diagram text before replacing
that fallback.
