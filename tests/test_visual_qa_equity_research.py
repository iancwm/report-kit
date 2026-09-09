"""Institutional-theme spec, Step 5: visual-regression QA scaffolding.

scripts/visual_qa_equity_research.py's compile/render steps need lualatex
and cannot be exercised in an environment without it (this session's,
included -- see the institutional-theme implementation plan's Step 5
section). Its compare_pages() function is deliberately a pure function of
two directories of PNGs, independent of that compile/render path, so it
*can* be exercised here with synthetic images -- these tests actually run
it, they do not just import the module.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pymupdf")
PIL_Image = pytest.importorskip("PIL.Image")

REPO = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "visual_qa_equity_research", REPO / "scripts" / "visual_qa_equity_research.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


qa = _load_module()


def _write_png(path: Path, *, size=(40, 30), color=(255, 255, 255)) -> None:
    PIL_Image.new("RGB", size, color).save(path)


def test_compare_pages_identical_dirs_report_no_mismatches(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    actual.mkdir()
    expected.mkdir()
    for name in ("page-01.png", "page-02.png"):
        _write_png(actual / name)
        _write_png(expected / name)
    assert qa.compare_pages(actual, expected) == []


def test_compare_pages_flags_page_set_mismatch(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    actual.mkdir()
    expected.mkdir()
    _write_png(actual / "page-01.png")
    _write_png(expected / "page-01.png")
    _write_png(expected / "page-02.png")
    mismatches = qa.compare_pages(actual, expected)
    assert len(mismatches) == 1
    assert "page set differs" in mismatches[0]


def test_compare_pages_flags_size_mismatch(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    actual.mkdir()
    expected.mkdir()
    _write_png(actual / "page-01.png", size=(40, 30))
    _write_png(expected / "page-01.png", size=(50, 30))
    mismatches = qa.compare_pages(actual, expected)
    assert len(mismatches) == 1
    assert "size differs" in mismatches[0]


def test_compare_pages_tolerates_small_diffs_under_threshold(tmp_path: Path) -> None:
    """A handful of differing pixels (anti-aliasing/hinting drift) should
    not fail the comparison at the default 1% threshold."""
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    actual.mkdir()
    expected.mkdir()
    size = (100, 100)  # 10,000 pixels; changing 5 of them is 0.05%
    img = PIL_Image.new("RGB", size, (255, 255, 255))
    img.save(expected / "page-01.png")
    img2 = img.copy()
    for x in range(5):
        img2.putpixel((x, 0), (250, 250, 250))
    img2.save(actual / "page-01.png")
    assert qa.compare_pages(actual, expected, threshold=0.01) == []


def test_compare_pages_flags_diffs_over_threshold(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    actual.mkdir()
    expected.mkdir()
    size = (20, 20)
    PIL_Image.new("RGB", size, (255, 255, 255)).save(expected / "page-01.png")
    PIL_Image.new("RGB", size, (0, 0, 0)).save(actual / "page-01.png")
    mismatches = qa.compare_pages(actual, expected, threshold=0.01)
    assert len(mismatches) == 1
    assert "page-01.png" in mismatches[0]
    assert "100.00% of pixels differ" in mismatches[0]


def test_main_warns_and_exits_0_without_lualatex(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Same non-blocking convention as scripts/acceptance_check.sh: a
    missing toolchain is a WARN and exit 0, not a failure -- this is a QA
    aid, not a gate by itself. Simulates the missing-lualatex environment
    this repository's own CI/dev sandbox actually has."""
    monkeypatch.setattr(qa.shutil, "which", lambda name: None)
    monkeypatch.setattr(sys, "argv", ["visual_qa_equity_research.py"])
    assert qa.main() == 0
    captured = capsys.readouterr()
    assert "lualatex not found" in captured.err
