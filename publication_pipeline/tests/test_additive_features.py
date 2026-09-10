import json
from pathlib import Path
import sys

import pytest

from python_scripts.reportkit.analysis import analyse_history

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication_pipeline.scripts.publication_build import stage_project_assets


def test_analyse_history_reports_recurring_diagnostics(tmp_path: Path) -> None:
    history = tmp_path / "history"
    history.mkdir()
    issue = {"type": "overfull_hbox", "owner": "CONTENT", "message": "8.4pt too wide"}
    for build_id in ("combined-one", "combined-two"):
        (history / f"{build_id}.json").write_text(
            json.dumps({"build_id": build_id, "diagnostics": {"issues": [issue]}}),
            encoding="utf-8",
        )

    result = analyse_history(history)

    assert result["build_count"] == 2
    assert result["recurring"] == [{"type": "overfull_hbox", "occurrences": 2, "builds": 2}]
    assert result["primitive_candidates"] == result["recurring"]


def test_pdf_inspection_reports_qa_metadata(tmp_path: Path) -> None:
    try:
        import pymupdf as fitz
    except ImportError:  # PyMuPDF < 1.26
        fitz = pytest.importorskip("fitz")

    pdf = tmp_path / "qa.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 72), "ReportKit QA")
    document.set_toc([[1, "QA", 1]])
    document.save(pdf)
    document.close()

    from publication_pipeline.scripts.inspect_pdf import inspect

    result = inspect(pdf)

    assert result["passed"] is True
    assert result["blank_pages"] == []
    assert result["bookmarks"]["count"] == 1
    assert result["page_dimensions"] == [{"page": 1, "width": 595.0, "height": 842.0}]
    assert result["fonts"]
    assert "near_margin_content" in result


def test_project_assets_are_staged_with_hashes(tmp_path: Path) -> None:
    source = tmp_path / "publication"
    output = tmp_path / "build"
    (source / "figures" / "nested").mkdir(parents=True)
    (source / "assets").mkdir()
    (source / "figures" / "nested" / "chart.png").write_bytes(b"chart")
    (source / "assets" / "logo.svg").write_text("<svg/>", encoding="utf-8")

    staged = stage_project_assets(source, output)

    assert {item["path"] for item in staged} == {"figures/nested/chart.png", "assets/logo.svg"}
    assert (output / "figures" / "nested" / "chart.png").read_bytes() == b"chart"
    assert (output / "assets" / "logo.svg").read_text(encoding="utf-8") == "<svg/>"
    assert all(len(item["sha256"]) == 64 for item in staged)
