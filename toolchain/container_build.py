#!/usr/bin/env python3
"""Container-side ReportKit publication build.

Runs inside the toolchain image, started by scripts/reportkit_container.py:
  /work/input-manifest.json  staged by the launcher (verified first)
  /work/source               staged publication (never written)
  /work/build                scratch: a working copy plus all TeX output
  /work/result                returned to the host; listed in container-build.json

It only sequences existing ReportKit commands. Document logic stays in the
CLI and publication_pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python_scripts"))
sys.path.insert(0, str(REPO_ROOT / "publication_pipeline" / "scripts"))

from reportkit.version import CONTRACT_VERSION, REPORTKIT_VERSION  # noqa: E402

SCHEMA = "reportkit-container-build/1"
MAX_LOG_BYTES = 256 * 1024
TEMPLATES = REPO_ROOT / "latex_templates"
REPORTKIT = [sys.executable, str(REPO_ROOT / "reportkit")]
CLASS_OPTIONS = re.compile(r"\\documentclass\s*\[([^\]]*)\]\s*\{reportkit\}")
PAPERS = {(210, 297): "a4", (297, 210): "a4-landscape", (216, 279): "letter", (279, 216): "letter-landscape"}

Runner = Callable[[list[str], Path, dict[str, str], int], subprocess.CompletedProcess]


class StepFailed(Exception):
    def __init__(self, step: str, exit_code: int) -> None:
        super().__init__(f"{step} failed with exit {exit_code}")
        self.step, self.exit_code = step, exit_code


def run_process(argv: list[str], cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(argv, 4, exc.stdout or b"", (exc.stderr or b"") + f"\ntimed out after {timeout} s".encode())


def measure_pdf(pdf: Path) -> dict[str, Any]:
    import pymupdf
    with pymupdf.open(pdf) as document:
        rect = document[0].rect
        width, height = round(rect.width * 25.4 / 72), round(rect.height * 25.4 / 72)
        return {"pages": document.page_count, "width_mm": width, "height_mm": height,
                "paper": PAPERS.get((width, height), f"{width}x{height}mm")}


def default_write_lock(path: Path, engine: str) -> None:
    from publication_build import write_lock
    from reportkit.toolchain import toolchain_context, version_line
    write_lock(path, engine=engine, toolchain=toolchain_context(REPO_ROOT),
               tool_versions={"python": platform.python_version(), "pandoc": version_line("pandoc") or "unknown"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Build:
    def __init__(self, work: Path, args: argparse.Namespace, runner: Runner, measure: Callable, write_lock: Callable, environ: dict[str, str]) -> None:
        self.work, self.args, self.runner, self.measure, self.write_lock = work, args, runner, measure, write_lock
        self.source, self.scratch, self.result = work / "source", work / "build", work / "result"
        self.environ = environ
        self.env = {**os.environ, "LC_ALL": "C", "HOME": str(work / "home"), "TEXMFVAR": str(work / "home" / "texmf-var"),
                    "REPORTKIT_PDF_PYTHON": sys.executable, "shell_escape": "f", "openout_any": "p"}
        self.steps: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, str]] = []
        self.payloads: dict[str, Any] = {}
        self.record: dict[str, Any] = {"selection": {}, "inspect_passed": False}

    def step(self, name: str, argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 900) -> dict | None:
        started = time.monotonic()
        proc = self.runner(argv, cwd or self.scratch, env or self.env, timeout)
        log = self.result / "logs" / f"{name}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(((proc.stdout or b"") + b"\n--- stderr ---\n" + (proc.stderr or b""))[-MAX_LOG_BYTES:])
        self.steps.append({"name": name, "exit_code": proc.returncode, "seconds": round(time.monotonic() - started, 2), "log": f"logs/{name}.log"})
        try:
            payload = json.loads(proc.stdout or b"null")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        self.payloads[name] = payload
        if isinstance(payload, dict):
            for item in (payload.get("diagnostics") or payload.get("issues") or [])[:100]:
                if isinstance(item, dict) and len(self.diagnostics) < 100:
                    self.diagnostics.append({"step": name, "code": str(item.get("code", "")), "severity": str(item.get("severity", "error")),
                                             "message": str(item.get("message", ""))[:500]})
        if proc.returncode != 0:
            raise StepFailed(name, proc.returncode)
        return payload

    def verify_inputs(self) -> None:
        manifest_path = self.work / "input-manifest.json"
        self.record["input_manifest_sha256"] = sha256(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {item["path"]: item["sha256"] for item in manifest["files"]}
        present = {p.relative_to(self.source).as_posix() for p in self.source.rglob("*") if p.is_file() or p.is_symlink()}
        problems = sorted(set(expected) ^ present) + [p for p in sorted(expected) if p in present and sha256(self.source / p) != expected[p]]
        log = self.result / "logs" / "verify-inputs.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        content = ("\n".join(problems[:200]) or "all staged inputs match input-manifest.json").encode("utf-8")
        log.write_bytes(content[-MAX_LOG_BYTES:])
        self.steps.append({"name": "verify-inputs", "exit_code": 3 if problems else 0, "seconds": 0, "log": "logs/verify-inputs.log"})
        if problems:
            self.diagnostics.append({"step": "verify-inputs", "code": "RK_CONTAINER_INPUT_MISMATCH", "severity": "error",
                                     "message": f"{len(problems)} staged paths differ from the input manifest"})
            raise StepFailed("verify-inputs", 3)
        shutil.copytree(self.source, self.scratch / "source")

    def pipeline(self) -> Path:
        workspace, out = self.scratch / "source", self.scratch / "output"
        paths = ["--source-root", str(workspace), "--output-root", str(out)]
        profile = ["--profile", self.args.profile] if self.args.profile else []
        self.step("check", [*REPORTKIT, "check", *paths, *profile, "--json"])
        self.step("build", [*REPORTKIT, "build", *paths, *profile, "--json"], timeout=self.args.compile_timeout_seconds * 4)
        report_path = out / "combined" / "build-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.record["selection"] = report.get("selection") or {}
        self.collect_file(report_path, "build-report.json")
        self.collect_file(workspace / "reportkit.lock", "reportkit.lock")
        return out / "combined" / report["pdf"]

    def direct_tex(self) -> Path:
        entry = PurePosixPath(self.args.entry)
        workspace = self.scratch / "source"
        tex = workspace.joinpath(*entry.parts)
        brief = workspace / "editorial-brief.json"
        if brief.is_file():
            self.step("audit-editorial", [*REPORTKIT, "audit-editorial", str(tex), "--brief", str(brief), "--json"])
        texinputs = os.pathsep.join(str(p) for p in (tex.parent, TEMPLATES, TEMPLATES / "themes", TEMPLATES / "publication_types")) + os.pathsep
        env = {**self.env, "TEXINPUTS": texinputs}
        if self.args.engine == "lualatex":
            env["openin_any"] = "a"  # pinned luaotfload reads its Unicode data through Lua (see publication_pipeline/README.md)
        for run in (1, 2):
            self.step(f"compile-{run}", [self.args.engine, "-no-shell-escape", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                      cwd=tex.parent, env=env, timeout=self.args.compile_timeout_seconds)
        self.step("diagnose", [*REPORTKIT, "diagnose", str(tex.with_suffix(".log")), "--source-root", str(workspace), "--output-root", str(self.scratch), "--json"])
        match = CLASS_OPTIONS.search(tex.read_text(encoding="utf-8", errors="replace"))
        options = dict(part.strip().split("=", 1) for part in (match.group(1) if match else "").split(",") if "=" in part)
        self.record["selection"] = {"publication_type": options.get("publication-type"), "theme": options.get("theme", "default"), "engine": self.args.engine}
        pdf = tex.with_suffix(".pdf")
        report = {"schema": "reportkit-direct-tex-build/1", "entry": self.args.entry, "engine": self.args.engine, "pdf": pdf.name,
                  "selection": self.record["selection"], "input_manifest_sha256": self.record["input_manifest_sha256"], "status": "passed"}
        (self.result / "build-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.write_lock(self.result / "reportkit.lock", self.args.engine)
        return pdf

    def collect_file(self, source: Path, relative: str) -> None:
        target = self.result / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def finish_pdf(self, pdf: Path) -> None:
        render_dir = self.scratch / "render"
        render = [*REPORTKIT, "render", str(pdf), "--out", str(render_dir), "--dpi", str(self.args.dpi), "--json"]
        if self.args.pages:
            render[-1:-1] = ["--pages", self.args.pages]
        self.step("render", render)
        inspection = self.step("inspect", [*REPORTKIT, "inspect", str(pdf), "--json"])
        self.record["inspect_passed"] = True
        (self.result / "inspection.json").write_text(json.dumps(inspection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.copytree(render_dir, self.result / "render", dirs_exist_ok=True)
        measured = self.measure(pdf)
        self.record["selection"] = {key: self.record["selection"].get(key) for key in ("publication_type", "theme", "engine", "paper")}
        self.record["selection"]["paper"] = self.record["selection"]["paper"] or measured["paper"]
        self.collect_file(pdf, pdf.name)
        self.record["pdf"] = {"path": pdf.name, "sha256": sha256(pdf), **{k: measured[k] for k in ("pages", "width_mm", "height_mm")}}

    def write_manifest(self, status: str, failed_step: str | None) -> None:
        outputs = [{"path": p.relative_to(self.result).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
                   for p in sorted(self.result.rglob("*")) if p.is_file() and p.name != "container-build.json"]
        manifest = {
            "schema": SCHEMA, "status": status, "failed_step": failed_step, "kind": self.args.kind,
            "image": {"reference": self.environ.get("REPORTKIT_IMAGE_REF"), "digest": self.environ.get("REPORTKIT_IMAGE_DIGEST") or None,
                      "id": self.environ.get("REPORTKIT_IMAGE_ID")},
            "release_eligible": self.environ.get("REPORTKIT_RELEASE_ELIGIBLE") == "1",
            "reportkit": {"version": REPORTKIT_VERSION, "contract_version": CONTRACT_VERSION, "commit": self.environ.get("REPORTKIT_COMMIT", "unknown")},
            "steps": self.steps, "diagnostics": self.diagnostics, "outputs": outputs, **self.record,
        }
        (self.result / "container-build.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _clear_to_logs(result: Path) -> None:
    for child in result.iterdir():
        if child.name != "logs":
            shutil.rmtree(child) if child.is_dir() else child.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", required=True, choices=("pipeline", "direct-tex"))
    parser.add_argument("--entry")
    parser.add_argument("--engine", choices=("lualatex", "pdflatex"), default="lualatex")
    parser.add_argument("--profile")
    parser.add_argument("--pages")
    parser.add_argument("--dpi", type=int, default=110)
    parser.add_argument("--compile-timeout-seconds", type=int, default=300)
    parser.add_argument("--work-root", default="/work")
    return parser


def main(argv: list[str] | None = None, *, runner: Runner = run_process, measure: Callable = measure_pdf,
         write_lock: Callable = default_write_lock, environ: dict[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work = Path(args.work_root)
    build = Build(work, args, runner, measure, write_lock, dict(os.environ if environ is None else environ))
    build.result.mkdir(parents=True, exist_ok=True)
    if args.kind == "direct-tex":
        entry = PurePosixPath(args.entry or "")
        if not args.entry or entry.is_absolute() or ".." in entry.parts or entry.suffix != ".tex":
            build.diagnostics.append({"step": "arguments", "code": "RK_CONTAINER_ENTRY_INVALID", "severity": "error",
                                      "message": "--entry must be a relative .tex path inside the source"})
            build.write_manifest("failed", "arguments")
            return 2
    try:
        build.verify_inputs()
        pdf = build.pipeline() if args.kind == "pipeline" else build.direct_tex()
        build.finish_pdf(pdf)
    except StepFailed as exc:
        _clear_to_logs(build.result)
        build.write_manifest("failed", exc.step)
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code if exc.exit_code in (2, 3, 4, 5) else 4
    except Exception as exc:  # noqa: BLE001 -- always return a manifest to the host
        _clear_to_logs(build.result)
        build.diagnostics.append({"step": "internal", "code": "RK_CONTAINER_INTERNAL", "severity": "error", "message": repr(exc)[:500]})
        build.write_manifest("failed", "internal")
        return 70
    build.write_manifest("passed", None)
    print(f"PASS: {build.record['pdf']['path']} ({build.record['pdf']['pages']} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
