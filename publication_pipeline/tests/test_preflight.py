"""Direct, no-build tests for publication_build._preflight().

Companion coverage for code-quality-review spec item C
(docs/superpowers/specs/2026-09-24-reportkit-code-quality-review-spec.md):
build() was split into a preflight stage (validate -> config -> resolve
target) and a compile stage (Pandoc, TeX passes, log gate, page rendering,
PDF inspection). This file is the "gate-failure path is only exercisable by
running an entire build" gap the spec named -- every case below calls
_preflight() in-process, with no pandoc/TeX/pdf tooling involved, and
exercises every multi-format target registered since the 2026-09-12
baseline: default, technical, institutional-research, executive
(presentation), venture, editorial (feature-article), executive-brief, and
book.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from publication_pipeline.scripts.publication_build import _PreflightResult, _preflight

REPO = Path(__file__).resolve().parents[2]


def _args(source_root: Path, *, mode: str = "combined", section: str | None = None, **overrides) -> argparse.Namespace:
    defaults = dict(
        mode=mode,
        section=section,
        source_root=str(source_root),
        output_root=str(source_root / "build"),
        profile=None,
        engine=None,
        version=None,
        title=None,
        author=None,
        cover=None,
        compile_timeout_seconds=120,
        memory_limit_mb=2048,
        workers=1,
        json=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _write_publication(
    tmp_path: Path,
    *,
    publication_type: str,
    theme: str,
    engine: str | None = None,
    extra_document_lines: str = "",
    extra_yaml: str = "",
    manuscript_body: str = "# Title\n\nSome body text.\n",
) -> Path:
    """Build the smallest publication.yaml + manuscript/ pair that resolves
    the given (publication_type, theme) pair through _preflight() -- valid
    enough to reach every multi-format branch without needing Pandoc/TeX.
    """
    root = tmp_path / "publication"
    (root / "manuscript").mkdir(parents=True)
    (root / "fragments").mkdir()
    lines = [
        "title: Example Publication\n",
        "author: ReportKit\n",
        "document:\n",
        f"  publication_type: {publication_type}\n",
        f"  theme: {theme}\n",
    ]
    if engine:
        lines.append(f"  engine: {engine}\n")
    if extra_document_lines:
        lines.append(extra_document_lines)
    (root / "publication.yaml").write_text("".join(lines) + extra_yaml, encoding="utf-8")
    (root / "manuscript" / "order.txt").write_text("01-body.md\n", encoding="utf-8")
    (root / "manuscript" / "01-body.md").write_text(manuscript_body, encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Success path: one case per multi-format target added since the
# 2026-09-12 baseline, asserting the resolved BuildTarget without compiling.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "publication_type, theme, engine, expected",
    [
        ("technical-report", "default", None, {"renderer": "paged", "template": "technical-report.tex", "engine": "pdflatex", "theme": "default"}),
        ("technical-report", "technical", None, {"renderer": "paged", "template": "technical-report.tex", "engine": "pdflatex", "theme": "default", "alias_of": "default"}),
        ("equity-research", "institutional-research", "lualatex", {"renderer": "paged", "template": "equity-research.tex", "engine": "lualatex", "theme": "institutional-research"}),
        ("presentation", "executive", "lualatex", {"renderer": "slides", "template": "presentation.tex", "engine": "lualatex", "theme": "executive"}),
        ("presentation", "venture", "lualatex", {"renderer": "slides", "template": "presentation.tex", "engine": "lualatex", "theme": "venture"}),
        ("feature-article", "editorial", "lualatex", {"renderer": "paged", "template": "feature-article.tex", "engine": "lualatex", "theme": "editorial"}),
        ("executive-brief", "executive", "lualatex", {"renderer": "paged", "template": "executive-brief.tex", "engine": "lualatex", "theme": "executive"}),
        ("book", "default", None, {"renderer": "paged", "template": "book.tex", "engine": "pdflatex", "theme": "default"}),
    ],
    ids=[
        "default", "technical", "institutional-research", "executive-presentation",
        "venture", "editorial-feature-article", "executive-brief", "book",
    ],
)
def test_preflight_resolves_every_multiformat_target(tmp_path, publication_type, theme, engine, expected) -> None:
    source_root = _write_publication(tmp_path, publication_type=publication_type, theme=theme, engine=engine)
    result = _preflight(_args(source_root))
    assert isinstance(result, _PreflightResult), result
    target = result.target
    assert target.publication_type == publication_type
    assert target.requested_theme == theme
    assert target.renderer == expected["renderer"]
    assert target.template == expected["template"]
    assert target.engine == expected["engine"]
    assert target.theme == expected["theme"]
    if "alias_of" in expected:
        assert target.alias_of == expected["alias_of"]
    assert result.entrypoint.is_file()
    assert result.manuscripts == [Path("01-body.md")]
    assert f"publication_type={publication_type}" in result.selection_marker
    assert result.engine == expected["engine"]


# ---------------------------------------------------------------------------
# Preflight failure branches -- each exercised directly, no build.
# ---------------------------------------------------------------------------

def test_nonpositive_timeout_rejected_before_any_validation(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    result = _preflight(_args(source_root, compile_timeout_seconds=0))
    assert result == 2


def test_nonpositive_memory_limit_rejected(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    result = _preflight(_args(source_root, memory_limit_mb=0))
    assert result == 2


def test_missing_manuscript_order_file_fails_publication_validation(tmp_path) -> None:
    source_root = tmp_path / "publication"
    (source_root / "manuscript").mkdir(parents=True)
    (source_root / "publication.yaml").write_text("title: Example\n", encoding="utf-8")
    result = _preflight(_args(source_root))
    assert result == 3


def test_incomplete_source_record_fails_authoring_validation(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    (source_root / "sources.yaml").write_text(
        "sources:\n  s1:\n    type: article\n", encoding="utf-8",  # missing title/file
    )
    result = _preflight(_args(source_root))
    assert result == 3


def test_invalid_license_url_fails_before_target_resolution(tmp_path) -> None:
    source_root = _write_publication(
        tmp_path, publication_type="technical-report", theme="default",
        extra_yaml="license:\n  content_license_url: http://not-https.example/\n",
    )
    result = _preflight(_args(source_root))
    assert result == 2


def test_unknown_publication_type_is_a_configuration_error(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="not-a-real-type", theme="default")
    result = _preflight(_args(source_root))
    assert result == 2


def test_theme_unsupported_for_publication_type_is_a_configuration_error(tmp_path) -> None:
    # "venture" only supports the "presentation" publication type.
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="venture", engine="lualatex")
    result = _preflight(_args(source_root))
    assert result == 2


def test_invalid_font_policy_is_a_configuration_error(tmp_path) -> None:
    source_root = _write_publication(
        tmp_path, publication_type="technical-report", theme="default",
        extra_yaml="theme:\n  font_policy: overzealous\n",
    )
    result = _preflight(_args(source_root))
    assert result == 2


def test_rtl_language_is_rejected_before_any_compile_work(tmp_path) -> None:
    source_root = _write_publication(
        tmp_path, publication_type="technical-report", theme="default",
        extra_document_lines="",
        extra_yaml="",
    )
    # Arabic is RTL, which every ReportKit renderer/theme explicitly rejects.
    text = (source_root / "publication.yaml").read_text(encoding="utf-8")
    (source_root / "publication.yaml").write_text(text + "language: ar\n", encoding="utf-8")
    result = _preflight(_args(source_root))
    assert result == 2


def test_brand_overrides_on_a_non_brand_theme_is_a_theme_override_error(tmp_path) -> None:
    # Only "venture" opts in to brand overrides (decision D6); "default" does not.
    source_root = _write_publication(
        tmp_path, publication_type="technical-report", theme="default",
        extra_yaml="brand:\n  primary: '#123456'\n",
    )
    result = _preflight(_args(source_root))
    assert result == 2


def test_section_mode_requires_a_section_argument(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    result = _preflight(_args(source_root, mode="section", section=None))
    assert result == 2


def test_section_argument_must_be_a_contained_markdown_path(tmp_path) -> None:
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    result = _preflight(_args(source_root, mode="section", section="../escape.md"))
    assert result == 2
    result = _preflight(_args(source_root, mode="section", section="01-body.tex"))
    assert result == 2


def test_section_naming_a_file_missing_from_disk_fails_after_registry_resolution(tmp_path) -> None:
    """order.txt-listed manuscripts are already checked by validate_publication;
    this is the redundant check for a --section CLI argument that names a
    file order.txt never mentions and which does not exist on disk."""
    source_root = _write_publication(tmp_path, publication_type="technical-report", theme="default")
    result = _preflight(_args(source_root, mode="section", section="02-missing.md"))
    assert result == 3


def test_explicit_paper_for_a_canvas_renderer_is_rejected_before_any_compile_work(tmp_path) -> None:
    """Decision D5: presentation (slides, a canvas renderer) never accepts an
    explicit document.paper -- resolve_build_target rejects it as a registry
    error, caught by _preflight before any manuscript/output work."""
    source_root = _write_publication(
        tmp_path, publication_type="presentation", theme="executive", engine="lualatex",
        extra_document_lines="  paper: a4\n",
    )
    result = _preflight(_args(source_root))
    assert result == 2


def test_missing_source_root_config_file_still_resolves_defaults(tmp_path) -> None:
    """An absent publication.yaml is legal (load_publication_config returns
    {}); resolve_identity then fails on the still-missing required title."""
    source_root = tmp_path / "publication"
    (source_root / "manuscript").mkdir(parents=True)
    (source_root / "fragments").mkdir()
    (source_root / "manuscript" / "order.txt").write_text("01-body.md\n", encoding="utf-8")
    (source_root / "manuscript" / "01-body.md").write_text("# Title\n", encoding="utf-8")
    result = _preflight(_args(source_root))
    assert result == 2
