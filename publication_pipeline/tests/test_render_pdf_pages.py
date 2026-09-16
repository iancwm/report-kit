from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "publication_pipeline" / "scripts" / "render_pdf_pages.py"

from publication_pipeline.scripts.render_pdf_pages import parse_page_selection, render  # noqa: E402


@pytest.mark.parametrize(
    ("spec", "page_count", "expected"),
    [
        ("1", 5, [1]),
        ("1,3,5", 5, [1, 3, 5]),
        ("1-3", 5, [1, 2, 3]),
        ("1,3,5-7", 8, [1, 3, 5, 6, 7]),
        (" 2 , 1 ", 5, [1, 2]),
    ],
)
def test_parse_page_selection_accepts_lists_and_ranges(spec: str, page_count: int, expected: list[int]) -> None:
    assert parse_page_selection(spec, page_count) == expected


@pytest.mark.parametrize(
    "spec",
    ["0", "-1", "3-1", "abc", "1,,2", "1-", "1-2-3", ""],
)
def test_parse_page_selection_rejects_malformed_tokens(spec: str) -> None:
    with pytest.raises(ValueError):
        parse_page_selection(spec, page_count=10)


def test_parse_page_selection_rejects_pages_beyond_the_document() -> None:
    with pytest.raises(ValueError, match="exceed page count"):
        parse_page_selection("1,9", page_count=5)


def test_parse_page_selection_deduplicates_and_sorts_overlapping_ranges() -> None:
    assert parse_page_selection("5-7,6,1", page_count=10) == [1, 5, 6, 7]


def _make_pdf(path: Path, page_count: int) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    document = pymupdf.open()
    for index in range(page_count):
        page = document.new_page(width=200, height=300)
        page.insert_text((20, 20), f"page {index + 1}")
    document.save(path)
    document.close()


def test_render_defaults_to_every_page(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 4)
    manifest = render(pdf, tmp_path / "out", dpi=72)
    assert manifest["page_count"] == 4
    assert manifest["rendered_pages"] == [1, 2, 3, 4]
    assert manifest["files"] == ["page-01.png", "page-02.png", "page-03.png", "page-04.png"]
    for name in manifest["files"]:
        assert (tmp_path / "out" / name).is_file()
    assert (tmp_path / "out" / "index.html").is_file()
    assert (tmp_path / "out" / "pages.json").is_file()


def test_render_honours_a_page_selection_and_names_files_by_true_page_number(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 6)
    manifest = render(pdf, tmp_path / "out", dpi=72, pages="2,4-5")
    assert manifest["page_count"] == 6
    assert manifest["rendered_pages"] == [2, 4, 5]
    assert manifest["files"] == ["page-02.png", "page-04.png", "page-05.png"]
    assert not (tmp_path / "out" / "page-01.png").exists()


def test_render_replaces_a_stale_out_dir(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.png").write_bytes(b"stale")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 2)
    render(pdf, out, dpi=72)
    assert not (out / "stale.png").exists()
    assert (out / "page-01.png").is_file()


def test_render_rejects_a_page_selection_outside_the_document(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 2)
    with pytest.raises(ValueError, match="exceed page count"):
        render(pdf, tmp_path / "out", dpi=72, pages="5")


def test_cli_reports_a_structured_diagnostic_for_a_missing_pdf(tmp_path: Path) -> None:
    json_path = tmp_path / "result.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "missing.pdf"), str(tmp_path / "out"), "--json", str(json_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["diagnostics"][0]["code"] == "RK_RENDER_PDF_MISSING"


def test_cli_reports_a_structured_diagnostic_for_an_invalid_page_selection(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 2)
    json_path = tmp_path / "result.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(pdf), str(tmp_path / "out"), "--pages", "99", "--json", str(json_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["diagnostics"][0]["code"] == "RK_RENDER_PAGES_INVALID"


def test_cli_writes_an_envelope_and_a_legacy_manifest_on_success(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, 3)
    json_path = tmp_path / "result.json"
    manifest_path = tmp_path / "manifest.json"
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT), str(pdf), str(out_dir),
            "--pages", "1-2", "--manifest", str(manifest_path), "--json", str(json_path),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(json_path.read_text(encoding="utf-8"))
    assert envelope["passed"] is True
    assert envelope["rendered_pages"] == [1, 2]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["rendered_pages"] == [1, 2]
