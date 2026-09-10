from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))
from license_metadata import load_license_metadata, rights_notice
from license_metadata import validate_license_metadata

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "publication_pipeline" / "scripts"))
from publication_build import write_metadata


def test_repository_license_metadata_is_complete():
    metadata = load_license_metadata(Path(__file__).resolve().parents[1] / "metadata" / "licenses.yml")
    assert metadata["software_license"] == "GPL-3.0-or-later"
    assert metadata["content_license"] == "CC-BY-4.0"
    assert metadata["content_license_url"].startswith("https://")
    assert "third-party" in rights_notice(metadata)


def test_license_url_rejects_unescaped_latex_metacharacters():
    metadata = {
        "software_license": "GPL-3.0-or-later",
        "content_license": "Internal",
        "content_license_url": r"https://example.com/license/{private}",
    }
    with pytest.raises(ValueError, match="LaTeX-special"):
        validate_license_metadata(metadata)


def test_license_url_is_tex_escaped_in_generated_metadata(tmp_path):
    metadata = {
        "software_license": "GPL-3.0-or-later",
        "content_license": "Internal",
        "content_license_url": "https://example.com/license%20terms?x=1&y=2#terms",
        "classification": "Confidential",
    }
    validate_license_metadata(metadata)
    output = tmp_path / "metadata.tex"
    write_metadata(
        output,
        identity={
            "title": "Test", "subtitle": "Test", "author": "", "version": "draft",
            "left_header": "Test", "footer": "Test", "subject": "", "keywords": "",
            "project_url": "", "disclaimer": "",
        },
        combined=True,
        license_values=metadata,
        cover_name=None,
        uses_tables=False,
        uses_code=False,
    )
    text = output.read_text(encoding="utf-8")
    assert r"https://example.com/license\%20terms?x=1\&y=2\#terms" in text
    assert r"\newcommand{\RKPubClassification}{Confidential}" in text
