# ReportKit — Claude execution guide (v2, verified environment)

This supersedes the v1 execution guide. `reportkit.cls`, `reportkit-boxes.sty`, `reportkit-code.sty`, and
`reportkit-diagrams.sty` are now present in the project, and the full pipeline has been **compiled and visually
verified** in this sandbox, not just checked for binaries. The "known gap" in v1 no longer applies — treat FULL
BUILD as the realistic default now, not SOURCE BUILD.

## 0. What changed since v1

- The four missing `.cls`/`.sty` files were uploaded and are now real project files.
- `reportkit_doctor.py` reported `MODE: FULL BUILD` (pdflatex, lualatex, bibtex all present — TeX Live 2023) —
  but that was a **false positive**: pdflatex was present, but the Libertinus fonts `reportkit.cls` requires
  (`\RequirePackage{libertinus}`, `\RequirePackage{libertinust1math}`) were not, and a real compile failed
  immediately. The doctor script has been patched to check for these via `kpsewhich` and downgrade to
  `SOURCE BUILD + FIGURES` when they're missing, with the fix command printed. **Use the patched
  `reportkit_doctor.py`, not the original** — see §2.
- A real compile bug was found and fixed in `reportkit-diagrams.sty` — see §1.
- Font packages are not preinstalled in this sandbox; they must be installed once per session (the sandbox
  filesystem resets between tasks, so this is not a one-time fix). See §2 step 3.

## 1. Fixed defect: `reportkit-diagrams.sty` v1.1.0

**Bug.** Fifteen places in the diagram macros write a decimal coefficient directly against an `\rk@...` length
macro with no operator between them — e.g. `0.25\rk@matrixw`. TeX/pgfmath expands the macro and concatenates
the text (`"0.25"` + `"12.2"` → `"0.2512.2"`), which is not a valid number, so any diagram using a 2×2 matrix
(`\RKMatrixCell`) or a layered architecture (`\RKLayer`) failed to compile with `Illegal unit of measure (pt
inserted)`. Swimlanes and plain node/edge networks were unaffected — they don't use this pattern.

**Verified before fixing:** compiled a matrix diagram and an architecture diagram from `REPORTKIT_API.md`'s own
example syntax; both failed with this error on first `pdflatex` pass.

**Fix applied (now in the project file):**
- Inserted an explicit `*` multiplication operator at all 15 sites (`0.25\rk@matrixw` → `0.25*\rk@matrixw`),
  which pgfmath parses correctly inside coordinate expressions.
- The two `text width={...}` node keys (matrix cell body, layer description) don't auto-evaluate arithmetic the
  way coordinates do, so those two now precompute the value with `\pgfmathsetlengthmacro` into a length macro
  first, then pass that macro to `text width=`.

**Verified after fixing:** recompiled both diagrams (plus a swimlane and a network, for regression coverage)
through two `pdflatex` passes each, rasterized every page with `pdftoppm`, and visually inspected the output —
2×2 matrix, layered architecture, swimlane with a handoff edge, and a two-node network all render correctly
with no clipped text, missing rectangles, or stray characters.

No change to the diagram *API* — `\RKMatrixCell`, `\RKLayer`, and all other macro signatures are unchanged.
Existing report `.tex` source using these macros needs no edits, only the patched `.sty`.

## 2.0 Font setup — use the portable bundle, not a blind apt-get (v3 addition)

Installing fonts via `apt-get install texlive-fonts-extra` (as §2 step 3 below describes)
works, but it is far more expensive than it needs to be, and naive attempts to avoid the
wait can silently fail. Both were observed directly in this sandbox:

**What actually happened, and why.** `texlive-fonts-extra` is a 1.7GB, ~106,000-file
package; the two font families `reportkit.cls` requires (`libertinus`,
`libertinust1math`) account for only 2,122 of those files, ~26MB uncompressed. The
first attempt to avoid waiting on the download used `nohup apt-get install ... &` in
one `bash_tool` call, intending to poll it from a later call — but that background
process was gone by the next call (killed when the sandboxed shell for that tool
invocation exited; `nohup` does not survive across tool-call boundaries here). A
second attempt ran the same install *without* `nohup`, as an ordinary foreground
command piped to `tail`; that process *did* survive past its own call's return and was
still running (confirmed via `ps aux`) when checked from a later call, and finished
successfully after being polled with a `while ps -p <pid> ...; do sleep 5; done` wait
loop. **Lesson: don't background long installs with `nohup ... &`; run them as a plain
foreground command and poll for completion from subsequent calls instead.** Do not
`kill` a process just because it's still running when you check on it — verify it's
actually stuck before intervening.

**The better fix: skip apt-get entirely with a portable font bundle.** Since only 26MB
of the 1.7GB package is ever used, extract just those files once, tar them, and store
the tarball as a project asset. Every subsequent session then does a ~14MB download
and local `tar -xzf` (a few seconds) instead of an apt-get resolving and unpacking a
1.7GB package (multiple minutes, and vulnerable to the lock/backgrounding issues
above). This was built and verified in this sandbox:

```bash
# One-time: after apt-get install has completed once, harvest only what's used
dpkg -L texlive-fonts-extra | grep -i libertinus | grep -v '/$' > filelist.txt
while read -r f; do
  rel="${f#/usr/share/texlive/texmf-dist/}"
  mkdir -p "texmf/$(dirname "$rel")"
  cp "$f" "texmf/$rel"
done < filelist.txt
tar -czf reportkit-libertinus-fonts.tar.gz -C texmf .   # ~14MB compressed
```

This was verified to be genuinely self-sufficient, not just "kpsewhich happens to find
the system copy too": the system-installed files were temporarily moved aside,
`kpsewhich libertinus.sty` was confirmed to fail, then `TEXMFHOME` was pointed at the
bundle alone and a full two-pass `pdflatex` compile of a real ReportKit report
succeeded end to end before the system files were restored.

**To use it in a session:** run `bootstrap.sh` (see §2.1 below) rather than doing this by
hand — it installs to `TEXMFLOCAL` (a system texmf directory), not `TEXMFHOME`. That
distinction matters: `TEXMFHOME` only works if exported, and environment variables do
not persist across separate `bash_tool` calls in this sandbox, so every later call
that compiles anything would need the export repeated. `TEXMFLOCAL` + `mktexlsr` is a
filesystem change, which does persist across calls with nothing to remember. This was
verified directly: fonts installed to `TEXMFLOCAL` resolved via plain `kpsewhich` in a
brand-new `bash_tool` call with no export, sourcing, or setup of any kind.

## 2.1 bootstrap.sh — one command instead of five

Sections 2.0–3 below describe the setup steps individually; `bootstrap.sh` (a project
file) runs all of them in one idempotent command and should be the normal way to start
any ReportKit task in this environment:

```bash
bash bootstrap.sh /mnt/project /home/claude/report
```

It copies the six core files into the working directory, installs fonts from the
bundle to `TEXMFLOCAL` if not already resolvable (skipping cleanly if they already
are), creates `figures/`, and runs the doctor, printing its verdict plainly. If core
files are missing from the project it stops with an explicit error rather than
guessing. If no font bundle is present it falls through to printing apt-get guidance
rather than hanging. Re-running it is safe — every step checks whether its work is
already done first.

This was verified end-to-end in this sandbox, including the failure path: with the
system Libertinus files temporarily hidden, `bootstrap.sh` correctly detected their
absence, installed the bundle to `TEXMFLOCAL`, and a full two-pass `pdflatex` compile
of a real report succeeded immediately afterward with no additional setup.

Note: `bootstrap.sh` covers the pdflatex/English path only. It does not yet install
`texlive-luatex` or the `LinBiolinum_K.otf` stub from §2.2 below — do that manually
for any report needing lualatex/Unicode content.

## 2.2 Unicode content (e.g. Vietnamese) — use lualatex, with two extra one-time steps

`pdflatex` with the Type1 Libertinus fonts cannot render precomposed Unicode
diacritics outside T1 encoding (confirmed directly: Vietnamese characters like ỉ, ệ
fail with "Unicode character ... not set up for use with LaTeX"). For any report
containing such content, compile with `lualatex` instead — `libertinus.sty`
auto-loads the correct OpenType math/text fonts under that engine. Two gaps were
found and fixed to make this work in this sandbox:

1. **`luaotfload` isn't installed by default.** Without it, `lualatex` fails with a
   cryptic `directlua` error (`attempt to index a nil value (global 'fonts')`) before
   reaching any document content. Fix: `apt-get install -y --no-install-recommends
   texlive-luatex` (~35MB, fast — nothing like the `texlive-fonts-extra` cost in
   §2.0).
2. **`libertinus-otf.sty` unconditionally requires `LinBiolinum_K.otf`**, an
   unrelated decorative font that Debian's TeX Live doesn't actually ship (an
   upstream packaging gap). Fails with `fontspec Error: The font "LinBiolinum_K"
   cannot be found`. Fix: drop any valid OTF file in as a stub under that filename
   (`font_data/LinBiolinum_K.otf` in the project bundle) — ReportKit content never
   invokes the command this defines, so the stub's actual appearance is irrelevant:
   ```bash
   mkdir -p /usr/local/share/texmf/fonts/opentype/public/libertine-stub
   cp LinBiolinum_K.otf /usr/local/share/texmf/fonts/opentype/public/libertine-stub/
   mktexlsr /usr/local/share/texmf
   ```

**A real bug was also found and fixed in `reportkit.cls` (v1.2.0 → v1.2.1) via this
path**, not just an environment gap: it unconditionally loaded `libertinust1math`
after `libertinus`, which is correct under pdflatex but, under lualatex, clobbered
`\times`'s glyph mapping (it silently rendered as `∝`). Fixed by guarding the legacy
math package behind `\ifPDFTeX`. Verified the fix doesn't break the pdflatex path:
the existing English guide recompiled to a byte-identical PDF afterward.

## 2. Standard task flow (replaces v1 §1)

1. `view` the project files actually needed (`SKILL.md` always; `STYLE_GUIDE.md` / `REPORTKIT_API.md` when
   writing content).
2. Run `bootstrap.sh` (§2.1) to set up the working directory and fonts in one step:
   ```bash
   bash /mnt/project/bootstrap.sh /mnt/project /home/claude/report
   cd /home/claude/report
   ```
   **Use the patched `reportkit-diagrams.sty` and `reportkit_doctor.py`** from this update, not the pre-fix
   versions, if `/mnt/project` hasn't been refreshed with them yet.
3. Install the Libertinus fonts once per session before trusting a FULL BUILD claim — the doctor will tell you
   if this is needed, but the install itself has to happen explicitly. **`bootstrap.sh` (§2.1) already does
   this** as part of step 2 above; this is only needed if bootstrapping some other way.
4. Run the doctor and report its actual `MODE:` line to the user rather than assuming:
   ```bash
   python3 reportkit_doctor.py
   ```
5. Build the bundle:
   ```text
   report/
     report.tex
     references.bib      # only if citations are used
     figures/
     make_figures.py
     README.md
   ```
6. Generate analytical figures with `reportkit_viz.py` per `REPORTKIT_API.md`. Confirm each `figures/*.pdf` +
   `.png` pair actually exists on disk before referencing it in `.tex`.
7. Compile twice (required for cross-references and captions):
   ```bash
   pdflatex -interaction=nonstopmode -halt-on-error report.tex
   pdflatex -interaction=nonstopmode -halt-on-error report.tex
   ```
   If it exits nonzero, read the `.log`, don't just retry — `-halt-on-error` gives a clean single failure point.
8. Rasterize and visually inspect every page before delivery:
   ```bash
   pdftoppm -png -r 150 report.pdf report_page
   ```
   then `view` each `report_page-N.png`. This is not optional — a nonzero-exit-code compile does not mean the
   diagrams actually look right (see §1: this exact class of bug compiled-looking-fine in isolation and only
   showed up as a runtime TeX error when the macros were actually invoked).
9. Copy final deliverables to `/mnt/user-data/outputs/` and call `present_files`.

## 3. Tool mapping (ChatGPT doc → Claude reality) — unchanged from v1

| ChatGPT-Project doc says | Claude does instead |
|---|---|
| "Attach files to Project context" | Files are already in `/mnt/project/`; `view` them directly |
| "ChatGPT Work / persistent build machine" | `bash_tool` sandbox, reset between tasks — nothing persists, so re-copy inputs and reinstall fonts each session |
| OpenAI `render_pdf.py` helper (§19 of `SKILL.md`) | `pdftoppm -png -r 150` is confirmed available in this sandbox; use it directly |
| "Do not assume Python is installed" | Confirmed: Python 3.12, matplotlib, numpy, pandas all present |
| "Do not assume TeX is installed" | Confirmed present (TeX Live 2023: pdflatex, lualatex, bibtex; **biber is not installed** — avoid biblatex+biber, use bibtex/natbib if a bibliography is needed) |

## 4. Non-negotiables carried over unchanged

Everything in `SKILL.md` §2–20 about narrative-first structure, callout restraint, metric/diagram/table/code
rules, and the visual QA checklist still applies exactly as written. This file only changes *how* Claude
executes the mechanics, not the report's design language.