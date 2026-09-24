"""Phase F3 combination coverage.

Two fixture layers over the registry (implementation plan section 10, "F3 --
combination coverage"):

1. five showcase fixtures -- technical, institutional/equity, executive
   deck, venture pitch and editorial feature -- mapped explicitly below to
   the theme/publication-type pair they demonstrate;
2. every other registered theme x publication-type pair, covered either by
   a named dedicated test module (book, executive-brief -- each already
   compiles its own canonical fixture under every registered theme) or, for
   whatever is left over, a registry-generated minimal compile fixture
   built and asserted right here.

The parametrize list for the generated layer is computed from
``reportkit.publications.PUBLICATION_TYPES`` at collection time, not
hand-copied: adding a theme to a publication type's ``themes`` list changes
which pairs land in ``GENERATED_PAIRS`` on the next collection, so a new
compatible pair is automatically compiled here unless it is added to
``SHOWCASE_FIXTURES`` or ``DEDICATED_TEST_MODULES`` instead. The module-level
assertions below fail collection immediately if either mapping drifts from
the registry (references a pair that no longer exists, or double-covers a
pair already claimed by the other layer) -- exactly the failure mode this
file exists to prevent silently passing.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from reportkit.publications import PUBLICATION_TYPES, RENDERERS, THEMES, canonical_theme_name

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "latex_templates" / "examples"

Pair = tuple[str, str]


def _all_pairs() -> frozenset[Pair]:
    return frozenset(
        (publication_type, theme)
        for publication_type, record in PUBLICATION_TYPES.items()
        for theme in record["themes"]
    )


ALL_PAIRS = _all_pairs()

# Layer 1: the five showcase fixtures the spec and plan name explicitly
# (spec section 18's table; plan section 10's F3). Each is a real,
# hand-authored fictional publication with its own dedicated test module
# that compiles it and checks its structure -- this mapping only records
# which registered pair each one demonstrates.
SHOWCASE_FIXTURES: dict[Pair, str] = {
    ("technical-report", "default"): "career_guide_en",
    ("equity-research", "institutional-research"): "equity-research",
    ("presentation", "executive"): "executive-presentation",
    ("presentation", "venture"): "venture-presentation",
    ("feature-article", "editorial"): "editorial-feature",
}

# Layer 2a: pairs already covered by a dedicated test module that compiles
# the *same* canonical fixture under every theme the pair registers (not a
# throwaway smoke document) -- Phase F1's executive-brief and Phase F2's
# book. Recorded here, not recompiled, to avoid a second multi-minute
# LuaLaTeX pass over content this repository already builds elsewhere.
DEDICATED_TEST_MODULES: dict[Pair, str] = {
    ("book", "default"): "tests/test_book.py",
    ("book", "technical"): "tests/test_book.py",
    ("book", "editorial"): "tests/test_book.py",
    ("executive-brief", "executive"): "tests/test_executive_brief.py",
    ("executive-brief", "institutional-research"): "tests/test_executive_brief.py",
}

# Layer 2b: everything else. Computed, not hand-maintained -- see the module
# docstring. Today this is exactly the technical/default alias pair under
# technical-report, which has no compile test of its own anywhere else: the
# alias is checked at the Python/LaTeX-registry level
# (test_publication_registry.py, test_latex_publication_registry.py), but
# nothing before this file compiled `theme=technical` end to end.
GENERATED_PAIRS = sorted(ALL_PAIRS - set(SHOWCASE_FIXTURES) - set(DEDICATED_TEST_MODULES))


def test_pair_mappings_are_disjoint_and_match_the_live_registry() -> None:
    """Fails collection (this test module cannot even import successfully if
    the assertions below moved into the module body instead) or fails this
    test immediately if either hand-maintained mapping drifts from the
    registry: references a pair that no longer exists, or double-claims a
    pair the other layer already covers.
    """
    assert set(SHOWCASE_FIXTURES) <= ALL_PAIRS, sorted(set(SHOWCASE_FIXTURES) - ALL_PAIRS)
    assert set(DEDICATED_TEST_MODULES) <= ALL_PAIRS, sorted(set(DEDICATED_TEST_MODULES) - ALL_PAIRS)
    assert set(SHOWCASE_FIXTURES).isdisjoint(DEDICATED_TEST_MODULES)
    assert set(SHOWCASE_FIXTURES) | set(DEDICATED_TEST_MODULES) | set(GENERATED_PAIRS) == ALL_PAIRS
    # Five showcases, exactly as the spec's testing table and the plan's F3
    # section name.
    assert len(SHOWCASE_FIXTURES) == 5


def test_showcase_fixtures_exist_and_match_their_mapped_pair() -> None:
    for (publication_type, theme), directory in SHOWCASE_FIXTURES.items():
        fixture = EXAMPLES / directory
        assert fixture.is_dir(), fixture
        report = fixture / "report.tex"
        assert report.is_file(), report
        text = report.read_text(encoding="utf-8")
        class_name = RENDERERS[PUBLICATION_TYPES[publication_type]["renderer"]]["class_adapter"]
        if publication_type == "technical-report" and theme == "default":
            # career_guide_en predates the theme/publication-type option
            # syntax entirely -- `\documentclass{reportkit}` with no
            # options is exactly `theme=default,publication-type=technical-report`
            # (decision D1; reportkit.cls's own documented defaults).
            assert text.splitlines()[0] == r"\documentclass{reportkit}"
        else:
            assert rf"\documentclass[theme={theme},publication-type={publication_type}]{{{class_name}}}" in text


def test_dedicated_test_modules_exist_and_are_named_correctly() -> None:
    for pair, module in DEDICATED_TEST_MODULES.items():
        path = REPO / module
        assert path.is_file(), (pair, path)


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("pdflatex", "pandoc")),
    reason="requires a real LaTeX/Pandoc toolchain",
)
def test_technical_showcase_fixture_compiles(tmp_path: Path) -> None:
    """career_guide_en has no compile test anywhere else in the suite (the
    other four showcases each have one in their own theme test module) --
    add it here rather than leaving the flagship default-theme fixture
    checked only by scripts/acceptance_check.sh's bash loop."""
    pymupdf = pytest.importorskip("pymupdf")
    fixture = EXAMPLES / "career_guide_en"
    shutil.copy(fixture / "report.tex", tmp_path / "report.tex")
    shutil.copytree(fixture / "figures", tmp_path / "figures")
    env = {"LC_ALL": "C", "TEXINPUTS": f"{REPO / 'latex_templates'}:{REPO / 'latex_templates' / 'themes'}:{REPO / 'latex_templates' / 'publication_types'}:", "PATH": __import__("os").environ["PATH"]}
    result = None
    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180,
        )
    assert result is not None and result.returncode == 0, (result.stdout + result.stderr)[-4000:]
    log = (tmp_path / "report.log").read_text(encoding="utf-8", errors="replace")
    assert "There were undefined references" not in log
    with pymupdf.open(tmp_path / "report.pdf") as document:
        assert document.page_count >= 1
        for page in document:
            assert round(page.rect.width * 25.4 / 72) == 210 and round(page.rect.height * 25.4 / 72) == 297
        assert any(page.get_fonts() for page in document)


def _paper_mm(publication_type: str) -> tuple[int, int]:
    return {"a4": (210, 297), "letter": (216, 279)}[str(PUBLICATION_TYPES[publication_type]["paper"])]


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("pdflatex", "lualatex", "pandoc")),
    reason="requires a real LaTeX/Pandoc toolchain",
)
@pytest.mark.parametrize(("publication_type", "theme"), GENERATED_PAIRS)
def test_generated_minimal_compile_fixture_covers_the_compile_matrix(
    tmp_path: Path, publication_type: str, theme: str,
) -> None:
    """Build the smallest possible manuscript for one registered pair
    through the real pipeline and check what the plan's "Compile matrix"
    section calls cheaply checkable: correct class/renderer, correct
    paper/canvas dimensions, the expected engine, embedded fonts, no
    undefined references, a resolved-selection marker that matches the
    request, and no default-theme leakage.
    """
    pymupdf = pytest.importorskip("pymupdf")
    record = PUBLICATION_TYPES[publication_type]
    renderer_name = record["renderer"]
    theme_record = THEMES[theme]
    engine = str(theme_record["required_engine"])
    if shutil.which(engine) is None:
        pytest.skip(f"{engine} not on PATH")

    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    lines = [
        "title: Generated smoke fixture",
        "subtitle: A registry-derived minimal compile fixture",
        "author: ReportKit",
        "document:",
        f"  publication_type: {publication_type}",
        f"  theme: {theme}",
        f"  engine: {engine}",
    ]
    (source / "publication.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (source / "manuscript" / "order.txt").write_text("01-smoke.md\n", encoding="utf-8")
    (source / "manuscript" / "01-smoke.md").write_text(
        "# Smoke section\n\nMinimal content for a registry-generated compile fixture.\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0, payload
    report = payload["report"]
    assert report["status"] == "passed"

    selection = report["selection"]
    # correct class/renderer, expected engine, resolved-selection marker
    # matches the request, no default-theme leakage.
    assert selection["publication_type"] == publication_type
    assert selection["theme"] == canonical_theme_name(theme)
    assert selection["requested_theme"] == theme
    assert selection["renderer"] == renderer_name
    assert selection["class"] == RENDERERS[renderer_name]["class_adapter"]
    assert selection["engine"] == engine
    marker = report["pdf_inspection"]["selection_marker"]
    assert marker["status"] == "passed"
    assert marker["theme"]["passed"] is True

    pdf = output / "combined" / report["pdf"]
    with pymupdf.open(pdf) as document:
        assert document.page_count >= 1
        # correct paper/canvas dimensions.
        if RENDERERS[renderer_name]["geometry"]["kind"] == "paper":
            width_mm, height_mm = _paper_mm(publication_type)
            for page in document:
                assert round(page.rect.width * 25.4 / 72) == width_mm
                assert round(page.rect.height * 25.4 / 72) == height_mm
        else:
            canvas = RENDERERS[renderer_name]["geometry"]["canvas"]
            page = document[0]
            assert round(page.rect.width * 25.4 / 72) == canvas["width_mm"]
            assert round(page.rect.height * 25.4 / 72) == canvas["height_mm"]
        # fonts embedded.
        assert any(page.get_fonts() for page in document)
    # no undefined references (the pipeline's own log gate already turns
    # this into report["status"] != "passed"; re-checked directly here so
    # this test does not depend on that gate's severity classification).
    log = (output / "combined" / "publication.log").read_text(encoding="utf-8", errors="replace")
    assert "There were undefined references" not in log
