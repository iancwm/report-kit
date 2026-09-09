from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))

from reportkit.config import load_publication_config, resolve_document, resolve_identity, theme_engine_conflict
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


def test_resolve_document_defaults_theme_and_publication_type() -> None:
    document = resolve_document({})
    assert document["theme"] == "default"
    assert document["publication_type"] == "technical-report"
    assert document["paper"] == "a4"


def test_theme_engine_conflict_none_for_default_theme() -> None:
    assert theme_engine_conflict(resolve_document({})) is None


def test_theme_engine_conflict_flags_institutional_without_lualatex() -> None:
    document = resolve_document({"publication": {"title": "T"}, "document": {"theme": "institutional-research"}})
    message = theme_engine_conflict(document)
    assert message is not None
    assert "institutional-research" in message
    assert "lualatex" in message


def test_theme_engine_conflict_satisfied_with_lualatex() -> None:
    document = resolve_document(
        {"publication": {"title": "T"}, "document": {"theme": "institutional-research", "engine": "lualatex"}}
    )
    assert theme_engine_conflict(document) is None


def test_theme_files_moved_out_of_reportkit_cls() -> None:
    """The theme split (institutional-theme spec, Step 1) must not leave any
    palette color behind in reportkit.cls -- it should live only in the
    selected theme file."""
    cls_text = (REPO / "latex_templates" / "reportkit.cls").read_text(encoding="utf-8")
    assert "\\definecolor" not in cls_text
    theme_text = (REPO / "latex_templates" / "themes" / "reportkit-theme-default.sty").read_text(encoding="utf-8")
    assert "\\definecolor{Ink}" in theme_text


def test_check_theme_resolves_default_theme_file() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz  # noqa: PLC0415

    path = reportkit_viz.theme_file_for("default", REPO)
    assert path == REPO / "latex_templates" / "themes" / "reportkit-theme-default.sty"
    assert reportkit_viz.validate_palette_against_latex(path) == []
    # reportkit.cls itself no longer carries the palette, so checking it
    # directly (the pre-v1.6 default) must report every color missing.
    old_default = REPO / "latex_templates" / "reportkit.cls"
    assert reportkit_viz.validate_palette_against_latex(old_default) != []
