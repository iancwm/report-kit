"""Focused tests for the constrained Markdown authoring path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reportkit.authoring import validate_authoring
from reportkit.authoring_ir import validate_ir
from reportkit.markdown_directives import parse_markdown
from reportkit.tex_renderer import render_ir


def test_reportkit_fence_is_removed_from_pandoc_input_but_ordinary_markdown_is_not() -> None:
    parsed = parse_markdown(
        "# Deck\n\nordinary *Markdown*\n\n"
        "```reportkit messageslide\nheadline: Margin & mix\n```\n",
        source_file="manuscript/01-deck.md",
    )

    assert "ordinary *Markdown*" in parsed.markdown
    assert "```reportkit" not in parsed.markdown
    assert len(parsed.directives) == 1
    node = parsed.directives[0]
    assert node.primitive == "messageslide"
    assert node.arguments == {"headline": "Margin & mix"}
    assert node.source.as_dict() == {"file": "manuscript/01-deck.md", "line": 5, "line_end": 7}


def test_three_directive_errors_are_collected_without_external_commands() -> None:
    parsed = parse_markdown(
        "```reportkit messageslids\nheadline: typo\n```\n\n"
        "```reportkit metric\nlabel: missing value\n```\n\n"
        "```reportkit titleslide\n```\n",
        source_file="manuscript/errors.md",
    )

    diagnostics = validate_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )

    assert len(diagnostics) == 3
    assert {item["code"] for item in diagnostics} == {
        "RK_AUTHORING_UNKNOWN_PRIMITIVE",
        "RK_AUTHORING_MISSING_ARGUMENTS",
        "RK_AUTHORING_UNAVAILABLE_PRIMITIVE",
    }
    assert all(item["source"]["file"] == "manuscript/errors.md" for item in diagnostics)
    assert all(item["source"]["line"] >= 1 for item in diagnostics)
    assert "messageslide" in diagnostics[0]["candidates"]
    assert diagnostics[1]["details"]["expected"] == ["label", "value"]


def test_validate_authoring_reads_directives_without_pandoc_or_tex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manuscript = tmp_path / "manuscript"
    manuscript.mkdir()
    (manuscript / "01.md").write_text(
        "```reportkit messageslids\nheadline: typo\n```\n", encoding="utf-8",
    )
    called = False

    def fail(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("validation must not invoke a subprocess")

    monkeypatch.setattr("subprocess.run", fail)
    result = validate_authoring(tmp_path)

    assert not result.ok
    assert result.documents["manuscript/01.md"].nodes[0].primitive == "messageslids"
    assert result.diagnostics[0]["code"] == "RK_AUTHORING_UNKNOWN_PRIMITIVE"
    assert called is False


def test_renderer_escapes_arguments_and_allows_only_explicit_trusted_fragments(tmp_path: Path) -> None:
    (tmp_path / "fragments").mkdir()
    (tmp_path / "fragments" / "fig-growth.tex").write_text(
        "\\begin{diagram}[description={trusted}]\nraw & TeX\n\\end{diagram}\n",
        encoding="utf-8",
    )
    parsed = parse_markdown(
        "```reportkit fullvisual\ncaption: 100% & safe_\nfragment: fragments/fig-growth\n```\n",
        source_file="manuscript/deck.md",
    )

    rendered = render_ir(
        parsed.ir,
        fragment_root=tmp_path,
        publication_type="presentation",
        theme="executive",
        renderer="slides",
    )[parsed.directives[0].placeholder or ""]

    assert rendered.startswith("\\begin{frame}\n\\begin{fullvisual}[100\\% \\& safe\\_][]")
    assert "100\\% \\& safe\\_" in rendered
    assert "\\begin{diagram}[description={trusted}]" in rendered
    assert "raw & TeX" in rendered
    assert "\\end{frame}" in rendered


def test_unsafe_fragment_is_a_security_diagnostic(tmp_path: Path) -> None:
    parsed = parse_markdown(
        "```reportkit fullvisual\nfragment: ../secret.tex\n```\n",
        source_file="manuscript/deck.md",
    )
    diagnostics = validate_ir(
        parsed.ir,
        publication_type="presentation",
        theme="executive",
        renderer="slides",
        root=tmp_path,
    )

    assert any(item["code"] == "RK_AUTHORING_UNSAFE_FRAGMENT" for item in diagnostics)
    assert any(item["type"] == "security_violation" for item in diagnostics)


def test_authoring_ir_schema_accepts_serialized_directive() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "reportkit-authoring.schema.json").read_text(encoding="utf-8"),
    )
    parsed = parse_markdown("```reportkit herometric\nvalue: 42\nlabel: Users\n```\n", source_file="deck.md")
    jsonschema.Draft202012Validator(schema).validate(parsed.ir.as_dict())
