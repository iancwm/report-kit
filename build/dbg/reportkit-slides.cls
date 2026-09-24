% ReportKit Slides -- presentation document class. Phase B of the
% multi-format publication architecture spec
% (docs/superpowers/specs/2026-09-09-reportkit-multi-format-publication-architecture-spec.md),
% decisions D5 (Beamer, aspectratio=169, 160mm x 90mm canvas) and D8 (Beamer
% is the slide backend; decorative navigation/animation are disabled in the
% public composition API).
%
% This class mirrors reportkit.cls's shape (theme/publication-type option
% parsing, generated-registry validation, theme + renderer-adapter loading)
% over Beamer instead of article. `\documentclass[theme=executive,
% publication-type=presentation]{reportkit-slides}` is the only currently
% registered combination (executive is the stable Phase C system -- see
% themes/reportkit-theme-executive.sty); the option parser and registry are
% otherwise renderer-generic so a later slides theme (venture, Phase D)
% needs no change here.
%
% aspectratio=169 already produces a 16.00cm x 9.00cm (160mm x 90mm) frame
% natively in this Beamer version (verified by reading beamer.cls's own
% aspect-ratio table, not assumed) -- no paperwidth/paperheight override is
% needed to hit the declared canvas.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{reportkit-slides}[2026/09/13 v1.0.0 ReportKit presentation class]

% -----------------------------------------------------------------------------
% Theme / publication-type selection
% -----------------------------------------------------------------------------
% Same shared parser reportkit.cls uses (reportkit-options.tex, generated
% from the canonical Python publication registry) -- unknown theme= and
% publication-type= values still fail loudly instead of reaching Beamer
% unrecognized. \rk@classrenderer=slides is what makes RKValidateSelection
% reject a paged publication type here (and would reject a slides
% publication type in reportkit.cls).
\newcommand{\rk@theme}{executive}
\newcommand{\rk@requestedtheme}{executive}
\newcommand{\rk@publicationtype}{presentation}
\newcommand{\rk@classrenderer}{slides}
\newcommand{\rk@classname}{reportkit-slides}
\input{reportkit-options.tex}
\ProcessOptions\relax
\RKValidateSelection

\LoadClass[aspectratio=169]{beamer}

\RequirePackage{reportkit-core}
% This class only produces slide output, so it loads the slides renderer
% core immediately after the shared core and before any theme or semantic
% module -- the slides counterpart of reportkit.cls's
% \RequirePackage{reportkit-paged-core} at this same position.
\RequirePackage{reportkit-slides-core}
\RKAssertRendererHooks
% The registry resolves aliases to the canonical implementation package
% before any theme code is loaded, exactly as reportkit.cls does; no theme
% currently aliases to executive, but the mechanism is shared.
\edef\rk@themepackage{\csname RKThemePackage@\rk@theme\endcsname}
\expandafter\RequirePackage\expandafter{\rk@themepackage}
% Phase A4 (decision D11): load the theme's renderer-specific adapter
% (geometry/canvas, running furniture, other slides-specific component
% values) right after its common package, resolved the same way
% reportkit.cls resolves its paged adapter.
\edef\rk@themeadapter{\csname RKThemeAdapter@\rk@theme\string @\rk@classrenderer\endcsname}
\expandafter\RequirePackage\expandafter{\rk@themeadapter}

% Publication types layer primitives on top of the selected theme, exactly
% as in reportkit.cls. publication-type=presentation (the only registered
% slides publication type) loads reportkit-presentation.
\edef\rk@pubtypepackage{\csname RKPublicationPackage@\rk@publicationtype\endcsname}
\ifx\rk@pubtypepackage\@empty\else
  \expandafter\RequirePackage\expandafter{\rk@pubtypepackage}%
\fi

% Semantic modules are part of the class contract, same as reportkit.cls --
% every one of these already routes through the renderer-hook contract
% (RKReserveSpace, RKDiagramPlacementBegin/End, RKDiagramCaption,
% RKDiagramSource) and the style-token contract (RKAssertStyleTokens),
% neither of which references a paged-only package, so they work unmodified
% under the slides renderer core loaded above.
\RequirePackage{reportkit-boxes}
\RequirePackage{reportkit-code}
\RequirePackage{reportkit-diagrams}
\RequirePackage{reportkit-grammar}

\endinput
