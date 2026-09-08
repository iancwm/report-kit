from pathlib import Path

from python_scripts.reportkit.authoring import render_links_tex, validate_authoring


def test_source_model_and_links_validate(tmp_path: Path) -> None:
    (tmp_path / "sources.yaml").write_text(
        "sources:\n"
        "  source_001:\n"
        "    type: ai_output\n"
        "    title: Interview notes\n"
        "    file: notes.md\n"
        "    links:\n"
        "      - docs\n"
        "chapters:\n"
        "  - id: intro\n"
        "    title: Introduction\n"
        "    purpose: Orient the reader\n"
        "    sources:\n"
        "      - source_001\n",
        encoding="utf-8",
    )
    (tmp_path / "links.yaml").write_text(
        "links:\n"
        "  docs:\n"
        "    url: https://example.com/docs\n"
        "    label: Documentation\n"
        "    type: documentation\n",
        encoding="utf-8",
    )
    result = validate_authoring(tmp_path)
    assert result.ok, result.errors
    output = tmp_path / "links.tex"
    render_links_tex(tmp_path / "links.yaml", output)
    assert "Documentation" in output.read_text(encoding="utf-8")
    assert "\\RKLink" in output.read_text(encoding="utf-8")
