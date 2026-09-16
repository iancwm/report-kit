"""Phase B (slide renderer) decision B4: automated accessibility-parity gate.

Automates the implementation plan's B4 verification record (previously
manual/one-off): title/author/subject/keywords metadata, catalog language,
outline bookmarks, and diagram ActualText alternatives on the checked-in
`presentation_acceptance_test.tex` smoke fixture. See
tests/test_slide_renderer.py for the static/registry contract (tagged-PDF
status, renderer-hook and presentation-token assertions) this file does not
repeat, and the plan's B4 section for the exact manual findings these
assertions encode -- including the real pdfsubject/pdfkeywords race-condition
bug found and fixed while first producing that record.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "latex_templates" / "examples" / "presentation_acceptance_test.tex"

sys.path.insert(0, str(REPO / "publication_pipeline" / "scripts"))


@pytest.fixture(scope="module")
def compiled_presentation(tmp_path_factory) -> "pymupdf.Document":
    engine = shutil.which("lualatex")
    if engine is None:
        pytest.skip("lualatex not on PATH")
    from publication_build import template_files  # canonical flattened TeX input list

    workdir = tmp_path_factory.mktemp("presentation-accessibility")
    for src in template_files():
        shutil.copy(src, workdir / src.name)
    shutil.copy(FIXTURE, workdir / FIXTURE.name)

    env = dict(os.environ, LC_ALL="C")
    proc = None
    for _ in range(2):  # a second pass resolves the outline/bookmark aux data
        proc = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", FIXTURE.name],
            cwd=workdir, env=env, capture_output=True, text=True, timeout=180,
        )
    pdf = workdir / FIXTURE.name.replace(".tex", ".pdf")
    if not pdf.exists():
        output = (proc.stdout + "\n" + proc.stderr)[-4000:]
        pytest.fail(
            f"lualatex produced no PDF for the presentation acceptance fixture "
            f"(exit {proc.returncode})\n{output}"
        )
    return pymupdf.open(pdf)


def _catalog_text(doc: "pymupdf.Document") -> str:
    return doc.xref_object(doc.pdf_catalog())


def test_canvas_dimensions_are_the_declared_160mm_by_90mm(compiled_presentation) -> None:
    assert compiled_presentation.page_count == 17
    page = compiled_presentation[0]
    mm_to_pt = 72 / 25.4
    assert page.rect.width == pytest.approx(160 * mm_to_pt, abs=0.5)
    assert page.rect.height == pytest.approx(90 * mm_to_pt, abs=0.5)


def test_title_author_subject_keywords_metadata(compiled_presentation) -> None:
    meta = compiled_presentation.metadata
    # Beamer's own \title/\subtitle/\author schedule pdftitle as "title -
    # subtitle" (not \title alone) -- this is Beamer's pre-existing
    # behavior, unrelated to the race-condition bug below.
    assert meta["title"] == "Every presentation composition, once - Phase B compile coverage, not a real deck"
    assert meta["author"] == "Test build"
    # Regression coverage for the B4 race-condition bug: Beamer's own
    # \title/\author schedule a \hypersetup call earlier than
    # \RKRegisterDocumentMetadata's, and hyperref silently drops every later
    # attempt at the same keys -- pdfsubject/pdfkeywords locked to empty
    # without reportkit-slides-core.sty's begindocument/before fix, even
    # though this fixture never overrides ReportKit's own defaults.
    assert meta["subject"] == "Technical report"
    assert meta["keywords"] == "ReportKit, technical report"


def test_catalog_language_is_declared(compiled_presentation) -> None:
    assert "/Lang(en-US)" in _catalog_text(compiled_presentation).replace(" ", "")


def test_display_doc_title_viewer_preference_is_set(compiled_presentation) -> None:
    assert "/ViewerPreferences" in _catalog_text(compiled_presentation)


def test_outline_bookmarks_match_the_fixtures_section_dividers(compiled_presentation) -> None:
    titles = [entry[1] for entry in compiled_presentation.get_toc(simple=True)]
    assert titles == [
        "Message and evidence",
        "Visuals",
        "Structure",
        "Appendix: Chart, table, and architecture aliases",
    ]


def test_meaningful_link_annotation_renders_under_slides(compiled_presentation) -> None:
    """Closes the plan's own documented B4 gap: "meaningful link annotations
    were not exercised... not verified empirically for slides specifically."
    \\RKLink is the identical, renderer-neutral \\href mechanism
    reportkit-core.sty already provides under the paged renderer; this
    asserts it actually produces a real URI link annotation under Beamer
    too, not just that it compiles."""
    uris = [
        link["uri"]
        for page in compiled_presentation
        for link in page.get_links()
        if link.get("kind") == pymupdf.LINK_URI
    ]
    assert "https://example.com/reportkit-spec" in uris


def test_every_diagram_page_carries_actualtext(compiled_presentation) -> None:
    """The fixture's three \\begin{diagram} calls (visualtext/chartslide/
    architectureslide) must each embed an ActualText alternative in their
    page's content stream -- the same renderer-neutral mechanism
    reportkit-diagrams.sty already proves under the paged renderer
    (tests/test_diagram_alttext.py), unmodified here."""
    pages_with_actualtext = []
    for page in compiled_presentation:
        for xref in page.get_contents():
            stream = compiled_presentation.xref_stream(xref)
            if stream and b"/ActualText" in stream:
                pages_with_actualtext.append(page.number)
                break
    assert len(pages_with_actualtext) == 3
