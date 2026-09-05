#!/usr/bin/env bash
# build-section.sh <manuscript-md-file>
#
# Builds one manuscript section into a standalone PDF for visual
# inspection. Example: scripts/build-section.sh manuscript/01-introduction.md
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <manuscript-md-file>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"          # data_engineering_guide/
REPO_ROOT="$(cd "$ROOT/.." && pwd)"                              # report-kit/
manuscript="$1"
name="$(basename "$manuscript" .md)"

sections_dir="$ROOT/build/sections"
isolated_dir="$ROOT/build/isolated/$name"
mkdir -p "$sections_dir" "$isolated_dir"

body_tex="$sections_dir/$name.tex"
bash "$ROOT/scripts/render-visuals.sh" "$manuscript" "$ROOT/fragments" "$body_tex"

cp "$REPO_ROOT"/latex_templates/*.cls "$REPO_ROOT"/latex_templates/*.sty "$isolated_dir"/
cp "$body_tex" "$isolated_dir/body.tex"

cat > "$isolated_dir/harness.tex" <<'EOF'
\documentclass{reportkit}
\setcounter{secnumdepth}{-1}
\setreportkitleftheader{DATA ENGINEERING GUIDE / SECTION BUILD}
\setreportkitfooter{Isolated section build for visual QA}
\setreportkitversion{draft}
\title{Section build}
\author{Isolated build harness}
\date{\today}
% Pandoc's own default LaTeX template defines \tightlist as standard
% boilerplate for tight (no-blank-line) list items; render-visuals.sh
% emits pandoc's body only (no --standalone template), so it must be
% supplied here for any manuscript containing an ordinary tight list.
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
% Pandoc's own default LaTeX template loads this exact block whenever the
% document contains a Markdown table (Pandoc renders tables as longtable);
% render-visuals.sh emits pandoc's body only (no --standalone template),
% and reportkit.cls loads booktabs but not longtable/array/calc, so this
% must be supplied here for any manuscript containing a table.
\usepackage{longtable,booktabs,array}
\usepackage{calc} % for calculating minipage widths
\usepackage{etoolbox}
\makeatletter
\patchcmd\longtable{\par}{\if@noskipsec\mbox{}\fi\par}{}{}
\makeatother
\IfFileExists{footnotehyper.sty}{\usepackage{footnotehyper}}{\usepackage{footnote}}
\makesavenoteenv{longtable}
\begin{document}
\maketitle
\input{body.tex}
\end{document}
EOF

(
  cd "$isolated_dir"
  pdflatex -interaction=nonstopmode -halt-on-error harness.tex
  pdflatex -interaction=nonstopmode -halt-on-error harness.tex
)

"$ROOT/build/.venv/bin/python" "$ROOT/scripts/render_pdf_pages.py" \
  "$isolated_dir/harness.pdf" "$isolated_dir/pages" --dpi 150

echo "build-section.sh: PDF at $isolated_dir/harness.pdf, pages in $isolated_dir/pages" >&2
