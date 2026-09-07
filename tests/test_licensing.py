from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))
from license_metadata import load_license_metadata, rights_notice


def test_repository_license_metadata_is_complete():
    metadata = load_license_metadata(Path(__file__).resolve().parents[1] / "metadata" / "licenses.yml")
    assert metadata["software_license"] == "GPL-3.0-or-later"
    assert metadata["content_license"] == "CC-BY-4.0"
    assert metadata["content_license_url"].startswith("https://")
    assert "third-party" in rights_notice(metadata)
