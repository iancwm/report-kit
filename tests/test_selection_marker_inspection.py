from __future__ import annotations

import json
from pathlib import Path

import pytest

from publication_pipeline.scripts.inspect_pdf import inspect, inspect_selection_marker


def _selection_marker(*, requested_theme: str = "institutional-research", theme: str = "institutional-research") -> str:
    return (
        "REPORTKIT-SELECTED publication_type=equity-research "
        f"requested_theme={requested_theme} theme={theme} "
        "renderer=paged class=reportkit template=publication-template.tex "
        "writer=latex engine=lualatex paper=letter canvas=-"
    )


def _pdf(tmp_path: Path, *, log_text: str | None = None) -> Path:
    fitz = pytest.importorskip("pymupdf", reason="requires PyMuPDF")
    pdf = tmp_path / "publication.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 72), "Selection marker QA")
    document.save(pdf)
    document.close()
    if log_text is not None:
        (tmp_path / "publication.log").write_text(log_text, encoding="utf-8")
    return pdf


def test_pdf_inspection_consumes_adjacent_selection_marker(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path, log_text="compile output\n" + _selection_marker() + "\n")

    result = inspect(pdf)

    assert result["passed"] is True
    assert result["selection_marker"]["status"] == "passed"
    assert result["selection_marker"]["selection"] == {
        "publication_type": "equity-research",
        "requested_theme": "institutional-research",
        "theme": "institutional-research",
        "renderer": "paged",
        "class": "reportkit",
        "template": "publication-template.tex",
        "writer": "latex",
        "engine": "lualatex",
        "paper": "letter",
        "canvas": None,
    }
    assert not result["diagnostics"]
    json.dumps(result)


def test_pdf_inspection_flags_default_theme_leakage(tmp_path: Path) -> None:
    pdf = _pdf(
        tmp_path,
        log_text=_selection_marker(requested_theme="institutional-research", theme="default") + "\n",
    )

    result = inspect(pdf)

    assert result["passed"] is False
    diagnostic = next(item for item in result["diagnostics"] if item["code"] == "RK_PDF_SELECTION_MARKER_THEME_LEAKAGE")
    assert diagnostic["type"] == "configuration_error"
    assert diagnostic["details"]["theme_check"] == {
        "requested": "institutional-research",
        "canonical_requested": "institutional-research",
        "resolved": "default",
        "passed": False,
    }


def test_selection_marker_check_accepts_the_technical_default_alias() -> None:
    result = inspect_selection_marker(_selection_marker(requested_theme="technical", theme="default"))

    assert result["passed"] is True
    assert result["selection_marker"]["theme"]["canonical_requested"] == "default"


def test_selection_marker_check_reports_expected_target_mismatch() -> None:
    result = inspect_selection_marker(
        _selection_marker(),
        expected_selection={"publication_type": "technical-report", "theme": "institutional-research"},
    )

    assert result["passed"] is False
    diagnostic = next(item for item in result["diagnostics"] if item["code"] == "RK_PDF_SELECTION_MARKER_MISMATCH")
    assert diagnostic["details"]["mismatches"] == {
        "publication_type": {"expected": "technical-report", "actual": "equity-research"},
    }


def test_existing_standalone_pdf_inspection_does_not_require_a_marker(tmp_path: Path) -> None:
    result = inspect(_pdf(tmp_path))

    assert result["passed"] is True
    assert result["selection_marker"]["status"] == "not_checked"


def test_required_selection_marker_reports_missing_marker(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    log = tmp_path / "build.log"
    log.write_text("no resolved target here\n", encoding="utf-8")

    result = inspect(pdf, selection_log=log)

    assert result["passed"] is False
    assert result["selection_marker"]["status"] == "missing"
    assert result["diagnostics"][0]["code"] == "RK_PDF_SELECTION_MARKER_MISSING"
