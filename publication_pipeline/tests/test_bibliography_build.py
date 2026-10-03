"""Bibliography staging, pass sequencing and build report."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import types

import pytest

from publication_pipeline.scripts import publication_build
from reportkit.bibliography import (
    BibliographySettings,
    aux_has_citations,
    blg_diagnostics,
    count_bbl_entries,
    write_bibliography_config,
)

REPO = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path, **overrides) -> BibliographySettings:
    values = dict(file="references.bib", path=tmp_path / "references.bib", stem="references",
                  style="numeric", title="Works & Sources", include_uncited=False)
    values.update(overrides)
    return BibliographySettings(**values)


def test_config_writer_escapes_title(tmp_path: Path) -> None:
    write_bibliography_config(tmp_path / "c.tex", _settings(tmp_path, include_uncited=True))
    text = (tmp_path / "c.tex").read_text(encoding="utf-8")
    assert "\\renewcommand{\\RKBibStyle}{numeric}" in text
    assert "\\renewcommand{\\RKBibFile}{references}" in text
    assert "\\renewcommand{\\RKBibTitle}{Works \\& Sources}" in text
    assert "\\RKBibIncludeUncitedtrue" in text


def test_log_helpers() -> None:
    assert aux_has_citations("\\relax\n\\citation{a}\n\\bibdata{references}\n")
    assert not aux_has_citations("\\relax\n\\bibdata{references}\n")
    blg = "Warning--empty journal in jones2019\nI couldn't open database file nope.bib\n(There were 2 warnings)\n"
    kinds = [(item["type"], item["severity"]) for item in blg_diagnostics(blg)]
    assert kinds == [("bibliography_warning", "warning"), ("bibliography_warning", "warning")]
    assert count_bbl_entries("\\bibitem[{A}(2024)]{a}\nx\n\\bibitem{b}\n") == 2


class _Recorder:
    """Fake run_limited: records commands and fakes TeX/bibtex outputs."""

    def __init__(self, output: Path, *, aux: str, bibtex_code: int = 0) -> None:
        self.output, self.aux, self.bibtex_code, self.commands = output, aux, bibtex_code, []

    def __call__(self, command, *, cwd, timeout, memory_limit_mb, **kwargs):
        self.commands.append(command[0])
        stream = kwargs.get("stdout")
        if command[0] == "bibtex":
            (self.output / "publication.bbl").write_text("\\bibitem{a}\n", encoding="utf-8")
            (self.output / "publication.blg").write_text("Warning--empty year in a\n", encoding="utf-8")
            if stream is not None:
                stream.write("bibtex\n")
            return types.SimpleNamespace(returncode=self.bibtex_code)
        (self.output / "publication.aux").write_text(self.aux, encoding="utf-8")
        if stream is not None:
            stream.write("tex pass\n")
        return types.SimpleNamespace(returncode=0)


def _run_passes(tmp_path: Path, monkeypatch, *, settings, aux: str, bibtex_code: int = 0):
    output = tmp_path / "out"
    output.mkdir()
    (output / "publication.tex").write_text("", encoding="utf-8")
    recorder = _Recorder(output, aux=aux, bibtex_code=bibtex_code)
    monkeypatch.setattr(publication_build, "run_limited", recorder)
    report = {"commands": [], "exit_codes": [], "bibliography": None if settings is None else {
        "file": settings.file, "style": settings.style, "entries_cited": 0, "bibtex_exit": None,
        "auto_placed": False, "diagnostics": []}}
    result = publication_build._compile_tex_passes(
        engine="pdflatex", tex=output / "publication.tex", log=output / "publication.log", output=output,
        texinputs="", timeout=10, memory_limit_mb=512, selection_marker="MARK", report=report,
        report_path=output / "build-report.json", history_root=tmp_path / "history", bibliography=settings,
    )
    return result, recorder.commands, report


def test_unconfigured_build_runs_exactly_two_tex_passes(tmp_path: Path, monkeypatch) -> None:
    result, commands, _ = _run_passes(tmp_path, monkeypatch, settings=None, aux="\\citation{a}\n")
    assert result is None
    assert commands == ["pdflatex", "pdflatex"]


def test_configured_build_with_citations_runs_bibtex_then_two_passes(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n")
    assert result is None
    assert commands == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]
    assert report["bibliography"]["bibtex_exit"] == 0
    assert report["bibliography"]["entries_cited"] == 1
    assert report["bibliography"]["diagnostics"][0]["type"] == "bibliography_warning"
    assert "bibtex publication" in report["commands"]


def test_configured_build_without_citations_skips_bibtex(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\bibdata{references}\n")
    assert result is None
    assert commands == ["pdflatex", "pdflatex"]
    assert report["bibliography"]["bibtex_exit"] is None


def test_bibtex_warnings_exit_one_is_not_a_failure(tmp_path: Path, monkeypatch) -> None:
    result, commands, _ = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n", bibtex_code=1)
    assert result is None
    assert commands == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]


def test_bibtex_error_fails_with_exit_four(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n", bibtex_code=2)
    assert result == 4
    assert commands == ["pdflatex", "bibtex"]
    assert report["status"] == "failed"


def test_missing_bibtex_fails_with_exit_five(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "out"
    output.mkdir()
    calls = []

    def fake(command, **kwargs):
        calls.append(command[0])
        if command[0] == "bibtex":
            raise FileNotFoundError("bibtex")
        (output / "publication.aux").write_text("\\citation{a}\n", encoding="utf-8")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(publication_build, "run_limited", fake)
    report = {"commands": [], "exit_codes": [], "bibliography": {"bibtex_exit": None, "diagnostics": [], "entries_cited": 0}}
    result = publication_build._compile_tex_passes(
        engine="pdflatex", tex=output / "publication.tex", log=output / "publication.log", output=output,
        texinputs="", timeout=10, memory_limit_mb=512, selection_marker="MARK", report=report,
        report_path=output / "build-report.json", history_root=tmp_path / "history", bibliography=_settings(tmp_path),
    )
    assert result == 5
    assert report["diagnostics"]["diagnostics"][0]["code"] == "RK_BIBTEX_MISSING"


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("pdflatex", "bibtex", "pandoc")), reason="requires pdflatex, bibtex, pandoc",
)
def test_markdown_project_with_subdirectory_bib_builds_end_to_end(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    source = tmp_path / "project"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "refs").mkdir()
    (source / "refs" / "main.bib").write_text(
        "@book{smith2024, author={Smith, Ada}, title={Gauges and Rivers}, publisher={Delta Press}, year={2024}}\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-intro.md\n", encoding="utf-8")
    (source / "manuscript" / "01-intro.md").write_text("# Introduction\n\nGauges matter [@smith2024].\n", encoding="utf-8")
    (source / "publication.yaml").write_text(
        "publication:\n  title: Bibliography smoke\n  author: Test\n  version: v1\n"
        "document:\n  publication_type: technical-report\n  theme: default\n  source_mode: markdown\n"
        "bibliography:\n  file: refs/main.bib\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    process = subprocess.run(
        [sys.executable, str(REPO / "publication_pipeline" / "scripts" / "publication_build.py"),
         "--mode", "combined", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-4000:] + process.stderr[-4000:]
    report = json.loads((output / "combined" / "build-report.json").read_text(encoding="utf-8"))
    assert report["bibliography"]["file"] == "refs/main.bib"
    assert report["bibliography"]["entries_cited"] == 1
    assert report["bibliography"]["auto_placed"] is True
    import pymupdf

    with pymupdf.open(output / "combined" / report["pdf"]) as document:
        text = "".join(page.get_text() for page in document)
    assert "[1]" in text and "Gauges and Rivers" in text and "References" in text


def test_pandoc_gets_natbib_only_when_requested(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "p"
    (root / "manuscript").mkdir(parents=True)
    manuscript = root / "manuscript" / "01.md"
    manuscript.write_text("Text [@a].\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake(command, **kwargs):
        seen.append(command)
        return types.SimpleNamespace(returncode=0, stdout="Text \\citep{a}.\n", stderr="")

    monkeypatch.setattr(publication_build, "run_limited", fake)
    publication_build.render_markdown(root, manuscript, tmp_path / "a.tex", natbib=True)
    publication_build.render_markdown(root, manuscript, tmp_path / "b.tex")
    assert "--natbib" in seen[0]
    assert "--natbib" not in seen[1]
