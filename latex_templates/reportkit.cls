% ReportKit v1.9.2 -- core document class
% Project-local technical report grammar.
% v1.1 adds structural pagination guards for section openings and diagrams.
% v1.6 introduces a theme/publication-type architecture: typography,
% geometry, palette, and running furniture now live in a selected theme file
% under latex_templates/themes/ instead of being hardcoded here. See
% docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md.
% `\documentclass{reportkit}` (no theme= option, equivalent to
% theme=default) reproduces the pre-v1.6 visual output exactly -- nothing was
% rewritten in the split, only relocated into reportkit-core.sty and
% themes/reportkit-theme-default.sty.
% v1.7 adds the institutional-research theme (Step 2 of the same spec):
% Letter geometry, Google Sans via fontspec, the spec's full type scale, and
% quieter semantic callouts. It requires LuaLaTeX -- config.py's
% theme_engine_conflict() refuses to build it under any other engine, and the
% theme file itself repeats that check at the TeX level.
% v1.8 adds the equity-research publication type (Step 3 of the same spec):
% front page, rating strip, sidebar, "what changed", exhibit system, and
% financial-model-page primitives, loaded from a new
% latex_templates/publication_types/ directory alongside themes/.
% publication-type=technical-report (the default) loads no extra file, same
% as before -- only equity-research adds one.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{reportkit}[2026/09/11 v1.9.2 ReportKit technical report class]

% -----------------------------------------------------------------------------
% Theme / publication-type selection
% -----------------------------------------------------------------------------
% Known declarations (including \DeclareOption{theme=institutional-research}
% and \DeclareOption{publication-type=equity-research})
% are generated from the canonical Python publication registry. The shared
% parser intercepts unknown theme= and publication-type= values instead of
% forwarding them to article, where they would otherwise produce a warning and
% a plausible PDF under the wrong design system.
\newcommand{\rk@theme}{default}
\newcommand{\rk@requestedtheme}{default}
\newcommand{\rk@publicationtype}{technical-report}
\newcommand{\rk@classrenderer}{paged}
\newcommand{\rk@classname}{reportkit}
\input{reportkit-options.tex}
\ProcessOptions\relax
\RKValidateSelection

\LoadClass[10pt,a4paper]{article}

\RequirePackage{reportkit-core}
% The registry resolves aliases to the canonical implementation package before
% any theme code is loaded (theme=technical uses the default package).
\edef\rk@themepackage{\csname RKThemePackage@\rk@theme\endcsname}
\expandafter\RequirePackage\expandafter{\rk@themepackage}

% Publication types layer primitives on top of the selected theme. The package
% name is also registry-backed so a future renderer/publication adapter cannot
% silently inherit a filename convention it does not own.
\edef\rk@pubtypepackage{\csname RKPublicationPackage@\rk@publicationtype\endcsname}
\ifx\rk@pubtypepackage\@empty\else
  \expandafter\RequirePackage\expandafter{\rk@pubtypepackage}%
\fi

% Semantic modules are part of the class contract.
\RequirePackage{reportkit-boxes}
\RequirePackage{reportkit-code}
\RequirePackage{reportkit-diagrams}
\RequirePackage{reportkit-grammar}

\endinput
