from __future__ import annotations

import re
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


def _skill_links() -> list[str]:
    return [
        link for link in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", _read("SKILL.md"))
        if not link.startswith(("http://", "https://"))
    ]


def test_every_skill_link_resolves() -> None:
    assert [link for link in _skill_links() if not (REPO / link).exists()] == []


def test_stop_rule_admits_markdown_forms() -> None:
    skill = _read("SKILL.md")
    assert "Use only primitives and Markdown forms listed by" in skill
    assert "Use only primitives listed by" not in skill


def test_loop_includes_preflight_inspect_and_diagnose() -> None:
    skill = _read("SKILL.md")
    assert "| Preflight | `reportkit doctor --require full-build --json`" in skill
    assert "reportkit inspect" in skill
    assert "reportkit diagnose" in skill
    assert "image_caveat" in skill


def test_skill_routes_images_and_project_files() -> None:
    skill = _read("SKILL.md")
    for reference in (
        "references/markdown-authoring.md", "references/licensing.md", "references/accessibility-tagging.md",
    ):
        assert f"]({reference}" in skill, reference
    assert "image slot" in skill
    assert "not `\\source`" in skill
