from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))

from reportkit.config import load_publication_config, resolve_document, resolve_identity
from reportkit.diagnostics import inspect_log
from reportkit.registry import check_skill_drift, generate_registry


REPO = Path(__file__).resolve().parents[1]


def test_nested_config_resolves_profile_and_document(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text(
        "publication:\n  title: Nested Report\n  author: Author\n"
        "document:\n  engine: lualatex\nprofiles:\n  release:\n    version: 2.0\n"
        "validation:\n  underfull_badness_threshold: 1200\n",
        encoding="utf-8",
    )
    config = load_publication_config(path)
    assert resolve_identity(config, {}, tmp_path, profile="release")["version"] == "2.0"
    assert resolve_document(config)["engine"] == "lualatex"


def test_flat_config_keeps_historical_identity_resolution() -> None:
    config = load_publication_config(REPO / "publication_pipeline/example_publication/publication.yaml")
    identity = resolve_identity(config, {}, REPO / "publication_pipeline/example_publication")
    assert identity["title"] == "Example Publication"
    assert identity["subtitle"] == "A minimal fixture for the publication pipeline"
    assert identity["version"] == "draft"
    assert identity["slug"] == "example-publication"


def test_nested_unknown_key_names_dotted_path(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("document:\n  engien: pdflatex\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"document\.engien"):
        load_publication_config(path)


def test_tabs_are_rejected_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("publication:\n\ttitle: Broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"publication\.yaml:2"):
        load_publication_config(path)


def test_diagnostics_map_wrapped_fragment_message() -> None:
    result = inspect_log(
        "(./body-00.tex\n"
        "Overfull \\hbox (8.4pt too\n"
        "wide) in paragraph at lines 10--12\n)\n",
        maps={"body-00.tex": {"source": "manuscript/01.md", "fragments": [{
            "start": 8, "end": 14, "path": "fragments/fig-flow.tex", "fragment_start": 1,
        }]}},
    )
    issue = result["issues"][0]
    assert issue["type"] == "overfull_hbox"
    assert issue["amount_pt"] == 8.4
    assert issue["file"] == "fragments/fig-flow.tex"
    assert issue["line"] == 3
    assert issue["owner"] == "CONTENT"


def test_registry_matches_skill_inventories() -> None:
    registry = generate_registry(REPO)
    assert len(registry["figures"]) == 19
    assert len(registry["callouts"]["public"]) == 10
    assert registry["callouts"]["aliases"]["evidence"] == "evidencenote"
    assert check_skill_drift(REPO) == []
