# Font setup

`reportkit.cls` requires the Libertinus font packages (`libertinus`,
`libertinust1math`), which are not part of a base TeX Live install — they
ship in the `texlive-fonts-extra` package on Debian/Ubuntu, a 1.7GB,
~106,000-file package. Only ~26MB (2,122 files) of that package is ever
used.

## Fast path: the portable bundle (default)

`font_data/reportkit-libertinus-fonts.tar.gz` is that ~26MB subset,
pre-harvested. `shell_scripts/bootstrap.sh` installs it automatically:
extracts the tarball into `TEXMFLOCAL` (a system texmf directory returned
by `kpsewhich -var-value TEXMFLOCAL`) and runs `mktexlsr`.

`TEXMFLOCAL` is used rather than `TEXMFHOME` deliberately: `TEXMFHOME` only
resolves if exported, and environment variables do not persist across
separate tool-call boundaries in a claude.ai code-execution sandbox — every
later call that compiles anything would need the export repeated. A
`TEXMFLOCAL` install is a filesystem change, which does persist across
calls with nothing to remember, and was verified to resolve via plain
`kpsewhich` in a brand-new sandbox call with no export, sourcing, or setup.

## Fallback: apt-get

If no bundle is present, `bootstrap.sh` prints:
```bash
apt-get update && apt-get install -y --no-install-recommends texlive-fonts-extra
```
Run this as a **plain foreground command**, not `nohup ... &` — a
backgrounded process does not survive past the tool call that started it
in this sandbox. If it runs long, it's safe to let the call return and poll
for completion from a later call with a wait loop
(`while ps -p <pid> >/dev/null; do sleep 5; done`); don't assume a
still-running process is stuck.

After a successful apt-get install, consider harvesting a fresh bundle
(the pattern `font_data/reportkit-libertinus-fonts.tar.gz` was built with)
so future sessions skip this cost — but only after checking with the
person, not silently.

## Unicode content (e.g. Vietnamese) — needs lualatex, two extra steps

`pdflatex` with Type1 Libertinus fonts cannot render precomposed Unicode
diacritics outside T1 encoding. For Unicode content, compile with
`lualatex` instead — `libertinus.sty` auto-loads the correct OpenType
fonts under that engine. Two one-time setup gaps, both fixed already in
this repo but needing manual setup per session:

1. **`luaotfload` isn't installed by default.** Without it, `lualatex`
   fails with a cryptic `directlua` error before reaching document
   content. Fix:
   ```bash
   apt-get install -y --no-install-recommends texlive-luatex
   ```
   (~35MB, fast — nothing like the `texlive-fonts-extra` cost above.)

2. **`libertinus-otf.sty` unconditionally requires `LinBiolinum_K.otf`**,
   an unrelated decorative font Debian's TeX Live doesn't actually ship
   (an upstream packaging gap). Fix: install the stub shipped in this repo
   — ReportKit content never invokes the command this font defines, so
   its actual appearance is irrelevant:
   ```bash
   mkdir -p /usr/local/share/texmf/fonts/opentype/public/libertine-stub
   cp font_data/LinBiolinum_K.otf /usr/local/share/texmf/fonts/opentype/public/libertine-stub/
   mktexlsr /usr/local/share/texmf
   ```

`bootstrap.sh` does not yet automate these two lualatex-only steps — do
them manually before compiling Unicode content.
