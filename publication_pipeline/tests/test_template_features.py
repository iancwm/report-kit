from pathlib import Path
import shutil

import pytest
import subprocess


def test_pandoc_feature_fixture_emits_supported_constructs():
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")
    fixture = Path(__file__).parent / "fixtures" / "markdown-features.md"
    result = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", str(fixture)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "tight list" in output
    assert "longtable" in output
    assert "verbatim" in output or "Highlighting" in output
    assert "href" in output
    assert "footnote" in output
