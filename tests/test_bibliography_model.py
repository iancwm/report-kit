"""Bibliography settings, .bib key scanning and citation extraction."""
from __future__ import annotations

from pathlib import Path

import pytest

from reportkit.bibliography import (
    BibliographyConfigError,
    bibliography_diagnostics,
    markdown_citation_keys,
    resolve_bibliography,
    scan_bib_keys,
    tex_citation_keys,
)
from reportkit.config import load_publication_config
from reportkit.publications import PUBLICATION_TYPES

EXPECTED_DEFAULTS = {
    "technical-report": ("numeric", "References", "Contents"),
    "book": ("author-year", "References", "Contents"),
    "feature-article": ("author-year", "References", "In this issue"),
    "executive-brief": ("numeric", "Sources", "Contents"),
    "equity-research": ("author-year", "Sources", "In this report"),
    "presentation": ("numeric", "References", "Agenda"),
}


def test_every_publication_type_declares_reference_and_contents_defaults() -> None:
    for name, (style, title, contents) in EXPECTED_DEFAULTS.items():
        record = PUBLICATION_TYPES[name]
        assert record["bibliography_style"] == style
        assert record["bibliography_title"] == title
        assert record["contents_title"] == contents


def _write_config(root: Path, body: str) -> dict:
    (root / "publication.yaml").write_text("publication:\n  title: T\n" + body, encoding="utf-8")
    return load_publication_config(root / "publication.yaml")


def test_unconfigured_project_has_no_bibliography(tmp_path: Path) -> None:
    config = _write_config(tmp_path, "")
    assert resolve_bibliography(config, None, "book", tmp_path) is None


def test_type_defaults_apply_when_style_and_title_are_omitted(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    settings = resolve_bibliography(config, None, "book", tmp_path)
    assert settings is not None
    assert (settings.style, settings.title, settings.stem) == ("author-year", "References", "references")
    assert settings.include_uncited is False


def test_overrides_and_profile_override(tmp_path: Path) -> None:
    (tmp_path / "refs").mkdir()
    (tmp_path / "refs" / "main.bib").write_text("", encoding="utf-8")
    config = _write_config(
        tmp_path,
        "bibliography:\n  file: refs/main.bib\n  style: numeric\n  title: Works cited\n  include_uncited: true\n"
        "profiles:\n  final:\n    bibliography:\n      style: author-year\n",
    )
    draft = resolve_bibliography(config, None, "book", tmp_path)
    final = resolve_bibliography(config, "final", "book", tmp_path)
    assert (draft.style, draft.title, draft.stem, draft.include_uncited) == ("numeric", "Works cited", "refs/main", True)
    assert final.style == "author-year"


def test_unknown_bibliography_key_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bibliography.format"):
        _write_config(tmp_path, "bibliography:\n  file: r.bib\n  format: apa\n")


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("bibliography:\n  file: missing.bib\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: ../outside.bib\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: 'my refs.bib'\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  style: numeric\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: references.bib\n  style: apa\n", "RK_BIBLIOGRAPHY_STYLE_INVALID"),
    ],
)
def test_invalid_configuration_raises_coded_error(tmp_path: Path, body: str, code: str) -> None:
    (tmp_path / "references.bib").write_text("", encoding="utf-8")
    (tmp_path / "my refs.bib").write_text("", encoding="utf-8")
    config = _write_config(tmp_path, body)
    with pytest.raises(BibliographyConfigError) as excinfo:
        resolve_bibliography(config, None, "technical-report", tmp_path)
    assert excinfo.value.code == code


def test_scan_bib_keys_handles_real_world_exports() -> None:
    text = (
        "% Zotero export\n"
        "@string{jan = \"January\"}\n"
        "@Comment{jabref-meta: databaseType:bibtex;}\n"
        "@preamble{\"\\newcommand{\\noop}[1]{}\"}\n"
        "@Article{smith:2024-a,\n  title={One}}\n"
        "@BOOK{ Jones.2019 ,\n  title={Two}}\n"
        "@misc(paren_key, title={Three})\n"
        "@article{smith:2024-a, title={Dup}}\n"
    )
    assert scan_bib_keys(text) == [("smith:2024-a", 5), ("Jones.2019", 7), ("paren_key", 9), ("smith:2024-a", 10)]


def test_markdown_citation_keys_ignore_code_and_email() -> None:
    text = (
        "As shown [@smith:2024-a; @jones2019, p. 3] and @lee2020 argues.\n"
        "Write to someone@example.com about it.\n"
        "Inline `@notacite` code.\n"
        "```\n@alsonot\n```\n"
        "Suppressed author [-@kim2021].\n"
    )
    assert markdown_citation_keys(text) == [
        ("smith:2024-a", 1), ("jones2019", 1), ("lee2020", 1), ("kim2021", 7),
    ]


def test_tex_citation_keys_cover_natbib_forms_and_skip_comments() -> None:
    text = (
        "See \\citep[p.~3]{a,b} and \\citet*{c}.\n"
        "% \\citep{commented}\n"
        "\\citealp{d} \\cite{e} \\citeauthor{f} \\citeyearpar[see][]{g}\n"
        "\\nocite{*}\n"
    )
    assert tex_citation_keys(text) == [("a", 1), ("b", 1), ("c", 1), ("d", 3), ("e", 3), ("f", 3), ("g", 3)]


def _md_project(root: Path, manuscript: str, *, bib: str | None, yaml_extra: str = "") -> tuple[dict, dict]:
    (root / "manuscript").mkdir()
    (root / "manuscript" / "01.md").write_text(manuscript, encoding="utf-8")
    if bib is not None:
        (root / "references.bib").write_text(bib, encoding="utf-8")
        yaml_extra = "bibliography:\n  file: references.bib\n" + yaml_extra
    config = _write_config(root, "document:\n  publication_type: technical-report\n  source_mode: markdown\n" + yaml_extra)
    return config, {"publication_type": "technical-report", "source_mode": "markdown", "main": "report.tex"}


def _codes(diagnostics: list[dict]) -> list[tuple[str, str]]:
    return [(item["code"], item["severity"]) for item in diagnostics]


def test_clean_project_has_no_bibliography_diagnostics(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "Cited [@a].\n", bib="@book{a, title={A}}\n")
    assert bibliography_diagnostics(tmp_path, config, None, document) == []


def test_undefined_citation_is_an_error_with_location(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "Intro.\nCited [@missing].\n", bib="@book{a, title={A}}\n")
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_CITATION_UNDEFINED", "error")]
    assert diagnostics[0]["source"]["file"] == "manuscript/01.md"
    assert diagnostics[0]["source"]["line"] == 2


def test_duplicate_bib_key_is_an_error(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib="@book{a, title={A}}\n@misc{a, title={B}}\n")
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_BIBLIOGRAPHY_DUPLICATE_KEY", "error")]


def test_citations_without_bibliography_section_are_an_error(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib=None)
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_CITATION_WITHOUT_BIBLIOGRAPHY", "error")]


def test_config_errors_surface_as_configuration_diagnostics(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib="", yaml_extra="  style: apa\n")
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_BIBLIOGRAPHY_STYLE_INVALID", "error")]
    assert diagnostics[0]["type"] == "configuration_error"


def test_tex_source_without_rkbibliography_warns(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    (tmp_path / "report.tex").write_text("\\documentclass{reportkit}\n\\begin{document}\n\\citep{a}\n\\end{document}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    document = {"publication_type": "technical-report", "source_mode": "tex", "main": "report.tex"}
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_BIBLIOGRAPHY_NOT_PLACED", "warning")]


def test_tex_fragments_are_scanned(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    (tmp_path / "report.tex").write_text("\\citep{a}\n\\RKBibliography\n", encoding="utf-8")
    (tmp_path / "fragments").mkdir()
    (tmp_path / "fragments" / "fig-x.tex").write_text("\\citet{nope}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    document = {"publication_type": "technical-report", "source_mode": "tex", "main": "report.tex"}
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_CITATION_UNDEFINED", "error")]
    assert diagnostics[0]["source"]["file"] == "fragments/fig-x.tex"


from reportkit.markdown_directives import parse_markdown
from reportkit.tex_renderer import render_ir


def test_references_and_contents_directives_render_engine_commands() -> None:
    text = "```reportkit contents\n```\n\nBody.\n\n```reportkit references\ntitle: Works cited\n```\n"
    parsed = parse_markdown(text)
    assert [node.primitive for node in parsed.directives] == ["RKContents", "RKBibliography"]
    rendered = list(render_ir(parsed.ir, publication_type="technical-report", theme="default", renderer="paged").values())
    assert rendered[0].startswith("\\RKContents")
    assert rendered[1] == "\\RKBibliography[Works cited]"
