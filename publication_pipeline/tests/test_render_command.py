from __future__ import annotations

import json
from pathlib import Path

import pytest

from publication_pipeline.scripts import render_pdf_pages
from reportkit.cli import build_parser


def test_parse_page_selection_is_sorted_unique_and_one_based() -> None:
    assert render_pdf_pages.parse_page_selection("3,1,2-4,3", 5) == [1, 2, 3, 4]


@pytest.mark.parametrize("selection", ["", "0", "1-", "4-2", "1,6", "one"])
def test_parse_page_selection_rejects_invalid_ranges(selection: str) -> None:
    with pytest.raises(ValueError):
        render_pdf_pages.parse_page_selection(selection, 5)


def test_render_keeps_previous_output_when_selection_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePixmap:
        def save(self, path: Path) -> None:
            path.write_bytes(b"png")

    class FakePage:
        def get_pixmap(self, *, matrix: object, alpha: bool) -> FakePixmap:
            assert alpha is False
            return FakePixmap()

    class FakeDocument:
        page_count = 3

        def __getitem__(self, index: int) -> FakePage:
            return FakePage()

        def close(self) -> None:
            pass

    class FakeFitz:
        class Matrix:
            def __init__(self, x: float, y: float) -> None:
                self.x = x
                self.y = y

        @staticmethod
        def open(path: Path) -> FakeDocument:
            return FakeDocument()

    monkeypatch.setattr(render_pdf_pages, "fitz", FakeFitz)
    pdf = tmp_path / "publication.pdf"
    pdf.write_bytes(b"pdf")
    output = tmp_path / "render"
    output.mkdir()
    (output / "sentinel").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError):
        render_pdf_pages.render(pdf, output, pages="2-1")

    assert (output / "sentinel").read_text(encoding="utf-8") == "keep"


def test_render_writes_selected_pages_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePixmap:
        def save(self, path: Path) -> None:
            path.write_bytes(b"png")

    class FakePage:
        def get_pixmap(self, *, matrix: object, alpha: bool) -> FakePixmap:
            return FakePixmap()

    class FakeDocument:
        page_count = 4

        def __getitem__(self, index: int) -> FakePage:
            return FakePage()

        def close(self) -> None:
            pass

    class FakeFitz:
        class Matrix:
            def __init__(self, x: float, y: float) -> None:
                self.x = x
                self.y = y

        @staticmethod
        def open(path: Path) -> FakeDocument:
            return FakeDocument()

    monkeypatch.setattr(render_pdf_pages, "fitz", FakeFitz)
    pdf = tmp_path / "publication.pdf"
    pdf.write_bytes(b"pdf")
    output = tmp_path / "render"

    manifest = render_pdf_pages.render(pdf, output, dpi=120, pages="1,3-4")

    assert manifest["page_count"] == 4
    assert manifest["rendered_pages"] == [1, 3, 4]
    assert manifest["dpi"] == 120
    assert [path.name for path in sorted(output.glob("page-*.png"))] == [
        "page-01.png", "page-03.png", "page-04.png",
    ]
    assert json.loads((output / "pages.json").read_text(encoding="utf-8"))["rendered_pages"] == [1, 3, 4]


def test_render_reports_missing_pymupdf_as_structured_environment_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    pdf = tmp_path / "publication.pdf"
    pdf.write_bytes(b"pdf")
    monkeypatch.setattr(render_pdf_pages, "fitz", None)
    args = build_parser().parse_args(["render", str(pdf), "--json"])

    assert args.handler(args) == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert payload["diagnostics"][0]["code"] == "RK_PYMUPDF_MISSING"


def test_render_reports_missing_pdf_as_structured_configuration_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    args = build_parser().parse_args(["render", str(tmp_path / "missing.pdf"), "--json"])

    assert args.handler(args) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert payload["diagnostics"][0]["code"] == "RK_RENDER_PDF_MISSING"


def test_render_rejects_non_positive_dpi_before_opening_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFitz:
        @staticmethod
        def open(path: Path) -> None:
            raise AssertionError("the PDF should not be opened")

    monkeypatch.setattr(render_pdf_pages, "fitz", FakeFitz)
    pdf = tmp_path / "publication.pdf"
    pdf.write_bytes(b"pdf")

    with pytest.raises(ValueError, match="positive"):
        render_pdf_pages.render(pdf, tmp_path / "render", dpi=0)
