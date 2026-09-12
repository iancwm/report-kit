from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

from reportkit.authoring import render_links_tex, tex_escape as authoring_tex_escape
from reportkit.cli import build_parser, main
from reportkit.latex import tex_escape
from reportkit.toolchain import version_line
from publication_build import resolve_roots, tex_escape as build_tex_escape
import reportkit_doctor


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("value", ["\\", "&", "%", "$", "#", "_", "{", "}", "~", "^"])
def test_all_latex_text_callers_share_the_same_escaper(value: str, tmp_path: Path) -> None:
    assert build_tex_escape is authoring_tex_escape is tex_escape
    links = tmp_path / "links.yaml"
    links.write_text(f"links:\n  item:\n    url: https://example.com/a%20b\n    label: A{value}B\n    type: documentation\n", encoding="utf-8")
    output = tmp_path / "links.tex"
    render_links_tex(links, output)
    assert tex_escape(f"A{value}B") in output.read_text(encoding="utf-8")


def test_link_labels_escape_tilde_and_circumflex(tmp_path: Path) -> None:
    links = tmp_path / "links.yaml"
    links.write_text(
        "links:\n  item:\n    url: https://example.com\n    label: A~B^C\n    type: documentation\n",
        encoding="utf-8",
    )
    output = tmp_path / "links.tex"
    render_links_tex(links, output)
    assert r"A\textasciitilde{}B\textasciicircum{}C" in output.read_text(encoding="utf-8")


def test_init_scaffolds_and_refuses_engine_boundary(tmp_path: Path) -> None:
    target = tmp_path / "publication"
    assert main(["init", str(target)]) == 0
    assert (target / "manuscript" / "order.txt").is_file()
    assert (target / "publication.yaml").is_file()
    assert main(["init", str(REPO / "not-a-publication"), "--json"]) == 2


def test_output_directory_is_honoured_after_cli_precedence(tmp_path: Path) -> None:
    source = tmp_path / "publication"
    source.mkdir()
    (source / "publication.yaml").write_text("title: Example\noutput:\n  directory: artefacts\n", encoding="utf-8")
    args = build_parser().parse_args(["build", "--source-root", str(source)])
    _, output = resolve_roots(args)
    assert output == (source / "artefacts").resolve()
    args = build_parser().parse_args(["build", "--source-root", str(source), "--output-root", str(tmp_path / "explicit")])
    _, output = resolve_roots(args)
    assert output == (tmp_path / "explicit").resolve()


def test_dependency_pins_overlap_consistently() -> None:
    requirement_files = [REPO / "toolchain" / "requirements.lock", REPO / "publication_pipeline" / "requirements.txt", REPO / "tests" / "requirements.txt"]
    declared: dict[str, set[str]] = {}
    for path in requirement_files:
        for package, version in re.findall(r"(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)", path.read_text(encoding="utf-8")):
            declared.setdefault(package.lower().replace("-", "_"), set()).add(version)
    lock = json.loads((REPO / "toolchain" / "toolchain.lock.json").read_text(encoding="utf-8"))
    for package, version in lock["python_packages"].items():
        declared.setdefault(package.lower().replace("-", "_"), set()).add(version)
    assert all(len(versions) == 1 for versions in declared.values()), declared


def test_setup_script_and_renderer_use_consumer_build_venv() -> None:
    setup = (REPO / "publication_pipeline/scripts/setup.sh").read_text(encoding="utf-8")
    assert "${1:-$PROJECT_ROOT/build/.venv}" in setup
    assert "output_root / \".venv\" / \"bin\" / \"python\"" in (REPO / "publication_pipeline/scripts/publication_build.py").read_text(encoding="utf-8")


def test_version_probe_uses_shared_toolchain_helper() -> None:
    assert version_line("definitely-not-a-reportkit-command") is None


def test_doctor_dependency_remediation_is_present_in_text_and_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(reportkit_doctor, "check_import", lambda name: (False, "not installed"))
    monkeypatch.setattr(sys, "argv", ["reportkit_doctor.py"])
    assert reportkit_doctor.main() == 0
    assert reportkit_doctor.PYTHON_DEPENDENCY_INSTALL in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["reportkit_doctor.py", "--json"])
    assert reportkit_doctor.main() == 0
    payload = json.loads(capsys.readouterr().out)
    diagnostic = next(item for item in payload["diagnostics"] if item["code"] == "RK_PYTHON_DEPENDENCIES_MISSING")
    assert reportkit_doctor.PYTHON_DEPENDENCY_INSTALL == diagnostic["remediation"]
