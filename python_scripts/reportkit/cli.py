"""Unified ReportKit command-line facade."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType

from .config import CONFIG_NAME, load_publication_config, resolve_settings
from .context import build_context
from .diagnostics import main as diagnostics_main
from .authoring import validate_authoring
from .analysis import analyse_history

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = REPO_ROOT / "publication_pipeline" / "example_publication"


def _module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _source_root(value: str | None) -> Path:
    return Path(value).resolve() if value else DEFAULT_SOURCE_ROOT.resolve()


def _output_root(source: Path, explicit: str | None, profile: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        directory = resolve_settings(load_publication_config(source / CONFIG_NAME), profile)["output"].get("directory")
    except (OSError, ValueError):
        directory = None
    return (source / str(directory)).resolve() if directory else source / "build"


def _build_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        mode=args.mode,
        section=args.section,
        workers=args.workers,
        source_root=str(_source_root(args.source_root)),
        output_root=args.output_root,
        version=args.version,
        title=args.title,
        author=args.author,
        cover=args.cover,
        profile=args.profile,
        engine=args.engine,
    )


def _run_doctor(args: argparse.Namespace) -> int:
    doctor = _module("reportkit_doctor", REPO_ROOT / "python_scripts" / "reportkit_doctor.py")
    original = sys.argv
    try:
        sys.argv = ["reportkit doctor"] + (["--require", args.require] if args.require else [])
        return doctor.main()
    finally:
        sys.argv = original


def _run_check(args: argparse.Namespace) -> int:
    validation = _module("publication_validation", REPO_ROOT / "publication_pipeline" / "scripts" / "publication_validation.py")
    root = _source_root(args.source_root)
    result = validation.validate_publication(root)
    authoring = validate_authoring(root)
    errors = result.errors + authoring.errors
    payload = {"passed": not errors, "manuscript_files": result.manuscript_files, "visuals": result.slugs, "labels": result.labels, "sources": authoring.sources, "chapters": authoring.chapters, "links": authoring.links, "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif not errors:
        print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.labels)} labels)")
    else:
        print("FAIL: publication validation", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    return 0 if not errors else 1


def _run_build(args: argparse.Namespace) -> int:
    build_module = _module("publication_build", REPO_ROOT / "publication_pipeline" / "scripts" / "publication_build.py")
    if args.mode != "sections":
        result = build_module.build(_build_args(args))
    else:
        root = _source_root(args.source_root)
        result = 0
        for entry in build_module.order_entries(root):
            if entry.startswith("00-"):
                continue
            section_args = _build_args(args)
            section_args.mode = "section"
            section_args.section = entry
            result |= build_module.build(section_args)
    if args.json:
        source = _source_root(args.source_root)
        output_root = _output_root(source, args.output_root, args.profile)
        report = output_root / "combined" / "build-report.json"
        if report.is_file():
            print(report.read_text(encoding="utf-8"))
    return result


def _run_inspect(args: argparse.Namespace) -> int:
    inspect_module = _module("inspect_pdf", REPO_ROOT / "publication_pipeline" / "scripts" / "inspect_pdf.py")
    pdf = Path(args.pdf) if args.pdf else None
    if pdf is None:
        source = _source_root(args.source_root)
        candidates = sorted((source / "build" / "combined").glob("*.pdf"))
        if not candidates:
            print("inspect: pass a PDF or build the combined publication first", file=sys.stderr)
            return 1
        pdf = candidates[0]
    result = inspect_module.inspect(pdf)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
    return 0 if result["passed"] else 1


def _run_package(args: argparse.Namespace) -> int:
    source = _source_root(args.source_root)
    build_root = _output_root(source, args.output_root)
    combined = build_root / "combined"
    report_path = combined / "build-report.json"
    if not report_path.is_file():
        print(f"package: missing combined build report: {report_path}", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        print("package: combined build is not passing", file=sys.stderr)
        return 1
    pdfs = sorted(combined.glob("*.pdf"))
    if not pdfs:
        print(f"package: no PDF in {combined}", file=sys.stderr)
        return 1
    release = Path(args.release_root).resolve() if args.release_root else build_root.parent / "output"
    release.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdfs[0], release / pdfs[0].name)
    shutil.copy2(report_path, release / "build-report.json")
    shutil.copy2(report_path, release / "manifest.json")
    lock = source / "reportkit.lock"
    if lock.is_file():
        shutil.copy2(lock, release / lock.name)
    pages = release / "pages"
    if pages.exists():
        shutil.rmtree(pages)
    shutil.copytree(combined / "pages", pages)
    payload = {"passed": True, "directory": str(release), "pdf": pdfs[0].name, "manifest": "manifest.json", "build_report": "build-report.json", "pages": "pages"}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"PASS: package assembled at {release}")
    return 0


def _run_analysis(args: argparse.Namespace) -> int:
    history = Path(args.history_dir).resolve() if args.history_dir else _source_root(args.source_root) / "build" / "history"
    result = analyse_history(history)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ReportKit history: {result['build_count']} builds, {len(result['recurring'])} recurring diagnostics")
        for item in result["recurring"]:
            print(f"- {item['type']}: {item['occurrences']} occurrences across {item['builds']} builds")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reportkit", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="delegate to the environment doctor")
    doctor.add_argument("--require", choices=("full-build",))
    doctor.set_defaults(handler=_run_doctor)

    context = sub.add_parser("context", help="generate the source-derived component registry")
    context.add_argument("--source-root", help="consumer publication project")
    context.add_argument("--profile")
    context.add_argument("--json", action="store_true")
    context.set_defaults(handler=lambda args: _context_command(args))

    check = sub.add_parser("check", help="delegate to static publication validation")
    check.add_argument("--source-root", help="consumer publication project")
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_run_check)

    build = sub.add_parser("build", help="delegate to the Pandoc and TeX publication build")
    build.add_argument("--mode", choices=("section", "combined", "sections"), default="combined")
    build.add_argument("--section")
    build.add_argument("--workers", type=int, default=1)
    build.add_argument("--source-root")
    build.add_argument("--output-root")
    build.add_argument("--profile")
    build.add_argument("--engine")
    build.add_argument("--version")
    build.add_argument("--title")
    build.add_argument("--author")
    build.add_argument("--cover")
    build.add_argument("--json", action="store_true")
    build.set_defaults(handler=_run_build)

    diagnose = sub.add_parser("diagnose", help="parse a TeX build log into structured diagnostics")
    diagnose.add_argument("log", nargs="?", type=Path)
    diagnose.add_argument("--source-root", type=Path)
    diagnose.add_argument("--build-dir", type=Path)
    diagnose.add_argument("--allowlist", type=Path)
    diagnose.add_argument("--underfull-badness", type=int, default=4000)
    diagnose.add_argument("--json", action="store_true")
    diagnose.set_defaults(handler=lambda args: _diagnose_command(args))

    inspect = sub.add_parser("inspect", help="delegate to PyMuPDF PDF inspection")
    inspect.add_argument("pdf", type=Path, nargs="?")
    inspect.add_argument("--source-root")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(handler=_run_inspect)

    package = sub.add_parser("package", help="assemble a passing combined build into a release directory")
    package.add_argument("--source-root")
    package.add_argument("--output-root")
    package.add_argument("--release-root")
    package.add_argument("--json", action="store_true")
    package.set_defaults(handler=_run_package)

    history = sub.add_parser("analyse-history", help="summarize recurring diagnostics in build history")
    history.add_argument("--source-root")
    history.add_argument("--history-dir")
    history.add_argument("--json", action="store_true")
    history.set_defaults(handler=_run_analysis)
    return parser


def _context_command(args: argparse.Namespace) -> int:
    try:
        result = build_context(REPO_ROOT, _source_root(args.source_root) if args.source_root else None, args.profile)
    except (OSError, ValueError) as exc:
        print(f"context: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ReportKit {result['version']} ({result['document']['engine']})")
        print(f"figures: {len(result['components']['figures'])}; callouts: {len(result['components']['callouts']['names'])}; charts: {len(result['components']['charts'])}")
    return 0


def _diagnose_command(args: argparse.Namespace) -> int:
    log = args.log
    if log is None:
        source = _source_root(str(args.source_root) if args.source_root else None)
        log = _output_root(source, None) / "combined" / "publication.log"
    argv = [str(log), "--underfull-badness", str(args.underfull_badness)]
    if args.json:
        argv += ["--json"]
    if args.source_root:
        argv += ["--source-root", str(args.source_root)]
    if args.build_dir:
        argv += ["--build-dir", str(args.build_dir)]
    if args.allowlist:
        argv += ["--allowlist", str(args.allowlist)]
    return diagnostics_main(argv)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)
