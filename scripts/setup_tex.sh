#!/usr/bin/env bash
# Install the TeX dependencies for a fresh Debian/Ubuntu clone, then prove
# that a LuaLaTeX ReportKit document compiles. --check only runs the proof.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" != "" && "${1:-}" != "--check" ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

if [[ "${1:-}" != "--check" ]]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "This installer needs Debian/Ubuntu apt-get; use toolchain/Dockerfile on another OS." >&2
    exit 2
  fi
  if [[ "$(id -u)" == 0 ]]; then
    ADMIN=()
  elif command -v sudo >/dev/null 2>&1; then
    ADMIN=(sudo)
  else
    echo "Run as root or install sudo to install TeX packages." >&2
    exit 2
  fi

  "${ADMIN[@]}" apt-get update
  "${ADMIN[@]}" apt-get install -y --no-install-recommends \
    fontconfig pandoc poppler-utils texlive-bibtex-extra \
    texlive-fonts-recommended texlive-latex-extra texlive-luatex \
    texlive-plain-generic texlive-science

  TEXMF_LOCAL="$(kpsewhich -var-value TEXMFLOCAL)"
  if [[ -z "$TEXMF_LOCAL" ]]; then
    echo "kpsewhich did not report TEXMFLOCAL." >&2
    exit 1
  fi
  if [[ -z "$(kpsewhich libertinus.sty)" || -z "$(kpsewhich libertinust1math.sty)" ]]; then
    "${ADMIN[@]}" mkdir -p "$TEXMF_LOCAL"
    "${ADMIN[@]}" tar -xzf "$ROOT/font_data/reportkit-libertinus-fonts.tar.gz" -C "$TEXMF_LOCAL"
  fi
  "${ADMIN[@]}" install -Dm644 "$ROOT/font_data/LinBiolinum_K.otf" \
    "$TEXMF_LOCAL/fonts/opentype/public/libertine-stub/LinBiolinum_K.otf"
  "${ADMIN[@]}" mktexlsr "$TEXMF_LOCAL"
  FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/reportkit"
  mkdir -p "$FONT_DIR"
  install -m644 "$ROOT"/font_data/GoogleSans-{Regular,Medium,Bold}.ttf "$FONT_DIR/"
  fc-cache -f "$FONT_DIR"
  if command -v luaotfload-tool >/dev/null 2>&1; then
    luaotfload-tool --update --force
  fi
fi

for command in lualatex kpsewhich; do
  command -v "$command" >/dev/null 2>&1 || { echo "Missing $command" >&2; exit 1; }
done

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cat > "$WORKDIR/editorial.tex" <<'TEX'
\documentclass[theme=editorial,publication-type=feature-article]{reportkit}
\begin{document}
LuaLaTeX setup verified.
\end{document}
TEX
cat > "$WORKDIR/institutional.tex" <<'TEX'
\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}
\begin{document}
LuaLaTeX setup verified.
\end{document}
TEX
for document in editorial institutional; do
  if ! (cd "$WORKDIR" && TEXINPUTS=".:$ROOT/latex_templates//:" \
    lualatex -interaction=nonstopmode -halt-on-error -file-line-error "./$document.tex" > "$document.log" 2>&1); then
    echo "LuaLaTeX $document smoke test failed; see the final error below:" >&2
    tail -40 "$WORKDIR/$document.log" >&2
    exit 1
  fi
done
echo "LuaLaTeX and the ReportKit editorial and institutional themes compile successfully."
