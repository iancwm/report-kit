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
]

# Semantic modules that must not know any theme's name. reportkit-diagrams.sty,
# reportkit-structure.sty, reportkit-process.sty and reportkit-spatial.sty are
# not yet migrated to the token contract (remaining A4 scope; see the
# implementation plan) and are deliberately not listed here -- adding one
# before its migration lands would make this test fail for the wrong reason.
SEMANTIC_MODULES = ["reportkit-boxes.sty"]

CANONICAL_THEMES = sorted({canonical_theme_name(name) for name in THEMES})


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
        module_text = (REPO / "latex_templates" / module).read_text(encoding="utf-8")
        assert r"\RKAssertStyleTokens" in module_text, f"{module} reads style tokens without asserting them first"
