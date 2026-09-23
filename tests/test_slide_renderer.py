"""Phase B/C (slide renderer, presentation semantics, and executive theme)
of the multi-format publication architecture spec: the "slides" renderer,
"presentation" publication type, and stable "executive" theme, plus decision D5's
canvas/paper rules. See tests/test_theme_contract.py for the shared
callout/metric style-token contract (executive is automatically covered
there once it's a canonical theme) and the implementation plan's B1-B3
sections for the compiled-fixture verification record this file's static
checks complement, not replace.
"""
from __future__ import annotations

from pathlib import Path
import re

import pytest

from reportkit.publications import (
    PUBLICATION_TYPES,
    RENDERERS,
    THEMES,
    PublicationRegistryError,
    check_publication_registry,
    resolve_build_target,
)

REPO = Path(__file__).resolve().parents[1]


def test_slides_renderer_is_registered() -> None:
    renderer = RENDERERS["slides"]
    assert renderer["class_adapter"] == "reportkit-slides"
    assert renderer["pandoc_writer"] == "beamer"
    assert renderer["geometry"]["kind"] == "canvas"
    assert renderer["geometry"]["canvas"] == {"width_mm": 160, "height_mm": 90}


def test_executive_theme_requires_lualatex_and_slides_adapter() -> None:
    theme = THEMES["executive"]
    assert theme["required_engine"] == "lualatex"
    assert theme["renderers"] == ["slides"]
    assert theme["renderer_adapters"]["slides"] == "reportkit-theme-executive-slides"
    assert theme["stability"] == "stable"


def test_presentation_publication_type_pairs_with_both_slide_themes() -> None:
    # Phase D: executive and venture share this one publication type; a
    # venture-specific publication type would mean the abstraction failed.
    presentation = PUBLICATION_TYPES["presentation"]
    assert presentation["renderer"] == "slides"
    assert presentation["themes"] == ["executive", "venture"]
    assert presentation["default_target"] == {"theme": "executive"}
    assert "paper" not in presentation


def test_publication_registry_is_internally_consistent() -> None:
    assert check_publication_registry(REPO) == []


def test_resolve_build_target_for_presentation_has_canvas_not_paper() -> None:
    target = resolve_build_target("presentation", "executive", engine="lualatex", repo_root=REPO)
    assert target.renderer == "slides"
    assert target.class_name == "reportkit-slides"
    assert target.paper is None
    assert target.canvas == {"width_mm": 160, "height_mm": 90}
    assert target.geometry["paper"] is None
    assert target.common_package == "reportkit-theme-executive"
    assert target.renderer_adapter == "reportkit-theme-executive-slides"
    assert target.accessibility["tagged_pdf"] == "unsupported"


def test_explicit_paper_for_a_canvas_renderer_is_a_configuration_error() -> None:
    """Decision D5: paper is a paged-only concept. An explicitly configured
    document.paper for a canvas (slides) renderer must fail loudly, not be
    silently dropped."""
    with pytest.raises(PublicationRegistryError, match="canvas renderer"):
        resolve_build_target("presentation", "executive", explicit_paper="a4", engine="lualatex", repo_root=REPO)


def test_technical_report_still_resolves_a4_paper_unaffected() -> None:
    """The D5 canvas/paper split must not change paged behavior."""
    target = resolve_build_target("technical-report", "default", repo_root=REPO)
    assert target.paper == "a4"
    assert target.canvas is None


def test_presentation_is_rejected_for_a_paged_theme() -> None:
    with pytest.raises(PublicationRegistryError):
        resolve_build_target("presentation", "default", repo_root=REPO)


def test_technical_report_is_rejected_for_the_slides_theme() -> None:
    with pytest.raises(PublicationRegistryError):
        resolve_build_target("technical-report", "executive", repo_root=REPO)


def test_reportkit_slides_cls_declares_the_canvas_aspect_ratio() -> None:
    cls_text = (REPO / "latex_templates" / "reportkit-slides.cls").read_text(encoding="utf-8")
    assert "aspectratio=169" in cls_text
    assert r"\RKValidateSelection" in cls_text
    assert r"\RKAssertRendererHooks" in cls_text


def test_reportkit_slides_core_implements_every_renderer_hook() -> None:
    core_text = (REPO / "latex_templates" / "reportkit-slides-core.sty").read_text(encoding="utf-8")
    for hook in (
        r"\renewcommand{\RKReserveSpace}",
        r"\renewcommand{\RKDiagramPlacementBegin}",
        r"\renewcommand{\RKDiagramPlacementEnd}",
        r"\renewcommand{\RKDiagramCaption}",
        r"\renewcommand{\RKDiagramSource}",
    ):
        assert hook in core_text, f"reportkit-slides-core.sty is missing {hook}"
    assert r"\rk@rendererhooksloadedtrue" in core_text
    # D8: decorative navigation is disabled in the public composition API.
    assert r"\setbeamertemplate{navigation symbols}{}" in core_text
    # Never loads paged-only mechanics (this file's own header explains why).
    for paged_package in ("{geometry}", "{fancyhdr}", "{titlesec}", "{needspace}"):
        assert f"\\RequirePackage{paged_package}" not in core_text


def test_reportkit_presentation_asserts_its_own_token_contract() -> None:
    presentation_text = (
        REPO / "latex_templates" / "publication_types" / "reportkit-presentation.sty"
    ).read_text(encoding="utf-8")
    assert r"\RKAssertPresentationTokens" in presentation_text
    # B2: composition, not a hardcoded theme name (comments may still discuss
    # "executive" as an example -- only the code must stay theme-agnostic).
    code_lines = [line for line in presentation_text.splitlines() if not line.lstrip().startswith("%")]
    assert "executive" not in "\n".join(code_lines)


@pytest.mark.parametrize("adapter", ["reportkit-theme-executive-slides", "reportkit-theme-venture-slides"])
def test_slides_adapters_populate_every_presentation_token(adapter: str) -> None:
    adapter_text = (REPO / "latex_templates" / "themes" / f"{adapter}.sty").read_text(encoding="utf-8")
    core_text = (REPO / "latex_templates" / "reportkit-core.sty").read_text(encoding="utf-8")
    declared = set(re.findall(r"\\newcommand\{\\(RKTokPresentation[A-Za-z]+)\}", core_text))
    assert "RKTokPresentationSurface" in declared
    for token in sorted(declared):
        assert re.search(rf"\\renewcommand\{{\\{token}\}}", adapter_text), f"{adapter} is missing {token}"
    required_tokens = [
        "RKTokPresentationKickerFont", "RKTokPresentationTitleFont", "RKTokPresentationSubtitleFont",
        "RKTokPresentationDividerTitleFont", "RKTokPresentationMessageFont", "RKTokPresentationBodyFont",
        "RKTokPresentationCaptionFont", "RKTokPresentationHeroValueFont", "RKTokPresentationHeroLabelFont",
        "RKTokPresentationColumnHeadingFont", "RKTokPresentationClosingFont", "RKTokPresentationRuleWidth",
    ]
    for token in required_tokens:
        assert rf"\renewcommand{{\{token}}}" in adapter_text, f"missing {token}"
    assert r"\rk@presentationtokensloadedtrue" in adapter_text


def test_core_declares_presentation_token_sentinels_separately_from_style_tokens() -> None:
    """Paged themes (default, institutional-research) must never be forced
    to populate slide-only tokens -- the two contracts use separate
    assertion gates (reportkit-core.sty's own comment explains why)."""
    core_text = (REPO / "latex_templates" / "reportkit-core.sty").read_text(encoding="utf-8")
    assert r"\RKAssertPresentationTokens" in core_text
    assert r"\ifrk@presentationtokensloaded" in core_text
    for theme_file in ("reportkit-theme-default.sty", "reportkit-theme-institutional-research.sty"):
        theme_text = (REPO / "latex_templates" / "themes" / theme_file).read_text(encoding="utf-8")
        assert "RKTokPresentation" not in theme_text, f"{theme_file} should not need presentation tokens"


# -----------------------------------------------------------------------------
# B3: slide visualization slots
# -----------------------------------------------------------------------------
def test_executive_figure_sizes_are_slide_slots_only() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    from reportkit.themes import get_theme

    theme = get_theme("executive")
    assert set(theme.figure_sizes) == {"slide-main", "slide-half", "slide-hero"}
    # Every slot must fit inside the declared 160mm x 90mm canvas.
    canvas_width_in = 160 / 25.4
    canvas_height_in = 90 / 25.4
    for name, (width_in, height_in) in theme.figure_sizes.items():
        assert 0 < width_in <= canvas_width_in, f"{name} width exceeds the canvas"
        assert 0 < height_in <= canvas_height_in, f"{name} height exceeds the canvas"


@pytest.mark.parametrize("theme_name", ["default", "technical", "institutional-research"])
def test_no_paged_theme_gains_accidental_slide_dimensions(theme_name: str) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    from reportkit.themes import get_theme

    theme = get_theme(theme_name)
    slide_keys = {key for key in theme.figure_sizes if key.startswith("slide-")}
    assert slide_keys == set(), f"{theme_name} unexpectedly has slide-* figure sizes: {slide_keys}"
    # The seven pre-Phase-B paged names must be unaffected (value-preserving).
    assert set(theme.figure_sizes) == {"full", "wide", "dominant", "compact", "square", "half", "sidebar"}


def test_unknown_theme_fails_explicitly_not_silently() -> None:
    from reportkit.themes import get_theme

    with pytest.raises(ValueError, match="executive-vip"):
        get_theme("executive-vip")


def test_executive_theme_palette_matches_its_latex_theme_file() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz as rkv
    from reportkit.themes import get_theme

    theme = get_theme("executive")
    sty_path = REPO / "latex_templates" / "themes" / "reportkit-theme-executive.sty"
    assert rkv.validate_palette_against_latex(sty_path, theme.latex_colors) == []
