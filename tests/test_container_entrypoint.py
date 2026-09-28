from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("container_build", REPO / "toolchain" / "container_build.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

MEASURE = lambda pdf: {"pages": 7, "width_mm": 210, "height_mm": 297, "paper": "a4"}  # noqa: E731


def stage(work: Path, files: dict[str, bytes]) -> None:
    source = work / "source"
    entries = []
    for rel, data in files.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entries.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (work / "input-manifest.json").write_text(json.dumps({"schema": "reportkit-input-manifest/1", "directories": [], "files": entries}))
    (work / "build").mkdir()
    (work / "result").mkdir()


class FakeTools:
    """Plays the reportkit CLI and TeX. fail maps a step name to an exit code.

    big_stdout optionally overrides a step's returned stdout bytes (while still
    performing that step's normal file side effects), so tests can prove log
    truncation against content that is genuinely larger than MAX_LOG_BYTES.
    """

    def __init__(self, fail: dict[str, int] | None = None, big_stdout: dict[str, bytes] | None = None) -> None:
        self.fail = fail or {}
        self.big_stdout = big_stdout or {}
        self.calls: list[tuple[str, list[str], dict]] = []

    def __call__(self, argv, cwd, env, timeout):
        name = argv[2] if len(argv) > 2 and argv[1].endswith("reportkit") else Path(argv[0]).name
        self.calls.append((name, argv, env))
        code = self.fail.get(name, 0)
        payload = {"passed": code == 0, "diagnostics": [] if code == 0 else [{"code": f"RK_FAKE_{name.upper()}", "severity": "error", "message": f"{name} failed"}]}
        if name == "build" and code == 0:
            out = Path(argv[argv.index("--output-root") + 1]) / "combined"
            out.mkdir(parents=True)
            (out / "doc.pdf").write_bytes(b"%PDF pipeline")
            (out / "build-report.json").write_text(json.dumps({"pdf": "doc.pdf", "selection": {"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": None}}))
            (Path(argv[argv.index("--source-root") + 1]) / "reportkit.lock").write_text("{}")
        if name in ("lualatex", "pdflatex") and code == 0:
            stem = Path(argv[-1]).stem
            (Path(cwd) / f"{stem}.pdf").write_bytes(b"%PDF direct")
            (Path(cwd) / f"{stem}.log").write_text("clean log")
        if name == "render" and code == 0:
            out = Path(argv[argv.index("--out") + 1])
            out.mkdir(parents=True)
            (out / "pages.json").write_text("{}")
            (out / "page-001.png").write_bytes(b"png")
        stdout = self.big_stdout.get(name, json.dumps(payload).encode())
        return subprocess.CompletedProcess(argv, code, stdout, b"stderr text")


def run(work: Path, tools: FakeTools, *argv: str, lock=lambda path, engine: path.write_text("{}")) -> int:
    return cb.main(["--work-root", str(work), *argv], runner=tools, measure=MEASURE, write_lock=lock,
                   environ={"REPORTKIT_IMAGE_REF": "img@sha256:" + "a" * 64, "REPORTKIT_IMAGE_DIGEST": "sha256:" + "a" * 64,
                            "REPORTKIT_COMMIT": "c" * 40, "REPORTKIT_RELEASE_ELIGIBLE": "1"})


def manifest(work: Path) -> dict:
    return json.loads((work / "result" / "container-build.json").read_text())


def test_pipeline_success_writes_complete_result(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n", "manuscript/01.md": b"# A\r\n"})
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "pipeline") == 0
    data = manifest(tmp_path)
    assert data["status"] == "passed" and data["kind"] == "pipeline"
    assert [s["name"] for s in data["steps"]] == ["verify-inputs", "check", "build", "render", "inspect"]
    assert data["selection"] == {"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": "a4"}
    assert data["pdf"]["pages"] == 7 and data["pdf"]["sha256"] == hashlib.sha256(b"%PDF pipeline").hexdigest()
    assert data["reportkit"]["commit"] == "c" * 40 and data["image"]["digest"] == "sha256:" + "a" * 64
    assert data["input_manifest_sha256"] == hashlib.sha256((tmp_path / "input-manifest.json").read_bytes()).hexdigest()
    result = tmp_path / "result"
    listed = {o["path"] for o in data["outputs"]}
    assert {"doc.pdf", "build-report.json", "reportkit.lock", "inspection.json", "render/pages.json", "render/page-001.png"} <= listed
    assert listed == {p.relative_to(result).as_posix() for p in result.rglob("*") if p.is_file()} - {"container-build.json"}


def test_source_is_never_written(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    run(tmp_path, FakeTools(), "--kind", "pipeline")
    assert sorted(p.name for p in (tmp_path / "source").iterdir()) == ["publication.yaml"]


def test_every_step_runs_without_shell_escape_and_offline_python(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass[theme=editorial,publication-type=feature-article]{reportkit}"})
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "direct-tex", "--entry", "report.tex") == 0
    compiles = [argv for name, argv, _ in tools.calls if name == "lualatex"]
    assert len(compiles) == 2 and all("-no-shell-escape" in argv for argv in compiles)
    env = next(env for name, _, env in tools.calls if name == "lualatex")
    assert env["shell_escape"] == "f" and env["openout_any"] == "p" and "latex_templates" in env["TEXINPUTS"]
    data = manifest(tmp_path)
    assert data["selection"] == {"publication_type": "feature-article", "theme": "editorial", "engine": "lualatex", "paper": "a4"}
    assert [s["name"] for s in data["steps"]] == ["verify-inputs", "compile-1", "compile-2", "diagnose", "render", "inspect"]


def test_editorial_brief_triggers_audit_first(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass{reportkit}", "editorial-brief.json": b"{}"})
    tools = FakeTools(fail={"audit-editorial": 3})
    assert run(tmp_path, tools, "--kind", "direct-tex", "--entry", "report.tex") == 3
    data = manifest(tmp_path)
    assert data["status"] == "failed" and data["failed_step"] == "audit-editorial"
    assert not any(name == "lualatex" for name, _, _ in tools.calls)
    assert data["diagnostics"][0]["code"] == "RK_FAKE_AUDIT-EDITORIAL"
    assert {o["path"] for o in data["outputs"]} == {"logs/verify-inputs.log", "logs/audit-editorial.log"}


@pytest.mark.parametrize("step,code", [("check", 3), ("build", 4), ("render", 5), ("inspect", 3)])
def test_pipeline_failure_stops_and_withholds_pdf(tmp_path: Path, step: str, code: int) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    assert run(tmp_path, FakeTools(fail={step: code}), "--kind", "pipeline") == code
    data = manifest(tmp_path)
    assert data["failed_step"] == step and data["status"] == "failed"
    assert not any(o["path"].endswith(".pdf") for o in data["outputs"])


def test_diagnostic_gate_failure_on_direct_tex(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass{reportkit}"})
    assert run(tmp_path, FakeTools(fail={"diagnose": 3}), "--kind", "direct-tex", "--entry", "report.tex") == 3
    assert manifest(tmp_path)["failed_step"] == "diagnose"


def test_input_mismatch_is_rejected_before_any_tool(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    (tmp_path / "source" / "publication.yaml").write_bytes(b"title: tampered\n")
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "pipeline") == 3
    assert tools.calls == [] and manifest(tmp_path)["failed_step"] == "verify-inputs"


def test_unexpected_extra_source_file_is_rejected(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    (tmp_path / "source" / "stowaway.tex").write_bytes(b"x")
    assert run(tmp_path, FakeTools(), "--kind", "pipeline") == 3


def test_logs_are_tail_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cb, "MAX_LOG_BYTES", 100)
    head_marker = b"HEAD-MARKER-STARTS-HERE"
    tail_marker = b"TAIL-MARKER-ENDS-HERE"
    build_stdout = head_marker + b"." * 500 + tail_marker
    tools = FakeTools(big_stdout={"build": build_stdout})
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    assert run(tmp_path, tools, "--kind", "pipeline") == 0
    # Reconstruct exactly what Build.step() concatenates before slicing, so the
    # assertion below only passes if the tail-slice actually happened correctly.
    expected_full = build_stdout + b"\n--- stderr ---\n" + b"stderr text"
    assert len(expected_full) > 100  # pre-truncation content must exceed the bound
    log_bytes = (tmp_path / "result" / "logs" / "build.log").read_bytes()
    assert len(log_bytes) == 100
    assert log_bytes == expected_full[-100:]
    assert head_marker not in log_bytes
    assert tail_marker in log_bytes


def test_verify_inputs_log_is_tail_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cb, "MAX_LOG_BYTES", 50)
    long_name = "manuscript/" + ("y" * 70) + ".md"
    stage(tmp_path, {"publication.yaml": b"title: T\n", long_name: b"body\n"})
    (tmp_path / "source" / long_name).write_bytes(b"tampered body\n")
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "pipeline") == 3
    assert tools.calls == []
    expected_full = long_name.encode("utf-8")
    assert len(expected_full) > 50  # pre-truncation content must exceed the bound
    log_bytes = (tmp_path / "result" / "logs" / "verify-inputs.log").read_bytes()
    assert len(log_bytes) == 50
    assert log_bytes == expected_full[-50:]
    assert not log_bytes.startswith(expected_full[:10])
    assert log_bytes.endswith(expected_full[-10:])


def test_direct_tex_entry_must_stay_inside_source(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"x"})
    assert run(tmp_path, FakeTools(), "--kind", "direct-tex", "--entry", "../etc/passwd.tex") == 2
