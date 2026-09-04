# LinBiolinum_K.otf stub

`libertinus-otf.sty` unconditionally tries to load `LinBiolinum_K.otf` (an unrelated
decorative companion font) whenever `libertinus.sty` is present, but Debian's TeX
Live does not ship that specific file — this is an upstream packaging gap, not
something specific to the main font bundle here.

This only matters when compiling with **lualatex** (for Unicode content such as
Vietnamese). It is never an issue under pdflatex. If you hit a
"fontspec Error: The font LinBiolinum_K cannot be found" error, install the included
stub (`LinBiolinum_K.otf` in this folder — it's just a renamed copy of
LibertinusSerif-Regular.otf; ReportKit content never actually invokes the
`\BiolinumKeyboard` command this satisfies, so its visual appearance is irrelevant):

```bash
mkdir -p /usr/local/share/texmf/fonts/opentype/public/libertine-stub
cp LinBiolinum_K.otf /usr/local/share/texmf/fonts/opentype/public/libertine-stub/
mktexlsr /usr/local/share/texmf
```

