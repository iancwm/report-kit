"""Unit tests for scripts/visual_qa_operator.py that need no pinned render.

Everything here runs on synthetic logs, glyph tables and pixel arrays, or on
the script's own gating logic with the toolchain probes monkeypatched. None of
it compiles the fixture, so none of it is evidence that the fixture's pages
were rendered or reviewed.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pymupdf")
pytest.importorskip("pdfplumber")
np = pytest.importorskip("numpy")

REPO = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "visual_qa_operator", REPO / "scripts" / "visual_qa_operator.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("visual_qa_operator", module)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


qa = _load_module()


def _run_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict | str, str]:
    monkeypatch.setattr(sys, "argv", ["visual_qa_operator.py", *argv])
    code = qa.main()
    captured = capsys.readouterr()
    payload: dict | str = captured.out
    if "--json" in argv:
        payload = json.loads(captured.out)
    return code, payload, captured.err


# ------------------------------------------------------------------ log parser


def test_parse_log_issues_clean_log_has_none() -> None:
    assert qa.parse_log_issues("This is pdfTeX\nOutput written on report.pdf (7 pages).\n") == []


def test_parse_log_issues_flags_overfull_hbox_and_vbox_with_line_numbers() -> None:
    log = "ok\nOverfull \\hbox (3.2pt too wide) in paragraph at lines 4--5\nfine\nOverfull \\vbox (1pt too high) has occurred\n"
    issues = qa.parse_log_issues(log)
    assert len(issues) == 2
    assert issues[0].startswith("line 2:") and "hbox" in issues[0]
    assert issues[1].startswith("line 4:") and "vbox" in issues[1]


def test_parse_log_issues_ignores_underfull_boxes() -> None:
    assert qa.parse_log_issues("Underfull \\hbox (badness 10000) in paragraph at lines 1--2\n") == []


def test_parse_log_issues_flags_fancyhdr_headheight_warning() -> None:
    log = "Package fancyhdr Warning: \\headheight is too small (12.0pt): \n(fancyhdr) Make it at least 14.5pt.\n"
    issues = qa.parse_log_issues(log)
    assert len(issues) == 1 and "headheight" in issues[0]


def test_parse_log_issues_ignores_unrelated_headheight_mentions() -> None:
    assert qa.parse_log_issues("geometry set \\headheight to 14pt\nfancyhdr loaded\n") == []


# ------------------------------------------------------------ font classifier


@pytest.mark.parametrize(
    ("name", "family"),
    [
        ("ABCDEF+LMSans10-Regular", "sans"),
        ("ABCDEF+LMSansDemiCond10-Regular", "sans"),
        ("XYZABC+LMRoman10-Regular", "roman"),
        ("XYZABC+LMMono10-Regular", "mono"),
        ("QWERTY+Helvetica", "other"),
        ("", "other"),
    ],
)
def test_font_family_classification(name: str, family: str) -> None:
    assert qa._font_family(name) == family


def _char(text: str, font: str, x: float, *, top: float = 10, page: int = 1) -> dict:
    return {"text": text, "fontname": font, "x0": x, "x1": x + 5, "top": top, "bottom": top + 8, "page": page}


def _region(expected: str, *, page: int = 1) -> dict:
    return {"page": page, "name": f"{expected}-region", "x0": 0, "x1": 100, "top": 0, "bottom": 30, "expected_font": expected}


def test_check_font_regions_accepts_matching_fonts() -> None:
    chars = [_char("a", "AAA+LMSans10-Regular", 5), _char("b", "AAA+LMSansDemiCond10-Regular", 12)]
    assert qa.check_font_regions(chars, [_region("sans")]) == []


def test_check_font_regions_names_wrong_font() -> None:
    chars = [_char("a", "AAA+LMSans10-Regular", 5), _char("b", "AAA+LMRoman10-Regular", 12)]
    problems = qa.check_font_regions(chars, [_region("sans")])
    assert len(problems) == 1
    assert "sans-region" in problems[0] and "LMRoman10-Regular" in problems[0]


def test_check_font_regions_reports_empty_region() -> None:
    problems = qa.check_font_regions([_char("a", "AAA+LMSans10-Regular", 500)], [_region("sans")])
    assert problems == ["sans-region: no text glyphs found in the expected region"]


def test_check_font_regions_ignores_whitespace_and_other_pages() -> None:
    chars = [
        _char(" ", "AAA+Helvetica", 5),
        _char("x", "AAA+Helvetica", 5, page=2),
        _char("y", "AAA+LMMono10-Regular", 8),
    ]
    assert qa.check_font_regions(chars, [_region("mono")]) == []


# ------------------------------------------------------------- pixel contrast


def test_terminal_contrast_passes_light_glyphs_on_dark_surface() -> None:
    pixels = np.full((20, 40, 3), 14, dtype=np.uint8)
    pixels[8:12, 5:30] = 245
    result = qa.check_terminal_contrast(pixels)
    assert result["passed"] is True
    assert result["background_luminance"] < 0.15
    assert result["glyph_luminance"] >= 0.8


def test_terminal_contrast_fails_black_text_on_dark_box() -> None:
    """The spec section 8 item 1 defect: body text inheriting black."""
    pixels = np.full((20, 40, 3), 14, dtype=np.uint8)
    pixels[8:12, 5:30] = 0
    result = qa.check_terminal_contrast(pixels)
    assert result["passed"] is False
    assert result["glyph_pixel_count"] == 0


def test_terminal_contrast_fails_light_surface() -> None:
    assert qa.check_terminal_contrast(np.full((10, 10), 240, dtype=np.uint8))["passed"] is False


def test_terminal_contrast_fails_when_too_few_glyph_pixels() -> None:
    pixels = np.full((20, 40), 10, dtype=np.uint8)
    pixels[0, :2] = 250
    assert qa.check_terminal_contrast(pixels)["passed"] is False


def test_terminal_contrast_rejects_empty_and_bad_shapes() -> None:
    assert qa.check_terminal_contrast(np.zeros((0, 0)))["passed"] is False
    assert qa.check_terminal_contrast(np.zeros(5))["passed"] is False


def test_terminal_contrast_accepts_normalised_float_input() -> None:
    pixels = np.full((20, 40), 0.05)
    pixels[5:10, 5:30] = 0.95
    assert qa.check_terminal_contrast(pixels)["passed"] is True


# ------------------------------------------------------------------- checklist


def test_manual_review_checklist_is_present_and_covers_spec_areas() -> None:
    assert len(qa.CHECKLIST) >= 6
    text = " ".join(qa.CHECKLIST).lower()
    for phrase in ("capability grid", "terminal", "diff", "figures 3, 5, and 6", "grayscale", "blank pages"):
        assert phrase in text
    assert len(set(qa.CHECKLIST)) == len(qa.CHECKLIST)


def test_page_count_bounds_are_sane() -> None:
    assert 1 <= qa.MINIMUM_PAGES <= qa.MAXIMUM_PAGES


# --------------------------------------------------- argument handling / gates


def test_help_lists_documented_options(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["visual_qa_operator.py", "--help"])
    with pytest.raises(SystemExit) as raised:
        qa.main()
    assert raised.value.code == 0
    out = capsys.readouterr().out
    for option in ("--update-expected", "--output-dir", "--dpi", "--threshold", "--json"):
        assert option in out


def test_unknown_option_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["visual_qa_operator.py", "--no-such-flag"])
    with pytest.raises(SystemExit) as raised:
        qa.main()
    assert raised.value.code == 2


def test_non_numeric_dpi_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["visual_qa_operator.py", "--dpi", "high"])
    with pytest.raises(SystemExit) as raised:
        qa.main()
    assert raised.value.code == 2


def test_missing_pdflatex_skips_with_clear_reason_and_exit_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: None)
    code, payload, _ = _run_main(monkeypatch, capsys, "--json")
    assert code == 0
    assert payload["skipped"] is True and payload["passed"] is True
    assert "pdflatex not found" in payload["reason"]


def test_missing_pdflatex_text_mode_warns_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: None)
    code, _, err = _run_main(monkeypatch, capsys)
    assert code == 0
    assert "pdflatex not found" in err


def _fake_toolchain(status: str, resolved_fingerprint: str, fingerprint: str = "sha256:pinned") -> dict:
    return {"resolved": {"status": status, "fingerprint": resolved_fingerprint}, "fingerprint": fingerprint}


def test_unpinned_toolchain_is_refused_before_any_compile(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("unpinned", "sha256:other"))

    def _no_compile(*args, **kwargs):
        raise AssertionError("the fixture must not be compiled on an unpinned toolchain")

    monkeypatch.setattr(qa, "compile_fixture", _no_compile)
    code, payload, _ = _run_main(monkeypatch, capsys, "--json", "--output-dir", str(tmp_path / "out"))
    assert code == 1
    assert payload["passed"] is False
    assert [d["code"] for d in payload["diagnostics"]] == ["RK_OPERATOR_TOOLCHAIN"]
    assert not (tmp_path / "out").exists()


def test_fingerprint_mismatch_is_also_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("pinned", "sha256:different"))
    code, payload, _ = _run_main(monkeypatch, capsys, "--json")
    assert code == 1
    assert payload["diagnostics"][0]["code"] == "RK_OPERATOR_TOOLCHAIN"


def test_text_mode_failure_prints_fail_and_exits_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("unpinned", "x"))
    code, out, _ = _run_main(monkeypatch, capsys)
    assert code == 1
    assert out.startswith("FAIL: Operator visual QA")


def test_missing_baseline_is_refused_unless_updating(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("pinned", "sha256:pinned"))
    monkeypatch.setattr(qa, "EXPECTED", tmp_path / "expected")

    def _no_compile(*args, **kwargs):
        raise AssertionError("no compile without a baseline")

    monkeypatch.setattr(qa, "compile_fixture", _no_compile)
    code, payload, _ = _run_main(monkeypatch, capsys, "--json", "--output-dir", str(tmp_path / "out"))
    assert code == 1
    assert [d["code"] for d in payload["diagnostics"]] == ["RK_OPERATOR_BASELINE"]


def test_baseline_with_different_dpi_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    expected = tmp_path / "expected"
    expected.mkdir()
    (expected / "baseline.json").write_text(
        json.dumps({"toolchain_fingerprint": "sha256:pinned", "dpi": 140, "pixel_difference_threshold": 0.01}),
        encoding="utf-8",
    )
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("pinned", "sha256:pinned"))
    monkeypatch.setattr(qa, "EXPECTED", expected)
    code, payload, _ = _run_main(monkeypatch, capsys, "--json", "--dpi", "100", "--output-dir", str(tmp_path / "out"))
    assert code == 1
    assert payload["diagnostics"][0]["code"] == "RK_OPERATOR_BASELINE"


def test_compile_failure_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(qa, "toolchain_context", lambda root: _fake_toolchain("pinned", "sha256:pinned"))
    monkeypatch.setattr(qa, "EXPECTED", tmp_path / "expected")
    monkeypatch.setattr(qa, "compile_fixture", lambda workdir: (workdir / "missing.pdf", "! Emergency stop.", 1))
    code, payload, _ = _run_main(monkeypatch, capsys, "--json", "--update-expected", "--output-dir", str(tmp_path / "out"))
    assert code == 1
    assert payload["diagnostics"][0]["code"] == "RK_OPERATOR_COMPILE"
    assert "Emergency stop" in payload["diagnostics"][0]["details"]["log_tail"]
    assert not (tmp_path / "expected" / "baseline.json").exists()


def test_fixture_paths_point_at_the_operator_report() -> None:
    assert qa.EXAMPLE == REPO / "latex_templates" / "examples" / "operator-report"
    assert (qa.EXAMPLE / "report.tex").is_file()
