"""Presentation-specific constrained-authoring tests."""
from __future__ import annotations

from reportkit.authoring_ir import validate_ir
from reportkit.markdown_directives import parse_markdown
from reportkit.registry import generate_registry
from reportkit.tex_renderer import render_ir


def _fenced(name: str, body: str) -> str:
    fence = chr(96) * 3
    return f"{fence}reportkit {name}\n{body}\n{fence}\n"


def test_assertionslide_accepts_friendly_kicker_and_renders_the_options_slot() -> None:
    parsed = parse_markdown(
        _fenced(
            "assertionslide",
            "kicker: Context\n"
            "assertion: Evidence should dominate the working slide.\n"
            "deck: Keep the body at its semantic size.",
        ),
        source_file="manuscript/01.md",
    )
    errors = validate_ir(
        parsed.ir,
        publication_type="presentation",
        theme="executive",
        renderer="slides",
        registry=generate_registry(),
    )
    assert errors == []
    rendered = render_ir(
        parsed.ir,
        renderer="slides",
        registry=generate_registry(),
    )
    output = next(iter(rendered.values()))
    assert r"\begin{assertionslide}[kicker={Context}]{Evidence should dominate the working slide.}[Keep the body at its semantic size.]" in output


def test_assertionslide_long_text_is_advisory_not_an_authoritative_tex_fit() -> None:
    long_assertion = " ".join(["This assertion needs rewriting"] * 20)
    parsed = parse_markdown(
        _fenced("assertionslide", f"assertion: {long_assertion}"),
        source_file="manuscript/long.md",
    )
    diagnostics = validate_ir(
        parsed.ir,
        publication_type="presentation",
        theme="executive",
        renderer="slides",
        registry=generate_registry(),
    )
    assert any(item["code"] == "RK_AUTHORING_PRESENTATION_ASSERTION_ADVISORY" for item in diagnostics)
    assert all(item["details"].get("authoritative") is False for item in diagnostics if item["code"] == "RK_AUTHORING_PRESENTATION_ASSERTION_ADVISORY")


def test_assertionslide_does_not_accept_raw_tex_escape_hatches() -> None:
    parsed = parse_markdown(
        _fenced("assertionslide", r"assertion: Safe text\nraw_tex: \textbf{unsafe}"),
        source_file="manuscript/unsafe.md",
    )
    diagnostics = validate_ir(
        parsed.ir,
        publication_type="presentation",
        theme="executive",
        renderer="slides",
        registry=generate_registry(),
    )
    assert any(item["code"] == "RK_AUTHORING_RAW_TEX_FORBIDDEN" for item in diagnostics)
