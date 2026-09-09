from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))

from reportkit.config import (
    load_publication_config,
    resolve_document,
    resolve_identity,
    resolve_theme,
    theme_engine_conflict,
    theme_font_policy_conflict,
)
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


def test_resolve_theme_defaults() -> None:
    theme = resolve_theme({})
    assert theme["font_family"] == "Google Sans"
    assert theme["font_path"] == ""
    assert theme["font_policy"] == "fallback"


def test_resolve_theme_reads_nested_theme_section(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text(
        "publication:\n  title: T\n"
        "theme:\n  font_family: Google Sans\n  font_policy: strict\n",
        encoding="utf-8",
    )
    theme = resolve_theme(load_publication_config(path))
    assert theme["font_family"] == "Google Sans"
    assert theme["font_policy"] == "strict"
    assert theme["font_path"] == ""


def test_theme_font_policy_conflict_none_for_known_values() -> None:
    assert theme_font_policy_conflict(resolve_theme({})) is None
    assert theme_font_policy_conflict({"font_policy": "strict"}) is None


def test_theme_font_policy_conflict_flags_unknown_value() -> None:
    message = theme_font_policy_conflict({"font_policy": "loose"})
    assert message is not None
    assert "loose" in message


def test_theme_section_rejects_unknown_key(tmp_path: Path) -> None:
    path = tmp_path / "publication.yaml"
    path.write_text("publication:\n  title: T\ntheme:\n  font_weight: bold\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"theme\.font_weight"):
        load_publication_config(path)


def test_reportkit_cls_declares_institutional_research_theme_option() -> None:
    cls_text = (REPO / "latex_templates" / "reportkit.cls").read_text(encoding="utf-8")
    assert r"\DeclareOption{theme=institutional-research}" in cls_text


def test_institutional_theme_file_uses_regular_naming() -> None:
    """The theme identifier is `institutional-research`, which is what
    reportkit.cls's \\edef\\rk@themepackage{reportkit-theme-\\rk@theme} and
    reportkit_viz.py's theme_file_for() both resolve to by literal
    substitution -- so the file must be named accordingly, not
    reportkit-theme-institutional.sty (spec §2's tree; see the
    implementation plan's filename-note)."""
    path = REPO / "latex_templates" / "themes" / "reportkit-theme-institutional-research.sty"
    assert path.is_file()
    assert not (REPO / "latex_templates" / "themes" / "reportkit-theme-institutional.sty").exists()


def test_institutional_theme_uses_letter_geometry_and_type_scale() -> None:
    theme_text = (REPO / "latex_templates" / "themes" / "reportkit-theme-institutional-research.sty").read_text(encoding="utf-8")
    assert "letterpaper" in theme_text
    assert r"\definecolor{Ink}{HTML}{202124}" in theme_text
    assert r"\definecolor{Accent}{HTML}{18A999}" in theme_text
    assert "10.7pt" in theme_text and "14.6pt" in theme_text


def test_institutional_theme_guards_against_pdftex() -> None:
    theme_text = (REPO / "latex_templates" / "themes" / "reportkit-theme-institutional-research.sty").read_text(encoding="utf-8")
    assert r"\ifPDFTeX" in theme_text
    assert "requires LuaLaTeX" in theme_text


def test_reportkit_boxes_default_theme_unchanged() -> None:
    """The institutional-theme branch added to reportkit-boxes.sty must not
    change the default theme's callout chrome: colback=Surface with a
    boxed frame stays the default (theme=default / no theme=) behaviour."""
    boxes_text = (REPO / "latex_templates" / "reportkit-boxes.sty").read_text(encoding="utf-8")
    assert "colback=Surface" in boxes_text
    assert "colframe=Hairline" in boxes_text
    # The quiet institutional variant coexists, gated on \rk@theme.
    assert r"\ifdefstring{\rk@theme}{institutional-research}" in boxes_text
    assert "colback=white" in boxes_text


def test_check_theme_resolves_default_theme_file() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz  # noqa: PLC0415

    path = reportkit_viz.theme_file_for("default", REPO)
    assert path == REPO / "latex_templates" / "themes" / "reportkit-theme-default.sty"
    assert reportkit_viz.validate_palette_against_latex(path) == []


def test_check_theme_institutional_honestly_fails_until_step4() -> None:
    """OQ2's resolution (Step 1 plan): check-theme becomes theme-parameterized
    immediately, but a per-theme Python palette (reportkit.themes.*) is Step 4
    work. Until that lands, --theme institutional-research compares the
    institutional LaTeX palette against the *default* Python palette and
    should fail -- an honest failure, not a false pass. This test pins that
    expectation so it fails loudly (and gets deleted) the moment Step 4 adds
    a real institutional-research Python palette."""
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz  # noqa: PLC0415

    path = reportkit_viz.theme_file_for("institutional-research", REPO)
    assert path == REPO / "latex_templates" / "themes" / "reportkit-theme-institutional-research.sty"
    assert reportkit_viz.validate_palette_against_latex(path) != []
    # reportkit.cls itself no longer carries the palette, so checking it
    # directly (the pre-v1.6 default) must report every color missing.
    old_default = REPO / "latex_templates" / "reportkit.cls"
    assert reportkit_viz.validate_palette_against_latex(old_default) != []
