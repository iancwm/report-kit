# PDF accessibility tagging spike

## Decision: no-go for this release

The time-boxed LuaLaTeX spike was rerun on 2026-09-13 in the pinned
`reportkit:toolchain` image (fingerprint
`6e0fc8ea7889634d3c337eacc4e4f68adb10c2c968e2e7e683f5c24de07408e5`) with the
ReportKit class, a `tcolorbox`-backed callout, and the state-machine grammar:

```text
docker run --rm --entrypoint /bin/bash -v "$PWD:/workspace" -w /workspace \
  reportkit:toolchain -lc 'export TEXINPUTS=/workspace/latex_templates:; \
  lualatex -file-line-error -interaction=nonstopmode -halt-on-error \
  reportkit-tagging-spike.tex'
```

The pinned format now provides `\DocumentMetadata`, but ReportKit fails when
the tagging test phase reaches `\begin{document}`:

```text
Use of \__text_expand_space:w doesn't match its definition.
l.3 \begin{document}
  ==> Fatal error occurred, no output PDF file
```

The format can enter the tagging test phase for a plain article, but this
checkout cannot produce meaningful tagged-PDF or reading-order evidence for a
ReportKit document. Tagged structure is therefore a known limitation of this
release and is not a release gate.

The hard accessibility requirements that do ship are PDF metadata, language,
bookmarks, meaningful link text, and diagram `description=` alternatives. The
diagram alternative currently uses a PDF `/ActualText` marked-content span;
that intentionally replaces extraction of labels inside the figure. A future
tagging spike should be rerun after upgrading the TeX format and should verify
both tagged structure and preservation of inner diagram text before replacing
that fallback.
