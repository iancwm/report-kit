from __future__ import annotations

from pathlib import Path

from reportkit.authoring import LINK_TYPES, validate_authoring
from reportkit.context import build_context
from reportkit.context_budget import build_context_slice
from reportkit.image_slots import ASPECT_RATIOS, IMAGE_FIELDS, IMAGE_SENTINEL_RE, IMAGE_SLOTS_FILENAME
from reportkit.markdown_directives import parse_markdown
from reportkit.markdown_forms import MARKDOWN_FORMS_DOCS, markdown_forms
from reportkit.publication_validation import SENTINEL_RE


REPO = Path(__file__).resolve().parents[1]


def _form(name: str) -> dict:
    return next(form for form in markdown_forms()["forms"] if form["name"] == name)


def test_primitives_slice_lists_markdown_forms() -> None:
    content = build_context_slice(build_context(REPO), "primitives")["content"]
    forms = content["markdown_forms"]
    assert forms["source_modes"] == ["markdown"]
    assert forms["docs"] == MARKDOWN_FORMS_DOCS == "references/markdown-authoring.md"
    assert [form["name"] for form in forms["forms"]] == ["directive", "visual", "image_slot", "links", "sources"]
    assert all(form["rules"] for form in forms["forms"])


def test_directive_example_parses_without_diagnostics() -> None:
    parsed = parse_markdown(_form("directive")["example"] + "\n")
    assert parsed.diagnostics == ()
    assert [node.primitive for node in parsed.directives] == ["redflag"]


def test_visual_and_image_examples_match_the_validator_markers() -> None:
    assert SENTINEL_RE.fullmatch(_form("visual")["example"])
    assert IMAGE_SENTINEL_RE.fullmatch(_form("image_slot")["example"])


def test_image_slot_form_mirrors_the_manifest_contract() -> None:
    form = _form("image_slot")
    assert form["requires"][0] == IMAGE_SLOTS_FILENAME
    assert form["fields"] == list(IMAGE_FIELDS)
    assert form["aspect_ratios"] == list(ASPECT_RATIOS)


def test_project_file_examples_validate(tmp_path: Path) -> None:
    assert _form("links")["types"] == sorted(LINK_TYPES)
    (tmp_path / "links.yaml").write_text(_form("links")["example"], encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(_form("sources")["example"], encoding="utf-8")
    result = validate_authoring(tmp_path)
    assert result.ok, result.errors
    assert result.links == ["field-survey-data"]
    assert result.sources == ["field-survey"]
