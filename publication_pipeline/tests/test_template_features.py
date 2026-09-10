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
