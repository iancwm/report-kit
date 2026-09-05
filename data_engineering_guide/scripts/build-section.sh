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
% Pandoc's own default LaTeX template emits this exact syntax-highlighting
% support (Shaded/Highlighting environments plus per-token-type color
% macros) whenever the document has a fenced code block with a recognized
% language; render-visuals.sh emits pandoc's body only (no --standalone
% template), so it must be supplied here for any manuscript containing a
% fenced code block. xcolor is already loaded by reportkit.cls (harmless
% to reload); color and fancyvrb are not loaded elsewhere.
\usepackage{xcolor}
\usepackage{color}
\usepackage{fancyvrb}
\newcommand{\VerbBar}{|}
\newcommand{\VERB}{\Verb[commandchars=\\\{\}]}
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\}}
\newenvironment{Shaded}{}{}
\newcommand{\AlertTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{#1}}}
\newcommand{\AnnotationTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\AttributeTok}[1]{\textcolor[rgb]{0.49,0.56,0.16}{#1}}
\newcommand{\BaseNTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\BuiltInTok}[1]{\textcolor[rgb]{0.00,0.50,0.00}{#1}}
\newcommand{\CharTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\CommentTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textit{#1}}}
\newcommand{\CommentVarTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\ConstantTok}[1]{\textcolor[rgb]{0.53,0.00,0.00}{#1}}
\newcommand{\ControlFlowTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{\textbf{#1}}}
\newcommand{\DataTypeTok}[1]{\textcolor[rgb]{0.56,0.13,0.00}{#1}}
\newcommand{\DecValTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\DocumentationTok}[1]{\textcolor[rgb]{0.73,0.13,0.13}{\textit{#1}}}
\newcommand{\ErrorTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{#1}}}
\newcommand{\ExtensionTok}[1]{#1}
\newcommand{\FloatTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\FunctionTok}[1]{\textcolor[rgb]{0.02,0.16,0.49}{#1}}
\newcommand{\ImportTok}[1]{\textcolor[rgb]{0.00,0.50,0.00}{\textbf{#1}}}
\newcommand{\InformationTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\KeywordTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{\textbf{#1}}}
\newcommand{\NormalTok}[1]{#1}
\newcommand{\OperatorTok}[1]{\textcolor[rgb]{0.40,0.40,0.40}{#1}}
\newcommand{\OtherTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{#1}}
\newcommand{\PreprocessorTok}[1]{\textcolor[rgb]{0.74,0.48,0.00}{#1}}
\newcommand{\RegionMarkerTok}[1]{#1}
\newcommand{\SpecialCharTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\SpecialStringTok}[1]{\textcolor[rgb]{0.73,0.40,0.53}{#1}}
\newcommand{\StringTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\VariableTok}[1]{\textcolor[rgb]{0.10,0.09,0.49}{#1}}
\newcommand{\VerbatimStringTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\WarningTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
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
