from pathlib import Path

import pytest

from python_scripts.reportkit.config import load_publication_config, resolve_document, resolve_identity


def test_legacy_flat_config_keeps_identity_resolution(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("title: Example\nsubtitle: Brief\nauthor: Author\n", encoding="utf-8")
    config = load_publication_config(path)
    assert config == {"title": "Example", "subtitle": "Brief", "author": "Author"}
    assert resolve_identity(config, {}, tmp_path)["slug"] == "example"


def test_nested_config_and_profile_override(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text(
        "publication:\n  title: Nested\n"
        "document:\n  engine: lualatex\n"
        "profiles:\n  release:\n    publication:\n      version: 2\n",
        encoding="utf-8",
    )
    config = load_publication_config(path)
    assert resolve_identity(config, {}, tmp_path, "release")["version"] == "2"
    assert resolve_document(config)["engine"] == "lualatex"


def test_nested_unknown_key_reports_path(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("publication:\n  engien: typo\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"publication\.engien"):
        load_publication_config(path)


def test_tab_indentation_reports_line(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("publication:\n\ttitle: Bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r":2:"):
        load_publication_config(path)
