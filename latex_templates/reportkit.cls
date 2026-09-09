% ReportKit v1.7.0 -- core document class
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
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{reportkit}[2026/09/09 v1.7.0 ReportKit technical report class]

% -----------------------------------------------------------------------------
% Theme / publication-type selection
% -----------------------------------------------------------------------------
% A fixed, enumerated option set -- not a general key=value parser -- so an
% unrecognised theme or publication-type name fails loudly rather than being
% silently accepted and ignored. \DeclareOption* passes anything unrecognised
% through to `article`, which will itself reject it; that is an acceptable
% (if not maximally friendly) failure mode for a name that doesn't exist yet
% -- see the institutional-theme implementation plan, Step 1, "deferred".
%
% `theme=default`, `theme=institutional-research`, and
% `publication-type=technical-report` exist so far. Adding a theme or
% publication type means adding both the corresponding \DeclareOption line
% here and the .sty file it loads.
\newcommand{\rk@theme}{default}
\newcommand{\rk@publicationtype}{technical-report}
\DeclareOption{theme=default}{\renewcommand{\rk@theme}{default}}
\DeclareOption{theme=institutional-research}{\renewcommand{\rk@theme}{institutional-research}}
\DeclareOption{publication-type=technical-report}{\renewcommand{\rk@publicationtype}{technical-report}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

\LoadClass[10pt,a4paper]{article}

\RequirePackage{reportkit-core}
% \rk@theme is a simple macro expanding to a literal theme name (set only by
% \renewcommand above, never by user input beyond the enumerated \DeclareOption
% set), so \edef-then-\expandafter is the standard, safe way to turn it into
% a package name: it fully expands \rk@theme once into \rk@themepackage, then
% hands \RequirePackage a literal token list, not a macro to expand itself.
\edef\rk@themepackage{reportkit-theme-\rk@theme}
\expandafter\RequirePackage\expandafter{\rk@themepackage}

% Semantic modules are part of the class contract.
\RequirePackage{reportkit-boxes}
\RequirePackage{reportkit-code}
\RequirePackage{reportkit-diagrams}
\RequirePackage{reportkit-grammar}

\endinput
