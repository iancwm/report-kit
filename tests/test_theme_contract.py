"""Phase A4 (decision D2) of the multi-format publication architecture spec:
component appearance lives behind theme-owned style tokens, not a semantic
module branching on \\rk@theme. This file is the static contract that keeps
that true as themes are added -- it does not compile any TeX (no toolchain
is assumed to be present; see scripts/acceptance_check.sh and the plan's own
verification notes for the compiled proof).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from reportkit.publications import THEMES, canonical_theme_name
from reportkit.themes import get_theme, validate_theme_contract

REPO = Path(__file__).resolve().parents[1]

# One entry per token reportkit-core.sty declares as a sentinel and
# reportkit-boxes.sty reads. Kept in one place so a new token added to the
# contract in one file and forgotten in another fails loudly here instead of
# only at compile time under whichever theme happens to be exercised.
REQUIRED_STYLE_TOKENS = [
    "RKTokCalloutColBack", "RKTokCalloutColFrame", "RKTokCalloutBoxRule",
    "RKTokCalloutLeftRule", "RKTokCalloutArc", "RKTokCalloutOuterArc",
    "RKTokCalloutPadLeft", "RKTokCalloutPadRight", "RKTokCalloutPadTop",
    "RKTokCalloutPadBottom", "RKTokCalloutBeforeSkip", "RKTokCalloutAfterSkip",
    "RKTokCalloutTitleFont",
    "RKTokMetricColBack", "RKTokMetricColFrame", "RKTokMetricBoxRule",
    "RKTokMetricArc", "RKTokMetricOuterArc", "RKTokMetricPadLeft",
    "RKTokMetricPadRight", "RKTokMetricPadTop", "RKTokMetricPadBottom",
    "RKTokMetricBeforeSkip", "RKTokMetricAfterSkip", "RKTokMetricBorderLineWidth",
    "RKTokMetricLabelFont", "RKTokMetricValueFont", "RKTokMetricSubtitleFont",
    "RKTokMetricSubtitleSpacing", "RKTokMetricWhyFont",
    # Diagram chrome (Phase A4's implemented diagram work -- reportkit-core.sty's
    # "Diagram chrome" contract section). Shared by reportkit-diagrams.sty,
    # reportkit-structure.sty, reportkit-process.sty and reportkit-spatial.sty.
    "RKTokDiagramNodeDraw", "RKTokDiagramNodeFill", "RKTokDiagramNodeText",
    "RKTokDiagramNodeRounding", "RKTokDiagramNodeMinHeight", "RKTokDiagramNodeTextWidth",
    "RKTokDiagramNodePadX", "RKTokDiagramNodePadY", "RKTokDiagramNodeFont",
    "RKTokDiagramAccentDraw", "RKTokDiagramAccentFill", "RKTokDiagramAccentWidth",
    "RKTokDiagramArrowLength", "RKTokDiagramArrowWidth",
    "RKTokDiagramEdgeFlowColor", "RKTokDiagramEdgeFlowWidth",
    "RKTokDiagramEdgeSequenceColor", "RKTokDiagramEdgeSequenceWidth",
    "RKTokDiagramEdgeDependencyColor", "RKTokDiagramEdgeDependencyWidth",
    "RKTokDiagramEdgeHandoffColor", "RKTokDiagramEdgeHandoffWidth",
    "RKTokDiagramEdgeCausalColor", "RKTokDiagramEdgeCausalWidth",
    "RKTokDiagramEdgeOptionalColor", "RKTokDiagramEdgeOptionalWidth",
    "RKTokDiagramEdgeLabelFill", "RKTokDiagramEdgeLabelPad",
    "RKTokDiagramEdgeLabelText", "RKTokDiagramEdgeLabelFont",
    "RKTokDiagramLayerDraw", "RKTokDiagramLayerFill", "RKTokDiagramLayerWidth",
    "RKTokDiagramLayerTitleFont", "RKTokDiagramLayerTitleText",
    "RKTokDiagramLayerBodyFont", "RKTokDiagramLayerBodyText",
    "RKTokDiagramTierDraw", "RKTokDiagramTierFill", "RKTokDiagramTierWidth",
    "RKTokDiagramTierLabelFont", "RKTokDiagramTierLabelText",
    "RKTokDiagramStackArrowColor", "RKTokDiagramStackArrowWidth",
    "RKTokDiagramCycleNodeFont", "RKTokDiagramCycleEdgeColor", "RKTokDiagramCycleEdgeWidth",
    "RKTokDiagramMatrixAxisColor", "RKTokDiagramMatrixAxisWidth",
    "RKTokDiagramMatrixAxisLabelFont", "RKTokDiagramMatrixAxisLabelText",
    "RKTokDiagramMatrixEndpointFont", "RKTokDiagramMatrixEndpointText",
    "RKTokDiagramMatrixAccentColor", "RKTokDiagramMatrixCellFont", "RKTokDiagramMatrixCellText",
    "RKTokDiagramMatrixPointColor", "RKTokDiagramMatrixPointRadius",
    "RKTokDiagramMatrixPointLabelFont", "RKTokDiagramMatrixPointLabelText",
    "RKTokDiagramLaneDividerColor", "RKTokDiagramLaneDividerWidth",
    "RKTokDiagramLaneLabelFont", "RKTokDiagramLaneLabelText",
    "RKTokDiagramTimelineAxisColor", "RKTokDiagramTimelineAxisWidth",
    "RKTokDiagramTimelineDotColor", "RKTokDiagramTimelineDotRadius",
    "RKTokDiagramRoadmapAccentColor", "RKTokDiagramRoadmapAccentFont",
    "RKTokDiagramStructureCardDraw", "RKTokDiagramStructureCardFill",
    "RKTokDiagramStructureCardRounding", "RKTokDiagramStructureCardWidth",
    "RKTokDiagramStructureCardPadX", "RKTokDiagramStructureCardPadY",
    "RKTokDiagramStructureCardFont", "RKTokDiagramStructureCardText",
    "RKTokDiagramStructureTitleFont", "RKTokDiagramStructureTitleText",
    "RKTokDiagramStructureMutedFont", "RKTokDiagramStructureMutedText",
    "RKTokDiagramStructureArrowColor", "RKTokDiagramStructureArrowWidth",
    "RKTokDiagramStructureArrowTip",
    # Algorithm-visualization state grammar (reportkit-algorithm-viz.sty):
    # one Draw/Fill/Text/LineStyle group per shared semantic state, plus the
    # unmarked-cell default, so state meaning survives grayscale printing.
    "RKTokAlgorithmCellDraw", "RKTokAlgorithmCellFill", "RKTokAlgorithmCellText", "RKTokAlgorithmCellLineStyle",
    "RKTokAlgorithmCurrentDraw", "RKTokAlgorithmCurrentFill", "RKTokAlgorithmCurrentText", "RKTokAlgorithmCurrentLineStyle",
    "RKTokAlgorithmActiveDraw", "RKTokAlgorithmActiveFill", "RKTokAlgorithmActiveText", "RKTokAlgorithmActiveLineStyle",
    "RKTokAlgorithmCandidateDraw", "RKTokAlgorithmCandidateFill", "RKTokAlgorithmCandidateText", "RKTokAlgorithmCandidateLineStyle",
    "RKTokAlgorithmFrontierDraw", "RKTokAlgorithmFrontierFill", "RKTokAlgorithmFrontierText", "RKTokAlgorithmFrontierLineStyle",
    "RKTokAlgorithmVisitedDraw", "RKTokAlgorithmVisitedFill", "RKTokAlgorithmVisitedText", "RKTokAlgorithmVisitedLineStyle",
    "RKTokAlgorithmResolvedDraw", "RKTokAlgorithmResolvedFill", "RKTokAlgorithmResolvedText", "RKTokAlgorithmResolvedLineStyle",
    "RKTokAlgorithmDiscardedDraw", "RKTokAlgorithmDiscardedFill", "RKTokAlgorithmDiscardedText", "RKTokAlgorithmDiscardedLineStyle",
    "RKTokAlgorithmBlockedDraw", "RKTokAlgorithmBlockedFill", "RKTokAlgorithmBlockedText", "RKTokAlgorithmBlockedLineStyle",
    "RKTokAlgorithmUnseenDraw", "RKTokAlgorithmUnseenFill", "RKTokAlgorithmUnseenText", "RKTokAlgorithmUnseenLineStyle",
    "RKTokAlgorithmCellFont", "RKTokAlgorithmCellMinSize", "RKTokAlgorithmCellPad", "RKTokAlgorithmCellRounding",
    "RKTokAlgorithmIndexFont", "RKTokAlgorithmIndexText",
    "RKTokAlgorithmPointerColor", "RKTokAlgorithmPointerFont", "RKTokAlgorithmPointerWidth",
    "RKTokAlgorithmContainerDraw", "RKTokAlgorithmContainerWidth",
    "RKTokAlgorithmAnnotationFont", "RKTokAlgorithmAnnotationText",
    "RKTokAlgorithmRowLabelFont", "RKTokAlgorithmRowLabelText",
    "RKTokAlgorithmTraceLabelFont", "RKTokAlgorithmTraceLabelText",
    "RKTokAlgorithmTraceSeparatorColor", "RKTokAlgorithmTraceSeparatorWidth",
]

# Semantic modules that must not know any theme's name. Phase A4's diagram
# work migrated reportkit-diagrams.sty, reportkit-structure.sty,
# reportkit-process.sty and reportkit-spatial.sty to
# the same token contract reportkit-boxes.sty already used; all four are
# listed here now for the same "no \rk@theme, no theme name" guarantee.
SEMANTIC_MODULES = [
    "reportkit-boxes.sty",
    "reportkit-diagrams.sty",
    "reportkit-structure.sty",
    "reportkit-process.sty",
    "reportkit-spatial.sty",
    "reportkit-algorithm-viz.sty",
]

# Modules in the diagram-chrome family that reportkit-diagrams.sty itself
# loads (reportkit-structure.sty, reportkit-process.sty,
# reportkit-spatial.sty): they read style tokens but do not call
# \RKAssertStyleTokens themselves, because reportkit-diagrams.sty already
# asserted the contract before \RequirePackage-ing them (see that file's own
# note). Only reportkit-boxes.sty and reportkit-diagrams.sty -- the two
# entry points a theme's tokens must be loaded before -- assert directly.
MODULES_WITHOUT_OWN_ASSERTION = {
    "reportkit-structure.sty", "reportkit-process.sty", "reportkit-spatial.sty",
}

CANONICAL_THEMES = sorted({canonical_theme_name(name) for name in THEMES})


@pytest.mark.parametrize("theme_name", CANONICAL_THEMES)
def test_python_theme_exposes_complete_semantic_records(theme_name: str) -> None:
    theme = get_theme(theme_name)
    assert validate_theme_contract(theme) == []
    assert theme.geometry.text_width_in == theme.text_width_in
    assert theme.charts.base_font == theme.base_font_size
    assert theme.typography.heading
    assert theme.typography.body
    assert theme.typography.chart
    assert theme.geometry.margins_mm
    assert theme.tables.header_treatment
    assert theme.charts.grid_style
    assert theme.diagrams.node_padding[0] > 0
    assert theme.script_coverage.verified


def test_theme_alias_reuses_one_complete_record() -> None:
    assert get_theme("technical") is get_theme("default")


def _non_comment_text(path: Path) -> str:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("%")]
    return "\n".join(lines)


def test_core_declares_every_required_token_as_a_sentinel() -> None:
    core_text = (REPO / "latex_templates" / "reportkit-core.sty").read_text(encoding="utf-8")
    assert r"\RKAssertStyleTokens" in core_text
    assert r"\ifrk@styletokensloaded" in core_text
    for token in REQUIRED_STYLE_TOKENS:
        assert rf"\newcommand{{\{token}}}" in core_text, f"reportkit-core.sty is missing a sentinel for {token}"


@pytest.mark.parametrize("theme", CANONICAL_THEMES)
def test_every_canonical_theme_populates_every_required_token(theme: str) -> None:
    package = str(THEMES[theme]["common_package"])
    theme_path = REPO / "latex_templates" / "themes" / f"{package}.sty"
    assert theme_path.is_file(), f"theme {theme!r} common package does not exist: {theme_path}"
    theme_text = theme_path.read_text(encoding="utf-8")
    for token in REQUIRED_STYLE_TOKENS:
        assert rf"\renewcommand{{\{token}}}" in theme_text, (
            f"{package}.sty (theme {theme!r}) does not populate {token}"
        )
    assert r"\rk@styletokensloadedtrue" in theme_text, (
        f"{package}.sty (theme {theme!r}) never sets \\rk@styletokensloadedtrue"
    )


@pytest.mark.parametrize("module", SEMANTIC_MODULES)
def test_semantic_modules_do_not_branch_on_theme_name(module: str) -> None:
    module_path = REPO / "latex_templates" / module
    code_text = _non_comment_text(module_path)
    assert "rk@theme" not in code_text, f"{module} still branches on \\rk@theme"
    for theme in THEMES:
        assert theme not in code_text, f"{module} names theme {theme!r} directly"


def test_semantic_modules_assert_style_tokens_before_reading_them() -> None:
    for module in SEMANTIC_MODULES:
        if module in MODULES_WITHOUT_OWN_ASSERTION:
            continue
        module_text = (REPO / "latex_templates" / module).read_text(encoding="utf-8")
        assert r"\RKAssertStyleTokens" in module_text, f"{module} reads style tokens without asserting them first"


def test_diagrams_requires_the_modules_that_skip_their_own_assertion() -> None:
    # reportkit-structure.sty/-process.sty/-spatial.sty rely on
    # reportkit-diagrams.sty having already asserted the token contract --
    # confirm that load order is the one actually declared, not just assumed.
    diagrams_text = (REPO / "latex_templates" / "reportkit-diagrams.sty").read_text(encoding="utf-8")
    for module in MODULES_WITHOUT_OWN_ASSERTION:
        package = module.removesuffix(".sty")
        assert rf"\RequirePackage{{{package}}}" in diagrams_text, (
            f"reportkit-diagrams.sty no longer requires {module}; it must assert style tokens itself"
        )
