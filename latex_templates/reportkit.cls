% ReportKit v1.9.3 -- core document class
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
% Phase A3 of the multi-format architecture spec splits reportkit-core.sty
% into an engine-neutral shared core and a new reportkit-paged-core.sty
% owning geometry/fancyhdr/titlesec/needspace/caption and the renderer-hook
% implementations (RKReserveSpace, RKDiagramPlacementBegin/End,
% RKDiagramCaption, RKDiagramSource) that semantic modules now call instead
% of those packages directly. This class still only produces paged output --
% it loads reportkit-paged-core right after reportkit-core -- but a future
% slides class can load a slides core supplying the same hooks. Output is
% unchanged; only the mechanism moved (verified: identical PDF bytes on the
% default and institutional/equity fixtures).
% Phase A4 (decision D11) splits each theme's common package (fonts, palette,
% renderer-neutral semantic appearance) from a per-renderer adapter package
% (geometry, running furniture, and other paged-specific values) -- this
% class now loads both, resolved from the same generated publication
% registry as the common package. See
% themes/reportkit-theme-default(-paged).sty and
% themes/reportkit-theme-institutional-research(-paged).sty for what moved.
% Output is unchanged (verified: identical rendered pixels on the default
% and institutional/equity fixtures; the default fixture's raw PDF bytes are
% also identical -- LuaLaTeX's own output was already not byte-reproducible
% on this local, unpinned toolchain even before this change, so the
% institutional/equity comparison is pixel- and text-level, not hash-level;
% see the implementation plan's A4 section).
% Also not its own version bump -- \ProvidesClass stays v1.9.3 until a
% release commit moves it, matching version.py's REPORTKIT_VERSION (see
% test_agent_contract.py's test_toolchain_fingerprint_and_release_version_are_stable).
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{reportkit}[2026/09/13 v1.9.3 ReportKit technical report class]

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
% This class only produces paged output, so it loads the paged renderer core
% immediately after the shared core and before any theme or semantic module.
% A future slides class loads a slides core in this same position instead.
\RequirePackage{reportkit-paged-core}
\RKAssertRendererHooks
% The registry resolves aliases to the canonical implementation package before
% any theme code is loaded (theme=technical uses the default package).
\edef\rk@themepackage{\csname RKThemePackage@\rk@theme\endcsname}
\expandafter\RequirePackage\expandafter{\rk@themepackage}
% Phase A4 (decision D11): the theme's common package above owns only
% renderer-neutral appearance (fonts, palette, style tokens). Page geometry,
% running furniture and other paged-specific values live in a per-renderer
% adapter package, resolved the same way as the common package and loaded
% right after it, before any semantic module. \string inserts a literal "@"
% that cannot be absorbed into the preceding control word (\rk@theme is
% catcode-11 under \makeatletter, same reasoning as \RKValidateSelection's
% RKPublicationTheme@...@... lookup in reportkit-options.tex).
\edef\rk@themeadapter{\csname RKThemeAdapter@\rk@theme\string @\rk@classrenderer\endcsname}
\expandafter\RequirePackage\expandafter{\rk@themeadapter}

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
\RequirePackage{reportkit-algorithms}
\RequirePackage{reportkit-diagrams}
\RequirePackage{reportkit-grammar}

\endinput
