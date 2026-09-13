from pathlib import Path
import shutil
import subprocess

import pytest


def test_pandoc_feature_fixture_emits_supported_constructs():
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc is not installed")
    fixture = Path(__file__).parent / "fixtures" / "markdown-features.md"
    result = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", str(fixture)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "tight list" in output
    assert "longtable" in output
    assert "verbatim" in output or "Highlighting" in output
    assert "href" in output
    assert "footnote" in output


def test_reportkit_pandoc_sets_proportional_graphics_defaults():
    preamble = (Path(__file__).resolve().parents[2] / "latex_templates" / "reportkit-pandoc.sty").read_text(encoding="utf-8")
    assert r"\def\maxwidth" in preamble
    assert r"\def\maxheight" in preamble
    assert r"\setkeys{Gin}{width=\maxwidth,height=\maxheight,keepaspectratio}" in preamble


def test_title_page_does_not_draw_rule_when_author_is_empty():
    template = (Path(__file__).resolve().parents[2] / "latex_templates" / "reportkit-longform.sty").read_text(encoding="utf-8")
    assert r"\ifx\@author\@empty" in template
    assert r"\rule{0.62\textwidth}{0.5pt}" in template


def test_publication_template_sets_empty_author_and_date_macros():
    template = (Path(__file__).resolve().parents[1] / "templates" / "publication-template.tex").read_text(encoding="utf-8")
    assert r"\detokenize\expandafter{\RKPubAuthor}" in template
    assert r"\author{}\else\author{\RKPubAuthor}" in template
    assert r"\date{}\else\date{\RKPubDate}" in template
