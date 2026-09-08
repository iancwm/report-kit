"""The stable ReportKit command-line facade."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from .config import CONFIG_NAME, load_publication_config, resolve_identity
from .context import build_context
from .diagnostics import inspect_log, load_allowlist, load_maps
from .registry import COMMANDS

PACKAGE_ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = PYTHON_ROOT.parent
PIPELINE_ROOT = REPO_ROOT / "publication_pipeline"
DEFAULT_SOURCE_ROOT = PIPELINE_ROOT / "example_publication"


def _json_or_print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif isinstance(payload, str):
        print(payload)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _source_root(args: argparse.Namespace) -> Path:
    return Path(args.source_root).resolve() if args.source_root else DEFAULT_SOURCE_ROOT.resolve()


def _output_root(args: argparse.Namespace, source_root: Path) -> Path:
    return Path(args.output_root).resolve() if args.output_root else source_root / "build"


def _add_publication_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-root", help="consumer publication project")
    parser.add_argument("--output-root", help="where publication build artefacts live")
    parser.add_argument("--profile", default=None, help="publication config profile (for example, release)")


def _run_doctor(args: argparse.Namespace) -> int:
    command = [sys.executable, str(REPO_ROOT / "python_scripts" / "reportkit_doctor.py")]
    if args.require:
        command += ["--require", args.require]
    proc = subprocess.run(command, text=True, capture_output=True)
    if args.json:
        _json_or_print({"passed": proc.returncode == 0, "output": proc.stdout, "error": proc.stderr}, True)
    else:
        print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def _run_check(args: argparse.Namespace) -> int:
    root = _source_root(args)
    module = _load_module("reportkit_publication_validation", PIPELINE_ROOT / "scripts" / "publication_validation.py")
    result = module.validate_publication(root)
    payload = {
        "passed": result.ok,
        "errors": result.errors,
        "manuscript_files": result.manuscript_files,
        "visuals": result.slugs,
        "labels": result.labels,
    }
    if args.json:
        _json_or_print(payload, True)
    elif result.ok:
        print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.labels)} labels)")
    else:
        print("FAIL: publication validation", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
    return 0 if result.ok else 1


def _run_build(args: argparse.Namespace) -> int:
    command = [sys.executable, str(PIPELINE_ROOT / "scripts" / "publication_build.py"), "--mode", args.mode]
    for name in ("source_root", "output_root", "profile", "engine", "title", "author", "version", "cover"):
        value = getattr(args, name, None)
        if value:
            command += [f"--{name.replace('_', '-')}", str(value)]
    section = args.section or args.chapter
    if section:
        command += ["--section", section]
    return subprocess.run(command).returncode


def _find_log(args: argparse.Namespace, source_root: Path) -> Path | None:
    if args.log:
        return Path(args.log).resolve()
    output = _output_root(args, source_root)
    candidates = [output / "combined" / "publication.log"]
    candidates.extend(sorted(output.glob("section-*/publication.log"), reverse=True))
    return next((path for path in candidates if path.is_file()), None)


def _run_diagnose(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    log = _find_log(args, source_root)
    if not log:
        print("FAIL: no publication.log found; pass a log path or build first", file=sys.stderr)
        return 1
    allowlist_path = Path(args.allowlist).resolve() if args.allowlist else source_root / "build-log-allowlist.json"
    if not allowlist_path.is_file():
        allowlist_path = REPO_ROOT / "publication_pipeline" / "config" / "build-log-allowlist.json"
    result = inspect_log(
        log.read_text(encoding="utf-8", errors="replace"),
        underfull_badness=args.underfull_badness,
        allowlist=load_allowlist(allowlist_path),
        maps=load_maps(log.parent),
    )
    result["log"] = str(log)
    if args.json:
        _json_or_print(result, True)
    else:
        if result["passed"]:
            print(f"PASS: {log} contains no actionable diagnostics")
        else:
            print(f"FAIL: {log} contains actionable diagnostics", file=sys.stderr)
            for issue in result["issues"]:
                location = issue.get("file") or "unknown source"
                if issue.get("line"):
                    location += f":{issue['line']}"
                print(f"- {location} [{issue['type']} / {issue['owner']}]: {issue['message']}", file=sys.stderr)
    return 0 if result["passed"] else 1


def _find_pdf(build_dir: Path) -> Path | None:
    report = build_dir / "build-report.json"
    if report.is_file():
        try:
            value = json.loads(report.read_text(encoding="utf-8"))
            if value.get("pdf"):
                candidate = build_dir / value["pdf"]
                if candidate.is_file():
                    return candidate
        except json.JSONDecodeError:
            pass
    return next((path for path in sorted(build_dir.glob("*.pdf")) if path.name != "publication-template.pdf"), None)


def _run_inspect(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    pdf = Path(args.pdf).resolve() if args.pdf else _find_pdf(_output_root(args, source_root) / "combined")
    if not pdf or not pdf.is_file():
        print("FAIL: no PDF found; pass a PDF path or build first", file=sys.stderr)
        return 1
    module = _load_module("reportkit_inspect_pdf", PIPELINE_ROOT / "scripts" / "inspect_pdf.py")
    result = module.inspect(pdf)
    if args.json:
        _json_or_print(result, True)
    elif result["passed"]:
        print(f"PASS: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
    else:
        print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box", file=sys.stderr)
    return 0 if result["passed"] else 1


def _run_package(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    build_dir = Path(args.build_dir).resolve() if args.build_dir else _output_root(args, source_root) / "combined"
    report_path = build_dir / "build-report.json"
    if not report_path.is_file():
        print(f"FAIL: missing combined build manifest: {report_path}", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        print("FAIL: package requires a passing combined build", file=sys.stderr)
        return 1
    pdf = _find_pdf(build_dir)
    if not pdf:
        print("FAIL: passing build has no PDF", file=sys.stderr)
        return 1
    destination = Path(args.destination).resolve() if args.destination else source_root / "output"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in (pdf, report_path, build_dir / "reportkit.lock", source_root / "reportkit.lock"):
        if path.is_file():
            target = destination / path.name
            shutil.copy2(path, target)
            copied.append(str(target))
    pages = build_dir / "pages"
    if pages.is_dir():
        target = destination / "pages"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(pages, target)
        copied.append(str(target))
    payload = {"passed": True, "destination": str(destination), "files": copied}
    if args.json:
        _json_or_print(payload, True)
    else:
        print(f"PASS: packaged release in {destination}")
        for path in copied:
            print(f"- {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reportkit", description="Deterministic ReportKit publication engine")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="delegate environment checks to reportkit_doctor.py")
    doctor.add_argument("--require", choices=("full-build",))
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_run_doctor)

    context = sub.add_parser("context", help="generate the capability registry from templates and CLI")
    _add_publication_paths(context)
    context.add_argument("--json", action="store_true")
    context.set_defaults(handler=lambda args: (_json_or_print(build_context(REPO_ROOT, _source_root(args), args.profile), True) or 0))

    check = sub.add_parser("check", help="delegate manuscript validation to publication_validation.py")
    _add_publication_paths(check)
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_run_check)

    build = sub.add_parser("build", help="delegate compilation to publication_build.py")
    _add_publication_paths(build)
    build.add_argument("--mode", choices=("combined", "section", "sections"), default="combined")
    build.add_argument("--section")
    build.add_argument("--chapter", help="compatibility alias for --section")
    build.add_argument("--engine")
    build.add_argument("--title")
    build.add_argument("--author")
    build.add_argument("--version")
    build.add_argument("--cover")
    build.set_defaults(handler=_run_build)

    diagnose = sub.add_parser("diagnose", help="parse a TeX log into source-aware diagnostics")
    _add_publication_paths(diagnose)
    diagnose.add_argument("log", nargs="?")
    diagnose.add_argument("--allowlist")
    diagnose.add_argument("--underfull-badness", type=int, default=4000)
    diagnose.add_argument("--json", action="store_true")
    diagnose.set_defaults(handler=_run_diagnose)

    inspect = sub.add_parser("inspect", help="delegate PDF geometry and metadata checks to inspect_pdf.py")
    _add_publication_paths(inspect)
    inspect.add_argument("pdf", nargs="?")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(handler=_run_inspect)

    package = sub.add_parser("package", help="assemble a passing combined build into output/")
    _add_publication_paths(package)
    package.add_argument("--build-dir")
    package.add_argument("--destination")
    package.add_argument("--json", action="store_true")
    package.set_defaults(handler=_run_package)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
