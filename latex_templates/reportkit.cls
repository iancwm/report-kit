% ReportKit v1.5.0 -- core document class
% Project-local technical report grammar.
% v1.1 adds structural pagination guards for section openings and diagrams.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{reportkit}[2026/09/06 v1.5.0 ReportKit technical report class]

\LoadClass[10pt,a4paper]{article}

\RequirePackage[a4paper,left=27mm,right=27mm,top=24mm,bottom=24mm,headsep=8mm,footskip=12mm]{geometry}
\RequirePackage{iftex}
% v1.2.1 fix: fontenc/inputenc and libertinust1math are pdfTeX-only concerns.
% Under luaTeX/XeTeX, libertinus.sty already auto-loads correct OpenType math
% support via unicode-math; separately loading the legacy T1 math companion
% package on top of that clobbers operator glyph mappings (observed: \times
% rendered as the wrong glyph -- resembling \propto -- once both were loaded
% together under lualatex). Guard both by engine so each engine gets exactly
% the math setup it needs, and no more.
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
\fi
\RequirePackage{libertinus}
\ifPDFTeX
  \RequirePackage{libertinust1math}
\fi
\RequirePackage{microtype}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage{siunitx}
\RequirePackage{enumitem}
\RequirePackage{titlesec}
\RequirePackage{fancyhdr}
\RequirePackage{needspace}
\RequirePackage{caption}
\RequirePackage{hyperref}
\providecommand{\RKLink}[1]{\href{#1}{#1}}
\RequirePackage{xparse}
\RequirePackage{etoolbox}

% -----------------------------------------------------------------------------
% Canonical ReportKit palette. Kept in sync with reportkit_viz.py.
% -----------------------------------------------------------------------------
\definecolor{Ink}{HTML}{24272D}
\definecolor{Muted}{HTML}{687386}
\definecolor{Hairline}{HTML}{D9DEE5}
\definecolor{LinkBlue}{HTML}{2C5E78}
\definecolor{Principle}{HTML}{2C5E78}
\definecolor{Decision}{HTML}{68558A}
\definecolor{Research}{HTML}{2B7074}
\definecolor{Tip}{HTML}{3F6D54}
\definecolor{RedFlag}{HTML}{A14B45}
\definecolor{Assumption}{HTML}{8A6A24}
\definecolor{Evidence}{HTML}{4B6472}
\definecolor{Limitation}{HTML}{6E6A67}
\definecolor{MetricAccent}{HTML}{315E86}
\definecolor{Surface}{HTML}{F7F8FA}
% v1.2 addition, paired with the \deliverablenote callout in
% reportkit-boxes.sty. Mirrored in reportkit_viz.py's LATEX_THEME_COLORS.
\definecolor{Deliverable}{HTML}{2C6E49}

\color{Ink}
\hypersetup{colorlinks=true,linkcolor=LinkBlue,urlcolor=LinkBlue,citecolor=LinkBlue,pdfborder={0 0 0},pdfdisplaydoctitle=true}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4.5pt plus 1pt minus .5pt}
\setlist{nosep,leftmargin=1.45em,topsep=3pt}
\sisetup{detect-all=true,group-separator={,}}
\captionsetup{font=small,labelfont=bf,labelsep=period,singlelinecheck=false,skip=4pt}

% -----------------------------------------------------------------------------
% Metadata and running furniture
% -----------------------------------------------------------------------------
\newcommand{\rk@leftheader}{REPORTKIT}
\newcommand{\rk@footer}{Technical report}
\newcommand{\rk@version}{v1.0}
\newcommand{\rk@subject}{Technical report}
\newcommand{\rk@keywords}{ReportKit, technical report}
\newcommand{\rk@language}{en-US}
\newcommand{\setreportkitleftheader}[1]{\renewcommand{\rk@leftheader}{#1}}
\newcommand{\setreportkitfooter}[1]{\renewcommand{\rk@footer}{#1}}
\newcommand{\setreportkitversion}[1]{\renewcommand{\rk@version}{#1}}
\newcommand{\setreportkitsubject}[1]{\renewcommand{\rk@subject}{#1}}
\newcommand{\setreportkitkeywords}[1]{\renewcommand{\rk@keywords}{#1}}
\newcommand{\setreportkitlanguage}[1]{\renewcommand{\rk@language}{#1}}

% Keep PDF metadata coupled to the document's normal title and author fields.
% hyperref performs the necessary PDF-string sanitisation for bookmarks and
% metadata, so callers can continue using ordinary LaTeX in \title/\author.
\AtBeginDocument{%
  \hypersetup{
    pdftitle={\@title},
    pdfauthor={\@author},
    pdfsubject={\rk@subject},
    pdfkeywords={\rk@keywords},
    pdfdisplaydoctitle=true
  }%
  % Write the catalog language directly; pdflang support varies by hyperref
  % engine, while the PDF catalog requirement is stable.
  \ifPDFTeX
    \pdfcatalog{/Lang (\rk@language)}%
  \else
    \pdfextension catalog {/Lang (\rk@language)}%
  \fi
}

\setlength{\headheight}{19pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\sffamily\fontsize{7.7}{9}\selectfont\color{Muted}\MakeUppercase{\rk@leftheader}}
\fancyhead[R]{\sffamily\fontsize{7.7}{9}\selectfont\color{Muted}\nouppercase{\leftmark}}
\fancyfoot[L]{\sffamily\fontsize{7.4}{9}\selectfont\color{Muted}\rk@footer\ · \rk@version}
\fancyfoot[R]{\sffamily\fontsize{7.4}{9}\selectfont\color{Muted}\thepage}
\renewcommand{\headrulewidth}{0.35pt}
\renewcommand{\footrulewidth}{0pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{Hairline}\leaders\hrule height \headrulewidth\hfill}}

% -----------------------------------------------------------------------------
% Section hierarchy and anti-stranding guards
% -----------------------------------------------------------------------------
% Every major heading reserves enough room for the heading plus several lines
% of body copy. This eliminates ordinary stranded headings without forcing
% arbitrary page breaks.
\newcommand{\RKSectionNeed}{14\baselineskip}
\newcommand{\RKSubsectionNeed}{7\baselineskip}

\titleformat{\section}{\Needspace{\RKSectionNeed}\sffamily\bfseries\Large\color{Ink}}{\color{LinkBlue}\thesection}{0.7em}{}
\titlespacing*{\section}{0pt}{15pt plus 3pt minus 2pt}{6pt}
\titleformat{\subsection}{\Needspace{\RKSubsectionNeed}\sffamily\bfseries\large\color{Ink}}{\color{LinkBlue}\thesubsection}{0.65em}{}
\titlespacing*{\subsection}{0pt}{12pt plus 2pt minus 2pt}{4pt}

% Use this when a section opens with a conceptual diagram after a short setup
% paragraph. It reserves the whole reading unit: heading + setup + compact
% diagram/caption. If insufficient space remains, the section starts next page.
\NewDocumentCommand{\RKDiagramSection}{m}{%
  \par\Needspace{0.46\textheight}%
  \section{#1}%
}

% Smaller variant for a subsection that opens with a diagram.
\NewDocumentCommand{\RKDiagramSubsection}{m}{%
  \par\Needspace{0.38\textheight}%
  \subsection{#1}%
}

% -----------------------------------------------------------------------------
% Title and executive summary
% -----------------------------------------------------------------------------
\renewcommand{\maketitle}{%
  \thispagestyle{fancy}%
  \vspace*{3mm}%
  {\sffamily\fontsize{8.5}{10}\selectfont\bfseries\color{LinkBlue}\MakeUppercase{\rk@leftheader}\par}%
  \vspace{6mm}%
  {\sffamily\bfseries\fontsize{24}{28}\selectfont\color{Ink}\@title\par}%
  \vspace{3mm}%
  \ifx\@author\@empty\else{\sffamily\fontsize{9.5}{12}\selectfont\color{Muted}\@author}\fi
  \ifx\@date\@empty\else{\sffamily\fontsize{9.5}{12}\selectfont\color{Muted}\quad\textperiodcentered\quad\@date}\fi
  \par\vspace{7mm}\color{Hairline}\hrule\color{Ink}\vspace{7mm}%
}

\NewDocumentEnvironment{execsummary}{}{%
  \par\Needspace{8\baselineskip}%
  \begin{list}{}{\setlength{\leftmargin}{0pt}\setlength{\rightmargin}{0pt}}\item\relax
  \color{Ink}\sffamily\small\textbf{EXECUTIVE SUMMARY}\par\vspace{2pt}\rmfamily\normalsize
}{%
  \end{list}\vspace{3pt}
}

% Figure/table provenance helper.
\newcommand{\source}[1]{\par\vspace{1pt}{\sffamily\fontsize{7.4}{9}\selectfont\color{Muted}\textit{Source:} #1}\par}

% Inline code helper; full code blocks live in reportkit-code.sty.
\newcommand{\code}[1]{\texttt{#1}}

% Semantic modules are part of the class contract.
\RequirePackage{reportkit-boxes}
\RequirePackage{reportkit-code}
\RequirePackage{reportkit-diagrams}
\RequirePackage{reportkit-grammar}

\endinput
