#!/usr/bin/env bash
# combine.sh -- assembles the full manuscript into one reportkit PDF.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
combined_dir="$ROOT/build/combined"
mkdir -p "$combined_dir" "$ROOT/build/sections"

body_tex="$combined_dir/body.tex"
: > "$body_tex"

while IFS= read -r md_name; do
  [[ -z "$md_name" ]] && continue
  section_body="$ROOT/build/sections/$(basename "$md_name" .md).tex"
  bash "$ROOT/scripts/render-visuals.sh" "$ROOT/manuscript/$md_name" "$ROOT/fragments" "$section_body"
  cat "$section_body" >> "$body_tex"
  printf '\n' >> "$body_tex"
done < "$ROOT/manuscript/order.txt"

cp "$REPO_ROOT"/latex_templates/*.cls "$REPO_ROOT"/latex_templates/*.sty "$combined_dir"/

cat > "$combined_dir/data-engineering-guide.tex" <<'EOF'
\documentclass{reportkit}
\setcounter{secnumdepth}{-1}
\setreportkitleftheader{DATA ENGINEERING GUIDE}
\setreportkitfooter{A Practical Guide to Data Engineering}
\setreportkitversion{draft}
\title{A Practical Guide to Data Engineering}
\author{Data Engineering Guide}
\date{\today}
% Same \tightlist shim as build-section.sh's harness.tex (Task 3) -- this
% is a separate document-assembly point that also combines Pandoc body
% output (no --standalone) with reportkit.cls, so it needs its own copy.
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
% Same Pandoc-standalone-template emergencystretch/xurl lines as
% build-section.sh's harness.tex -- this is a separate document-assembly
% point that also needs them, for the same reason (prevents overfull lines
% on long unbreakable spans like a bare s3:// path in \texttt).
\setlength{\emergencystretch}{3em} % prevent overfull lines
\IfFileExists{xurl.sty}{\usepackage{xurl}}{} % add URL line breaks if available
% Same hyphenat fallback as build-section.sh's harness.tex -- needed so a
% long unbroken s3:// path in \texttt can hyphenate instead of overflowing.
\usepackage[htt]{hyphenat}
% Same longtable/booktabs/array/calc block as build-section.sh's
% harness.tex (Task 3) -- this is a separate document-assembly point that
% also needs it, for the same reason.
\usepackage{longtable,booktabs,array}
\usepackage{calc}
\usepackage{etoolbox}
\makeatletter
\patchcmd\longtable{\par}{\if@noskipsec\mbox{}\fi\par}{}{}
\makeatother
\IfFileExists{footnotehyper.sty}{\usepackage{footnotehyper}}{\usepackage{footnote}}
\makesavenoteenv{longtable}
% Same syntax-highlighting block as build-section.sh's harness.tex (Task
% 3) -- this is a separate document-assembly point that also needs it.
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
  cd "$combined_dir"
  pdflatex -interaction=nonstopmode -halt-on-error data-engineering-guide.tex
  pdflatex -interaction=nonstopmode -halt-on-error data-engineering-guide.tex
)

"$ROOT/build/.venv/bin/python" "$ROOT/scripts/render_pdf_pages.py" \
  "$combined_dir/data-engineering-guide.pdf" "$combined_dir/pages" --dpi 150

echo "combine.sh: PDF at $combined_dir/data-engineering-guide.pdf, pages in $combined_dir/pages" >&2
