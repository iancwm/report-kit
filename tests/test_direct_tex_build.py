"""Direct-TeX target gates and build staging (agent reasoning loop spec §4.3)."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from reportkit.diagnostics import registered_exit_code
from reportkit.target import TargetState
from reportkit.tex_target import engine_gate, read_class_options, tex_gates


REPO = Path(__file__).resolve().parents[1]
EDITORIAL_SOURCE = REPO / "latex_templates" / "examples" / "editorial-feature"


def _state(*, publication_type: str = "feature-article", theme: str = "editorial") -> TargetState:
    return TargetState(
        publication_type=publication_type,
        theme=theme,
        renderer="paged",
        source_mode="tex",
        main="report.tex",
        declared_by="publication.yaml",
        intent=None,
        require_declared=False,
    )


def _project(root: Path, *, class_options: str = "publication-type=feature-article,theme=editorial") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "publication.yaml").write_text(
        "title: Direct TeX fixture\n"
        "document:\n"
        "  publication_type: feature-article\n"
        "  theme: editorial\n"
        "  source_mode: tex\n"
        "  main: report.tex\n",
        encoding="utf-8",
    )
    (root / "report.tex").write_text(
        f"\\documentclass[{class_options}]{{reportkit}}\n"
        "\\begin{document}\nDirect TeX.\n\\end{document}\n",
        encoding="utf-8",
    )
    return root


def _build(source: Path, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(REPO / "reportkit"), "build", "--mode", "combined",
            "--source-root", str(source), "--output-root", str(output), *extra, "--json",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )


def _has_editorial_tex_prerequisites() -> bool:
    if shutil.which("lualatex") is None:
        return False
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        return False
    package = subprocess.run(
        [kpsewhich, "siunitx.sty"], capture_output=True, text=True, timeout=5,
    )
    return package.returncode == 0 and bool(package.stdout.strip())


def test_read_class_options_parses_required_options_independent_of_order(tmp_path: Path) -> None:
    tex = tmp_path / "report.tex"
    tex.write_text(
        "% \\documentclass[publication-type=wrong,theme=default]{reportkit}\n"
        "\\documentclass[11pt, theme = {editorial}, publication-type = {feature-article}]{reportkit}\n",
        encoding="utf-8",
    )

    assert read_class_options(tex) == {
        "publication-type": "feature-article",
        "theme": "editorial",
    }


@pytest.mark.parametrize(
    "source",
    (
        r"\documentclass{reportkit}",
        r"\documentclass[theme=editorial]{reportkit}",
        r"\documentclass[publication-type=feature-article,theme=editorial]{article}",
        r"% \documentclass[publication-type=feature-article,theme=editorial]{reportkit}",
    ),
)
def test_read_class_options_returns_none_when_declaration_is_incomplete_or_not_reportkit(
    tmp_path: Path, source: str,
) -> None:
    tex = tmp_path / "report.tex"
    tex.write_text(source, encoding="utf-8")

    assert read_class_options(tex) is None


def test_tex_gates_reject_missing_or_mismatched_target_before_compile(tmp_path: Path) -> None:
    tex = tmp_path / "report.tex"
    tex.write_text(r"\documentclass[publication-type=technical-report,theme=default]{reportkit}", encoding="utf-8")

    diagnostic = tex_gates(_state(), tex)[0]

    assert diagnostic["code"] == "RK_TARGET_MISMATCH"
    assert registered_exit_code([diagnostic]) == 3
    assert diagnostic["details"]["actual"]["theme"] == "default"

    tex.write_text(r"\documentclass{reportkit}", encoding="utf-8")
    missing = tex_gates(_state(), tex)[0]
    assert missing["code"] == "RK_TARGET_MISMATCH"
    assert missing["details"]["actual"] is None


def test_engine_gate_uses_theme_engine_conflict() -> None:
    assert engine_gate(_state(), "lualatex") == []
    diagnostic = engine_gate(_state(), "pdflatex")[0]

    assert diagnostic["code"] == "RK_ENGINE_DOWNGRADE"
    assert registered_exit_code([diagnostic]) == 5
    assert "lualatex" in diagnostic["message"]


def test_direct_tex_gates_stop_build_before_output_or_tex_is_started(tmp_path: Path) -> None:
    source = _project(tmp_path / "publication", class_options="publication-type=feature-article,theme=default")
    output = tmp_path / "build-mismatch"

    mismatch = _build(source, output)

    assert mismatch.returncode == 3
    assert json.loads(mismatch.stdout)["diagnostics"][0]["code"] == "RK_TARGET_MISMATCH"
    assert not output.exists()

    (source / "report.tex").write_text(
        r"\documentclass[publication-type=feature-article,theme=editorial]{reportkit}" + "\n"
        r"\begin{document}Direct TeX.\end{document}" + "\n",
        encoding="utf-8",
    )
    downgrade = _build(source, tmp_path / "build-downgrade", "--engine", "pdflatex")

    assert downgrade.returncode == 5
    assert json.loads(downgrade.stdout)["diagnostics"][0]["code"] == "RK_ENGINE_DOWNGRADE"
    assert not (tmp_path / "build-downgrade").exists()


@pytest.mark.skipif(
    not _has_editorial_tex_prerequisites(),
    reason="requires LuaLaTeX and siunitx.sty (install the TeX dependencies with scripts/setup_tex.sh)",
)
def test_direct_tex_build_stages_source_and_records_selection(tmp_path: Path) -> None:
    source = _project(tmp_path / "publication")
    (source / "report.tex").write_bytes((EDITORIAL_SOURCE / "report.tex").read_bytes())
    shutil.copytree(EDITORIAL_SOURCE / "figures", source / "figures")
    output = tmp_path / "build"

    result = _build(source, output)
    payload = json.loads(result.stdout)

    assert result.returncode == 0, payload
    report = payload["report"]
    assert report["status"] == "passed"
    assert report["selection"]["engine"] == "lualatex"
    assert report["selection"]["declared_by"] == "publication.yaml"
    staged_tex = output / "combined" / "publication.tex"
    assert staged_tex.read_bytes() == (source / "report.tex").read_bytes()
    assert (output / "combined" / report["pdf"]).is_file()
