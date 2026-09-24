"""Contract and safe-rendering coverage for callout titles."""
from __future__ import annotations

import pytest

from reportkit.authoring_ir import validate_ir
from reportkit.markdown_directives import parse_markdown
from reportkit.registry import generate_registry
from reportkit.tex_renderer import render_ir


CALLOUTS = (
    "principle",
    "decisionpoint",
    "researchproblem",
    "assumption",
    "redflag",
    "evidencenote",
    "limitationnote",
    "tipnote",
    "deliverablenote",
    "evidence",
    "limitation",
    "tip",
)


def _directive(source: str):
    parsed = parse_markdown(source, source_file="manuscript/callouts.md")
    assert not parsed.diagnostics
    assert len(parsed.directives) == 1
    return parsed


def test_callout_contract_exposes_replacement_and_legacy_title_forms() -> None:
    registry = generate_registry()
    records = registry["primitives"]["callout"]

    for name in CALLOUTS:
        record = records[name]
        assert record["signature"] == "o g"
        assert [(item["name"], item["specifier"], item["required"]) for item in record["arguments"]] == [
            ("title", "o", False),
            ("legacy_suffix", "g", False),
        ]

    metric = records["metric"]
    assert metric["signature"] == "m m"
    assert [item["name"] for item in metric["arguments"]] == ["label", "value"]


@pytest.mark.parametrize(
    ("primitive", "body", "expected"),
    [
        ("redflag", "content: Risk text", "\\begin{redflag}\nRisk text\n\\end{redflag}"),
        ("redflag", "title: Weak\ncontent: Risk text", "\\begin{redflag}[Weak]\nRisk text\n\\end{redflag}"),
        ("redflag", "legacy_suffix: Specific risk\ncontent: Risk text", "\\begin{redflag}{Specific risk}\nRisk text\n\\end{redflag}"),
        ("evidence", "title: Observed\ncontent: Evidence text", "\\begin{evidence}[Observed]\nEvidence text\n\\end{evidence}"),
        ("tip", "legacy_suffix: For operators\ncontent: Tip text", "\\begin{tip}{For operators}\nTip text\n\\end{tip}"),
    ],
)
def test_callout_directives_render_the_exact_title_form(primitive: str, body: str, expected: str) -> None:
    parsed = _directive(f"```reportkit {primitive}\n{body}\n```\n")
    rendered = render_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )[parsed.directives[0].placeholder or ""]
    assert rendered == expected


def test_empty_replacement_title_emits_default_resolving_form() -> None:
    parsed = _directive("```reportkit redflag\ntitle:\ncontent: Risk text\n```\n")
    rendered = render_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )[parsed.directives[0].placeholder or ""]
    assert rendered == "\\begin{redflag}[]\nRisk text\n\\end{redflag}"


def test_callout_title_and_body_text_are_tex_escaped() -> None:
    parsed = _directive(
        "```reportkit redflag\n"
        "title: Weak & narrow\n"
        "content: 100% & safe_\n"
        "```\n"
    )
    rendered = render_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )[parsed.directives[0].placeholder or ""]
    assert "[Weak \\& narrow]" in rendered
    assert "100\\% \\& safe\\_" in rendered


def test_replacement_and_legacy_titles_are_mutually_exclusive() -> None:
    parsed = _directive(
        "```reportkit redflag\n"
        "title: Weak\n"
        "legacy_suffix: Specific risk\n"
        "content: Risk text\n"
        "```\n"
    )
    diagnostics = validate_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )
    assert [item["code"] for item in diagnostics] == ["RK_AUTHORING_CALLOUT_TITLE_COLLISION"]


def test_metric_keeps_its_label_value_contract() -> None:
    parsed = _directive("```reportkit metric\nlabel: Users\nvalue: 42\n```\n")
    rendered = render_ir(
        parsed.ir,
        publication_type="technical-report",
        theme="default",
        renderer="paged",
    )[parsed.directives[0].placeholder or ""]
    assert rendered == "\\begin{metric}{Users}{42}\n\\end{metric}"


@pytest.mark.parametrize(
    "theme_options",
    ["theme=default,publication-type=technical-report", "theme=institutional-research,publication-type=equity-research"],
)
def test_all_callout_title_forms_compile_under_both_paged_themes(compile_doc, theme_options: str) -> None:
    body: list[str] = []
    for primitive in CALLOUTS:
        body.extend(
            [
                f"\\begin{{{primitive}}}\nNo title body.\n\\end{{{primitive}}}",
                f"\\begin{{{primitive}}}[Override]\nReplacement body.\n\\end{{{primitive}}}",
                f"\\begin{{{primitive}}}{{Legacy}}\nLegacy body.\n\\end{{{primitive}}}",
            ]
        )
    body.append("\\begin{metric}{Users}{42}\n\\end{metric}")
    document = compile_doc("\n\n".join(body), name="callout-title-forms", class_options=theme_options)
    text = "\n".join(page.get_text() for page in document)
    assert "OVERRIDE" in text
    assert "LEGACY" in text
    assert "METRIC" in text
    assert "42" in text
