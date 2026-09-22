"""Static contract tests for dense presentation compositions."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRESENTATION = REPO / "latex_templates" / "publication_types" / "reportkit-presentation.sty"
CORE = REPO / "latex_templates" / "reportkit-core.sty"
ADAPTER = REPO / "latex_templates" / "themes" / "reportkit-theme-executive-slides.sty"


def _source_without_comments(path: Path) -> str:
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("%")
    )


def test_cardgrid_contract_is_theme_neutral_and_semantic() -> None:
    source = _source_without_comments(PRESENTATION)
    assert "\\NewDocumentEnvironment{cardgrid}" in source
    assert "\\NewDocumentCommand{\\carditem}" in source
    assert "executive" not in source
    assert "\\RKTokPresentationCardGutter" in source
    assert "\\RKTokPresentationDenseBodyFont" in source
    for variant in ("plain", "surface", "accent-rail", "numbered", "emphasis"):
        assert variant in PRESENTATION.read_text(encoding="utf-8")


def test_dense_tokens_are_declared_and_populated_by_slides_adapter() -> None:
    core = CORE.read_text(encoding="utf-8")
    adapter = ADAPTER.read_text(encoding="utf-8")
    for token in (
        "RKTokPresentationDenseBodyFont",
        "RKTokPresentationAnnotationFont",
        "RKTokPresentationSourceFont",
        "RKTokPresentationCardGutter",
        "RKTokPresentationCardPadding",
        "RKTokPresentationCardMinHeight",
        "RKTokPresentationCardRuleWidth",
        "RKTokPresentationProseWidth",
    ):
        assert f"\\newcommand{{\\{token}}}" in core
        assert f"\\renewcommand{{\\{token}}}" in adapter
