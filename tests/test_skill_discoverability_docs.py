from __future__ import annotations

from pathlib import Path

from reportkit.markdown_forms import MARKDOWN_FORMS_DOCS


REPO = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def test_markdown_authoring_reference_covers_every_form() -> None:
    text = _read(MARKDOWN_FORMS_DOCS)
    for needle in (
        "## Markdown forms", "## Project files", "## Brand overrides", "## Direct TeX projects",
        "[[REPORTKIT-VISUAL:fig:", "fragments/fig-", "[[REPORTKIT-IMAGE:img:", "```reportkit",
        "links.yaml", "sources.yaml", "brand:", "venture", "RK_IMAGE_SLOTS_TEX_MODE",
        "callouts-and-image-slots.md",
    ):
        assert needle in text, needle


def test_image_slot_guide_states_markdown_only_and_credit_rule() -> None:
    text = _read("references/callouts-and-image-slots.md")
    assert "Image slots are Markdown-only" in text
    assert "RK_IMAGE_SLOTS_TEX_MODE" in text
    assert "do not add `\\source{...}`" in text


def test_format_guides_route_photographs() -> None:
    feature = _read("references/feature-article-authoring.md")
    assert "## Photographs and illustrations" in feature
    assert "openingvisual" in feature and "Image slots are Markdown-only" in feature
    for guide in ("references/presentation-authoring.md", "references/book-authoring.md"):
        text = _read(guide)
        assert "## Photographs and illustrations" in text, guide
        assert "markdown-authoring.md" in text, guide
    assert "brand-overrides" in _read("references/presentation-authoring.md")
