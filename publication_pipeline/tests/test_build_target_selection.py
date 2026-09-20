"""Phase A5 (make the pipeline target-aware) of the multi-format publication
architecture spec: publication_build.py resolves a real BuildTarget instead
of a hardcoded module-level TEMPLATE constant, selects the Pandoc writer
through the renderer record, stages/compiles a stable "publication.tex"
regardless of which entrypoint was selected, and records the resolved
selection in build-report.json and the compile log.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from reportkit.publications import PUBLICATION_TYPES, RENDERERS, resolve_build_target
from publication_pipeline.scripts.publication_build import stage_entrypoint
from reportkit.publication_validation import validate_publication

REPO = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO / "publication_pipeline"


def test_every_registered_publication_type_has_an_existing_entrypoint() -> None:
    """Every publication_type's registry-declared template must exist on
    disk -- resolve_build_target()/check_publication_registry() already
    enforce this for renderers' template_base, but this asserts it for
    every publication type's own `template` field specifically, the exact
    field build() now resolves an entrypoint from."""
    for name, record in PUBLICATION_TYPES.items():
        entrypoint = PIPELINE_ROOT / "templates" / str(record["template"])
        assert entrypoint.is_file(), f"publication type {name!r} names a missing entrypoint: {entrypoint}"


def test_every_registered_entrypoint_exposes_the_target_placeholders() -> None:
    placeholders = (
        "%%REPORTKIT_THEME%%",
        "%%REPORTKIT_PUBLICATION_TYPE%%",
        "%%REPORTKIT_CLASS%%",
    )
    for name, record in PUBLICATION_TYPES.items():
        entrypoint = PIPELINE_ROOT / "templates" / str(record["template"])
        text = entrypoint.read_text(encoding="utf-8")
        for placeholder in placeholders:
            assert text.count(placeholder) == 1, f"{name} entrypoint has an invalid {placeholder} slot"


def test_every_renderer_writer_is_a_real_pandoc_writer() -> None:
    assert RENDERERS["paged"]["pandoc_writer"] == "latex"
    assert RENDERERS["slides"]["pandoc_writer"] == "beamer"


def test_stage_entrypoint_replaces_only_registry_target_placeholders(tmp_path: Path) -> None:
    source = tmp_path / "entrypoint.tex"
    destination = tmp_path / "staged.tex"
    source.write_text(
        r"\documentclass[theme=%%REPORTKIT_THEME%%,publication-type=%%REPORTKIT_PUBLICATION_TYPE%%]{%%REPORTKIT_CLASS%%}" + "\n",
        encoding="utf-8",
    )

    stage_entrypoint(
        source,
        destination,
        theme="institutional-research",
        publication_type="equity-research",
        class_name="reportkit",
    )

    assert destination.read_text(encoding="utf-8") == (
        r"\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}" + "\n"
    )


def test_equity_fixture_is_a_pipeline_publication() -> None:
    source = REPO / "latex_templates" / "examples" / "equity-research"
    assert (source / "publication.yaml").is_file()
    assert (source / "manuscript" / "order.txt").is_file()
    assert list((source / "manuscript").glob("*.md")), "equity fixture needs Markdown source"
    assert list((source / "fragments").glob("fig-*.tex")), "equity fixture needs trusted fragments"
    result = validate_publication(source)
    assert result.ok, result.errors
    assert result.slugs == ["usage-index", "platform-mix", "risk-reward"]


def test_resolved_build_target_drives_template_and_writer_selection() -> None:
    """The exact fields build() reads off the resolved target -- if either
    of these ever silently reverted to a hardcoded value, this is the test
    that would catch it without needing a full compile."""
    paged = resolve_build_target("technical-report", "default", repo_root=REPO)
    assert paged.template == "technical-report.tex"
    assert paged.pandoc_writer == "latex"

    slides = resolve_build_target("presentation", "executive", engine="lualatex", repo_root=REPO)
    assert slides.template == "presentation.tex"
    assert slides.pandoc_writer == "beamer"


def _build(source_root: Path, output_root: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--source-root", str(source_root), "--output-root", str(output_root), "--json"],
        capture_output=True, text=True,
    )
    if result.returncode:
        print(f"reportkit build stderr:\n{result.stderr}", file=sys.stderr)
        for log_name in ("publication-pass-1.log", "publication-pass-2.log", "publication.log"):
            log = output_root / "combined" / log_name
            if log.is_file():
                print(f"{log_name} tail:\n{log.read_text(encoding='utf-8', errors='replace')[-16000:]}", file=sys.stderr)
    return result.returncode, json.loads(result.stdout)


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("pdflatex", "pandoc")),
    reason="requires a real LaTeX/Pandoc toolchain",
)
def test_paged_build_stages_a_stable_publication_tex_and_records_selection(tmp_path: Path) -> None:
    source = tmp_path / "publication"
    output = tmp_path / "build"
    shutil.copytree(REPO / "publication_pipeline" / "example_publication", source)
    code, payload = _build(source, output)
    assert code == 0, payload
    report = payload["report"]

    combined = output / "combined"
    assert (combined / "publication.tex").is_file()
    assert (combined / "publication.pdf").is_file()
    # The final, packaged PDF is slug-named -- not "publication.pdf" (that
    # name is the internal compiled artifact, independent of the source
    # entrypoint's own filename).
    assert report["pdf"] != "publication.pdf"

    selection = report["selection"]
    assert selection["publication_type"] == "technical-report"
    assert selection["renderer"] == "paged"
    assert selection["class"] == "reportkit"
    assert selection["template"] == "technical-report.tex"
    assert selection["writer"] == "latex"
    assert selection["paper"] == "a4"
    assert selection["canvas"] is None

    log_text = (combined / "publication.log").read_text(encoding="utf-8")
    assert "REPORTKIT-SELECTED" in log_text
    assert "publication_type=technical-report" in log_text
    assert "renderer=paged" in log_text


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("lualatex", "pandoc")),
    reason="requires a real LuaLaTeX/Pandoc toolchain",
)
def test_equity_fixture_builds_through_the_normal_pipeline(tmp_path: Path) -> None:
    """The direct-TeX equity witness has a Markdown/fragments pipeline path."""
    source = tmp_path / "publication"
    shutil.copytree(REPO / "latex_templates" / "examples" / "equity-research", source)
    output = tmp_path / "build"
    code, payload = _build(source, output)
    assert code == 0, payload

    report = payload["report"]
    selection = report["selection"]
    assert selection["publication_type"] == "equity-research"
    assert selection["theme"] == "institutional-research"
    assert selection["renderer"] == "paged"
    assert selection["class"] == "reportkit"
    assert selection["template"] == "equity-research.tex"
    assert selection["writer"] == "latex"
    assert selection["engine"] == "lualatex"
    assert selection["paper"] == "letter"

    staged = output / "combined" / "publication.tex"
    staged_text = staged.read_text(encoding="utf-8")
    assert r"\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}" in staged_text
    assert report["page_count"] >= 3


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("lualatex", "pandoc")),
    reason="the executive theme requires lualatex",
)
def test_presentation_builds_through_the_normal_pipeline(tmp_path: Path) -> None:
    """Phase B's own definition of done ("a presentation builds from
    publication.yaml through the normal pipeline") -- verified here, not
    just asserted. Plain Markdown headings become frames via Pandoc's own
    Beamer writer (B1's "plain Markdown frames" path); reportkit-
    presentation.sty's compositions are the separate directive/fragment
    path and are not exercised by this fixture."""
    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "publication.yaml").write_text(
        "title: Example Deck\n"
        "subtitle: A minimal fixture for the presentation pipeline\n"
        "author: ReportKit\n"
        "document:\n"
        "  publication_type: presentation\n"
        "  theme: executive\n"
        "  engine: lualatex\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-deck.md\n", encoding="utf-8")
    (source / "manuscript" / "01-deck.md").write_text(
        "# First slide\n\nPlain Markdown content.\n\n# Second slide\n\n- A bullet\n- Another bullet\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    code, payload = _build(source, output)
    assert code == 0, payload
    report = payload["report"]
    assert report["status"] == "passed"

    selection = report["selection"]
    assert selection["publication_type"] == "presentation"
    assert selection["renderer"] == "slides"
    assert selection["class"] == "reportkit-slides"
    assert selection["template"] == "presentation.tex"
    assert selection["writer"] == "beamer"
    assert selection["engine"] == "lualatex"
    assert selection["paper"] is None
    assert selection["canvas"] == {"width_mm": 160, "height_mm": 90}

    pdf = output / "combined" / report["pdf"]
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open(pdf)
    # Title slide (from presentation.tex's \RKFrontMatter) + two Markdown
    # frames.
    assert doc.page_count == 3
    width_pt, height_pt = doc[0].rect.width, doc[0].rect.height
    assert round(width_pt * 25.4 / 72) == 160
    assert round(height_pt * 25.4 / 72) == 90


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="requires pandoc for early validation to reach target resolution")
def test_explicit_paper_for_presentation_is_rejected_before_any_compile_work(tmp_path: Path) -> None:
    """Decision D5, enforced at the pipeline entrypoint, not just the
    registry function directly (test_slide_renderer.py covers that): a
    canvas renderer's config.paper is a configuration error, exit 2, before
    manuscripts are even read."""
    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "publication.yaml").write_text(
        "title: Example Deck\n"
        "author: ReportKit\n"
        "document:\n"
        "  publication_type: presentation\n"
        "  theme: executive\n"
        "  engine: lualatex\n"
        "  paper: a4\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("", encoding="utf-8")
    output = tmp_path / "build"
    code, payload = _build(source, output)
    assert code == 2, payload
    assert any("canvas renderer" in str(item.get("message", "")) for item in payload["diagnostics"])
